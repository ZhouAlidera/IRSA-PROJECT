from rest_framework import serializers
from .models import NifLocal ,NifEmploye

class NifLocalSerializer(serializers.ModelSerializer):
    class Meta:
        model = NifLocal
        fields = ['nif', 'raison_sociale']

class NifEmployeSerializer(serializers.ModelSerializer):
    class Meta:
        model = NifEmploye
        fiels = ['nif','cin','nom_prenom']