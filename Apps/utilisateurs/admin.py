from django.contrib import admin
from django import forms
from .models import UserCustom, Employeur, Employe, AgentFiscale

# --- 1. CONFIGURATION DES INLINES ---

class EmployeurInline(admin.StackedInline):
    model = Employeur
    can_delete = False
    extra = 0
    # On évite les tuples dans les fields pour un affichage vertical propre
    fields = ('nif', 'raison_sociale', 'statut_juridique', 'siege_social')

class AgentFiscaleInline(admin.StackedInline):
    model = AgentFiscale
    can_delete = False
    extra = 0
    fields = ('nom', 'prenom', 'matricule_agent')

# --- 2. ADAPTATION DU COMPTE UTILISATEUR ---

@admin.register(UserCustom)
class UserCustomAdmin(admin.ModelAdmin):
    inlines = (EmployeurInline, AgentFiscaleInline)
    
    list_display = ("email", "first_name", "last_name", "is_staff", "is_active")
    # Défini comme recherchable pour permettre l'autocomplete ailleurs
    search_fields = ("email", "first_name", "last_name")
    ordering = ("email",)

    fieldsets = (
        ('Identifiants de connexion', {
            'fields': ('email', 'password'),
        }),
        ('Informations personnelles', {
            'fields': ('first_name', 'last_name'),
        }),
        ('Permissions & Accès', {
            'fields': ('is_active', 'is_staff', 'is_superuser', 'groups', 'user_permissions'),
            'classes': ('collapse',), # On enroule pour alléger l'interface
        }),
        ('Audit', {
            'fields': ('last_login', 'date_joined'),
            'classes': ('collapse',),
        }),
    )

    def save_model(self, request, obj, form, change):
        if not change or 'password' in form.changed_data:
            obj.set_password(obj.password)
        super().save_model(request, obj, form, change)

    def get_inline_instances(self, request, obj=None):
        if not obj:
            return []
        return super().get_inline_instances(request, obj)

# --- 3. AUTRES MODÈLES (NETTOYAGE DES DROPDOWNS) ---

@admin.register(Employeur)
class EmployeurAdmin(admin.ModelAdmin):
    # Remplacer les dropdowns par une recherche fluide
    search_fields = ['raison_sociale', 'nif']
    list_display = ('raison_sociale', 'nif')
    autocomplete_fields = ['user'] 
    
    list_display = ("raison_sociale", "nif", "get_email", "get_first_name")
    search_fields = ("nif", "raison_sociale", "user__email")

    def get_first_name(self, obj): return obj.user.first_name
    def get_last_name(self, obj): return obj.user.last_name
    def get_email(self, obj): return obj.user.email
    
    # Organisation verticale sans icônes 
    fieldsets = (
        ('Lien Compte', {'fields': ('user',)}),
        ('Données Entreprise', {'fields': ('nif', 'raison_sociale')}),
    )

@admin.register(AgentFiscale)
class AgentFiscaleAdmin(admin.ModelAdmin):
    autocomplete_fields = ['user']
    list_display = ('nom', 'prenom', 'user_email')
    search_fields = ('nom', 'prenom', 'user__email')
    
    def user_email(self, obj): return obj.user.email

@admin.register(Employe)
class EmployeAdmin(admin.ModelAdmin):
    
    # INDISPENSABLE : permet de supprimer les icônes de sélection
    autocomplete_fields = ['user'] 
    
    search_fields = ['nom_prenom', 'nif_individuel', 'cin', 'num_cnaps']
    list_display = ('nom_prenom', 'nif_individuel', 'num_cnaps', 'fonction', 'get_user_email')
    list_filter = ('fonction',)

    fieldsets = (
        ('Profil Utilisateur', {'fields': ('user',)}),
        ('Identité Fiscale', {'fields': ('nom_prenom', 'nif_individuel', 'cin', 'num_cnaps')}),
        ('Poste', {'fields': ('fonction',)}),
    )

    def get_user_email(self, obj):
        return obj.user.email if obj.user else "Pas de compte"
    get_user_email.short_description = "Email Utilisateur"


