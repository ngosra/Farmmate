def record(request, action, instance, summary, organization=None):
    from organizations.models import AuditLog

    member = getattr(request, "_fm_membership", None)
    org = organization or getattr(instance, "organization", None)
    if org is None and member is not None:
        org = member.organization
    actor = request.user if getattr(request.user, "is_authenticated", False) else None
    AuditLog.objects.create(
        organization=org,
        actor=actor,
        action=action,
        entity_type=instance.__class__.__name__,
        entity_id=str(getattr(instance, "pk", "")),
        summary=summary[:240],
    )
