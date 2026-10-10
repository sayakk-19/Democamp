from django.shortcuts import render, redirect
from django.contrib.auth import login, logout, authenticate
from django.core.exceptions import ValidationError
import re
from django.db.models import Q
from django.http import HttpResponse
from django.contrib import messages
from store.models import *
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
        a = request.POST['email']
        b = request.POST['pwd']
        if Register.objects.filter(email=a, pwd=b, appr=1):
            messages.success(request,'You are successfully logged in')
            return render(request,'welcome.html')
        elif Register.objects.filter(email = a).filter(~Q(pwd=b)).exists():
            messages.error(request, "Please provide correct password")
            return render(request,'index1.html')
        else:
            messages.error(request,'Please provide the valid credentials to proceed further...')
            return render(request,'index1.html')
    return HttpResponse("404 - Not Found")    
def registration(request):
    print("====== REGISTRATION VIEW TRIGGERED ======")
    print(f"Method Type: {request.method}")
    if request.method == "POST":
        print("====== POST DATA RECEIVED ======")
        name = request.POST.get('name')
        email = request.POST.get('email')
        phno = request.POST.get('phno')
        pwd = request.POST.get('pwd')
        reenter_pwd = request.POST.get('reenter_pwd')
        age = request.POST.get('age')
        position = request.POST.get('position')

        if not re.match(r'^(?=.*[A-Z])(?=.*[a-z])(?=.*\d)(?=.*[@#$%^&+=!]).{8,}$', pwd):
            return render(request, "registration.html", {
                "password_error": "Password must contain at least 8 characters, one uppercase, one lowercase, one number and one special character."
            })
        if pwd != reenter_pwd:
            messages.error(request, 'Passwords do not match')
            return render(request, 'registration.html')
        if not name.isalnum():
            messages.error(request, 'Username should only contain numbers and letters')
            return render(request, 'registration.html')
        if len(name) > 15:
            messages.error(request, 'Username must not exceed 15 characters')
            return render(request, 'registration.html') 
        if Register.objects.filter(name = name).first():
            messages.error(request, "Username is taken...")
            return render(request, 'registration.html')
        if len(phno) != 10:
            messages.error(request, "Phone number must be of 10 digits")
            return render(request, 'registration.html')
        if Register.objects.filter(email = email).first():
            messages.error(request, "Email already exists...")

            return render(request, 'registration.html')
        try:
            regi = Register(name=name, email=email, phno=phno, pwd=pwd, reenter_pwd=reenter_pwd, age=age, position=position, appr=0)
            regi.full_clean()
            regi.save()
            print("====== DATA SAVED TO DATABASE ======")
            messages.success(request,'You are successfully registered')
            return render(request, 'index1.html')

        except ValidationError as e:

            phno_error = ""
            age_error = ""

            if "phno" in e.message_dict:
                phno_error = e.message_dict["phno"][0]

            if "age" in e.message_dict:
                age_error = e.message_dict["age"][0]

            return render(request, "registration.html", {
                "phno_error": phno_error,
                "age_error": age_error
            })
    # elif 'pwd' != 'reenter_pwd':
    #     # messages.success(request,'Please give the same password')
    #     return render(request,'registration.html')
    # else: 
    return render(request,'registration.html')
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

def handleLogout(request):
    logout(request)
    messages.success("Successfully logged out")
    return render(request, 'index.html')

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
    a=request.GET['a1']
    b=request.GET['a2']
    if player.objects.filter(Email = a, Passwd = b, appr = 1):
        return render(request,'welcome.html')
    else:
        return render(request,'login.html')
def edit(request, id):
    regi = Register.objects.get(id=id)
    return render(request, 'edit.html', {'a' : regi})
def update(request, id):
    regi = Register.objects.get(id=id)
    regi.name = request.GET['a1']    
    regi.email = request.GET['a2']    
    regi.phno = request.GET['a3']    
    regi.pwd = request.GET['a4']    
    regi.reenter_pwd = request.GET['a4']    
    regi.age = request.GET['a5']    
    regi.position = request.GET['a6']
    regi.save()
    return redirect('../admin_panel')
def delete(request, id):
    regi = Register.objects.get(id=id)
    regi.delete()
    return redirect('../admin_panel')    
def approv(request):
    regi = Register.objects.filter(appr = 0).values()
    return render(request, 'approv.html', {'a':regi})
def apr(request, id):
    regi=Register.objects.get(id=id)
    regi.appr=1
    regi.save()
    return redirect('../approv')

def admin(request):
    regi = Register.objects.all()
    return render(request, 'admin_panel.html', {'a':regi})           
    