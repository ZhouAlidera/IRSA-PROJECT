from django.urls import path
from .import views
from django.urls import path
from . import views

urlpatterns = [
    # --- Inscription Employeur (existant) ---
    path('register/employeur/step-1/', views.register_employe_step_one, name='register_employe_step_one'),
    path('register/employeur/step-2/', views.register_employe_step_two, name='register_employe_step_two'),
    path('dashbord/employe/', views.dashborad_employe, name='dashboard_employe'),
    path('mes-declarations/', views.mes_declarations_irsa, name='mes_declarations_irsa'),

    # # --- Portail Employé ---
    # path('mon-espace/', views.portail_employe_view, name='portail_employe'),
]