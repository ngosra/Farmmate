from django.contrib.auth.password_validation import validate_password
from django.db import transaction
from rest_framework.exceptions import ValidationError

from accounts.models import User
from organizations.models import Farmer, Membership


def create_member(organization, data):
    email = data["email"].strip().lower()
    if User.objects.filter(email=email).exists():
        raise ValidationError({"email": "An account with this email already exists."})
    try:
        validate_password(data["password"])
    except Exception as exc:
        raise ValidationError({"password": list(getattr(exc, "messages", [str(exc)]))}) from exc
    role = data["role"]
    farmer_id = (data.get("farmer_id") or "").strip().upper() or None
    if role == Membership.Role.FARMER and not farmer_id:
        raise ValidationError({"farmer_id": "A FarmerID is required for a farmer login."})
    if farmer_id and User.objects.filter(farmer_id=farmer_id).exists():
        raise ValidationError({"farmer_id": "This FarmerID is already in use."})
    if farmer_id and Farmer.objects.filter(organization=organization, farmer_id=farmer_id).exists():
        raise ValidationError({"farmer_id": "This FarmerID is already used in the organization."})
    display_name = (data.get("display_name") or "").strip()
    if not display_name:
        display_name = f"{data.get('first_name', '')} {data.get('last_name', '')}".strip() or email
    with transaction.atomic():
        user = User.objects.create_user(
            email=email,
            password=data["password"],
            first_name=data.get("first_name", ""),
            last_name=data.get("last_name", ""),
            phone=data.get("phone", ""),
            farmer_id=farmer_id,
        )
        membership = Membership.objects.create(user=user, organization=organization, role=role)
        if role == Membership.Role.FARMER:
            Farmer.objects.create(
                organization=organization,
                user=user,
                farmer_id=farmer_id,
                display_name=display_name,
                phone=data.get("phone", ""),
                email=email,
            )
    return membership
