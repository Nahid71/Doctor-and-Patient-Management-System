__author__ = 'harlanhaskins'
import re
from django.core import validators
from django.core.exceptions import ValidationError
from django.contrib.admin import models
from django.contrib.contenttypes.models import ContentType
from django.utils.text import get_text_list


def sanitize_phone(number):
    """
    Removes all non-digit characters from a string.
    Useful for storing phone numbers.
    """
    if not number:
        return None
    regex = re.compile(r'[^\d.]+')
    return regex.sub('', number)


def none_if_invalid(item):
    """
    Takes advantage of python's 'falsiness' check by
    turning 'falsy' data (like [], "", and 0) into None.
    :param item: The item for which to check falsiness.
    :return: None if the item is falsy, otherwise the item.
    """
    return item if bool(item) else None


def email_is_valid(email):
    """
    Wrapper for Django's email validator that returns a boolean
    instead of requiring a try/catch block.
    :param email: The email to validate
    :return: Whether or not the email conforms to RFC 2822.
    """
    try:
        validators.validate_email(email)
        return True
    except ValidationError:
        return False


def get_change_message(fields):
    """
    Create a change message for *fields* (a sequence of field names).
    """
    return 'Changed %s.' % get_text_list(fields, 'and')


def addition(request, obj):
    """
    Log that an object has been successfully added.
    """
    models.LogEntry.objects.log_action(
        user_id=request.user.pk,
        content_type_id=ContentType.objects.get_for_model(obj).pk,
        object_id=obj.pk,
        object_repr=repr(obj),
        action_flag=models.ADDITION
    )


def change(request, obj, message_or_fields):
    """
    Log that an object has been successfully changed.

    The argument *message_or_fields* must be a sequence of modified field names
    or a custom change message.
    """
    if isinstance(message_or_fields, str):
        message = message_or_fields
    else:
        message = get_change_message(message_or_fields)
    models.LogEntry.objects.log_action(
        user_id=request.user.pk,
        content_type_id=ContentType.objects.get_for_model(obj).pk,
        object_id=obj.pk,
        object_repr=repr(obj),
        action_flag=models.CHANGE,
        change_message=message
    )


def deletion(request, obj, object_repr=None):
    """
    Log that an object will be deleted.
    """
    models.LogEntry.objects.log_action(
        user_id=request.user.id,
        content_type_id=ContentType.objects.get_for_model(obj).pk,
        object_id=obj.pk,
        object_repr=object_repr or repr(obj),
        action_flag=models.DELETION
    )
