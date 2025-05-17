
from django.shortcuts import render, redirect, get_object_or_404 # type: ignore
from django.contrib.auth import authenticate, login, logout # type: ignore
from django.contrib import messages # type: ignore
from django.contrib.auth.forms import UserCreationForm # type: ignore
from .forms import RegisterUserForm, ProfileUpdateForm, UserUpdateForm
from django.contrib.auth.decorators import login_required  # type: ignore

# Create your views here.

def loginUser(request):
    if request.method=="POST":
        username = request.POST['username']
        password = request.POST['password']
        user = authenticate(request, username = username, password = password)
        if user is not None:
            login(request, user)
            return redirect('home')
        else:
            messages.success(request, ("There was an error logging in."))
            return redirect('login')
    else:
        return render(request, 'userPages/login.html', {})
    
def logoutUser(request):
    logout(request)
    messages.success(request, ("Logged out successfully."))
    return redirect('home')

def registerUser(request):
    if request.method == "POST":
        form = RegisterUserForm(request.POST)
        if form.is_valid():
            form.save()
            username = form.cleaned_data['username']
            password = form.cleaned_data['password1']
            user = authenticate(username = username, password = password)
            login(request, user)
            messages.success(request, ("Registration successful"))
            return redirect('home')
    else:
        form = RegisterUserForm()

    return render(request, 'userPages/register.html' ,{'form':form})

@login_required
def showProfile(request):
    if request.method == "POST":
        u_form = UserUpdateForm(request.POST, instance=request.user)
        p_form = ProfileUpdateForm(request.POST, request.FILES, instance=request.user.profile)

        if u_form.is_valid() and p_form.is_valid():
            u_form.save()
            p_form.save()
            messages.success(request, ("Updated Succesfully! "))
            return redirect('yourProfile')
    else:
        u_form = UserUpdateForm(instance=request.user)
        p_form = ProfileUpdateForm(instance=request.user.profile)
        
    context = {
        'u_form': u_form,
        'p_form': p_form  
        }
    return render(request,"profilePages/yourProfile.html", context)
