from rest_framework.exceptions import NotFound, ValidationError
from rest_framework.response import Response
from rest_framework.views import APIView

from api.access import require_membership
from reports.builders import (
    batch_for,
    compliance_rows,
    csv_response,
    farm_rows,
    inventory_rows,
    production_rows,
    trace_rows,
    yield_report,
)
from reports.dashboard import build_dashboard

REPORTS = {
    "farms": ("farm-report.csv", farm_rows),
    "production": ("production-report.csv", production_rows),
    "yield": ("yield-report.csv", yield_report),
    "inventory": ("inventory-report.csv", inventory_rows),
    "compliance": ("compliance-report.csv", compliance_rows),
}


class DashboardView(APIView):
    def get(self, request):
        member = require_membership(request)
        return Response(build_dashboard(request.user, member))


class ReportView(APIView):
    def get(self, request, kind):
        member = require_membership(request)
        if kind == "traceability":
            batch = batch_for(member, request.query_params.get("batch"))
            if batch is None:
                raise NotFound("Batch was not found in your organization.")
            rows = trace_rows(batch)
        else:
            builder = REPORTS.get(kind)
            if builder is None:
                raise NotFound("Unknown report.")
            _filename, function = builder
            if kind == "inventory":
                rows = function(member)
            else:
                rows = function(request.user, member)
        if request.query_params.get("format") == "csv":
            filename = "traceability-report.csv" if kind == "traceability" else REPORTS[kind][0]
            return csv_response(filename, rows)
        return Response({"kind": kind, "rows": rows})


class ReportIndexView(APIView):
    def get(self, request):
        require_membership(request)
        return Response(
            {
                "reports": [
                    "farms",
                    "production",
                    "yield",
                    "inventory",
                    "compliance",
                    "traceability",
                ],
                "csv": "Add ?format=csv. Traceability also needs ?batch=<id>.",
            }
        )


_ = ValidationError
