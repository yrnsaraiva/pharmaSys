from django.urls import path
from . import views

urlpatterns = [
    path('', views.dashboard, name='dashboard'),
    path('exportar-validade-excel/', views.exportar_validade_proxima_excel, name='exportar_validade_excel'),
    
]
