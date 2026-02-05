from django.shortcuts import render, redirect
from django.contrib import messages
from django.db import transaction
from django.contrib.auth import get_user_model

# Import de vos modèles et formulaires
from utilisateurs.models import Employe
from NifAPI.models import NifEmploye
from .forms import RegisterStepOneForm, RegisterStepTwoForm

User = get_user_model()

def register_employe_step_one(request):
    if request.method == "POST":
        form = RegisterStepOneForm(request.POST)
        if form.is_valid():
            nif_saisi = form.cleaned_data['nif']
            cin_saisi = form.cleaned_data['cin']
            # Normalisation du nom pour éviter les erreurs de casse
            nom_saisi = form.cleaned_data.get('nom_prenom', '').strip().upper()

            try:
                # 1. Vérification dans la base fiscale (NifAPI)
                nif_officiel = NifEmploye.objects.get(nif=nif_saisi)
                
                # 2. Vérification dans la base employeur (Employe)
                employe_base = Employe.objects.get(cin=cin_saisi)

                # 3. Triple vérification stricte
                if (nom_saisi != nif_officiel.nom_prenom.upper() or 
                    nom_saisi != employe_base.nom_prenom.upper()):
                    messages.error(request, "Les informations fournies ne correspondent pas à nos registres fiscaux ou employeurs.")
                    return render(request, 'Portail_employes/auth/register_step_one.html', {'form': form})

                # 4. Vérification si déjà inscrit
                if employe_base.user:
                    messages.warning(request, "Un compte existe déjà pour ce profil. Veuillez vous connecter.")
                    return redirect('login')

                # Succès : Stockage en session pour l'étape suivante
                request.session['register_employe_data'] = {
                    'nif': nif_saisi,
                    'employe_id': employe_base.id,
                    'nom_prenom': employe_base.nom_prenom # Pour l'affichage au step 2
                }
                
                # Message informatif pour l'utilisateur
                messages.info(request, f"Identité confirmée : {employe_base.nom_prenom}. Veuillez finaliser votre inscription.")
                return redirect('register_employe_step_two')

            except (NifEmploye.DoesNotExist, Employe.DoesNotExist):
                messages.error(request, "Identification impossible. Le NIF ou le CIN n'est pas répertorié.")
    else:
        form = RegisterStepOneForm()

    return render(request, 'Portail_employes/auth/register_step_one.html', {'form': form})


def register_employe_step_two(request):
    temp_data = request.session.get('register_employe_data')

    if not temp_data:
        return redirect('register_employe_step_one')

    if request.method == "POST":
        form = RegisterStepTwoForm(request.POST)
        if form.is_valid():
            with transaction.atomic():
                # Création de l'UserCustom
                user = User.objects.create_user(
                    email=form.cleaned_data['email'],
                    password=form.cleaned_data['password']
                )
                # Liaison et enregistrement final du NIF
                employe = Employe.objects.get(id=temp_data['employe_id'])
                employe.user = user
                employe.nif_individuel = temp_data['nif']
                employe.save()

            del request.session['register_employe_data']
            messages.success(request, "Compte activé ! Vous pouvez vous connecter.")
            return redirect('login')
    else:
        # AUTO-REMPLISSAGE : On passe le nom validé au formulaire
        form = RegisterStepTwoForm(initial={'full_name': temp_data.get('nom_prenom')})

    return render(request, 'Portail_employes/auth/register_step_two.html', {
        'form': form,
        'nom_valide': temp_data.get('nom_prenom')
    })