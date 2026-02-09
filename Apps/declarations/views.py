from django.shortcuts import render

from django.shortcuts import render, redirect
from .forms import PeriodeFiscaleForm
from django.contrib import messages
from django.core.files.storage import default_storage
from django.contrib.auth.decorators import login_required
from .models import DeclarationIRSA

from utilisateurs.models import Employeur
# Create your views here.
@login_required
def declaration(request):
    return render(request,'declaration.html')
# MISI ZVATRA TSY NORMALB-----------------------------
@login_required
def creer_periode_fiscale(request):
    # On crée une clé unique par utilisateur
    session_key = f'temp_periode_fiscale_{request.user.id}'
    
    if request.method == 'POST':
        form = PeriodeFiscaleForm(request.POST)
        if form.is_valid():
            data = form.cleaned_data
            
            # Stockage spécifique à cet utilisateur
            request.session[session_key] = {
                'date_debut': data['date_debut'].isoformat(),
                'date_fin': data['date_fin'].isoformat(),
                'date_limite': data['date_limite'].isoformat() if data.get('date_limite') else None,
                'annee': data.get('annee'),
                'periode_type': data.get('periode_type', 'mensuel'),
            }
            return redirect('upload_annexe') 
    else:
        # On ne pré-remplit QUE si c'est vraiment voulu (ex: bouton retour)
        # Sinon, pour une nouvelle période, on laisse vide
        initial_data = request.session.get(session_key, {})
        form = PeriodeFiscaleForm(initial=initial_data)
    
    # On ajoute des headers pour empêcher le cache du navigateur
    response = render(request, 'declaration/presentation.html', {'form': form})
    response['Cache-Control'] = 'no-store, no-cache, must-revalidate, max-age=0'
    return response

import os
from .models import PeriodeFiscale
@login_required
def upload_annexe(request):
    # 1. Récupération des données temporaires de la session (Step 1)
    temp_periode = request.session.get(f'temp_periode_fiscale_{request.user.id}')
    
    # 2. Sécurité : Si aucune donnée temporaire n'existe, on redirige vers l'étape 1
    if not temp_periode:
        messages.warning(request, "Veuillez d'abord configurer la période fiscale de votre déclaration.")
        return redirect('presentation')

    # 3. Gestion du POST (Upload)
    if request.method == "POST":
        excel_file = request.FILES.get("file")
        
        if excel_file:
            # Vérification du format
            if not excel_file.name.endswith(('.xlsx', '.xls')):
                messages.error(request, "Format non supporté. Utilisez un fichier Excel.")
                return render(request, "annexe/upload_form.html", {"periode_data": temp_periode})

            # --- CRÉATION DE LA PÉRIODE EN BASE ---
            # C'est ici que l'on transforme le brouillon de session en objet réel
            try:
                periode_obj,created = PeriodeFiscale.objects.get_or_create(
                    employeur=request.user.employeur,
                    date_debut=temp_periode['date_debut'],
                    date_fin=temp_periode['date_fin'],
                    date_limite=temp_periode.get('date_limite'),
                    annee=temp_periode.get('annee'),
                    periode_type=temp_periode.get('periode_type', 'mensuel')
                )
                
                # Mise à jour de la session avec l'ID réel pour les étapes suivantes
                request.session['current_periode_id'] = periode_obj.id
                # On peut nettoyer la donnée temporaire
                del request.session[f'temp_periode_fiscale_{request.user.id}']
                
            except Exception as e:
                messages.error(request, f"Erreur lors de la création de la période : {e}")
                return redirect('presentation')

            # Sauvegarde du fichier
            folder = f"temp/imports/{request.user.id}"
            file_path = default_storage.save(f"{folder}/{excel_file.name}", excel_file)
            
            request.session["excel_file_path"] = file_path
            request.session.modified = True
            
            messages.success(request, "Fichier chargé et période configurée avec succès.")
            return redirect("preview_annexe")
        else:
            messages.error(request, "Veuillez sélectionner un fichier.")

    # Au GET : on affiche les infos de la période stockées en session (pour rassurer l'utilisateur)
    return render(request, "annexe/upload_form.html", {
        "periode_data": temp_periode
    })
import os
import pandas as pd
from decimal import Decimal, ROUND_HALF_UP
from django.conf import settings
from django.contrib import messages
from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from .models import PeriodeFiscale, TrancheBareme, ImportIRSATemporaire
from .utils import calculer_irsa_brut, calculer_reduction_charge 
from decimal import Decimal
import logging
logger = logging.getLogger(__name__)
#------------------RECTIFICATION DE CALCUL
@login_required
def preview_annexe(request):
    periode_id = request.session.get('current_periode_id')
    file_path = request.session.get("excel_file_path")
    
    if not file_path or not periode_id:
        messages.error(request, "Données de session manquantes. Veuillez recommencer.")
        return redirect("upload_annexe")

    try:
        periode_obj = PeriodeFiscale.objects.get(id=periode_id)
        employeur = request.user.employeur 

        full_path = os.path.join(settings.MEDIA_ROOT, file_path)
        if not os.path.exists(full_path):
            raise FileNotFoundError(f"Le fichier {file_path} n'existe plus sur le serveur.")

        engine = "openpyxl" if file_path.endswith(".xlsx") else "xlrd"
        
        # CAS si le canevas du société s'appelle autremnet que CANEVAS_IRSA
        try:
            df_raw = pd.read_excel(full_path, sheet_name="CANEVAS_IRSA", header=None, engine=engine)
        except Exception as e:
            raise ValueError(f"Impossible de lire l'onglet 'CANEVAS_IRSA'. Vérifiez le nom de la feuille. Erreur: {e}")

        start_row = -1
        num_cnaps= "NUMÉRO D'IDENTIFICATION À LA CNAPS (LAHARAM-PAMANTARANA CNAPS)"
        nom_prenoms="NOM ET PRÉNOM DU TRAVAILLEUR (ANARANA SY FANAMPIN'ANARAN'NY MPIASA)"
        Nb_charge="NOMBRE DE PERSONNES À CHARGE (ISAN'OLONA IADIDIANA)"
        cin="NUMÉRO CARTE D'IDENTITÉ NATIONALE OU DE RÉSIDENT (LAHARAN'NY KARAPANONDROM-PIRENENA NA KARA-BAHINY)"
        fonction="FONCTION (ASANY)"
        
        for i, row in df_raw.iterrows():
            if num_cnaps in row.values:
                start_row = i
                break
        
        if start_row == -1:
            raise ValueError("La colonne 'N° CNaPS' est introuvable. Utilisez le canevas officiel.")

        df = pd.read_excel(full_path, sheet_name="CANEVAS_IRSA", header=start_row, engine=engine)
        df.columns = df.columns.str.strip()
        df = df.dropna(subset=[num_cnaps, nom_prenoms], how='all').fillna(0)

        # tranches = TrancheBareme.objects.filter(annee_fiscale=periode_obj.annee).order_by('seuil_minimal')
        # if not tranches.exists():
        #     messages.warning(request, f"Attention: Aucun barème trouvé pour l'année {periode_obj.annee}. Les calculs seront à 0.")

        ImportIRSATemporaire.objects.filter(employeur=employeur).delete()

        any_error = False
        objs_to_create = []

        # Définition des noms de colonnes longs pour éviter les erreurs de frappe
        COL_BRUT = "RÉMUNÉRATION BRUTE EN NUMÉRAIRE (KARAMA TSY AFA-KARATSAKA RAISINA LELAVOLA) ( B )"
        COL_AVANTAGE = "VALEUR DES AVANTAGES EN NATURE IMPOSABLES (SANDAN'NY TOMBOTSOA TSY ARA-BOLA IHARAN'NY HETRA) ( C )"
        COL_PENSION = "RETENUE ET VERSEMENT EN VUE DE LA CONSTITUTION DE PENSION OU DE RETRAITE (LATSAKEMBOKA ESORINA HO AN'NY FISOTROAN-DRONONO) ( D )"
        COL_SANTE = "RETENUE AU TITRE DE COTISATION OUVRIÈRE DUE À UNE ORGANISATION SANITAIRE (LATSAKEMBOKA HO AN'NY FAHASALAMAN'NY MPIASA) ( E )"
        COL_RNI = "REVENUS NETS IMPOSABLES (KARAMA SY NY TOA AZY AFA-KARATSAKA AMERANA NY HETRA) ( F = B + C - D - E )"
        COL_NET_EXCEL = "IMPÔT NET RETENU (HETRA ALOA AFA-KARATSAKA) ( I = G - H )"
        COL_BRUT_IMPOT = "IMPÔT BRUT CORRESPONDANT (HETRA TANDRIFIN'IZANY) ( G )"
        # tsy ao ny reduction
        for index, row in df.iterrows():
            try:
                # Helper pour convertir en Decimal proprement
                def to_dec(val):
                    try: return Decimal(str(val))
                    except: return Decimal('0.00')

                brut = to_dec(row.get(COL_BRUT, 0))
                avantage = to_dec(row.get(COL_AVANTAGE, 0))
                pension = to_dec(row.get(COL_PENSION, 0))
                cotisation = to_dec(row.get(COL_SANTE, 0))
                rni_excel = to_dec(row.get(COL_RNI, 0))
                impot_net_excel = to_dec(row.get(COL_NET_EXCEL, 0))
                impot_brut_excel = to_dec(row.get(COL_BRUT_IMPOT, 0))
                nb_charge = int(to_dec(row.get(Nb_charge, 0)))

                # Calculs
                rni_theo = (brut + avantage - pension - cotisation).quantize(Decimal('1.00'))
                
                impot_brut_theo = to_dec(calculer_irsa_brut(rni_theo))
                # for t in tranches:
                #     if rni_theo > t.seuil_minimal:
                #         plafond = t.seuil_maximal if t.seuil_maximal else rni_theo
                #         base = min(rni_theo, plafond) - t.seuil_minimal
                #         impot_brut_theo += base * (t.taux / Decimal('100'))
                reduction_theo = to_dec(calculer_reduction_charge(nb_charge))
               
                impot_net_theo = max(impot_brut_theo - reduction_theo, 3000.0)
                
                est_valide = abs(impot_net_excel - impot_net_theo) <= 2 and abs(rni_excel - rni_theo) <= 2
                if not est_valide: any_error = True

                objs_to_create.append(ImportIRSATemporaire(
                    employeur=employeur,
                    num_cnaps=str(row.get(num_cnaps, '')),
                    nom_prenom=str(row.get(nom_prenoms, '')),
                    cin=str(row.get(cin, '')),
                    fonction=str(row.get(fonction, '')),
                    remuneration_brute=brut,
                    avantages_nature=avantage,
                    pension=pension,
                    cotisation_sante=cotisation,
                    revenu_net=rni_excel,
                    revenu_net_theo=rni_theo,
                    impot_brut=impot_brut_excel,
                    personnes_charge=nb_charge,
                    reduction_charge=reduction_theo,
                    impot_net=impot_net_excel,
                    impot_net_theo=impot_net_theo,
                    est_valide=est_valide,
                    statut=ImportIRSATemporaire.StatusChoices.IMPORTE
                ))
            except Exception as line_err:
                logger.error(f"Erreur à la ligne {index}: {line_err}")
                continue # On ignore la ligne corrompue pour ne pas stopper tout l'import

        if not objs_to_create:
            raise ValueError("Aucune donnée valide n'a pu être extraite du fichier.")

        ImportIRSATemporaire.objects.bulk_create(objs_to_create)
        rows = ImportIRSATemporaire.objects.filter(employeur=employeur)

        return render(request, "annexe/annexe_preview.html", {
            "rows": rows,
            "any_error": any_error,
            "periode": periode_obj
        })

    except Exception as e:
        logger.exception("Erreur critique lors de la lecture de l'annexe")
        messages.error(request, f"Erreur : {str(e)}")
        return redirect("upload_annexe")
#------------------------------------------------------------------------------------
@login_required
def convertir_en_brouillon(request):
    employeur = request.user.employeur
    
    # On récupère les lignes qui viennent d'être injectées par l'Excel
    lignes_importees = ImportIRSATemporaire.objects.filter(
        employeur=employeur, 
        statut=ImportIRSATemporaire.StatusChoices.IMPORTE
    )

    if not lignes_importees.exists():
        messages.warning(request, "Aucune donnée importée trouvée.")
        return redirect('upload_annexe')
    lignes_importees.update(statut=ImportIRSATemporaire.StatusChoices.BROUILLON)
    
    messages.success(request, "Les données ont été préparées. Vous pouvez maintenant les vérifier.")
    return redirect('detail_import_brouillon')

from django.db.models import Q, Sum
from django.core.paginator import Paginator
from django.shortcuts import render, get_object_or_404
from django.contrib.auth.decorators import login_required

from django.db.models import Q, Sum
from django.core.paginator import Paginator
from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect
from .models import ImportIRSATemporaire, DeclarationIRSA  # Assurez-vous des imports

@login_required
def detail_import_brouillon(request):
    employeur = request.user.employeur
    query = request.GET.get('q', '')
    periode_id = request.session.get('current_periode_id')

    if not periode_id:
        messages.error(request, "Session expirée ou période non définie.")
        return redirect('presentation')

    # --- RÉCUPÉRATION SÉCURISÉE DE LA DÉCLARATION ---
    # On cherche d'abord si elle existe pour cette période/employeur
    declaration = DeclarationIRSA.objects.filter(
        employeur=employeur, 
        periode_id=periode_id
    ).first()

    # Si elle n'existe pas du tout, on la crée en statut 'brouillon' (minuscule selon votre modèle)
    if not declaration:
        declaration = DeclarationIRSA.objects.create(
            employeur=employeur,
            periode_id=periode_id,
            statut='brouillon'
        )

    # --- RÉCUPÉRATION DES LIGNES (IMPORT TEMPORAIRE) ---
    # Ici on utilise bien la constante BROUILLON ('BROUILLON' majuscule en base)
    lignes_list = ImportIRSATemporaire.objects.filter(
        employeur=employeur,
        statut=ImportIRSATemporaire.StatusChoices.BROUILLON
    ).order_by('nom_prenom')
    
    # Filtre de recherche
    if query:
        lignes_list = lignes_list.filter(
            Q(nom_prenom__icontains=query) | 
            Q(num_cnaps__icontains=query) |
            Q(cin__icontains=query)
        )

    # Totaux (On s'assure que ce soit 0 si None)
    stats = lignes_list.aggregate(
        total_irsa=Sum('impot_net_theo'),
        total_brut=Sum('remuneration_brute')
    )

    # Pagination
    paginator = Paginator(lignes_list, 10)
    page_number = request.GET.get('page')
    lignes_page = paginator.get_page(page_number)

    # Vérification des erreurs de calcul (est_valide=False)
    any_error = lignes_list.filter(est_valide=False).exists()

    context = {
        "rows": lignes_page,
        "total_irsa": stats['total_irsa'] or 0,
        "total_brut": stats['total_brut'] or 0,
        "query": query,
        "any_error": any_error,
        "declaration": declaration, # Crucial pour l'URL du bouton dans le template
        "periode_id": periode_id,
    }

    if request.headers.get('x-requested-with') == 'XMLHttpRequest':
        return render(request, "annexe/partials/table_brouillon.html", context)

    return render(request, "annexe/detail_brouillon.html", context)

from django.views.decorators.http import require_POST

@login_required
@require_POST
def supprimer_ligne_temp(request, pk):
    ligne = get_object_or_404(
        ImportIRSATemporaire, 
        pk=pk, 
        employeur=request.user.employeur,
        statut=ImportIRSATemporaire.StatusChoices.BROUILLON
    )
    
    nom = ligne.nom_prenom
    ligne.delete()
    
    messages.success(request, f"Le salarié {nom} a été retiré du brouillon.")
    return redirect('detail_import_brouillon')

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.contrib import messages
from decimal import Decimal
from .models import ImportIRSATemporaire
from utilisateurs.models import Employe

@login_required
def ajouter_employe_brouillon(request):
    employeur = request.user.employeur

    if request.method == "POST":
        # 1. Récupération des données
        nom = request.POST.get('nom_prenom', '').strip()
        cin = request.POST.get('cin', '').strip()
        cnaps = request.POST.get('num_cnaps', '').strip()
        
        # 2. Vérification des doublons (CIN et CNaPS)
        # On cherche dans le Brouillon ET dans la base réelle des Employés
        doublon_brouillon = ImportIRSATemporaire.objects.filter(
            employeur=employeur, 
            statut="BROUILLON"
        ).filter(Q(cin=cin) | Q(num_cnaps=cnaps)).exists()

        doublon_base = Employe.objects.filter(
            employeur=employeur
        ).filter(Q(cin=cin) | Q(num_cnaps=cnaps)).exists()

        if doublon_brouillon or doublon_base:
            messages.error(request, f"Erreur : Un employé avec le CIN {cin} ou CNaPS {cnaps} existe déjà.")
            return render(request, "annexe/ajouter_employe.html") # Reste sur la page avec les données

        try:
            with transaction.atomic():
                # 3. Extraction des valeurs numériques
                brut = Decimal(request.POST.get('brut', '0'))
                avantage = Decimal(request.POST.get('avantage', '0'))
                sante = Decimal(request.POST.get('sante', '0'))
                nb_enfants = int(request.POST.get('charges', '0'))

                # 4. Calculs de sécurité côté serveur (Barème Madagascar)
                pension = (brut * Decimal('0.01')).quantize(Decimal('1'))
                rni = max(Decimal('0'), (brut + avantage) - (pension + sante))
                
                # Calcul IRSA Rapide
                irsa_brut = Decimal('0')
                if rni > 350000:
                    if rni <= 400000: irsa_brut = (rni - 350000) * Decimal('0.05')
                    elif rni <= 500000: irsa_brut = Decimal('2500') + (rni - 400000) * Decimal('0.10')
                    elif rni <= 600000: irsa_brut = Decimal('12500') + (rni - 500000) * Decimal('0.15')
                    elif rni <= 4000000: irsa_brut = Decimal('27500') + (rni - 600000) * Decimal('0.20')
                    else: irsa_brut = Decimal('707500') + (rni - 4000000) * Decimal('0.25')

                reduction = nb_enfants * Decimal('2000')
                irsa_net = max(irsa_brut - reduction, Decimal('0'))
                if rni > 350000 and irsa_net < 3000:
                    irsa_net = Decimal('3000')

                # 5. Création de la ligne de brouillon
                ImportIRSATemporaire.objects.create(
                    employeur=employeur,
                    nom_prenom=nom,
                    cin=cin,
                    num_cnaps=cnaps,
                    fonction=request.POST.get('fonction', ''),
                    remuneration_brute=brut,
                    avantages_nature=avantage,
                    pension=pension,
                    reduction_charge=reduction,
                    impot_brut=brut,
                    cotisation_sante=sante,
                    personnes_charge=nb_enfants,
                    revenu_net_theo=rni,
                    impot_net_theo=irsa_net.quantize(Decimal('1')),
                    statut="BROUILLON",
                    est_valide=True
                )

                messages.success(request, f"L'employé {nom} a été ajouté au brouillon avec un IRSA de {irsa_net:,.0f} Ar.")
                return redirect('detail_import_brouillon')

        except Exception as e:
            messages.error(request, f"Une erreur technique est survenue : {str(e)}")
            
    return render(request, "annexe/ajouter_employe.html")
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from decimal import Decimal
from django.db.models import Q
from .models import ImportIRSATemporaire # Remplacez par votre modèle

def modifier_employe_brouillon(request, pk):
    # On récupère l'employé spécifique du brouillon
    # On cherche l'item dont la déclaration appartient à l'utilisateur actuel
    item = get_object_or_404(
        ImportIRSATemporaire, 
        pk=pk, 
        employeur=request.user.employeur
    )    
    if request.method == "POST":
        # 1. Récupération des données du formulaire
        nom = request.POST.get('nom_prenom', '').strip()
        cin = request.POST.get('cin', '').strip()
        cnaps = request.POST.get('num_cnaps', '').strip()

        # 2. Vérification des doublons (exclure l'item actuel)
        doublon = ImportIRSATemporaire.objects.filter(
            employeur=request.user.employeur,
            statut="BROUILLON"
        ).filter(Q(cin=cin) | Q(num_cnaps=cnaps)).exclude(pk=pk).exists()

        if doublon:
            messages.error(request, f"Impossible de modifier : Le CIN {cin} ou CNaPS {cnaps} est déjà utilisé par un autre employé dans ce brouillon.")
        else:
            try:
                # 3. Calculs de sécurité côté serveur
                brut = Decimal(request.POST.get('brut', '0'))
                avantage = Decimal(request.POST.get('avantage', '0'))
                sante = Decimal(request.POST.get('sante', '0'))
                nb_enfants = int(request.POST.get('charges', '0'))

                # Calculs IRSA (Logique identique à l'ajout)
                pension = (brut * Decimal('0.01')).quantize(Decimal('1'))
                rni = max(Decimal('0'), (brut + avantage) - (pension + sante))
                
                # Barème simplifié pour la démo (à ajuster selon votre barème exact)
                irsa_brut = Decimal('0')
                if rni > 350000:
                    if rni <= 400000: irsa_brut = (rni - 350000) * Decimal('0.05')
                    elif rni <= 500000: irsa_brut = Decimal('2500') + (rni - 400000) * Decimal('0.10')
                    elif rni <= 600000: irsa_brut = Decimal('12500') + (rni - 500000) * Decimal('0.15')
                    elif rni <= 4000000: irsa_brut = Decimal('27500') + (rni - 600000) * Decimal('0.20')
                    else: irsa_brut = Decimal('707500') + (rni - 4000000) * Decimal('0.25')

                reduction = nb_enfants * Decimal('2000')
                irsa_net = max(irsa_brut - reduction, Decimal('0'))
                if rni > 350000 and irsa_net < 3000: irsa_net = Decimal('3000')

                # 4. Mise à jour de l'objet
                item.nom_prenom = nom
                item.cin = cin
                item.num_cnaps = cnaps
                item.fonction = request.POST.get('fonction', '')
                item.remuneration_brute = brut
                item.avantages_nature = avantage
                item.pension = pension
                item.cotisation_sante = sante
                item.personnes_charge = nb_enfants
                item.revenu_net_theo = rni
                item.impot_net_theo = irsa_net.quantize(Decimal('1'))
                item.save()

                messages.success(request, f"Modifications enregistrées pour {nom}.")
                return redirect('detail_import_brouillon') # Redirige vers la table
            except Exception as e:
                messages.error(request, f"Erreur lors de la mise à jour : {str(e)}")

    # Pour le GET : on utilise le même template que l'ajout
    return render(request, "annexe/ajouter_employe.html", {'item': item, 'is_edit': True})