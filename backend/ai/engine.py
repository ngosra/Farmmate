import json
import re
import urllib.error
import urllib.request

from django.conf import settings

from certification.models import Certification, ComplianceItem
from certification.services import visible_certifications
from farms.land import missing_land_use_years
from farms.scope import scoped_farmers, scoped_farms, scoped_fields
from inventory.models import InputProduct
from inventory.services import on_hand
from ndvi.models import Observation
from production.services import yield_rows
from traceability.models import Batch
from traceability.services import balance

INTENTS = (
    ("ndvi", ("ndvi", "satellite", "vegetation")),
    ("compliance", ("complian", "certif", "missing", "gap", "evidence", "organic", "eudr", "nop")),
    ("yield", ("yield", "harvest", "production", "crop")),
    ("inventory", ("inventory", "stock", "fertilizer", "pesticide", "input")),
    ("trace", ("trace", "batch", "qr")),
    ("plan", ("plan", "next season", "recommend", "what should")),
    ("summary", ("summary", "overview", "status", "dashboard")),
)


def classify(question: str) -> list[str]:
    text = question.lower()
    found = [name for name, words in INTENTS if any(word in text for word in words)]
    return found or ["summary"]


def _statement(kind, text, sources=None):
    return {"kind": kind, "text": text, "sources": sources or []}


def _unknown_names(question, farms):
    known = {farm.name.lower() for farm in farms}
    unknown = []
    for name in re.findall(r'"([^"]+)"', question):
        if name.lower() not in known:
            unknown.append(name)
    return unknown


def _summary(farms, fields, farmers):
    return [
        _statement(
            "recorded",
            (
                f"There are {farmers.count()} farmers, {farms.count()} farms, "
                f"and {fields.count()} fields in the records you can see."
            ),
        )
    ]


def _compliance(user, membership):
    certifications = list(
        visible_certifications(user, membership).select_related("standard", "farmer")
    )
    if not certifications:
        return [
            _statement(
                "missing",
                "No certification checklist has been opened, so there is no readiness score.",
            )
        ]
    statements = []
    for certification in certifications:
        label = certification.farmer.display_name if certification.farmer_id else "the organization"
        statements.append(
            _statement(
                "recorded",
                (
                    f"{certification.standard.code} for {label} has official status "
                    f"{certification.get_status_display()}."
                ),
                [{"type": "Certification", "id": str(certification.id), "label":
                    certification.standard.code}],
            )
        )
    missing = ComplianceItem.objects.filter(
        certification__in=certifications,
        state=ComplianceItem.State.MISSING,
    ).select_related("requirement")
    missing_rows = list(missing[:8])
    if not missing_rows:
        statements.append(_statement("recorded", "No checklist items are marked missing."))
    for item in missing_rows:
        statements.append(
            _statement(
                "missing",
                f"Missing evidence: {item.requirement.title}.",
                [{"type": "ComplianceItem", "id": str(item.id), "label": item.requirement.title}],
            )
        )
    official = [row for row in certifications if row.status == Certification.Status.CERTIFIED]
    if not official:
        statements.append(
            _statement(
                "recorded",
                "None of these checklists has an official certified decision.",
            )
        )
    return statements


def _yields(fields):
    rows = yield_rows(fields)
    if not rows or all(row["quantity_kg"] == 0 for row in rows):
        return [_statement("missing",
            "No harvest quantities are recorded, so there is no yield to calculate.")]
    statements = []
    for row in rows:
        if row["quantity_kg"] == 0:
            continue
        if row["kg_per_hectare"] is None:
            text = (
                f"{row['farm_name']} / {row['field_name']} has {row['quantity_kg']} kg harvested. "
                "Kilograms per hectare were not calculated because the field has no area."
            )
        else:
            text = (
                f"{row['farm_name']} / {row['field_name']} has {row['quantity_kg']} kg harvested "
                f"on {row['area_hectares']} ha, which is {row['kg_per_hectare']} kg/ha."
            )
        statements.append(
            _statement(
                "calculated",
                text,
                [{"type": "Field", "id": row["field_id"], "label": row["field_name"]}],
            )
        )
    return statements


def _ndvi(fields):
    observations = list(
        Observation.objects.filter(field__in=fields).select_related("field").order_by("observed_on")
    )
    if not observations:
        return [
            _statement(
                "missing",
                "No NDVI observations are stored. Satellite data has not been retrieved.",
            )
        ]
    statements = []
    satellites = [row for row in observations if row.source == Observation.Source.SATELLITE]
    manuals = [row for row in observations if row.source == Observation.Source.MANUAL]
    if not satellites:
        statements.append(
            _statement(
                "recorded",
                "There are manual NDVI readings. There are no satellite observations.",
            )
        )
    for row in satellites[-5:]:
        statements.append(
            _statement(
                "recorded",
                (
                    f"Satellite NDVI for {row.field.name} on {row.observed_on} "
                    f"was {row.ndvi_mean} from {row.provider or 'the configured provider'}."
                ),
            )
        )
    for row in manuals[-5:]:
        statements.append(
            _statement(
                "recorded",
                (
                    f"Manual NDVI for {row.field.name} on {row.observed_on} "
                    f"was {row.ndvi_mean}."
                ),
            )
        )
    return statements


def _inventory(membership):
    products = list(InputProduct.objects.filter(organization=membership.organization))
    if not products:
        return [_statement("missing", "No agricultural inputs are recorded.")]
    statements = []
    for product in products[:8]:
        quantity = on_hand(product)
        statements.append(
            _statement(
                "calculated",
                f"{product.name} has {quantity} {product.unit} on hand.",
                [{"type": "InputProduct", "id": str(product.id), "label": product.name}],
            )
        )
        if product.reorder_level and quantity <= product.reorder_level:
            statements.append(
                _statement(
                    "recommendation",
                    (
                        f"{product.name} is at or below its reorder level of "
                        f"{product.reorder_level} {product.unit}."
                    ),
                )
            )
    return statements


def _trace(membership):
    batches = list(
        Batch.objects.filter(organization=membership.organization).order_by("-created_at")[:5]
    )
    if not batches:
        return [_statement("missing", "No traceability batches are recorded.")]
    statements = []
    for batch in batches:
        row = balance(batch)
        statements.append(
            _statement(
                "calculated",
                (
                    f"Batch {batch.code} ({batch.product_name}) sourced {row['sourced_kg']} kg "
                    f"and has {row['remaining_kg']} kg remaining."
                ),
                [{"type": "Batch", "id": str(batch.id), "label": batch.code}],
            )
        )
    return statements


def _plan(user, membership, fields):
    statements = _compliance(user, membership)
    statements.append(
        _statement(
            "recommendation",
            "Use the missing checklist items as the next season's record-keeping plan.",
        )
    )
    for field in fields:
        years = missing_land_use_years(field)
        if years:
            statements.append(
                _statement(
                    "missing",
                    f"{field.name} is missing land-use years: {', '.join(map(str, years))}.",
                    [{"type": "Field", "id": str(field.id), "label": field.name}],
                )
            )
    return statements


def narrate(question, statements):
    key = getattr(settings, "AI_API_KEY", "") or ""
    if not key:
        return None, "not_configured"
    base = (getattr(settings, "AI_API_BASE", "") or "https://api.openai.com/v1").rstrip("/")
    model = getattr(settings, "AI_MODEL", "") or "gpt-4o-mini"
    body = {
        "model": model,
        "temperature": 0,
        "messages": [
            {
                "role": "system",
                "content": (
                    "Summarize the supplied FarmMate statements for the signed-in user. "
                    "Use only those statements. Do not add farms, yields, inspections, "
                    "certificates, or satellite values. If a statement says data is missing, "
                    "say it is missing. Describe recommendations as recommendations."
                ),
            },
            {
                "role": "user",
                "content": json.dumps({"question": question, "statements": statements}),
            },
        ],
    }
    request = urllib.request.Request(
        f"{base}/chat/completions",
        data=json.dumps(body).encode("utf-8"),
        headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=20) as response:
            payload = json.loads(response.read().decode("utf-8"))
        text = payload["choices"][0]["message"]["content"]
    except (urllib.error.URLError, KeyError, TimeoutError, json.JSONDecodeError, TypeError):
        return None, "unavailable"
    return text, "generated"


def ask(user, membership, question: str) -> dict:
    farms = list(scoped_farms(user, membership))
    fields = list(scoped_fields(user, membership))
    farmers = scoped_farmers(user, membership)
    intents = classify(question)
    statements = []
    for name in _unknown_names(question, farms):
        statements.append(_statement("missing", f'No farm named "{name}" is recorded.'))
    builders = {
        "summary": lambda: _summary(farms, fields, farmers),
        "compliance": lambda: _compliance(user, membership),
        "yield": lambda: _yields(fields),
        "inventory": lambda: _inventory(membership),
        "trace": lambda: _trace(membership),
        "ndvi": lambda: _ndvi(fields),
        "plan": lambda: _plan(user, membership, fields),
    }
    for intent in intents:
        statements.extend(builders[intent]())
    joined = " ".join(row["text"] for row in statements)
    answer = joined or "There are no recorded facts for that question."
    narrative, narrative_status = narrate(question, statements)
    sources = []
    for row in statements:
        sources.extend(row["sources"])
    return {
        "question": question,
        "intents": intents,
        "answer": answer,
        "statements": statements,
        "sources": sources,
        "narrative": narrative,
        "narrative_status": narrative_status,
    }
