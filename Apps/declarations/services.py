from django.db import transaction
from django.shortcuts import get_object_or_404
from .models import (
    PeriodeFiscale,
    ImportIRSATemporaire, LigneDeclarationIRSA, DetailRevenu, 
    DetailDeduction, TypeRevenu, TypeDeduction, SituationFamiliale, DeclarationIRSA, RegimeSpecialIRSA
)
from django.db import transaction
from django.db.models import Q
from django.shortcuts import get_object_or_404, redirect
from django.contrib import messages
from utilisateurs.models import Employe, Employeur


@transaction.atomic
def valider_brouillon_vers_declaration(request, declaration_id):
    if request.method == "POST":
        # 1. Récupération de la déclaration
        declaration = get_object_or_404(
            DeclarationIRSA, 
            pk=declaration_id, 
            employeur=request.user.employeur
        )
        
        # 2. Récupération des lignes du brouillon
        lignes_brouillon = ImportIRSATemporaire.objects.filter(
            employeur=request.user.employeur,
            statut='BROUILLON'
        )

        if not lignes_brouillon.exists():
            messages.warning(request, "Votre brouillon est vide.")
            return redirect('detail_import_brouillon')

        try:
            # Récupération des types de base (Assurez-vous qu'ils existent en BD)
            type_sal = TypeRevenu.objects.get(code='SAL_BASE')
            type_av = TypeRevenu.objects.get(code='AVANT_NATURE')
            type_retr = TypeDeduction.objects.get(code='COT_RETRAITE')
            type_sante = TypeDeduction.objects.get(code='COT_CNAPS')

            total_travailleurs = 0
            masse_globale = 0

            for b in lignes_brouillon:
                # --- A. GESTION DE L'EMPLOYÉ ---
                # On identifie l'employé par son CNaPS (unique pour un employeur)
                employe, _ = Employe.objects.get_or_create(
                    num_cnaps=b.num_cnaps,
                    employeur=request.user.employeur,
                    defaults={
                        'nom_prenom': b.nom_prenom, 
                        'cin': b.cin, 
                        'fonction': b.fonction
                    }
                )

                # --- B. LIGNE DE DÉCLARATION (Correction de l'erreur UNIQUE) ---
                # update_or_create vérifie si le couple (declaration, employe) existe déjà
                ligne, created = LigneDeclarationIRSA.objects.update_or_create(
                    declaration=declaration,
                    employe=employe,
                    defaults={
                        'salaire_imposable': b.revenu_net_theo,
                        'irsa_due': b.impot_net_theo
                    }
                )

                # --- C. NETTOYAGE DES DÉTAILS PRÉCÉDENTS ---
                # Si la ligne existait déjà, on supprime les anciens revenus/déductions
                # pour éviter les doublons lors de la création ci-dessous.
                if not created:
                    DetailRevenu.objects.filter(ligne=ligne).delete()
                    DetailDeduction.objects.filter(ligne=ligne).delete()

                # --- D. VENTILATION DES MONTANTS ---
                DetailRevenu.objects.create(ligne=ligne, type_revenu=type_sal, montant=b.remuneration_brute)
                if b.avantages_nature > 0:
                    DetailRevenu.objects.create(ligne=ligne, type_revenu=type_av, montant=b.avantages_nature)

                DetailDeduction.objects.create(ligne=ligne, type_deduction=type_retr, montant=b.pension)
                if b.cotisation_sante > 0:
                    DetailDeduction.objects.create(ligne=ligne, type_deduction=type_sante, montant=b.cotisation_sante)

                # --- E. SITUATION FAMILIALE ---
                # On utilise update_or_create ici aussi pour éviter les doublons de situation à la même date
                SituationFamiliale.objects.update_or_create(
                    employe=employe,
                    date_debut=declaration.periode.date_debut,
                    defaults={'nombre_personnes_charge': b.personnes_charge}
                )

                total_travailleurs += 1
                masse_globale += b.remuneration_brute

            # --- F. RÉGIME SPÉCIAL (GLOBAL) ---
            RegimeSpecialIRSA.objects.update_or_create(
                declaration=declaration,
                defaults={
                    'taux_unitaire_min': 2000, 
                    'nombre_travailleurs': total_travailleurs,
                    'masse_salaire_globale': masse_globale
                }
            )

            # --- G. FINALISATION ----total_brut et total_irsa pas encore à la base  ---------------------
            totaux = LigneDeclarationIRSA.objects.filter(
                declaration=declaration
            ).aggregate(
                total_irsa=Sum('irsa_due'),
                total_imposable=Sum('salaire_imposable'),
                nb_employes=Count('id')
            )
            declaration.total_irsa=totaux['total_irsa'] or 0
            declaration.total_salaire_imposable=totaux['total_imposable'] or 0
            declaration.nombre_travailleurs_total=totaux['nb_employes'] or 0
            declaration.statut = 'confirme'
            # declaration.total_irsa=sum(lignes_brouillon.impot_net_theo)
            declaration.save()

            # Nettoyage définitif du brouillon
            lignes_brouillon.delete() 

            messages.success(request, f"Déclaration confirmée avec succès !")
            return redirect('dashboard_employeur')

        except Exception as e:
            # En cas d'erreur, transaction.atomic annule tout ce qui a été fait dans le try
            messages.error(request, f"Erreur lors de la confirmation : {str(e)}")
            return redirect('detail_import_brouillon')
        
from django.db.models import Sum

def detail_recapitulatif_avant_confirmation(request, declaration_id):
    declaration = get_object_or_404(DeclarationIRSA, pk=declaration_id, employeur=request.user.employeur)
    
    # On récupère les lignes du brouillon
    rows = ImportIRSATemporaire.objects.filter(
        employeur=request.user.employeur, 
        statut='BROUILLON'
    )

    # Calcul des totaux pour le header
    stats = rows.aggregate(
        total_brut=Sum('remuneration_brute'),
        total_irsa=Sum('impot_net_theo'),
        total_rni=Sum('revenu_net_theo')
    )

    return render(request, 'declaration/recapitulatif.html', {
        'declaration': declaration,
        'rows': rows,
        'stats': stats
    })
from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.db.models import Sum, Count
from .models import DeclarationIRSA

from django.db.models import Count, Sum
from django.db.models.functions import ExtractMonth # Import important pour le tri par mois

@login_required
def liste_declarations_view(request):
    # 1. On filtre les déclarations de l'employeur
    # 2. On utilise select_related pour éviter les requêtes N+1 sur la période
    # 3. On extrait le mois de date_debut pour pouvoir trier dessus
    declarations = DeclarationIRSA.objects.filter(
        employeur=request.user.employeur
    ).select_related('periode').annotate(
        nb_employes=Count('lignes'),
        # Rappel : on utilise irsa_annote pour ne pas entrer en conflit avec le champ total_irsa
        irsa_annote=Sum('lignes__irsa_due'),
        # On crée un champ virtuel "mois_tri" basé sur la date de début
        mois_tri=ExtractMonth('periode__date_debut')
    ).order_by('-periode__annee', '-mois_tri', '-id')

    return render(request, 'declaration/liste_declarations.html', {
        'declarations': declarations
    })
import json
from django.db.models import Sum
from django.db.models.functions import TruncMonth
from django.core.serializers.json import DjangoJSONEncoder


from datetime import datetime, date

def get_deadline_info():
    today = date.today()
    # La deadline est le 15 de ce mois
    deadline = date(today.year, today.month, 15)
    
    # Si on a déjà dépassé le 15, la prochaine est le 15 du mois suivant
    if today > deadline:
        if today.month == 12:
            deadline = date(today.year + 1, 1, 15)
        else:
            deadline = date(today.year, today.month + 1, 15)
            
    jours_restants = (deadline - today).days
    
    # Déterminer le niveau d'alerte
    if jours_restants <= 3:
        status = "danger"  # Rouge
    elif jours_restants <= 7:
        status = "warning" # Orange
    else:
        status = "info"    # Bleu/Vert
        
    return {
        'deadline': deadline,
        'jours_restants': jours_restants,
        'status': status
    }

import json
from datetime import date
from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.db.models import Sum, Count, Q
from django.db.models.functions import TruncMonth
from .models import DeclarationIRSA, ImportIRSATemporaire

@login_required
def dashboard_employeur(request):
    employeur = request.user.employeur
    today = date.today()

    # --- 1. GESTION DYNAMIQUE DE LA DEADLINE (Le 15 du mois) ---
    deadline = date(today.year, today.month, 15)
    if today > deadline:
        # Si on a dépassé le 15, on calcule la deadline du mois prochain
        next_month = today.month % 12 + 1
        year = today.year + (1 if today.month == 12 else 0)
        deadline = date(year, next_month, 15)
            
    jours_restants = (deadline - today).days
    
    # Niveaux d'alerte UI
    if jours_restants <= 3:
        deadline_status = "danger"
    elif jours_restants <= 7:
        deadline_status = "warning"
    else:
        deadline_status = "info"

    # --- 2. STATISTIQUES POUR LE GRAPHIQUE (Évolution IRSA) ---
    # On récupère les 6 derniers mois confirmés
    stats_queryset = (
        DeclarationIRSA.objects.filter(
            employeur=employeur, 
            statut='valide'
        )
        .annotate(month=TruncMonth('periode__date_debut'))
        .values('month')
        .annotate(total=Sum('total_irsa'))
        .order_by('month')[:6]
    )

    labels = [s['month'].strftime("%b") for s in stats_queryset]
    data_values = [float(s['total']) for s in stats_queryset]

    # --- 3. KPIs (Indicateurs Clés) ---
    # Récupération de la toute dernière déclaration pour l'affichage de l'effectif
    derniere_decl = DeclarationIRSA.objects.filter(
        employeur=employeur,
        statut='valide'
    ).order_by('-periode__date_debut').first()

    # Total IRSA cumulé sur l'année civile en cours
    total_annuel = DeclarationIRSA.objects.filter(
        employeur=employeur,
        statut='valide',
        periode__annee=today.year
    ).aggregate(total=Sum('total_irsa'))['total'] or 0

    # Vérification si un brouillon est actuellement en cours (Saisie ou Excel)
    brouillon_count = ImportIRSATemporaire.objects.filter(
        employeur=employeur,
        statut='BROUILLON'
    ).count()

    # Liste des 5 dernières activités
    recent_declarations = DeclarationIRSA.objects.filter(
        employeur=employeur
    ).select_related('periode').order_by('-id')[:5]

    # --- 4. CONSTRUCTION DU CONTEXTE ---
    context = {
        # Graphique
        'chart_labels': json.dumps(labels),
        'chart_data': json.dumps(data_values),
        
        # Deadline
        'deadline_info': {
            'date': deadline,
            'jours': jours_restants,
            'status': deadline_status
        },
        
        # Chiffres clés
        'total_irsa_annuel': total_annuel,
        'nb_employes_actuel': derniere_decl.nombre_travailleurs_total if derniere_decl else 0,
        'brouillon_en_cours': brouillon_count,
        'recent_declarations': recent_declarations,
        'today': today,
    }

    return render(request, 'dashboard/employeur.html', context)

from django.contrib import messages
from django.shortcuts import get_object_or_404, redirect
from django.db import transaction
from .models import DeclarationIRSA

@login_required
@transaction.atomic
def valider_declaration(request, declaration_id):
    """
    Passe le statut de 'confirme' à 'valide'.
    C'est l'étape finale qui clôture le dossier fiscal du mois.
    """
    if request.method == "POST":
        # On s'assure que la déclaration appartient bien à l'employeur
        # et qu'elle est dans l'état 'confirme' uniquement
        declaration = get_object_or_404(
            DeclarationIRSA, 
            pk=declaration_id, 
            employeur=request.user.employeur,
            statut='confirme'
        )

        try:
            # Changement de statut
            declaration.statut = 'valide'
            declaration.save()

            # Optionnel : Générer ici un numéro de quittance ou de reçu
            # declaration.numero_quittance = "Q-2026-XXXX"
            # declaration.save()

            messages.success(
                request, 
                f"La déclaration {declaration.numero_document} est désormais validée et clôturée."
            )
        except Exception as e:
            messages.error(request, f"Erreur lors de la validation : {str(e)}")
        
        return redirect('liste_declarations')
    
    return redirect('liste_declarations')

from django.http import JsonResponse
from django.views.decorators.http import require_POST
from .models import ImportIRSATemporaire

# 1. La vue qui affiche la page
def valider_saisie_manuelle(request):
    temp_periode = request.session.get('temp_periode_fiscale')
    
    # On récupère les employés déjà saisis pour ne pas les perdre au rafraîchissement
    employes_existants = ImportIRSATemporaire.objects.filter(
        employeur=request.user.employeur,
        statut='BROUILLON'
    )
    
    return render(request, "declaration/saisie_manuelle.html", {
        'periode': temp_periode,
        'employes_deja_saisis': employes_existants
    })

# 2. La vue AJAX (Appelée par le bouton "Ajouter" du modal)
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from .models import ImportIRSATemporaire

from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from .models import ImportIRSATemporaire

@require_http_methods(["POST"])
def ajax_ajouter_employe(request):
    try:
        # On récupère les données avec les noms de clés correspondants au FormData JS
        obj = ImportIRSATemporaire.objects.create(
            employeur=request.user.employeur,
            nom_prenom=request.POST.get('nom_prenom'),
            num_cnaps=request.POST.get('num_cnaps'),
            cin=request.POST.get('cin'),
            fonction=request.POST.get('fonction'),
            
            # Valeurs numériques de base
            remuneration_brute=float(request.POST.get('remuneration_brute', 0)),
            avantages_nature=float(request.POST.get('avantages_nature', 0)),
            pension=float(request.POST.get('pension', 0)),
            cotisation_sante=float(request.POST.get('cotisation_sante', 0)),
            personnes_charge=int(request.POST.get('personnes_charge', 0)),
            
            # Nouveaux champs calculés par le JS pour éviter les valeurs nulles
            revenu_net=float(request.POST.get('revenu_net', 0)),
            impot_brut=float(request.POST.get('impot_brut', 0)),
            reduction_charge=float(request.POST.get('reduction_charge', 0)),
            impot_net=float(request.POST.get('impot_net', 0)),
            
            # Champs théoriques (doublons de sécurité pour votre logique système)
            revenu_net_theo=float(request.POST.get('revenu_net_theo', 0)),
            impot_net_theo=float(request.POST.get('impot_net_theo', 0)),
            
            statut='BROUILLON'
        )
        
        return JsonResponse({
            'status': 'success', 
            'id': obj.id,
            'message': 'Employé enregistré avec succès'
        })

    except ValueError as e:
        return JsonResponse({'status': 'error', 'message': 'Données numériques invalides'}, status=400)
    except Exception as e:
        return JsonResponse({'status': 'error', 'message': str(e)}, status=400)

@require_http_methods(["DELETE"])
def ajax_supprimer_employe(request, id):
    try:
        emp = ImportIRSATemporaire.objects.get(id=id, employeur=request.user.employeur)
        emp.delete()
        return JsonResponse({'status': 'success'})
    except:
        return JsonResponse({'status': 'error'}, status=404)
from .models import PeriodeFiscale

from datetime import datetime
from django.db import transaction

@login_required
@transaction.atomic
def convertir_en_brouillon_SM(request):
    employeur = request.user.employeur
    temp_periode = request.session.get('temp_periode_fiscale')

    if not temp_periode:
        messages.error(request, "Session expirée. Veuillez recommencer.")
        return redirect('upload_annexe')

    # 1. Conversion des chaînes de caractères en objets DATE Python
    try:
        # On convertit les strings 'YYYY-MM-DD' en objets date
        d_debut = datetime.strptime(temp_periode['date_debut'], '%Y-%m-%d').date()
        d_fin = datetime.strptime(temp_periode['date_fin'], '%Y-%m-%d').date()
        
        # Pour la date limite, on utilise celle en session ou on en calcule une par défaut (ex: le 15 du mois suivant)
        if temp_periode.get('date_limite'):
            d_limite = datetime.strptime(temp_periode['date_limite'], '%Y-%m-%d').date()
        else:
            # Sécurité si date_limite est absente
            d_limite = d_fin 
            
    except (ValueError, TypeError) as e:
        messages.error(request, f"Erreur de formatage de date : {str(e)}")
        return redirect('upload_annexe')

    # 2. Récupération des lignes temporaires
    lignes_importees = ImportIRSATemporaire.objects.filter(employeur=employeur)
    if not lignes_importees.exists():
        messages.warning(request, "Aucune donnée trouvée dans votre saisie.")
        return redirect('upload_annexe')

    # 3. CRÉATION DE LA PÉRIODE (Respectant strictement votre classe PeriodeFiscale)
    # Note : Pas de champ 'employeur' ici comme vous l'avez noté
    periode_obj = PeriodeFiscale.objects.create(
        annee=d_debut.year,  # Maintenant .year fonctionne sur l'objet date
        date_debut=d_debut,
        date_fin=d_fin,
        date_limite=d_limite,
        periode_type=temp_periode.get('periode_type', 'mensuel')
    )

    # 4. CRÉATION DE LA DÉCLARATION
    # C'est ici que l'on lie tout à l'employeur
    declaration = DeclarationIRSA.objects.create(
        employeur=employeur,
        periode=periode_obj,
        statut='brouillon'
    )

    # 5. Mise à jour du statut des lignes
    lignes_importees.update(statut='BROUILLON')

    # 6. Nettoyage et session
    request.session['current_periode_id'] = periode_obj.id
    request.session['current_declaration_id'] = declaration.id
    if 'temp_periode_fiscale' in request.session:
        del request.session['temp_periode_fiscale']
    
    return redirect('detail_import_brouillon')

from django.shortcuts import get_object_or_404
from django.db.models import Sum
from django.conf import settings
from django.http import HttpResponse
from django.template.loader import render_to_string
from weasyprint import HTML
import tempfile

from .models import (
    DeclarationIRSA, LigneDeclarationIRSA, DetailRevenu, 
    DetailDeduction, SituationFamiliale, RegimeSpecialIRSA
)

def export_declaration_pdf(request, declaration_id):
    # 1. Récupération de la déclaration et de l'employeur
    declaration = get_object_or_404(
        DeclarationIRSA.objects.select_related('employeur', 'periode'), 
        pk=declaration_id
    )
    
    # 2. Agrégation des données pour les rubriques
    lignes = declaration.lignes.all()
    lignes_ids = lignes.values_list('id', flat=True)
    employes_ids = lignes.values_list('employe_id', flat=True)

    # Rubrique 2: Avantages en nature
    r2_avantages = DetailRevenu.objects.filter(
        ligne_id__in=lignes_ids, 
        type_revenu__code='AVANT_NATURE'
    ).aggregate(total=Sum('montant'))['total'] or 0

    # Rubrique 5: CNaPS (Cotisation ouvrière)
    r5_cnaps = DetailDeduction.objects.filter(
        ligne_id__in=lignes_ids, 
        type_deduction__code='COT_CNAPS'
    ).aggregate(total=Sum('montant'))['total'] or 0

    # Rubrique 6: RNI (Déjà stocké dans votre modèle)
    r6_rni = declaration.total_salaire_imposable

    # Rubrique 3: Rémunération Brute (RNI + Déductions)
    # Note: On peut aussi sommer tous les DetailRevenu
    r3_brut = DetailRevenu.objects.filter(
        ligne_id__in=lignes_ids
    ).aggregate(total=Sum('montant'))['total'] or 0

    # Rubrique 22: Réduction pour charge de famille (2000 Ar / personne)
    total_charges = SituationFamiliale.objects.filter(
        employe_id__in=employes_ids,
        date_debut__lte=declaration.periode.date_debut
    ).aggregate(total=Sum('nombre_personnes_charge'))['total'] or 0
    r22_reduction = total_charges * 2000

    # Rubrique 24: Impôt net à payer
    r24_net = max(0, declaration.total_irsa - r22_reduction)

    # 3. Préparation du contexte pour le template
    context = {
        'dec': declaration,
        'emp': declaration.employeur,
        'r1': declaration.nombre_travailleurs_total,
        'r2': r2_avantages,
        'r3': r3_brut,
        'r5': r5_cnaps,
        'r6': r6_rni,
        'r7': declaration.total_irsa,
        'r20': declaration.total_irsa,
        'r22': r22_reduction,
        'r24': r24_net,
        # On passe la date d'aujourd'hui pour le dépôt
        'date_depot': declaration.date_declaration,
    }

    # 4. Génération du PDF avec WeasyPrint
    html_string = render_to_string('components/formulaire_officiel.html', context)
    html = HTML(string=html_string, base_url=request.build_absolute_uri())
    
    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = f'inline; filename="IRSA_{declaration.numero_document}.pdf"'
    
    # Création du PDF en mémoire
    html.write_pdf(response)
    
    return response