from django import forms
from django.contrib.auth.forms import UserCreationForm,AuthenticationForm
from .models import UserCustom
from django.contrib.auth import authenticate,get_user_model


from django.contrib.auth.forms import UserCreationForm

# Étape 1 : NIF + Raison sociale
class RegisterStepOneForm(forms.Form):
    nif = forms.CharField(label="NIF")
    raison_sociale = forms.CharField(label="Raison sociale")
    adresse = forms.CharField(widget=forms.Textarea)

User = get_user_model()

class RegisterStepTwoForm(forms.Form):
    first_name = forms.CharField(label="Prénom")
    last_name = forms.CharField(label="Nom")
    email = forms.EmailField(label="Email")

    password = forms.CharField(
        label="Mot de passe",
        widget=forms.PasswordInput
    )
    password_confirm = forms.CharField(
        label="Confirmer le mot de passe",
        widget=forms.PasswordInput
    )

    def clean_email(self):
        email = self.cleaned_data['email']
        if User.objects.filter(email=email).exists():
            raise forms.ValidationError("Cet email est déjà utilisé.")
        return email

    def clean(self):
        cleaned_data = super().clean()
        password = cleaned_data.get("password")
        password_confirm = cleaned_data.get("password_confirm")

        if password != password_confirm:
            raise forms.ValidationError("Les mots de passe ne correspondent pas.")

        return cleaned_data


class LoginForm(AuthenticationForm):
    username=forms.EmailField(label='Email')
   
User = get_user_model()

class UserSecureUpdateForm(forms.ModelForm): # Modification compte avec confirmation pass
    password = forms.CharField(
        label="Mot de passe actuel",
        widget=forms.PasswordInput
    )

    class Meta:
        model = User
        fields = ["first_name", "last_name", "email"]

    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop("user", None)
        super().__init__(*args, **kwargs)

    def clean_password(self):
        pwd = self.cleaned_data.get("password")
        if not self.user.check_password(pwd):
            raise forms.ValidationError("Mot de passe incorrect.")
        return pwd
