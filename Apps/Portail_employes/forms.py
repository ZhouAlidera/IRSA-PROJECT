from django import forms
from django.contrib.auth import get_user_model

User = get_user_model()

class RegisterStepOneForm(forms.Form):
    nif = forms.CharField(
        label="NIF Individuel",
        widget=forms.TextInput(attrs={'placeholder': 'Ex: NIF202600001', 'class': 'form-input'})
    )
    cin = forms.CharField(
        label="Numéro CIN",
        widget=forms.TextInput(attrs={'placeholder': 'Votre CIN', 'class': 'form-input'})
    )

class RegisterStepTwoForm(forms.Form):
    full_name = forms.CharField(
        label="Nom et Prénoms",
        widget=forms.TextInput(attrs={'readonly': 'readonly', 'class': 'bg-gray-100'})
    )
    email = forms.EmailField(label="Email Personnel")
    password = forms.CharField(label="Mot de passe", widget=forms.PasswordInput)
    password_confirm = forms.CharField(label="Confirmer", widget=forms.PasswordInput)

    def clean_email(self):
        email = self.cleaned_data['email']
        if User.objects.filter(email=email).exists():
            raise forms.ValidationError("Cet email est déjà associé à un compte.")
        return email

    def clean(self):
        cleaned_data = super().clean()
        if cleaned_data.get("password") != cleaned_data.get("password_confirm"):
            raise forms.ValidationError("Les mots de passe ne correspondent pas.")
        return cleaned_data