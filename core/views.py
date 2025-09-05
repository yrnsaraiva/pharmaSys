from django.shortcuts import render
from django.utils import timezone
from datetime import timedelta, datetime
from django.db.models import Sum, Count, Q, F
from django.contrib.auth.decorators import login_required

from vendas.models import Venda
from productos.models import Produto, Lote


@login_required
def dashboard(request):
    hoje = timezone.now().date()
    inicio_mes = hoje.replace(day=1)
    trinta_dias_atras = hoje - timedelta(days=30)

    # Vendas do dia
    vendas_hoje = Venda.objects.filter(data_venda__date=hoje)
    total_vendas_hoje = vendas_hoje.aggregate(total=Sum('total'))['total'] or 0

    validade_proxima = Lote.objects.filter(
        data_validade__range=[hoje, hoje + timedelta(days=30)]
    ).count()

    # Receita mensal
    receita_mensal = Venda.objects.filter(
        data_venda__date__gte=inicio_mes
    ).aggregate(total=Sum('total'))['total'] or 0

    # Vendas dos últimos 30 dias para o gráfico
    vendas_ultimos_30_dias = []
    categorias_30_dias = []

    for i in range(31):
        data = trinta_dias_atras + timedelta(days=i)
        total_dia = Venda.objects.filter(
            data_venda__date=data
        ).aggregate(total=Sum('total'))['total'] or 0

        vendas_ultimos_30_dias.append(float(total_dia))
        categorias_30_dias.append(data.strftime('%d/%m'))

    receita_ultimos_30_dias = sum(vendas_ultimos_30_dias)

    # Produtos mais vendidos (últimos 30 dias)
    produtos_mais_vendidos = Produto.objects.filter(
        itemvenda__venda__data_venda__gte=trinta_dias_atras
    ).annotate(
        total_vendido=Sum('itemvenda__quantidade')
    ).order_by('-total_vendido')[:5]

    # Preparar dados para gráfico de pizza
    produtos_pizza = []
    for produto in produtos_mais_vendidos:
        produtos_pizza.append({
            'name': produto.nome,
            'y': float(produto.total_vendido or 0)
        })

    #productos abaixo do stock minimo
    produtos_estoque_baixo = Produto.objects.annotate(
        total_estoque=Sum('lote__quantidade_disponivel')
    ).filter(
        total_estoque__lt=F('estoque_minimo')
    )

    context = {
        'total_vendas_hoje': total_vendas_hoje,
        'estoque_baixo': produtos_estoque_baixo.count(),
        'validade_proxima': validade_proxima,
        'receita_ultimos_30_dias': receita_ultimos_30_dias,
        'vendas_ultimos_30_dias': vendas_ultimos_30_dias,
        'categorias_30_dias': categorias_30_dias,
        'produtos_pizza': produtos_pizza,
    }

    return render(request, "dashbord/dashbord.html", context)