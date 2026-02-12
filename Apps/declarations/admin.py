from django.contrib import admin
from django.utils import timezone
from django.shortcuts import get_object_or_404, redirect
from django.db.models import Sum, Q
from django.http import HttpResponse
from django.template.loader import render_to_string
from django.urls import path
from django.utils.html import format_html
from weasyprint import HTML

# Imports Unfold
from unfold.admin import ModelAdmin, StackedInline
from unfold.decorators import action

# Imports de vos modèles
from declarations.models import (
    PeriodeFiscale, DeclarationIRSA, LigneDeclarationIRSA, 
    TypeDeduction, TypeRevenu, DetailDeduction, DetailRevenu, 
    RegimeSpecialIRSA, SituationFamiliale, TrancheBareme, ImportIRSATemporaire
)
from utilisateurs.models import Employeur, Employe

# --- 1. CONFIGURATION DU DASHBOARD ---

original_each_context = admin.site.each_context

def new_each_context(request):
    context = original_each_context(request)
    try:
        maintenant = timezone.now()
        retards_query = PeriodeFiscale.objects.filter(
            date_limite__lt=maintenant.date()
        ).exclude(
            declarations__statut__in=['confirme', 'valide', 'archive']
        ).distinct()

        context['dashboard_stats'] = {
            'total_periodes': PeriodeFiscale.objects.count(),
            'periodes_en_retard': retards_query.count(),
            'total_declarations': DeclarationIRSA.objects.count(),
            'total_employeurs': Employeur.objects.count(),
            'urgent_a_valider': DeclarationIRSA.objects.filter(statut='confirme').count(),
            'brouillons_en_cours': DeclarationIRSA.objects.filter(statut='brouillon').count(),
            'total_alertes': retards_query.count() + DeclarationIRSA.objects.filter(statut='confirme').count()
        }
    except Exception:
        context['dashboard_stats'] = None
    return context

admin.site.each_context = new_each_context

# --- 2. FILTRES PERSONNALISÉS ---

class FiltreRetardataire(admin.SimpleListFilter):
    title = 'Statut de dépôt'
    parameter_name = 'retard'

    def lookups(self, request, model_admin):
        return (('oui', '⚠️ En retard'),)

    def queryset(self, request, queryset):
        if self.value() == 'oui':
            return queryset.filter(
                date_limite__lt=timezone.now().date()
            ).exclude(
                declarations__statut__in=['confirme', 'valide', 'archive']
            )

# --- 3. INLINES ---

class LigneDeclarationIRSAInline(StackedInline):
    model = LigneDeclarationIRSA
    extra = 0
    tab = True 
    autocomplete_fields = ['employe']
    readonly_fields = ('date_lecture',)

# --- 4. CONFIGURATION DES ADMINS ---

@admin.register(PeriodeFiscale)
class PeriodeFiscaleAdmin(ModelAdmin):
    list_display = ('employeur', 'annee', 'get_mois_display', 'periode_type', 'date_limite', 'get_statut_depot')
    list_filter = (FiltreRetardataire, 'annee', 'periode_type')
    list_filter_sheet = True 
    search_fields = ['annee', 'employeur__raison_sociale', 'employeur__nif']
    autocomplete_fields = ['employeur']

    @admin.display(description='Mois')
    def get_mois_display(self, obj):
        return obj.date_debut.strftime('%B').capitalize()

    # CORRECTION : Suppression de label=True pour éviter le TypeError
    @admin.display(description='État de dépôt')
    def get_statut_depot(self, obj):
        depot_existe = obj.declarations.filter(statut__in=['confirme', 'valide', 'archive']).exists()
        
        if not depot_existe and obj.date_limite < timezone.now().date():
            # On utilise les classes Tailwind natives de Unfold pour le badge
            return format_html(
                '<span class="font-bold px-2 py-1 rounded-md text-xs bg-red-100 text-red-700 dark:bg-red-500/20 dark:text-red-400">⚠️ EN RETARD</span>'
            )
        elif not depot_existe:
            return "En attente"
        
        return format_html(
            '<span class="font-bold px-2 py-1 rounded-md text-xs bg-green-100 text-green-700 dark:bg-green-500/20 dark:text-green-400">✅ Déposé</span>'
        )

@admin.register(DeclarationIRSA)
class DeclarationIRSAAdmin(ModelAdmin):
    ordering = ('employeur__raison_sociale', '-periode__annee', '-periode__date_debut')
    list_display = ('numero_document', 'get_employeur_nif', 'employeur', 'periode', 'statut_badge', 'total_irsa', 'action_buttons')
    list_filter = ('statut', 'periode', 'employeur')
    list_filter_sheet = True
    search_fields = ('numero_document', 'employeur__raison_sociale', 'employeur__nif')
    autocomplete_fields = ['employeur', 'periode']
    inlines = [LigneDeclarationIRSAInline]

    actions_list = ["marquer_comme_archive"] 
    actions_row = ["generer_pdf_row"]       

    @action(description="📦 Archiver", icon="archive")
    def marquer_comme_archive(self, request, queryset):
        queryset.update(statut='archive')

    @action(description="📄 PDF", icon="description")
    def generer_pdf_row(self, request, object_id):
        return redirect(f"/admin/declarations/declarationirsa/{object_id}/pdf/")

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        if 'statut__exact' not in request.GET:
            return qs.exclude(statut='archive')
        return qs

    @admin.display(description='NIF')
    def get_employeur_nif(self, obj):
        return obj.employeur.nif

    # CORRECTION : Unfold gère les couleurs si on retourne un tuple (Valeur, Couleur)
    @admin.display(description='Statut')
    def statut_badge(self, obj):
        display_text = obj.get_statut_display()
        colors = {
            'brouillon': 'neutral',
            'confirme': 'warning',
            'valide': 'success',
            'archive': 'info',
        }
        # En retournant ce tuple, Unfold crée automatiquement le badge coloré
        return display_text, colors.get(obj.statut, 'neutral')

    @admin.display(description='Actions rapides')
    def action_buttons(self, obj):
        return format_html(
            '<a href="{}/pdf/" target="_blank" class="font-bold text-primary-600">Imprimer</a>',
            obj.id
        )

    fieldsets = (
        ('Informations Générales', {
            'fields': ('employeur', 'periode', 'statut', 'numero_document'),
        }),
        ('Audit Financier', {
            'fields': (('total_salaire_imposable', 'total_irsa'), 'nombre_travailleurs_total'),
        }),
    )

    def get_urls(self):
        return [path('<int:declaration_id>/pdf/', self.admin_site.admin_view(self.generer_feedback_pdf))] + super().get_urls()

    def generer_feedback_pdf(self, request, declaration_id):
        declaration = get_object_or_404(DeclarationIRSA.objects.select_related('employeur', 'periode'), pk=declaration_id)
        lignes = declaration.lignes.all()
        lignes_ids = lignes.values_list('id', flat=True)
        
        r2_avantages = DetailRevenu.objects.filter(ligne_id__in=lignes_ids, type_revenu__code='AVANT_NATURE').aggregate(total=Sum('montant'))['total'] or 0
        r5_cnaps = DetailDeduction.objects.filter(ligne_id__in=lignes_ids, type_deduction__code='COT_CNAPS').aggregate(total=Sum('montant'))['total'] or 0
        r3_brut = DetailRevenu.objects.filter(ligne_id__in=lignes_ids).aggregate(total=Sum('montant'))['total'] or 0
        
        total_charges = SituationFamiliale.objects.filter(employe_id__in=lignes.values_list('employe_id', flat=True), date_debut__lte=declaration.periode.date_debut).aggregate(total=Sum('nombre_personnes_charge'))['total'] or 0
        r22_reduction = total_charges * 2000
        
        context = {
            'dec': declaration, 'emp': declaration.employeur,
            'r1': declaration.nombre_travailleurs_total, 'r2': r2_avantages,
            'r3': r3_brut, 'r5': r5_cnaps, 'r6': declaration.total_salaire_imposable,
            'r7': declaration.total_irsa, 'r20': declaration.total_irsa,
            'r22': r22_reduction, 'r24': max(0, declaration.total_irsa - r22_reduction),
        }

        html_string = render_to_string('components/formulaire_officiel.html', context)
        response = HttpResponse(content_type='application/pdf')
        response['Content-Disposition'] = f'inline; filename="IRSA_{declaration.numero_document}.pdf"'
        HTML(string=html_string, base_url=request.build_absolute_uri()).write_pdf(response)
        return response

# --- 5. ENREGISTREMENTS RESTANTS ---
admin.site.register(TypeDeduction, ModelAdmin)
admin.site.register(TypeRevenu, ModelAdmin)
admin.site.register(TrancheBareme, ModelAdmin)
admin.site.register(ImportIRSATemporaire, ModelAdmin)
admin.site.register(RegimeSpecialIRSA, ModelAdmin)