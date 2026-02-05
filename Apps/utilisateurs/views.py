from django.shortcuts import render
from .forms import LoginForm
from django.contrib.auth import logout,login, authenticate as auth_login
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.shortcuts import render, redirect, get_object_or_404
from django.urls import reverse
from .models import UserCustom
from .forms import UserSecureUpdateForm
from django.http import HttpResponse
from django.conf import settings
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from .models import Employe
from decimal import Decimal
from .forms import RegisterStepOneForm, RegisterStepTwoForm
from django.contrib.auth import get_user_model
from .models import Employeur
from django.utils import timezone
from django.db.models import Sum
from datetime import datetime, date
import calendar
from django.utils import timezone
from datetime import date

from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.db.models import Sum
from django.core.exceptions import ObjectDoesNotExist
from datetime import date
# Create your views here.
def home(request):
    return render(request,'base_tailwind.html')

User = get_user_model()

def register_step_one(request):
    if request.method == "POST":
        form = RegisterStepOneForm(request.POST)
        if form.is_valid():
            request.session['register_step_one'] = form.cleaned_data
            return redirect('register_step_two')
    else:
        form = RegisterStepOneForm()

    return render(request, 'auth/register_step_one.html', {'form': form})

from django.contrib import messages

def register_step_two(request):
    step_one_data = request.session.get('register_step_one')

    if not step_one_data:
        return redirect('register_step_one')

    if request.method == "POST":
        form = RegisterStepTwoForm(request.POST)
        if form.is_valid():
            # Création de l'utilisateur
            user = User.objects.create_user(
                email=form.cleaned_data['email'],
                password=form.cleaned_data['password'],
                first_name=form.cleaned_data['first_name'],
                last_name=form.cleaned_data['last_name'],
            )

            # Création de l'entreprise
            Employeur.objects.create(
                user=user,
                nif=step_one_data['nif'],
                raison_sociale=step_one_data['raison_sociale'],
                adresse=step_one_data['adresse'],
            )

            del request.session['register_step_one']
            messages.success(request, " Inscription réussie ! Bienvenue sur la plateforme.")
            # AJOUT : Message pour déclencher le nettoyage JS
            messages.success(request, "registration_complete")
            return redirect('login')

    else:
        form = RegisterStepTwoForm()

    return render(request, 'auth/register_step_two.html', {'form': form})

from django.contrib.auth import login
from django.contrib import messages

def login_view(request):
    if request.method == "POST":
        form = LoginForm(request, data=request.POST)
        if form.is_valid():
            user = form.get_user()
            login(request, user)
            
            messages.success(request, f"Bienvenue {user.first_name}, vous êtes connecté !")
            
            # --- LOGIQUE DE REDIRECTION SELON LE PROFIL ---
            
            if hasattr(user, 'agentfiscale'):
                # C'est un Agent de la DGI
                return redirect("home") 
            
            elif hasattr(user, 'employeur'):
                # C'est un Employeur/Entreprise
                return redirect("home")
            
            else:
                # Cas par défaut (ex: SuperAdmin ou compte sans profil encore créé)
                return redirect("home")
                
        else:
            messages.error(request, "Email ou mot de passe incorrect.")
    else:
        form = LoginForm()
    
    return render(request, "auth/login.html", {"form": form})

def logout_view(request):
    logout(request)
    return redirect('home')
