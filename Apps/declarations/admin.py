from django.contrib import admin
from declarations.models import PeriodeFiscale, DeclarationIRSA, LigneDeclarationIRSA, TypeDeduction, TypeRevenu, DetailDeduction, DetailRevenu, RegimeSpecialIRSA, SituationFamiliale, TrancheBareme,ImportIRSATemporaire 
from utilisateurs.models import Employeur, Employe
from declarations.views import declaration
# Register your models here.
admin.site.register(PeriodeFiscale)
admin.site.register(DeclarationIRSA)
admin.site.register(LigneDeclarationIRSA)
admin.site.register(TypeDeduction)
admin.site.register(TypeRevenu)
admin.site.register(DetailDeduction)
admin.site.register(DetailRevenu)
admin.site.register(SituationFamiliale)
admin.site.register(RegimeSpecialIRSA)
admin.site.register(TrancheBareme)
admin.site.register(ImportIRSATemporaire)

# admin.py

from django.contrib import admin
from django.utils import timezone

# 1. On sauvegarde la fonction index originale de Django
admin_index_original = admin.site.index

# 2. On crée notre nouvelle fonction index
def index_personnalise(request, extra_context=None):
    extra_context = extra_context or {}
    
    # Calcul des statistiques pour l'agent fiscal
    extra_context['dashboard_stats'] = {
        'total_periodes': PeriodeFiscale.objects.count(),
        'periodes_en_retard': PeriodeFiscale.objects.filter(date_limite__lt=timezone.now()).count(),
        'total_declarations': DeclarationIRSA.objects.count(),
        'total_employeurs': Employeur.objects.count(), 
    }
    
    # On appelle la fonction originale avec notre contexte enrichi
    return admin_index_original(request, extra_context=extra_context)

# 3. On remplace la méthode de l'objet admin.site par notre fonction
admin.site.index = index_personnalise