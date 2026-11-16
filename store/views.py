from django.shortcuts import render, redirect
from django.contrib.auth import login, logout as auth_logout, authenticate
from django.contrib.auth.models import User
from django.contrib.auth.hashers import check_password, make_password
from django.contrib.admin.views.decorators import staff_member_required
from django.core.exceptions import ValidationError
import re
from django.db.models import Q
from django.http import HttpResponse
from django.contrib import messages
from django.views.decorators.http import require_POST
from store.accounts import ACCOUNT_MODELS, get_store_account, start_store_session
from store.models import *
from store.registration_validation import (
    RANGE_ERROR_CODES,
    RANGE_ERROR_MESSAGE,
    range_errors,
    registration_limits,
)
from .helpers import store_login_required

# Create your views here.
def test(request):
    return HttpResponse('Testing the page...')
def about(request):
    return render(request,'about.html')
def about1(request):
    return render(request,'about1.html')
def contact(request):
    return render(request,'contact.html')
def contact1(request):
    return render(request,'contact1.html')
def games(request):
    return render(request,'games.html')
def games1(request):
    return render(request,'games1.html')
def index(request):
    return render(request,'index.html')
def index2(request):
    return render(request,'index2.html')
def tranner(request):
    return render(request,'tranner.html')
def tranner1(request):
    return render(request,'tranner1.html')
def sports(request):
    return render(request,'sports.html')
def index1(request):
    return render(request,'index1.html')
def indexcode(request):
    if request.method == 'POST':
        a = request.POST.get('email', '').strip()
        b = request.POST.get('pwd', '')

        # account = Register.objects.filter(email=a, pwd=b, appr=1).first()
        # if account:
        #     start_store_session(request, 'register', account)
        #     messages.success(request,'You are successfully logged in')
        #     return redirect('store_home')
        # elif Register.objects.filter(email = a).filter(~Q(pwd=b)).exists():
        #     messages.error(request, "Please provide correct password")
        #     return render(request,'index1.html')
        # else:
        #     messages.error(request,'Please provide the valid credentials to proceed further...')
        #     return render(request,'index1.html')

        account = Register.objects.filter(email=a).first()
        if account is None:
            messages.error(request, 'Invalid username')
            return render(request, 'index1.html')
        
        try:
            password_valid = bool(b) and check_password(b, account.pwd_hash)
        except (TypeError, ValueError):
            password_valid = False

        if not password_valid:
            messages.error(request, 'Please provide correct password')
            return render(request, 'index1.html')
        elif account.appr != 1:
            messages.error(request, 'Your account is awaiting approval. Please log in after it has been approved.')
            return render(request, 'index1.html')
        else:
            start_store_session(request, 'register', account)
            messages.success(request, 'You are successfully logged in')
            return render(request, 'welcome.html')

    return HttpResponse("404 - Not Found")  
  
def registration(request):
    # print("====== REGISTRATION VIEW TRIGGERED ======")
    # print(f"Method Type: {request.method}")
    error_fields = {
        'name': 'name_error',
        'email': 'email_error',
        'phno': 'phno_error',
        'pwd': 'password_error',
        'reenter_pwd': 'reenter_pwd_error',
        'age': 'age_error',
        'position': 'position_error',
    }
    context = dict.fromkeys(error_fields.values(), '')
    context['field_limits'] = registration_limits()
    if request.method == "POST":
        # print("====== POST DATA RECEIVED ======")
        name = request.POST.get('name', '')
        email = request.POST.get('email', '')
        phno = request.POST.get('phno', '')
        pwd = request.POST.get('pwd', '')
        reenter_pwd = request.POST.get('reenter_pwd', '')
        age = request.POST.get('age', '')
        position = request.POST.get('position', '')

        input_range_errors = range_errors(request.POST)
        if input_range_errors:
            context.update({error_fields[field]: message for field, message in input_range_errors.items()})
            return render(request, 'registration.html', context)

        if not re.match(r'^(?=.*[A-Z])(?=.*[a-z])(?=.*\d)(?=.*[@#$%^&+=!]).{8,}$', pwd):
            context['password_error'] = "Password must contain at least 8 characters, one uppercase, one lowercase, one number and one special character."
            return render(request, "registration.html", context)
        if pwd != reenter_pwd:
            messages.error(request, 'Passwords do not match')
            return render(request, 'registration.html', context)
        if not name.isalnum():
            messages.error(request, 'Username should only contain numbers and letters')
            return render(request, 'registration.html', context)
        if Register.objects.filter(name = name).first():
            messages.error(request, "Username is taken...")
            return render(request, 'registration.html', context)
        if len(phno) != 10:
            messages.error(request, "Phone number must be of 10 digits")
            return render(request, 'registration.html', context)
        if Register.objects.filter(email = email).first():
            messages.error(request, "Email already exists...")
            return render(request, 'registration.html', context)
        try:
            regi = Register(name=name, email=email, pwd=pwd, phno=phno, age=age, position=position, appr=0)
            regi.pwd_hash = make_password(pwd)
            regi.reenter_pwd = make_password(reenter_pwd)
            regi.full_clean()
            regi.save()
            # print("====== DATA SAVED TO DATABASE ======")
            messages.success(request,'You are successfully registered')
            return render(request, 'index1.html')

        except ValidationError as e:
            if hasattr(e, 'error_dict'):
                for field, field_errors in e.error_dict.items():
                    if field in error_fields:
                        if any(error.code in RANGE_ERROR_CODES for error in field_errors):
                            context[error_fields[field]] = RANGE_ERROR_MESSAGE
                        else:
                            context[error_fields[field]] = ' '.join(
                                message for error in field_errors for message in error.messages
                            )
                    else:
                        messages.error(request, ' '.join(
                            message for error in field_errors for message in error.messages
                        ))
            else:
                messages.error(request, ' '.join(e.messages))
            return render(request, "registration.html", context)
    # elif 'pwd' != 'reenter_pwd':
    #     # messages.success(request,'Please give the same password')
    #     return render(request,'registration.html')
    # else: 
    return render(request,'registration.html', context)
    # return HttpResponse('404 - Not Found')

# def registration_form(request):
#     return render(request, 'registration.html')
# def registration1(request):
#     return render(request, 'registration1.html')
# def handleLogin(request):
#     if request.method == 'POST':
#         loginUsername = request.POST['name']
#         loginPassword = request.POST['password']
#         user = authenticate(name=loginUsername, pwd=loginPassword)

#         if user is not None:

#     return redirect(index)

@require_POST
def handleLogout(request):
    auth_logout(request)
    messages.success(request, "Successfully logged out")
    return redirect('store_home')


@require_POST
def account_delete(request):
    account = get_store_account(request)
    if account is None:
        messages.error(request, "Please log in before deleting your account.")
        return redirect('store_login')
    if request.POST.get('confirm_delete') != 'DELETE':
        messages.error(request, "Confirm account deletion before continuing.")
        return redirect('store_home')

    # The account identity always comes from the authenticated store session.
    ACCOUNT_MODELS[account['kind']].objects.filter(pk=account['id'], appr=1).delete()
    auth_logout(request)
    messages.success(request, "Your account has been deleted.")
    return redirect('store_home')

def register(request):
    return render(request,'register.html')
def reg(request):
    p=player()
    p.Name=request.GET['a1']
    p.Email=request.GET['a2']
    p.Passwd=request.GET['a3']
    p.Age=request.GET['a4']
    p.Position=request.GET['a5']
    p.Phno=request.GET['a6']
    p.appr=0
    # p.appr=request.GET['a7']
    p.save()
    return render(request,'register.html')
def login(request):
    return render(request,'login.html')
def logcode(request):
    if request.method != 'POST':
        return redirect('store_legacy_login')
    a=request.POST.get('a1', '').strip()
    b=request.POST.get('a2', '')
    account = player.objects.filter(Email=a, Passwd=b, appr=1).first()
    if account:
        start_store_session(request, 'player', account)
        messages.success(request, 'You are successfully logged in')
        return redirect('store_home')
    else:
        return render(request,'login.html')


@store_login_required
def welcome(request):
    return render(request, 'welcome.html')

@staff_member_required
def edit(request, id):
    regi = Register.objects.get(id=id)
    return render(request, 'edit.html', {'a' : regi})

@staff_member_required
@require_POST
def update(request, id):
    regi = Register.objects.get(id=id)
    regi.name = request.POST['a1']
    regi.email = request.POST['a2']
    regi.phno = request.POST['a3']
    regi.pwd = request.POST['a4']
    regi.reenter_pwd = request.POST['a4']
    regi.age = request.POST['a5']
    regi.position = request.POST['a6']
    regi.save()
    return redirect('store_admin_panel')


@staff_member_required
@require_POST
def delete(request, id):
    regi = Register.objects.get(id=id)
    regi.delete()
    return redirect('store_admin_panel')


@staff_member_required
def approv(request):
    regi = Register.objects.filter(appr = 0).values()
    return render(request, 'approv.html', {'a':regi})

@staff_member_required
@require_POST
def apr(request, id):
    regi=Register.objects.get(id=id)
    regi.appr=1
    regi.save()
    return redirect('store_approvals')

@staff_member_required
def admin(request):
    regi = Register.objects.all()
    return render(request, 'admin_panel.html', {'a':regi})

import secrets
from datetime import timedelta
from django.core.mail import send_mail
from django.utils import timezone

def send_otp(account):
    code = f"{secrets.randbelow(10**6):06d}"
    EmailOTP.objects.filter(account=account, used=False).update(used=True)  # invalidate old codes
    EmailOTP.objects.create(
        account=account,
        code_hash=make_password(code),
        expires_at=timezone.now() + timedelta(minutes=5),
    )
    send_mail(
        'Your verification code',
        f'Your code is {code}. It expires in 5 minutes.',
        None,  # uses DEFAULT_FROM_EMAIL
        [account.email],
    )

def verify_otp(account, code):
    otp = EmailOTP.objects.filter(account=account, used=False).order_by('-created_at').first()
    if not otp or otp.is_expired() or otp.attempts >= 5:
        return False
    otp.attempts += 1
    otp.save(update_fields=['attempts'])
    if check_password(code, otp.code_hash):
        otp.used = True
        otp.save(update_fields=['used'])
        return True
    return False