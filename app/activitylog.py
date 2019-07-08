__author__ = 'kodigray'
"""
from django.dispatch import receiver
from django.db.models import signals
from eventlog.models import log


@receiver(signals.user_logged_in)
def handle_user_logged_in(sender, **kwargs):
    log(
        user = kwargs.get("user"),
        action = "User Logged In",
        extra = {}
    )


@receiver(signals.password_changed)
def handle_password_changed(sender, **kwargs):
    log(
        user = kwargs.get("user"),
        action = "password changed",
        extra = {}
    )


@receiver(signals.user_login_attempt)
def handle_user_login_attempt(sender, **kwargs):
    log(
        user = None,
        action = "login attempted",
        extra = {
            "username": kwargs.get("username"),
            "result": kwargs.get("result")
        }
    )


@receiver(signals.user_sign_up_attempt)
def handle_user_sign_up_attempt(sender, **kwargs):
    log(
        user = None,
        action = "signup attempted",
        extra = {
            "username": kwargs.get("username"),
            "email": kwargs.get("email"),
            "result": kwargs.get("result")
        }
    )

@receiver(signals.user_edit_profile)
def handle_user_edit_profile(sender, **kwargs):
    log(
        user = kwargs.get("user"),
        action = "user edited profile",
        extra = {
            "ID": kwargs.get("id")
        }
    )


@receiver(signals.user_signed_up)
def handle_user_signed_up(sender, **kwargs):
    log(
        user = kwargs.get("user"),
        action = "user signed up",
        extra = {
            "ID": kwargs.get("id"),
            "email": kwargs.get("email")
        }
    )


@receiver(signals.doc_deleted_prescription)
def handle_doc_deleted_prescription(sender, **kwargs):
    log(
        user = kwargs.get("user"),
        action = "deleted a prescription",
        extra = {
            "ID": kwargs.get("id")
        }
    )


@receiver(signals.doc_edits_prescription)
def handle_doc_edits_prescription(sender, **kwargs):
    log(
        user = kwargs.get("user"),
        action = "edited a prescription",
        extra = {
            "ID": kwargs.get("id")
        }
    )

@receiver(signals.doc_adds_prescription)
def handle_doc_adds_prescription(sender, **kwargs):
    log(
        user = kwargs.get("user"),
        action = "added a prescription",
        extra = {
            "ID": kwargs.get("id")
        }
    )


@receiver(signals.add_appointment)
def handle_add_appointment(sender, **kwargs):
    log(
        user = kwargs.get("user"),
        action = "added an appointment",
        extra = {
            "ID": kwargs.get("id")
        }
    )

@receiver(signals.edits_appointment)
def handle_edits_appointment(sender, **kwargs):
    log(
        user = kwargs.get("user"),
        action = "edited an appointment",
        extra = {
            "ID": kwargs.get("id")
        }
    )


@receiver(signals.deleted_appointment)
def handle_deleted_appointment(sender, **kwargs):
    log(
        user = kwargs.get("user"),
        action = "deleted an appointment",
        extra = {
            "ID": kwargs.get("id")
        }
    )

@receiver(signals.edits_patient_profile)
def handle_edits_patient_profile(sender, **kwargs):
    log(
        user = kwargs.get("user"),
        action = "edited patients profile",
        extra = {
            "ID": kwargs.get("id")
        }
    )


@receiver(signals.exports_patient_information)
def handle_exports_patient_information(sender, **kwargs):
    log(
        user = kwargs.get("user"),
        action = "exported information of a patient",
        extra = {
            "ID": kwargs.get("id")
        }
    )

@receiver(signals.doc_releases_test_results)
def handle_doc_releases_test_results(sender, **kwargs):
    log(
        user = kwargs.get("user"),
        action = "released test results of patient",
        extra = {
            "ID": kwargs.get("id")
        }
    )


@receiver(signals.hospital_transferred_patient)
def handle_hospital_transferred_patient(sender, **kwargs):
    log(
        user = kwargs.get("user"),
        action = "patient was transferred from hospital",
        extra = {
            "ID": kwargs.get("id")
        }
    )

@receiver(signals.extended_stay_for_patient)
def handle_extended_stay_for_patient(sender, **kwargs):
    log(
        user = kwargs.get("user"),
        action = "Patient was put on extended stay by doctor",
        extra = {
            "ID": kwargs.get("id")
        }
    )


@receiver(signals.doc_discharges_patient)
def handle_doc_discharges_patient(sender, **kwargs):
    log(
        user = kwargs.get("user"),
        action = "patient was discharged by doctor",
        extra = {
            "ID": kwargs.get("id")
        }
    )

@receiver(signals.doc_uploads_update)
def handle_doc_uploads_update(sender, **kwargs):
    log(
        user = kwargs.get("user"),
        action = "doctor uploaded an update to patient profile",
        extra = {
            "ID": kwargs.get("id")
        }
    )
"""