from rest_framework.response import Response
from .models import NifLocal
from .serializers import NifLocalSerializer
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny


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
