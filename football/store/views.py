from django.shortcuts import render, redirect
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
    a = request.GET['email']
    b = request.GET['pwd']
    if Register.objects.filter(email=a, pwd=b, appr=1):
        messages.success(request,'You are successfully logged in')
        return render(request,'welcome.html')
    else:
        messages.success(request,'Please provide the valid credentials to proceed further...')
        return render(request,'index1.html')
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

        if pwd != reenter_pwd:
            messages.success(request, 'Passwords do not match')
            return redirect('registration.html')
        if Register.objects.filter(name = name).first():
            messages.success(request, "Username is taken...")
            return redirect('registration.html')
        if Register.objects.filter(email = email).first():
            messages.success(request, "Email already exists...")
            return redirect('registration.html')

        regi = Register(name=name, email=email, phno=phno, pwd=pwd, reenter_pwd=reenter_pwd, age=age, position=position, appr=0)
        regi.save()
        print("====== DATA SAVED TO DATABASE ======")
        messages.success(request,'You are successfully registered')
        return redirect('index1.html')
    # elif 'pwd' != 'reenter_pwd':
    #     # messages.success(request,'Please give the same password')
    #     return render(request,'registration.html')
    # else: 
    return render(request, 'registration.html')
# def registration1(request):
#     return render(request, 'registration1.html')
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
    