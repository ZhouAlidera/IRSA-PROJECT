from django.db import models

# Create your models here.
# MODELS POUR LE NIFLOCAL
class NifLocal(models.Model):
    nif = models.CharField(max_length=15, unique=True, editable=False)
    raison_sociale = models.CharField(max_length=255)
    date_created = models.DateTimeField(auto_now_add=True)
    
    def save(self, *args, **kwargs):
        if not self.nif:
            # Génération automatique : NIF + année + compteur
            year = str(self.date_created.year if self.date_created else 2025)
            last = NifLocal.objects.filter(nif__startswith=f'NIF{year}').order_by('id').last()
            counter = int(last.nif[-5:]) + 1 if last else 1
            self.nif = f'NIF{year}{str(counter).zfill(5)}'
        super().save(*args, **kwargs)


    def __str__(self):
        return self.nif
    class Meta:
        app_label = 'NifAPI'
    
from django.db import models

class NifEmploye(models.Model):
    nif = models.CharField(max_length=15, unique=True, editable=False)
    cin = models.CharField(max_length=20, blank=True, null=True)
    nom_prenom = models.CharField(max_length=255,null=True, blank=True)
    date_created = models.DateTimeField(auto_now_add=True)
    
    def save(self, *args, **kwargs):
        if not self.nif:
            import datetime
            # On utilise l'année en cours pour la génération
            year = str(datetime.datetime.now().year)
            prefix = f'NIF{year}'
            
            # Recherche du dernier NIF généré pour cette année
            last = NifLocal.objects.filter(nif__startswith=prefix).order_by('-nif').first()
            
            if last:
                # On extrait les 5 derniers chiffres et on incrémente
                try:
                    last_counter = int(last.nif[-5:])
                    counter = last_counter + 1
                except (ValueError, IndexError):
                    counter = 1
            else:
                counter = 1
                
            self.nif = f'{prefix}{str(counter).zfill(5)}'
            
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.nif} - {self.nom_prenom}"

    class Meta:
        verbose_name = "Base NIF Employe"
        verbose_name_plural = "Base NIF Employes"
        app_label = 'NifAPI'
    