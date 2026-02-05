from django.shortcuts import render, redirect
from django.contrib import messages
from django.db import transaction
from django.contrib.auth import get_user_model

# Import de vos modèles et formulaires
from utilisateurs.models import Employe
from NifAPI.models import NifEmploye
from .forms import RegisterStepOneForm, RegisterStepTwoForm

User = get_user_model()

import re
from django.shortcuts import render, redirect
from django.contrib import messages

def normalize_name(name):
    """
    Supprime les espaces au début/fin, remplace les espaces multiples 
    par un seul, et met tout en majuscules.
    """
    if not name:
        return ""
    # Enlève espaces début/fin + force majuscules
    name = name.strip().upper()
    # Remplace plusieurs espaces ou tabulations par un seul espace
    return re.sub(r'\s+', ' ', name)

def register_employe_step_one(request):
    if request.method == "POST":
        form = RegisterStepOneForm(request.POST)
        if form.is_valid():
            nif_saisi = form.cleaned_data['nif']
            cin_saisi = form.cleaned_data['cin']
            # Normalisation de la saisie (qui vient du champ readonly rempli par le JS)
            nom_saisi = normalize_name(form.cleaned_data.get('nom_prenom', ''))

            try:
                # 1. Vérification dans la base fiscale (NifAPI)
                nif_officiel = NifEmploye.objects.get(nif=nif_saisi)
                
                # 2. Vérification dans la base employeur (Employe)
                employe_base = Employe.objects.get(cin=cin_saisi)

                # 3. Triple vérification flexible mais sûre
                nom_fisc_clean = normalize_name(nif_officiel.nom_prenom)
                nom_emp_clean = normalize_name(employe_base.nom_prenom)

                if nom_saisi != nom_fisc_clean or nom_saisi != nom_emp_clean:
                    # Debug optionnel pour voir ce qui diffère dans la console
                    print(f"DEBUG: Saisi: '{nom_saisi}' | Fisc: '{nom_fisc_clean}' | Emp: '{nom_emp_clean}'")
                    
                    messages.error(request, "Les informations fournies ne correspondent pas à nos registres fiscaux ou employeurs.")
                    return render(request, 'Portail_employes/auth/register_step_one.html', {'form': form})

                # 4. Vérification si déjà inscrit
                if employe_base.user:
                    messages.warning(request, "Un compte existe déjà pour ce profil. Veuillez vous connecter.")
                    return redirect('login')

                # Succès : Stockage en session
                request.session['register_employe_data'] = {
                    'nif': nif_saisi,
                    'employe_id': employe_base.id,
                    'nom_prenom': employe_base.nom_prenom
                }
                
                messages.info(request, f"Identité confirmée : {employe_base.nom_prenom}.")
                return redirect('register_employe_step_two')

            except (NifEmploye.DoesNotExist, Employe.DoesNotExist):
                messages.error(request, "Identification impossible. Le NIF ou le CIN n'est pas répertorié.")
    else:
        form = RegisterStepOneForm()

    return render(request, 'Portail_employes/auth/register_step_one.html', {'form': form})

from django.db import transaction, IntegrityError
from django.contrib.auth import get_user_model
from django.shortcuts import render, redirect
from django.contrib import messages

User = get_user_model() # Meilleure pratique pour récupérer votre User personnalisé

def register_employe_step_two(request):
    temp_data = request.session.get('register_employe_data')

    if not temp_data:
        return redirect('register_employe_step_one')

    if request.method == "POST":
        form = RegisterStepTwoForm(request.POST)
        if form.is_valid():
            email = form.cleaned_data['email']
            password = form.cleaned_data['password']

            # --- SÉCURITÉ : Vérifier si l'email est déjà pris ---
            if User.objects.filter(email=email).exists():
                messages.error(request, "Cet email est déjà utilisé par un autre compte.")
                return render(request, 'Portail_employes/auth/register_step_two.html', {
                    'form': form,
                    'nom_valide': temp_data.get('nom_prenom')
                })

            try:
                with transaction.atomic():
                    # 1. Création de l'utilisateur
                    user = User.objects.create_user(
                        email=email,
                        password=password
                    )

                    # 2. Liaison avec l'employé
                    # On utilise select_for_update() pour verrouiller la ligne durant la transaction
                    employe = Employe.objects.select_for_update().get(id=temp_data['employe_id'])
                    
                    employe.user = user
                    employe.nif_individuel = temp_data['nif']
                    employe.save()

                # 3. Nettoyage et succès
                del request.session['register_employe_data']
                messages.success(request, "Compte activé ! Vous pouvez vous connecter.")
                return redirect('login')

            except IntegrityError:
                messages.error(request, "Une erreur technique est survenue. Veuillez réessayer.")
            except Employe.DoesNotExist:
                messages.error(request, "Profil employé introuvable.")
                return redirect('register_employe_step_one')
    else:
        form = RegisterStepTwoForm(initial={'full_name': temp_data.get('nom_prenom')})

    return render(request, 'Portail_employes/auth/register_step_two.html', {
        'form': form,
        'nom_valide': temp_data.get('nom_prenom')
    })
#-----------------------------------------------------------------------------    
def dashborad_employe(request):
    return render(request,'Portail_employes/dashboard.html')


from django.shortcuts import render, redirect
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from declarations.models import LigneDeclarationIRSA

@login_required
def mes_declarations_irsa(request):
    # 1. Récupération sécurisée du profil
    profil = getattr(request.user, 'employe_profile', None)
    
    if not profil:
        messages.error(request, "Aucun profil employé trouvé pour ce compte.")
        return redirect('home')

    # 2. On récupère ses identifiants
    nif = profil.nif_individuel
    cin = profil.cin
    
    # 3. Requête flexible : On cherche par NIF OU par CIN
    # Cela permet de trouver les lignes même si l'employeur n'a saisi que le CIN
    from django.db.models import Q
    
    mes_lignes = LigneDeclarationIRSA.objects.filter(
        Q(employe__nif_individuel=nif) | Q(employe__cin=cin)
    ).select_related(
        'declaration__periode', 
        'declaration__employeur'
    ).distinct().order_by('-declaration__periode__date_debut')

    # --- DEBUG : À supprimer après test ---
    if not mes_lignes.exists():
        print(f"DEBUG: Aucun match trouvé pour NIF: {nif} ou CIN: {cin}")
    # ---------------------------------------

    return render(request, "Portail_employes/mes_declarations.html", {
        'lignes': mes_lignes,
        'nom_valide': profil.nom_prenom
    })

from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from declarations.models import SituationFamiliale

@login_required
def profil_employe_view(request):
    employe = request.user.employe_profile
    
    # Récupérer la situation familiale la plus récente
    situation = SituationFamiliale.objects.filter(employe=employe).order_by('-date_debut').first()
    
    context = {
        'employe': employe,
        'situation': situation,
    }
    return render(request, 'Portail_employes/profil.html', context)

from django.shortcuts import render, get_object_or_404
from django.contrib.auth.decorators import login_required
from declarations.models import LigneDeclarationIRSA

from django.utils import timezone

@login_required
def detail_declaration_irsa(request, pk):
    # Récupération du profil via le related_name 'employe_profile'
    profil = request.user.employe_profile
    
    # Récupération de la ligne avec sécurité par CIN
    declaration_ligne = get_object_or_404(
        LigneDeclarationIRSA.objects.select_related(
            'declaration__periode', 
            'declaration__employeur'
        ), 
        pk=pk, 
        employe__cin=profil.cin
    )

    # --- LOGIQUE "VU" ---
    # On marque comme lu si l'employé ouvre la page
    if not declaration_ligne.est_lu:
        declaration_ligne.est_lu = True
        # On peut aussi enregistrer l'heure exacte si tu as ajouté le champ date_lecture
        if hasattr(declaration_ligne, 'date_lecture'):
            declaration_ligne.date_lecture = timezone.now()
        declaration_ligne.save(update_fields=['est_lu', 'date_lecture'] if hasattr(declaration_ligne, 'date_lecture') else ['est_lu'])

    context = {
        'ligne': declaration_ligne,
        'revenus': declaration_ligne.revenus.all(),
        'deductions': declaration_ligne.deductions.all(),
    }
    
    return render(request, "Portail_employes/detail_declaration.html", context)