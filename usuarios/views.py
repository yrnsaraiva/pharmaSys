# usuarios/views.py
from django.contrib.auth import authenticate, login
from django.shortcuts import render, redirect
from django.contrib import messages
from django.conf import settings


def login_view(request):
    if request.method == "POST":
        username = request.POST.get("username")
        password = request.POST.get("password")

        user = authenticate(request, username=username, password=password)

        if user is not None:
            login(request, user)

            remember_me = request.POST.get("remember_me")
            if not remember_me:
                request.session.set_expiry(0)  # expira ao fechar navegador
            else:
                request.session.set_expiry(settings.SESSION_COOKIE_AGE)

            return redirect("dashboard")
        else:
            messages.error(request, "Usuário ou senha inválidos.")

    return render(request, "usuarios/login.html")
