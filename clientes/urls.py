from django.urls import path
from . import views

urlpatterns = [
    path('', views.listar_cliente, name='listar_cliente'),
    path('criar/', views.criar_cliente, name='criar_cliente'),
    path('<int:cliente_id>/editar/', views.editar_cliente, name='editar_cliente'),
    path('<int:cliente_id>/apagar/', views.deletar_cliente, name='deletar_cliente'),
    path('<int:cliente_id>/detalhes/', views.detalhes_cliente, name='detalhes_cliente'),
]
