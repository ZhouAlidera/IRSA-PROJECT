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
from django.db.models import Q
from declarations.models import LigneDeclarationIRSA

@login_required
def mes_declarations_irsa(request):
    profil = getattr(request.user, 'employe_profile', None)
    
    if not profil:
        messages.error(request, "Aucun profil employé trouvé pour ce compte.")
        return redirect('home')

    # 1. Capture des filtres depuis l'URL
    query = request.GET.get('q', '')
    year_filter = request.GET.get('year', '')

    # 2. Base de la requête (Filtrage par identité)
    filters = Q(employe__nif_individuel=profil.nif_individuel) | Q(employe__cin=profil.cin)
    
    mes_lignes = LigneDeclarationIRSA.objects.filter(filters).select_related(
        'declaration__periode', 
        'declaration__employeur'
    ).distinct()

    # 3. Application de la recherche dynamique (Employeur ou N° Document)
    if query:
        mes_lignes = mes_lignes.filter(
            Q(declaration__employeur__raison_sociale__icontains=query) |
            Q(declaration__numero_document__icontains=query)
        )

    # 4. Application du triage par année
    if year_filter and year_filter.isdigit():
        mes_lignes = mes_lignes.filter(declaration__periode__annee=year_filter)

    # 5. Tri final et récupération des années disponibles pour le dropdown
    mes_lignes = mes_lignes.order_by('-declaration__periode__date_debut')
    
    # Liste des années uniques pour le filtre (pour le menu déroulant)
    annees_disponibles = LigneDeclarationIRSA.objects.filter(filters).values_list(
        'declaration__periode__annee', flat=True
    ).distinct().order_by('-declaration__periode__annee')

    return render(request, "Portail_employes/mes_declarations.html", {
        'lignes': mes_lignes,
        'nom_valide': profil.nom_prenom,
        'annees': annees_disponibles,
        'selected_year': year_filter,
        'search_query': query,
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

from django.db.models import Sum
from django.contrib.auth.decorators import login_required
from django.utils import timezone
from declarations.models import LigneDeclarationIRSA

from django.db.models import Sum
from django.contrib.auth.decorators import login_required
from django.utils import timezone
from declarations.models import LigneDeclarationIRSA, DeclarationIRSA # Importez DeclarationIRSA

@login_required
def dashboard_employe(request):
    aujourdhui = timezone.now()
    annee_actuelle = aujourdhui.year
    employe = request.user.employe_profile 
    
    # Utilisation des TextChoices pour éviter les erreurs de frappe
    status = DeclarationIRSA.StatusChoices

    # 1. Alerte : Déclaration CONFIRMÉE (pas encore validée)
    alerte_attente = LigneDeclarationIRSA.objects.filter(
        employe=employe,
        declaration__statut=status.CONFIRME # Utilise 'confirme'
    ).select_related('declaration').order_by('-declaration__date_declaration').first()

    # 2. Statistiques (uniquement sur ce qui est VALIDÉ)
    total_irsa_annee = LigneDeclarationIRSA.objects.filter(
        employe=employe, 
        declaration__date_declaration__year=annee_actuelle,
        declaration__statut=status.VALIDE # Utilise 'valide'
    ).aggregate(total=Sum('irsa_due'))['total'] or 0

    # 3. Données graphique (6 derniers mois validés)
    recent_stats = LigneDeclarationIRSA.objects.filter(
        employe=employe,
        declaration__statut=status.VALIDE
    ).select_related('declaration').order_by('-declaration__periode')[:6]
    
    # 4. Historique (Validé + Confirmé pour que l'employé voie ce qui arrive)
    # On exclut le brouillon pour l'employé
    dernieres_fiches = LigneDeclarationIRSA.objects.filter(
        employe=employe
    ).exclude(
        declaration__statut=status.BROUILLON
    ).select_related('declaration').order_by('-id')[:5]

    context = {
        'total_irsa': total_irsa_annee,
        'annee_actuelle': annee_actuelle,
        'dernieres_fiches': dernieres_fiches,
        'recent_stats': recent_stats,
        'alerte_attente': alerte_attente,
        'status': status, # On passe les choix au template pour les tests
    }
    return render(request, 'Portail_employes/dashboard.html', context)

from django.conf import settings
from django.http import HttpResponse
from django.template.loader import render_to_string
from django.shortcuts import get_object_or_404
from django.utils import timezone
from weasyprint import HTML
from declarations.models import LigneDeclarationIRSA, DetailRevenu, DetailDeduction

def generer_pdf_fiche(request, fiche_id):
    # 1. Récupérer la ligne (sécurité : liée au profil de l'employé connecté)
    fiche = get_object_or_404(LigneDeclarationIRSA, id=fiche_id, employe=request.user.employe_profile)
    
    # 2. Récupérer les détails stockés dans les tables liées
    # On utilise select_related pour éviter les requêtes SQL répétitives dans le template
    details_revenus = DetailRevenu.objects.filter(ligne=fiche).select_related('type_revenu')
    details_deductions = DetailDeduction.objects.filter(ligne=fiche).select_related('type_deduction')

    # 3. Calculs financiers pour le bulletin
    salaire_brut = sum(item.montant for item in details_revenus)
    total_retenues_sociales = sum(item.montant for item in details_deductions)
    
    # Le Net à payer = Brut - Retenues (CNaPS/Santé) - IRSA
    salaire_net = salaire_brut - total_retenues_sociales - fiche.irsa_due

    # 4. Préparer le contexte
    context = {
        'fiche': fiche,
        'details_revenus': details_revenus,
        'details_deductions': details_deductions,
        'salaire_brut': salaire_brut,
        'total_retenues': total_retenues_sociales + fiche.irsa_due,
        'salaire_net': salaire_net,
        'entreprise': fiche.declaration.employeur,
        'date_edition': timezone.now(),
    }
    
    # 5. Rendre le HTML et générer le PDF
    html_string = render_to_string('Portail_employes/pdf_template.html', context)
    html = HTML(string=html_string, base_url=request.build_absolute_uri())
    pdf = html.write_pdf()
    
    # 6. Envoyer la réponse
    response = HttpResponse(pdf, content_type='application/pdf')
    filename = f"Bulletin_{fiche.employe.nif_individuel}_{fiche.declaration.periode}.pdf"
    response['Content-Disposition'] = f'inline; filename="{filename}"'
    
    return response