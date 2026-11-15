"""Session helpers for the store's existing approved account models."""

from .models import Register, player


ACCOUNT_MODELS = {"register": Register, "player": player}
ACCOUNT_SESSION_KEYS = ("store_account_type", "store_account_id")


def clear_store_account(request):
    for key in ACCOUNT_SESSION_KEYS:
        request.session.pop(key, None)
    request._store_account = None
    request._store_account_resolved = True


def start_store_session(request, kind, account):
    """Rotate the session key before recording a successful approved login."""
    request.session.cycle_key()
    request.session["store_account_type"] = kind
    request.session["store_account_id"] = account.pk
    request._store_account_resolved = False


def get_store_account(request):
    """Return display fields only, validating approval on each request."""
    if request is None:
        return None
    if getattr(request, "_store_account_resolved", False):
        return request._store_account

    kind = request.session.get("store_account_type")
    account_id = request.session.get("store_account_id")
    model = ACCOUNT_MODELS.get(kind)
    if model is None or not isinstance(account_id, int) or isinstance(account_id, bool):
        clear_store_account(request)
        return None

    display_fields = (
        ("name", "email", "phno", "age", "position")
        if kind == "register"
        else ("Name", "Email", "Phno", "Age", "Position")
    )
    account = model.objects.only("id", *display_fields).filter(pk=account_id, appr=1).first()
    if account is None:
        clear_store_account(request)
        return None

    if kind == "register":
        details = {
            "name": account.name,
            "email": account.email,
            "phone": account.phno,
            "age": account.age,
            "position": account.position,
        }
    else:
        details = {
            "name": account.Name,
            "email": account.Email,
            "phone": str(account.Phno),
            "age": account.Age,
            "position": account.Position,
        }
    request._store_account = {"id": account.pk, "kind": kind, **details}
    request._store_account_resolved = True
    return request._store_account
