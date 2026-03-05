from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static

# Importe as views de erro
from error_views import handler404, handler500, handler403, handler400

# Configurar os handlers de erro GLOBAIS do Django
handler404 = handler404
handler500 = handler500
handler403 = handler403
handler400 = handler400

urlpatterns = [
    path('', include('core.urls')),
    path('admin/', admin.site.urls),
    path('usuarios/', include('usuarios.urls')),
    path('fornecedores/', include('fornecedores.urls')),
    path('productos/', include('productos.urls')),
    path('clientes/', include('clientes.urls')),
    path('vendas/', include('vendas.urls')),
    path('relatorios/', include('relatorios.urls')),
]

# Para servir arquivos estáticos em desenvolvimento
if settings.DEBUG:
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

# URLs de teste para desenvolvimento (opcional)
if settings.DEBUG:
    from error_views import test_500_view
    urlpatterns += [
        path('test-error/500/', test_500_view, name='test_500'),
        path('test-error/404/', lambda request: handler404(request, None)),
    ]