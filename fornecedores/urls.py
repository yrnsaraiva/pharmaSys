from django.urls import path, include
from . import views

urlpatterns = [
    path('', views.fornecedores_list, name='listar_fornecedores'),
    path('criar/', views.cadastrar_fornecedor, name='cadastrar_fornecedor'),
    path("<int:fornecedor_id>/editar/", views.editar_fornecedor, name="editar_fornecedor"),
    path("<int:fornecedor_id>/apagar/", views.remover_fornecedor, name="remover_fornecedor"),
]
