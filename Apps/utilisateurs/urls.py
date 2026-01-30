from django.urls import path
from .import views

urlpatterns = [
    path('', views.dashboard, name='home'),
    path('register/step-1/', views.register_step_one, name='register_step_one'),
    path('register/step-2/', views.register_step_two, name='register_step_two'),
    path('logout/',views.logout_view,name='logout'),
    path('login/',views.login_view,name='login'),
]
