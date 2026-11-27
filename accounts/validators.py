import re

from django.core.exceptions import ValidationError

PHONE_PATTERN = re.compile(r"^\+?[0-9][0-9\s().-]{5,28}[0-9]$")


def validate_phone(value):
    """Accept digits with optional +, spaces, dashes, dots and parentheses."""
    value = (value or "").strip()
    if value and not PHONE_PATTERN.match(value):
        raise ValidationError(
            "Enter a valid phone number (digits, spaces, +, -, ( ) only)."
        )
    return value