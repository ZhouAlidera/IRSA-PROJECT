from django.contrib import admin
from django import forms
from .models import UserCustom, Employeur, Employe, AgentFiscale

# --- 1. CONFIGURATION DES INLINES ---

class EmployeurInline(admin.StackedInline):
    model = Employeur
    can_delete = False
    extra = 0

class AgentFiscaleInline(admin.StackedInline):
    model = AgentFiscale
    can_delete = False
    extra = 0

# --- 2. ADAPTATION AVEC MODELADMIN ---

@admin.register(UserCustom)
class UserCustomAdmin(admin.ModelAdmin): # Changement ici : ModelAdmin
    inlines = (EmployeurInline, AgentFiscaleInline)
    
    # Affichage de la liste
    list_display = ("email", "first_name", "last_name", "is_staff", "is_active")
    search_fields = ("email", "first_name", "last_name")
    ordering = ("email",)

    # Organisation des champs pour la modification
    fieldsets = (
        (None, {'fields': ('email', 'password')}),
        ('Informations personnelles', {'fields': ('first_name', 'last_name')}),
        ('Permissions', {'fields': ('is_active', 'is_staff', 'is_superuser', 'groups', 'user_permissions')}),
        ('Dates importantes', {'fields': ('last_login', 'date_joined')}),
    )

    # Sécurité : Hachage automatique du mot de passe à la sauvegarde
    def save_model(self, request, obj, form, change):
        # Si c'est un nouvel utilisateur ou si le mot de passe a été modifié
        if not change or 'password' in form.changed_data:
            obj.set_password(obj.password)
        super().save_model(request, obj, form, change)

    # Logique pour masquer les profils vides lors de l'ajout
    def get_inline_instances(self, request, obj=None):
        if not obj:
            return []
        return super().get_inline_instances(request, obj)

# --- 3. AUTRES MODÈLES ---

@admin.register(Employeur)
class EmployeurAdmin(admin.ModelAdmin):
    list_display = ("get_first_name", "get_last_name", "get_email", "nif", "raison_sociale")
    search_fields = ("nif", "raison_sociale", "user__email")

    def get_first_name(self, obj): return obj.user.first_name
    def get_last_name(self, obj): return obj.user.last_name
    def get_email(self, obj): return obj.user.email

@admin.register(AgentFiscale)
class AgentFiscaleAdmin(admin.ModelAdmin):
    list_display = ('nom', 'prenom', 'user_email')
    def user_email(self, obj): return obj.user.email

admin.site.register(Employe)