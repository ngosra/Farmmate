from celery import shared_task

from certification.services import create_expiry_reminders


@shared_task
def flag_expiring_certifications():
    return create_expiry_reminders()
