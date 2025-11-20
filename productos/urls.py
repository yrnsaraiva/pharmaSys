from django.urls import path, include
from . import views

urlpatterns = [
    path('', views.productos_list, name='productos_list'),
    path('criar/', views.cadastrar_producto, name='cadastrar_producto'),
    path('categorias/', views.categorias_list, name='categorias_list'),
    path('categoria/criar/', views.criar_categoria, name='criar_categoria'),
    path("categoria/<int:categoria_id>/apagar/", views.remover_categoria, name="remover_categoria"),
    path("<int:producto_id>/apagar/", views.remover_producto, name="remover_producto"),
    path("<int:producto_id>/editar/", views.editar_producto, name="editar_producto"),
    path("lotes/", views.listar_lotes, name="listar_lotes"),
    path("lote/criar/", views.criar_lote, name="cadastrar_lote"),
    path("lote/<int:pk>/apagar/", views.remover_lote, name="remover_lote"),
    path('exportar-produtos-pdf/', views.exportar_produtos_pdf, name='exportar_produtos_pdf'),
    path('exportar-excel-simples/', views.exportar_produtos_excel, name='exportar_produtos_excel'),



]
