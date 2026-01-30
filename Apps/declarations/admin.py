from django.contrib import admin
from declarations.models import PeriodeFiscale, DeclarationIRSA, LigneDeclarationIRSA, TypeDeduction, TypeRevenu, DetailDeduction, DetailRevenu, RegimeSpecialIRSA, SituationFamiliale, TrancheBareme,ImportIRSATemporaire 
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