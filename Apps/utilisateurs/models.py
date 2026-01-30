from django.db import models
from django.contrib.auth.models import AbstractUser , BaseUserManager
from django.conf import settings



# Création de superuser
class CustomUserManager(BaseUserManager):
    use_in_migrations = True

    def create_user(self, email, password=None, **extra_fields):
        if not email:
            raise ValueError("L'adresse email est obligatoire")

        email = self.normalize_email(email)
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, email, password=None, **extra_fields):
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)
        extra_fields.setdefault("is_active", True)

        if extra_fields.get("is_staff") is not True:
            raise ValueError("Le superuser doit avoir is_staff=True")
        if extra_fields.get("is_superuser") is not True:
            raise ValueError("Le superuser doit avoir is_superuser=True")

        return self.create_user(email, password, **extra_fields)
# creation user
class UserCustom(AbstractUser):
    username = None
    email = models.EmailField(unique=True)

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = []
    
    objects = CustomUserManager()

    def __str__(self):
        return self.email
    class Meta:
        app_label = 'utilisateurs'


class Employeur(models.Model):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    nif = models.CharField(max_length=30, unique=True)
    raison_sociale = models.CharField(max_length=255, unique=True)
    adresse = models.TextField()
    
    compteur_document = models.PositiveIntegerField(default=0, help_text="Compteur séquentiel des documents fiscaux")

    def __str__(self):
        return self.raison_sociale
    class Meta:
        app_label = 'utilisateurs'

class AgentFiscale(models.Model):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    nom = models.CharField(max_length=100)
    prenom = models.CharField(max_length=100)

    def __str__(self):
        return f"{self.nom} {self.prenom}"
    class Meta:
        app_label = 'utilisateurs'


class Employe(models.Model):
    num_cnaps = models.CharField(max_length=30)
    nom_prenom = models.CharField(max_length=255)
    cin = models.CharField(max_length=20, blank=True, null=True)
    fonction = models.CharField(max_length=255)

    employeur = models.ForeignKey(
        "Employeur",
        on_delete=models.CASCADE,
        related_name="employes"
    )

    class Meta:
        unique_together = ("num_cnaps", "employeur", "cin")
        ordering = ["nom_prenom"]
        app_label = 'utilisateurs'

    def __str__(self):
        return f"{self.nom_prenom} ({self.num_cnaps})"
