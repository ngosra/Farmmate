"""Starter certification checklists.

These prompts help a cooperative prepare records. They are not the legal text of
EU organic rules, the EU Deforestation Regulation, or the USDA National Organic
Program, and completing them does not certify a farm.
"""

CATALOG = [
    {
        "code": "EU_ORGANIC",
        "name": "EU organic preparation",
        "authority": "European Union",
        "summary": (
            "Starter checklist for preparing EU organic records. "
            "It is not the regulation and it is not a certificate."
        ),
        "requirements": [
            {
                "code": "LAND_HISTORY",
                "title": "Three-year land-use history",
                "description": "Land-use records for this year and the two previous years.",
                "weight": 3,
            },
            {
                "code": "BOUNDARIES",
                "title": "Field boundaries recorded",
                "description": "Field boundaries are stored so the area can be calculated.",
                "weight": 2,
            },
            {
                "code": "INPUTS",
                "title": "Inputs identified",
                "description": "Inputs in use are listed and checked against the standard.",
                "weight": 3,
            },
            {
                "code": "SEED_SOURCE",
                "title": "Planting material source",
                "description": "The source of seed or planting material is recorded.",
                "weight": 1,
            },
            {
                "code": "TRAINING",
                "title": "Farmer training record",
                "description": "The farmer has at least one recorded training attendance.",
                "weight": 1,
            },
            {
                "code": "HARVESTS",
                "title": "Harvest quantities recorded",
                "description": "Harvest dates and quantities are recorded for the season.",
                "weight": 2,
            },
        ],
    },
    {
        "code": "EUDR",
        "name": "EUDR preparation",
        "authority": "European Union",
        "summary": (
            "Starter checklist for EU Deforestation Regulation preparation. "
            "It does not determine legality or deforestation-free status."
        ),
        "requirements": [
            {
                "code": "GEOLOCATION",
                "title": "Plot geolocation",
                "description": "Each plot has coordinates or a mapped boundary.",
                "weight": 3,
            },
            {
                "code": "LAND_USE",
                "title": "Land-use history",
                "description":
                    "Land-use history is available for the period the standard asks about.",
                "weight": 3,
            },
            {
                "code": "PRODUCER",
                "title": "Producer identification",
                "description": "The producer is identified on the farmer record.",
                "weight": 2,
            },
            {
                "code": "QUANTITY",
                "title": "Production quantity",
                "description": "Production quantities are recorded for the commodity.",
                "weight": 2,
            },
            {
                "code": "TRACE",
                "title": "Batch traceability",
                "description": "Product can be followed from harvest to a batch.",
                "weight": 2,
            },
        ],
    },
    {
        "code": "USDA_NOP",
        "name": "USDA NOP preparation",
        "authority": "USDA National Organic Program",
        "summary": (
            "Starter checklist for USDA National Organic Program preparation. "
            "It is not an organic system plan and it is not a certificate."
        ),
        "requirements": [
            {
                "code": "OSP",
                "title": "System plan declared",
                "description": "The farmer has declared how the farm is managed.",
                "weight": 3,
            },
            {
                "code": "MATERIALS",
                "title": "Materials reviewed",
                "description": "Inputs are reviewed against the applicable materials list.",
                "weight": 3,
            },
            {
                "code": "BOUNDARIES",
                "title": "Boundaries described",
                "description": "Field boundaries, and buffers where relevant, are described.",
                "weight": 2,
            },
            {
                "code": "AUDIT_TRAIL",
                "title": "Harvest audit trail",
                "description": "Harvests can be traced to a field and a date.",
                "weight": 2,
            },
            {
                "code": "INSPECTION",
                "title": "Inspection recorded",
                "description": "An inspection has been scheduled or completed for this farm.",
                "weight": 2,
            },
        ],
    },
]


def sync_catalog(standard_model, requirement_model):
    for entry in CATALOG:
        standard, _created = standard_model.objects.update_or_create(
            code=entry["code"],
            defaults={
                "name": entry["name"],
                "authority": entry["authority"],
                "summary": entry["summary"],
                "organization": None,
            },
        )
        for requirement in entry["requirements"]:
            requirement_model.objects.update_or_create(
                standard=standard,
                code=requirement["code"],
                defaults={
                    "title": requirement["title"],
                    "description": requirement["description"],
                    "weight": requirement["weight"],
                },
            )
