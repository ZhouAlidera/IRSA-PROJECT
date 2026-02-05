import csv
import json
from django.core.management.base import BaseCommand
from NifAPI.models import NifEmploye  # Adaptez l'import

class Command(BaseCommand):
    help = "Remplit la table NifEmploye depuis un fichier ou une liste"

    def add_arguments(self, parser):
        # Optionnel : permettre de passer un fichier en argument
        parser.add_argument('--file', type=str, help='Chemin vers le fichier CSV ou JSON')

    def handle(self, *args, **options):
        file_path = options['file']
        
        # Exemple de données statiques si aucun fichier n'est fourni
        if not file_path:
            self.stdout.write("Aucun fichier fourni, utilisation des données de test...")
            data = [
                {'nif': '4001234567', 'cin': '101202303404', 'nom_prenom': 'RAKOTO Jean'},
                {'nif': '4009876543', 'cin': '202303404505', 'nom_prenom': 'RASOA Marie'},
            ]
            self.insert_data(data)
        else:
            # Logique pour lire un CSV (exemple)
            if file_path.endswith('.csv'):
                with open(file_path, mode='r', encoding='utf-8') as f:
                    reader = csv.DictReader(f)
                    self.insert_data(list(reader))
            
        self.stdout.write(self.style.SUCCESS('Remplissage terminé avec succès !'))

    def insert_data(self, data):
        count = 0
        for item in data:
            # update_or_create évite les doublons si vous relancez le script
            obj, created = NifEmploye.objects.update_or_create(
                nif=item['nif'],
                defaults={
                    'cin': item['cin'],
                    'nom_prenom': item['nom_prenom']
                }
            )
            if created:
                count += 1
        
        self.stdout.write(f"{count} nouveaux employés ajoutés.")
# python manage.py remplir_nif
# python manage.py remplir_nif --file employes.csv
#nif,cin,nom_prenom
#4001234567,101202303404,RAKOTO Jean
#4009876543,202303404505,RASOA Marie