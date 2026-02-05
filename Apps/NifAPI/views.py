from rest_framework.response import Response
from .models import NifLocal ,NifEmploye
from .serializers import NifLocalSerializer ,NifEmployeSerializer
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from utilisateurs.models import Employe


@api_view(['GET'])
@permission_classes([AllowAny])
def nif_info(request):
    nif = request.GET.get('nif')
    print(">>> NIF reçu :", repr(nif))   # DEBUG

    try:
        entreprise = NifLocal.objects.get(nif=nif)
        serializer = NifLocalSerializer(entreprise)
        return Response({'exists': True, 'data': serializer.data})
    except NifLocal.DoesNotExist:
        return Response({'exists': False})

@api_view(['GET'])
@permission_classes([AllowAny])
def nif_employe(request):
    nif_saisi = request.GET.get('nif')
    cin_saisi = request.GET.get('cin')
    
    try:
        # 1. Existe-t-il dans la base fiscale ?
        nif_data = NifEmploye.objects.get(nif=nif_saisi)
        
        # 2. Existe-t-il dans la base Employe (Excel) avec ce CIN ?
        # On vérifie aussi que le nom concorde pour éviter les erreurs
        employe_base = Employe.objects.get(cin=cin_saisi)
        
        if nif_data.nom_prenom.upper() != employe_base.nom_prenom.upper():
            return Response({'exists': False, 'message': 'Le NIF et le CIN ne correspondent pas au même nom.'})

        return Response({
            'exists': True, 
            'nom_prenom': employe_base.nom_prenom,
            'message': 'Identité confirmée'
        })
    except (NifEmploye.DoesNotExist, Employe.DoesNotExist):
        return Response({'exists': False, 'message': 'Informations introuvables.'})
    