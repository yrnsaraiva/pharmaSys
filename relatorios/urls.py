from django.urls import path, include
from . import views

urlpatterns = [


    path('', views.relatorios_avancados, name='relatorios_avancados'),  # Nova URL
]