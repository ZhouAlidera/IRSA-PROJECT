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
    
    
    