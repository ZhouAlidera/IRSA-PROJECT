from django.urls import path
from .import views

urlpatterns=[
    path('api/nif-info/', views.nif_info, name='nif-info'),
]
