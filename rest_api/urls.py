# from store.models import Register
from django.urls import path
from . import views

urlpatterns=[
    path('users/', views.users),
]