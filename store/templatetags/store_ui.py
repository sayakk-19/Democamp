"""Shared profile controls for store, shop, and blog pages."""

from django import template
from django.middleware.csrf import get_token

from store.accounts import get_store_account


register = template.Library()


def _account_context(context):
    request = context.get("request")
    csrf_token = context.get("csrf_token")
    if not csrf_token and request is not None:
        csrf_token = get_token(request)
    return {
        "request": request,
        "store_account": get_store_account(request),
        "csrf_token": csrf_token,
        "messages": context.get("messages", []),
    }


@register.inclusion_tag("store/includes/account_menu.html", takes_context=True)
def store_account_menu(context, hide_signup=False, show_login=False):
    account_context = _account_context(context)
    account_context["hide_signup"] = hide_signup
    account_context["show_login"] = show_login
    request = account_context["request"]
    account_context["store_button_effects"] = bool(
        request is not None and request.path.startswith("/store/")
    )
    return account_context


@register.inclusion_tag("store/includes/account_panels.html", takes_context=True)
def store_account_panels(context):
    return _account_context(context)
