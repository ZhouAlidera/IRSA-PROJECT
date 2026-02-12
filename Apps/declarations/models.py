from django.db import models
from utilisateurs.models import Employe, Employeur

# Create your models here.
class PeriodeFiscale(models.Model):
    employeur = models.ForeignKey(
        'utilisateurs.Employeur', # Remplace par le bon chemin vers ton modèle Employeur
        on_delete=models.PROTECT,
        related_name='periodes_fiscales',
        null=True
    )
    annee = models.PositiveIntegerField()
    date_debut = models.DateField()
    date_fin = models.DateField()
    PERIODE_CHOICES = [ ('mensuel', 'Mensuel'), ('bimestriel', 'Bimestriel'), ('trimestriel', 'Trimestriel'), ]
    periode_type = models.CharField(max_length=20, choices=PERIODE_CHOICES, default='mensuel')
    date_limite= models.DateField()

    def __str__(self):
        return str(self.annee)
    
    class Meta:
        unique_together = ('annee', 'date_debut', 'date_fin','employeur')
        app_label = 'declarations'


class DeclarationIRSA(models.Model):
    class StatusChoices(models.TextChoices):
        BROUILLON = 'brouillon', 'Brouillon'
        CONFIRME = 'confirme', 'Confirmé'
        VALIDE = 'valide', 'Validé'
        ARCHIVE = 'archive', 'archivé'

    # ... autres champs ...

    statut = models.CharField(
        max_length=20,
        choices=StatusChoices.choices,
        default=StatusChoices.BROUILLON
    )
    employeur = models.ForeignKey(
        "utilisateurs.Employeur",
        on_delete=models.PROTECT,
        related_name="declarations",
        verbose_name="Contribuable Déclarant"
    )
    numero_document = models.CharField(
        max_length=50, 
        unique=True, 
        verbose_name="Numéro Document"
    )
    nature_impots = models.CharField(
        max_length=255, 
        default="IMPÔTS SUR LES REVENUS SALARIAUX ET ASSIMILÉS",
        verbose_name="Nature d'impôts"
    )
    periode = models.ForeignKey(
        PeriodeFiscale,
        on_delete=models.PROTECT,
        related_name="declarations"
    )
    date_declaration = models.DateField(auto_now_add=True)
    total_irsa = models.DecimalField(max_digits=15, decimal_places=2, default=0) # total irsa calcule
    total_salaire_imposable = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    nombre_travailleurs_total = models.IntegerField(
        default=0, 
        verbose_name="1 - Nombre de travailleurs"
    ) 

    class Meta:
        unique_together = ("employeur", "periode")
        app_label = 'declarations'

    def __str__(self):
        return f"IRSA {self.employeur} - {self.periode}"
    def save(self, *args, **kwargs):
        if not self.numero_document:
            annee = self.periode.date_debut.year
            mois = str(self.periode.date_debut.month).zfill(2)
            prefixe = "".join(filter(str.isalnum, self.employeur.raison_sociale))[:3].upper()
            count = DeclarationIRSA.objects.filter(
                employeur=self.employeur, 
                periode=self.periode
            ).count() + 1
            
            self.numero_document = f"IRSA-{prefixe}-{annee}{mois}-{str(count).zfill(3)}"
            
        super().save(*args, **kwargs)

class LigneDeclarationIRSA(models.Model):
    declaration = models.ForeignKey(
        DeclarationIRSA,
        on_delete=models.CASCADE,
        related_name="lignes"
    )
    employe = models.ForeignKey(
        "utilisateurs.Employe",
        on_delete=models.PROTECT,
        related_name="lignes_irsa"
    )

    salaire_imposable = models.DecimalField(max_digits=15, decimal_places=2)
    # total_deduction = models.DecimalField(max_digits=15, decimal_places=2)
    irsa_due = models.DecimalField(max_digits=15, decimal_places=2)
    est_lu = models.BooleanField(default=False) 
    date_lecture = models.DateTimeField(null=True, blank=True)

    class Meta:
        unique_together = ("declaration", "employe")
        app_label = 'declarations'
        
class TypeRevenu(models.Model):
    code = models.CharField(max_length=30, unique=True)
    libelle = models.CharField(max_length=255)
    imposable = models.BooleanField(default=True)

    def __str__(self):
        return self.libelle
    class Meta:
        app_label = 'declarations'

class DetailRevenu(models.Model):
    ligne = models.ForeignKey(
        LigneDeclarationIRSA,
        on_delete=models.CASCADE,
        related_name="revenus"
    )
    type_revenu = models.ForeignKey(
        TypeRevenu,
        on_delete=models.PROTECT
    )
    montant = models.DecimalField(max_digits=15, decimal_places=2) # salaire de base et avantage en nature
    class Meta:
        app_label = 'declarations'

class TypeDeduction(models.Model):
    code = models.CharField(max_length=30, unique=True)
    libelle = models.CharField(max_length=255)
    plafonnee = models.BooleanField(default=False)

    def __str__(self):
        return self.libelle
    class Meta:
        app_label = 'declarations'

class DetailDeduction(models.Model):
    ligne = models.ForeignKey(
        LigneDeclarationIRSA,
        on_delete=models.CASCADE,
        related_name="deductions"
    )
    type_deduction = models.ForeignKey(
        TypeDeduction,
        on_delete=models.PROTECT
    )
    montant = models.DecimalField(max_digits=15, decimal_places=2) # cotisation 
    class Meta:
        app_label = 'declarations'
    
class SituationFamiliale(models.Model):
    employe = models.ForeignKey(
        "utilisateurs.Employe",
        on_delete=models.CASCADE,
        related_name="situations_familiales"
    )

    nombre_personnes_charge = models.PositiveIntegerField()
    date_debut = models.DateField()
    date_fin = models.DateField(null=True, blank=True)

    def est_valide(self, date):
        return self.date_debut <= date and (self.date_fin is None or self.date_fin >= date)
    class Meta:
        app_label = 'declarations'
    
class RegimeSpecialIRSA(models.Model):
    declaration = models.ForeignKey(
        DeclarationIRSA,
        on_delete=models.CASCADE,
        related_name="regimes_speciaux"
    )

    taux_unitaire_min = models.PositiveIntegerField()
    taux_unitaire_max = models.PositiveIntegerField(null=True, blank=True)

    nombre_travailleurs = models.PositiveIntegerField()
    masse_salaire_globale = models.DecimalField(max_digits=15, decimal_places=2)
    class Meta:
        app_label = 'declarations'
    
class TrancheBareme(models.Model):
    # Pour gérer les changements de loi d'une année à l'autre
    annee_fiscale = models.PositiveIntegerField(verbose_name="Année d'application")
    
    # Définition de la tranche
    seuil_minimal = models.DecimalField(max_digits=15, decimal_places=2, verbose_name="À partir de")
    seuil_maximal = models.DecimalField(max_digits=15, decimal_places=2, null=True, blank=True, verbose_name="Jusqu'à")
    
    # Le taux (ex: 5% -> 0.05 ou 5.00 selon ta préférence de calcul)
    taux = models.DecimalField(max_digits=5, decimal_places=2, verbose_name="Taux (%)")
    minimum_perception = models.DecimalField(
        max_digits=15, 
        decimal_places=2, 
        default=3000,
        help_text="Impôt minimum à payer (ex: 3.000 Ar)"
    )

    class Meta:
        ordering = ['annee_fiscale', 'seuil_minimal']
        verbose_name = "Tranche du barème IRSA"
        app_label = 'declarations'

    def __str__(self):
        if self.seuil_maximal:
            return f"{self.annee_fiscale} : De {self.seuil_minimal} à {self.seuil_maximal} ({self.taux}%)"
        return f"{self.annee_fiscale} : Plus de {self.seuil_minimal} ({self.taux}%)"
        
class ImportIRSATemporaire(models.Model):
    class StatusChoices(models.TextChoices):
        IMPORTE = 'IMPORTE', 'Importé'
        BROUILLON = 'BROUILLON', 'Brouillon'
        CONFIRME = 'CONFIRME', 'Confirmé'

    # ... vos champs précédents ...
    
    statut = models.CharField(
        max_length=20, 
        choices=StatusChoices.choices, 
        default=StatusChoices.BROUILLON
    )
    employeur = models.ForeignKey(
        "utilisateurs.Employeur",
        on_delete=models.PROTECT
    )
    num_cnaps = models.CharField(max_length=30)
    nom_prenom = models.CharField(max_length=255)
    cin = models.CharField(max_length=20, blank=True, null=True)
    fonction = models.CharField(max_length=150, blank=True, null=True)
    remuneration_brute = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    avantages_nature = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    pension = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    cotisation_sante = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    revenu_net = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    impot_brut = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    personnes_charge = models.IntegerField(default=0)
    reduction_charge = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    impot_net = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    revenu_net_theo = models.DecimalField(max_digits=12, decimal_places=2, default=0, help_text="RNI calculé par le système")
    impot_net_theo = models.DecimalField(max_digits=12, decimal_places=2, default=0, help_text="IRSA calculé par le système")
    est_valide = models.BooleanField(default=False)
    class Meta:
        app_label = 'declarations'

    