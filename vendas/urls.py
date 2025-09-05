from django.urls import path
from . import views

urlpatterns = [
    path('', views.listar_vendas, name='listar_vendas'),
    path('criar/', views.criar_venda, name='criar_venda'),
    path('remover-produto/<int:produto_id>/', views.remover_produto, name='remover_produto'),
    path('atualizar-quantidade/<int:produto_id>/', views.atualizar_quantidade, name='atualizar_quantidade'),
    path('finalizar/', views.finalizar_venda, name='finalizar_venda'),
    path('cancelar/', views.cancelar_venda, name='cancelar_venda'),

    path("<int:venda_id>/apagar/", views.remover_venda, name="remover_venda"),
    path('<int:venda_id>/detalhes/', views.detalhes_venda, name='detalhes_venda'),

    path('imprimir-recibo/<int:venda_id>/', views.imprimir_recibo_imagem, name='imprimir_recibo'),
]