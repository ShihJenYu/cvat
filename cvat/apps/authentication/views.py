
# Copyright (C) 2018 Intel Corporation
#
# SPDX-License-Identifier: MIT

from django.shortcuts import render
from django.contrib.auth.views import LoginView
from django.http import HttpResponseRedirect, JsonResponse
from . import forms

from django.contrib.auth import login, authenticate
from django.shortcuts import render, redirect

from django.conf import settings
from django.contrib.auth.decorators import permission_required
from cvat.apps.authentication.decorators import login_required

import hashlib,os

def register_user(request):
    if request.method == 'POST':
        form = forms.NewUserForm(request.POST)
        if form.is_valid():
            form.save()
            username = form.cleaned_data.get('username')
            raw_password = form.cleaned_data.get('password1')
            mysterious_key = request.POST['mysterious_key']
            user = authenticate(username=username, password=raw_password, mysterious_key=mysterious_key)
            login(request, user)
            return redirect('/')
    else:
        form = forms.NewUserForm()
    return render(request, 'register.html', {'form': form})

def user_login(request):
    mysterious_error = False
    if request.method == 'POST':
        print('in my user_login;')

        username = request.POST['username']
        password = request.POST['password']
        mysterious_key = request.POST['mysterious_key']
        print('username',username)
        print('password',password)
        print('mysterious_key',mysterious_key)
        user = authenticate(username=username, password=password, mysterious_key=mysterious_key)
        print('user is',user)
        if user:
            login(request, user)
            return redirect('/')
        form = forms.AuthForm()
        mysterious_error = True
    else:
        form = forms.AuthForm()
    return render(request, 'login.html', {'form': form, 'mysterious_error':mysterious_error})


@login_required
def auth_mysteriousKey(request):

    isAdmin = request.user.groups.filter(name='admin').exists()
    if isAdmin:
        return JsonResponse({'auth':"success"})
    else:
        params = request.POST.dict()
        mysterious_key = params['mysteriousKey']
        print('mysteriousKey', mysterious_key)
        OFFICE_IP = []
        with open(os.path.join(settings.OTHERS_ROOT,'ip_settings.txt')) as f:
            OFFICE_IP = f.readlines()

        OFFICE_IP = [ip.strip() for ip in OFFICE_IP]
        OFFICE_Key = []
        for ip in OFFICE_IP:
            mhash = hashlib.md5()
            mhash.update(ip.encode('utf-8'))
            OFFICE_Key.append(mhash.hexdigest())
        print('OFFICE_Key',OFFICE_Key)

        username = request.user.username
        print('username',username)
        ip_valid = False
        if username.lower().startswith('oto') and mysterious_key in OFFICE_Key:
            ip_valid = True
        if (not username.lower().startswith('oto')) and (not mysterious_key in OFFICE_Key):
            ip_valid = True
        print(ip_valid)
        
        if ip_valid:
            return JsonResponse({'auth':"success"})
        else:
            return JsonResponse({'auth':"error"})
