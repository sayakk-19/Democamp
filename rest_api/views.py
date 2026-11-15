from django.http import HttpResponse, JsonResponse
from django.shortcuts import render, redirect
from store.models import Register
from rest_framework import serializers
from rest_framework.response import Response

# Create your views here.

def users(request):
    web_users = Register.objects.all()
    serialized_web_users = list(web_users.values())
    return JsonResponse(serialized_web_users, safe=False)