from django.urls import path
from .import views
from .import services

urlpatterns = [
    path('declaration/',views.declaration, name="declaration"),
    path('presentation/',views.creer_periode_fiscale, name="presentation"),
    path('piece-jointe/',views.upload_annexe, name="upload_annexe"),
    path('recapitulatif/controle/',views.preview_annexe, name="preview_annexe"),
    path('recapitulatif/confirmer/',views.convertir_en_brouillon, name="convertir_en_brouillon"),
    path('detail/annexe/',views.detail_import_brouillon, name="detail_import_brouillon"),
    path('import/supprimer/<int:pk>/', views.supprimer_ligne_temp, name='supprimer_ligne_temp'),
    path('import/ajouter/employe/', views.ajouter_employe_brouillon, name='ajouter_employe_brouillon'),
    path('import/brouillon/modifier/<int:pk>/', views.modifier_employe_brouillon, name='modifier_employe_brouillon'),
    path(
        'declaration/<int:declaration_id>/recapitulatif/', 
        services.detail_recapitulatif_avant_confirmation, 
        name='recapitulatif_declaration'
    ),
    path(
        'declaration/<int:declaration_id>/finaliser/', 
        services.valider_brouillon_vers_declaration, 
        name='finaliser_declaration'
    ),
    path(
        'declarations/liste/', 
        services.liste_declarations_view, 
        name='liste_declarations'
    ),
    path('declarations/valider-finale/<int:declaration_id>/', services.valider_declaration, name='valider_declaration'),
    path('dashboard/', services.dashboard_employeur, name='dashboard_employeur'),
    path('declaration/manuelle', services.valider_saisie_manuelle, name='valider_saisie_manuelle'),
    path('declaration/ajax/ajouter/', services.ajax_ajouter_employe, name='ajax_ajouter_employe'),
    path('declaration/ajax/supprimer/<int:id>/', services.ajax_supprimer_employe, name='ajax_supprimer_employe'),
    path('declaration/saisie/manuelle', services.convertir_en_brouillon_SM, name='convertir_en_brouillon_SM'),
    
    path('declaration/<int:declaration_id>/pdf/', services.export_declaration_pdf, name='export_irsa_pdf'),
    path('debug/reset/', services.reset_session_debug), # vider session pour le developpement
          
]
