# error_views.py (adicione esta função)
from django.shortcuts import render
import traceback


def handler500(request, exception=None):
    """View personalizada para erro 500"""
    error_trace = None
    if exception:
        error_trace = traceback.format_exc()

    context = {
        'error_code': '500',
        'error_title': 'Erro Interno do Servidor',
        'error_message': 'O servidor encontrou um erro interno ou configuração incorreta.',
        'error_trace': error_trace,
    }
    return render(request, 'errors/500.html', context, status=500)


def handler404(request, exception):
    """View personalizada para erro 404"""
    context = {
        'error_code': '404',
        'error_title': 'Página Não Encontrada',
        'error_message': 'A página que você está procurando não existe ou foi movida.',
    }
    return render(request, 'errors/404.html', context, status=404)


def handler403(request, exception):
    """View personalizada para erro 403"""
    context = {
        'error_code': '403',
        'error_title': 'Acesso Proibido',
        'error_message': 'Você não tem permissão para acessar esta página.',
    }
    return render(request, 'errors/403.html', context, status=403)


def handler400(request, exception):
    """View personalizada para erro 400"""
    context = {
        'error_code': '400',
        'error_title': 'Requisição Inválida',
        'error_message': 'A requisição enviada não pôde ser processada pelo servidor.',
    }
    return render(request, 'errors/400.html', context, status=400)


# Função de teste para desenvolvimento
def test_500_view(request):
    """View apenas para testar o erro 500"""
    raise Exception("Este é um teste de erro 500 - PharmaSys")