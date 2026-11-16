from functools import wraps
from django.contrib import messages
from django.shortcuts import redirect
from store.accounts import get_store_account

def store_login_required(view):
    @wraps(view)
    def wrapper(request, *args, **kwargs):
        if get_store_account(request) is None:
            messages.error(request, "Please log in first.")
            return redirect('store_login')
        return view(request, *args, **kwargs)
    return wrapper