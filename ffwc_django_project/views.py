from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login
from django.contrib import messages
import datetime
from rest_framework.decorators import api_view

@api_view(['GET'])
def home_view(request):

    scheme = request.scheme  # http or https
    host = request.get_host()  # e.g., 0.0.0.0:8006
    remoteIP = f"{scheme}://{host}"

    context = {
        'data_load': remoteIP + '/data_load/',
    }
    return render(request, 'home.html', context)


def home(request):
    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')
        user = authenticate(request, username=username, password=password)
        if user is not None:
            login(request, user)
            messages.success(request, 'Login successful!')
            return redirect('home')  # Redirect to API home after login
        else:
            messages.error(request, 'Invalid username or password.')
    return render(request, 'login.html')
