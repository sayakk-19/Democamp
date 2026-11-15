"""Shared input limits for the existing registration form."""

from decimal import Decimal, InvalidOperation

from django.core.validators import (
    MaxLengthValidator,
    MaxValueValidator,
    MinLengthValidator,
    MinValueValidator,
)

from .models import Register


RANGE_ERROR_MESSAGE = "You exceeded the input field range"
RANGE_ERROR_CODES = {"max_length", "min_length", "max_value", "min_value"}
REGISTRATION_FIELDS = ("name", "email", "phno", "pwd", "reenter_pwd", "age", "position")


def registration_limits():
    """Return model limits plus the form's existing stricter input limits."""
    limits = {}
    validator_keys = (
        (MaxLengthValidator, "max_length", min),
        (MinLengthValidator, "min_length", max),
        (MaxValueValidator, "max_value", min),
        (MinValueValidator, "min_value", max),
    )
    for name in REGISTRATION_FIELDS:
        field = Register._meta.get_field(name)
        field_limits = {}
        if field.max_length is not None:
            field_limits["max_length"] = field.max_length
        for validator in field.validators:
            for validator_type, key, stricter in validator_keys:
                if isinstance(validator, validator_type):
                    limit = validator.limit_value
                    limit = limit() if callable(limit) else limit
                    field_limits[key] = stricter(field_limits.get(key, limit), limit)
        limits[name] = field_limits

    limits["name"]["max_length"] = min(limits["name"].get("max_length", 15), 15)
    limits["phno"]["min_length"] = max(limits["phno"].get("min_length", 10), 10)
    limits["phno"]["max_length"] = min(limits["phno"].get("max_length", 10), 10)
    for name in ("pwd", "reenter_pwd"):
        limits[name]["min_length"] = max(limits[name].get("min_length", 8), 8)
    return limits


def range_errors(data):
    """Return all out-of-range raw inputs without querying account records."""
    errors = {}
    for name, limits in registration_limits().items():
        value = data.get(name)
        # Missing values remain subject to the existing required/format checks.
        if value is None or value == "":
            continue
        text = str(value)
        if (
            "max_length" in limits and len(text) > limits["max_length"]
            or "min_length" in limits and len(text) < limits["min_length"]
        ):
            errors[name] = RANGE_ERROR_MESSAGE
            continue
        if "min_value" not in limits and "max_value" not in limits:
            continue
        try:
            number = Decimal(text)
        except (InvalidOperation, TypeError, ValueError):
            # The model will report invalid numbers with its normal message.
            continue
        if not number.is_finite():
            continue
        if (
            "min_value" in limits and number < Decimal(str(limits["min_value"]))
            or "max_value" in limits and number > Decimal(str(limits["max_value"]))
        ):
            errors[name] = RANGE_ERROR_MESSAGE
    return errors
