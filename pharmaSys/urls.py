from django.contrib import admin
from django.urls import path, include

urlpatterns = [
    path('', include('core.urls')),
    path('admin/', admin.site.urls),
    path('usuarios/', include('usuarios.urls')),
    path('fornecedores/', include('fornecedores.urls')),
    path('productos/', include('productos.urls')),
    path('clientes/', include('clientes.urls')),
    path('vendas/', include('vendas.urls')),
]
