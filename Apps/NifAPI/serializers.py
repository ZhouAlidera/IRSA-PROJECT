from rest_framework import serializers
from .models import NifLocal

class NifLocalSerializer(serializers.ModelSerializer):
    class Meta:
        model = NifLocal
        fields = ['nif', 'raison_sociale']
