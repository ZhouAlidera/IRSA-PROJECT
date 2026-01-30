from django import forms
from .models import PeriodeFiscale

class PeriodeFiscaleForm(forms.ModelForm):
    class Meta:
        model = PeriodeFiscale
        fields = ['date_debut', 'date_fin', 'periode_type', 'date_limite', 'annee']
        widgets = {
            'date_debut': forms.DateInput(attrs={'type': 'date', 'id': 'id_date_debut'}),
            'date_fin': forms.DateInput(attrs={'type': 'date', 'id': 'id_date_fin'}),
            'date_limite': forms.DateInput(attrs={'type': 'date', 'id': 'id_date_limite', 'readonly': 'readonly'}),
            'periode_type': forms.Select(attrs={'id': 'id_periode_type'}),
            'annee': forms.NumberInput(attrs={'id': 'id_annee'}),
        }