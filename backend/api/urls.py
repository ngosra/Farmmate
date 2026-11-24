from django.urls import include, path
from rest_framework.routers import DefaultRouter

from ai.views import AssistantView
from api.auth import (
    LoginView,
    LogoutView,
    MeView,
    PasswordChangeView,
    PasswordResetConfirmView,
    PasswordResetRequestView,
    RefreshView,
    RegisterView,
)
from api.health import HealthView
from certification.views import (
    CertificationViewSet,
    ComplianceItemViewSet,
    CorrectiveActionViewSet,
    StandardViewSet,
)
from crops.views import CropViewSet, PlantingViewSet
from farmers.views import DeclarationViewSet, FarmerViewSet, IdentificationViewSet
from farms.views import FarmDocumentViewSet, FarmViewSet, FieldViewSet, LandUseViewSet
from inspections.views import InspectionCheckViewSet, InspectionViewSet
from inventory.views import (
    InputApprovalViewSet,
    InputProductViewSet,
    StockMovementViewSet,
    SupplierViewSet,
)
from ndvi.views import ObservationViewSet
from organizations.views import (
    AuditLogView,
    MemberViewSet,
    OrganizationDetailView,
    OrganizationListView,
)
from production.views import ActivityViewSet, HarvestViewSet, StorageViewSet
from reports.views import DashboardView, ReportIndexView, ReportView
from traceability.views import BatchViewSet, TraceView
from training.views import AttendanceViewSet, TrainingMaterialViewSet, TrainingSessionViewSet

router = DefaultRouter()
router.register("members", MemberViewSet, basename="member")
router.register("farmers", FarmerViewSet, basename="farmer")
router.register("declarations", DeclarationViewSet, basename="declaration")
router.register("identifications", IdentificationViewSet, basename="identification")
router.register("farms", FarmViewSet, basename="farm")
router.register("fields", FieldViewSet, basename="field")
router.register("land-use", LandUseViewSet, basename="land-use")
router.register("farm-documents", FarmDocumentViewSet, basename="farm-document")
router.register("crops", CropViewSet, basename="crop")
router.register("plantings", PlantingViewSet, basename="planting")
router.register("activities", ActivityViewSet, basename="activity")
router.register("harvests", HarvestViewSet, basename="harvest")
router.register("storage", StorageViewSet, basename="storage")
router.register("suppliers", SupplierViewSet, basename="supplier")
router.register("inputs", InputProductViewSet, basename="input")
router.register("input-approvals", InputApprovalViewSet, basename="input-approval")
router.register("stock-movements", StockMovementViewSet, basename="stock-movement")
router.register("standards", StandardViewSet, basename="standard")
router.register("certifications", CertificationViewSet, basename="certification")
router.register("compliance-items", ComplianceItemViewSet, basename="compliance-item")
router.register("corrective-actions", CorrectiveActionViewSet, basename="corrective-action")
router.register("inspections", InspectionViewSet, basename="inspection")
router.register("inspection-checks", InspectionCheckViewSet, basename="inspection-check")
router.register("training-sessions", TrainingSessionViewSet, basename="training-session")
router.register("training-materials", TrainingMaterialViewSet, basename="training-material")
router.register("attendance", AttendanceViewSet, basename="attendance")
router.register("batches", BatchViewSet, basename="batch")
router.register("observations", ObservationViewSet, basename="observation")

urlpatterns = [
    path("health/", HealthView.as_view(), name="health"),
    path("auth/login/", LoginView.as_view(), name="auth-login"),
    path("auth/register/", RegisterView.as_view(), name="auth-register"),
    path("auth/refresh/", RefreshView.as_view(), name="auth-refresh"),
    path("auth/logout/", LogoutView.as_view(), name="auth-logout"),
    path("auth/me/", MeView.as_view(), name="auth-me"),
    path("auth/password/", PasswordChangeView.as_view(), name="auth-password"),
    path("auth/password-reset/", PasswordResetRequestView.as_view(), name="auth-password-reset"),
    path(
        "auth/password-reset/confirm/",
        PasswordResetConfirmView.as_view(),
        name="auth-password-reset-confirm",
    ),
    path("organizations/", OrganizationListView.as_view(), name="organization-list"),
    path("organizations/<uuid:pk>/", OrganizationDetailView.as_view(), name="organization-detail"),
    path("dashboard/", DashboardView.as_view(), name="dashboard"),
    path("reports/", ReportIndexView.as_view(), name="report-index"),
    path("reports/<slug:kind>/", ReportView.as_view(), name="report-detail"),
    path("trace/<str:public_code>/", TraceView.as_view(), name="trace"),
    path("assistant/", AssistantView.as_view(), name="assistant"),
    path("audit/", AuditLogView.as_view(), name="audit"),
    path("", include(router.urls)),
]
