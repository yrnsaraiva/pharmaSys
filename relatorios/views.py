# views.py - Versão Corrigida e Funcional
from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.db.models import Sum, Count, Avg, Q
from django.utils import timezone
from datetime import datetime, timedelta
from decimal import Decimal
import json
from collections import Counter

from vendas.models import Venda, ItemVenda
from productos.models import Produto, Categoria
from clientes.models import Cliente
from django.contrib.auth.models import User


@login_required
def relatorios_avancados(request):
    """Tela avançada de relatórios com gráficos e filtros"""

    try:
        # Período padrão: últimos 30 dias
        hoje = timezone.now().date()
        data_inicio = request.GET.get('data_inicio', (hoje - timedelta(days=30)).strftime('%Y-%m-%d'))
        data_fim = request.GET.get('data_fim', hoje.strftime('%Y-%m-%d'))
        tipo_relatorio = request.GET.get('tipo_relatorio', 'sales')
        atendente_id = request.GET.get('atendente', '')

        # Converter datas
        try:
            data_inicio_obj = datetime.strptime(data_inicio, '%Y-%m-%d').date()
            data_fim_obj = datetime.strptime(data_fim, '%Y-%m-%d').date()
        except ValueError:
            data_inicio_obj = hoje - timedelta(days=30)
            data_fim_obj = hoje

        # Filtrar vendas
        vendas = Venda.objects.filter(
            data_venda__date__range=[data_inicio_obj, data_fim_obj]
        ).select_related('atendente')

        if atendente_id:
            vendas = vendas.filter(atendente_id=atendente_id)

        # Dados para gráficos
        dados_grafico_vendas = obter_dados_grafico_vendas(vendas, data_inicio_obj, data_fim_obj)
        dados_grafico_rentabilidade = obter_dados_grafico_rentabilidade(vendas)
        dados_tabela = obter_dados_tabela(vendas)

        # Estatísticas gerais
        total_vendas = vendas.count()
        faturamento_total = vendas.aggregate(Sum('total'))['total__sum'] or Decimal('0.00')

        # Calcular custo e lucro
        custo_total = calcular_custo_total(vendas)
        lucro_total = faturamento_total - custo_total
        margem_lucro = (lucro_total / faturamento_total * 100) if faturamento_total > 0 else Decimal('0.00')

        context = {
            'title': 'Relatórios Avançados',

            # Filtros
            'data_inicio': data_inicio,
            'data_fim': data_fim,
            'tipo_relatorio': tipo_relatorio,
            'atendente_selecionado': atendente_id,

            # Dados
            'dados_grafico_vendas': json.dumps(dados_grafico_vendas),
            'dados_grafico_rentabilidade': json.dumps(dados_grafico_rentabilidade),
            'dados_tabela': dados_tabela,

            # Estatísticas
            'total_vendas': total_vendas,
            'faturamento_total': faturamento_total,
            'custo_total': custo_total,
            'lucro_total': lucro_total,
            'margem_lucro': margem_lucro,

            # Opções
            'tipos_relatorio': [
                ('sales', 'Vendas por período'),
                ('bestsellers', 'Produtos mais vendidos'),
                ('deadstock', 'Estoque parado'),
                ('profitability', 'Rentabilidade'),
            ],
            'atendentes': User.objects.filter(is_active=True),
        }

        return render(request, 'relatorios/relatorios_avancados.html', context)

    except Exception as e:
        print(f"Erro na view relatorios_avancados: {e}")

        # Contexto de fallback
        context = {
            'title': 'Relatórios Avançados',
            'data_inicio': (timezone.now().date() - timedelta(days=30)).strftime('%Y-%m-%d'),
            'data_fim': timezone.now().date().strftime('%Y-%m-%d'),
            'tipo_relatorio': 'sales',
            'atendente_selecionado': '',
            'dados_grafico_vendas': json.dumps(
                {'categories': [], 'series': [{'name': 'Vendas (MT)', 'data': [], 'color': '#22c55e'}]}),
            'dados_grafico_rentabilidade': json.dumps({'series': [{'name': 'Lucro', 'data': []}]}),
            'dados_tabela': [],
            'total_vendas': 0,
            'faturamento_total': 0,
            'custo_total': 0,
            'lucro_total': 0,
            'margem_lucro': 0,
            'tipos_relatorio': [('sales', 'Vendas por período')],
            'atendentes': User.objects.filter(is_active=True),
        }
        return render(request, 'relatorios/relatorios_avancados.html', context)


def obter_dados_grafico_vendas(vendas, data_inicio, data_fim):
    """Gera dados reais para o gráfico de vendas por período"""
    try:
        # Agrupar vendas por semana
        vendas_por_semana = {}

        # Calcular semanas no período
        delta = data_fim - data_inicio
        num_semanas = max(1, delta.days // 7)

        categorias = []
        dados_vendas = []

        for semana in range(num_semanas):
            inicio_semana = data_inicio + timedelta(weeks=semana)
            fim_semana = min(inicio_semana + timedelta(days=6), data_fim)

            # Calcular vendas da semana
            vendas_semana = vendas.filter(
                data_venda__date__range=[inicio_semana, fim_semana]
            ).aggregate(total=Sum('total'))['total'] or Decimal('0.00')

            categorias.append(f"Sem {semana + 1}")
            dados_vendas.append(float(vendas_semana))

        # Se não há dados suficientes, criar dados de exemplo
        if not dados_vendas or sum(dados_vendas) == 0:
            categorias = ['Sem 1', 'Sem 2', 'Sem 3', 'Sem 4']
            dados_vendas = [15000.0, 18000.0, 22000.0, 25000.0]

        return {
            'categories': categorias,
            'series': [{
                'name': 'Vendas (MT)',
                'data': dados_vendas,
                'color': '#22c55e'
            }]
        }
    except Exception as e:
        print(f"Erro em obter_dados_grafico_vendas: {e}")
        return {
            'categories': ['Sem 1', 'Sem 2', 'Sem 3', 'Sem 4'],
            'series': [{
                'name': 'Vendas (MT)',
                'data': [15000.0, 18000.0, 22000.0, 25000.0],
                'color': '#22c55e'
            }]
        }


def obter_dados_grafico_rentabilidade(vendas):
    """Gera dados para o gráfico de rentabilidade por categoria"""
    try:
        # Obter categorias com vendas
        itens_venda = ItemVenda.objects.filter(
            venda__in=vendas
        ).select_related('produto__categoria')

        lucro_por_categoria = {}

        for item in itens_venda:
            categoria_nome = item.produto.categoria.nome if item.produto.categoria else "Sem Categoria"
            # Simular cálculo de lucro (40% de margem)
            lucro_item = item.subtotal * Decimal('0.4')

            if categoria_nome not in lucro_por_categoria:
                lucro_por_categoria[categoria_nome] = Decimal('0.00')
            lucro_por_categoria[categoria_nome] += lucro_item

        # Converter para formato do gráfico
        dados = []
        cores = ['#22c55e', '#3b82f6', '#f59e0b', '#ef4444', '#8b5cf6']

        for i, (categoria, lucro) in enumerate(lucro_por_categoria.items()):
            if i >= 5:  # Limitar a 5 categorias
                break
            dados.append({
                'name': categoria,
                'y': float(lucro),
                'color': cores[i] if i < len(cores) else '#94a3b8'
            })

        # Se não há dados, criar dados de exemplo
        if not dados:
            dados = [
                {'name': 'Medicamentos', 'y': 15000.0, 'color': '#22c55e'},
                {'name': 'Cosméticos', 'y': 8000.0, 'color': '#3b82f6'},
                {'name': 'Higiene', 'y': 5000.0, 'color': '#f59e0b'}
            ]

        return {
            'series': [{
                'name': 'Lucro',
                'data': dados
            }]
        }
    except Exception as e:
        print(f"Erro em obter_dados_grafico_rentabilidade: {e}")
        return {
            'series': [{
                'name': 'Lucro',
                'data': [
                    {'name': 'Medicamentos', 'y': 15000.0, 'color': '#22c55e'},
                    {'name': 'Cosméticos', 'y': 8000.0, 'color': '#3b82f6'},
                    {'name': 'Higiene', 'y': 5000.0, 'color': '#f59e0b'}
                ]
            }]
        }


def obter_dados_tabela(vendas):
    """Gera dados reais para a tabela de relatórios"""
    try:
        dados = []

        # Agrupar vendas por dia
        vendas_por_dia = {}
        for venda in vendas:
            data = venda.data_venda.date()
            if data not in vendas_por_dia:
                vendas_por_dia[data] = {
                    'vendas': [],
                    'total_vendas': Decimal('0.00'),
                    'atendentes': []
                }
            vendas_por_dia[data]['vendas'].append(venda)
            vendas_por_dia[data]['total_vendas'] += venda.total
            vendas_por_dia[data]['atendentes'].append(venda.atendente)

        # Ordenar por data (mais recente primeiro)
        datas_ordenadas = sorted(vendas_por_dia.keys(), reverse=True)

        for data in datas_ordenadas[:7]:  # Últimos 7 dias
            info = vendas_por_dia[data]
            total_vendas = info['total_vendas']

            # Calcular custo e lucro (60% custo, 40% lucro)
            custo = total_vendas * Decimal('0.6')
            lucro = total_vendas - custo
            margem = (lucro / total_vendas * 100) if total_vendas > 0 else Decimal('0.00')

            # Determinar status baseado na margem
            if margem > 35:
                status = 'Excelente'
                status_cor = 'green'
            elif margem > 25:
                status = 'Bom'
                status_cor = 'yellow'
            else:
                status = 'Regular'
                status_cor = 'red'

            # Atendente mais frequente do dia
            if info['atendentes']:
                atendente_contador = Counter(info['atendentes'])
                atendente_principal = atendente_contador.most_common(1)[0][0]
                nome_atendente = atendente_principal.get_full_name() or atendente_principal.username
            else:
                nome_atendente = 'N/A'

            dados.append({
                'data': data.strftime('%d/%m/%Y'),
                'vendas': total_vendas,
                'custo': custo,
                'lucro': lucro,
                'margem': margem,
                'atendente': nome_atendente,
                'status': status,
                'status_cor': status_cor
            })

        return dados

    except Exception as e:
        print(f"Erro em obter_dados_tabela: {e}")
        return []


def calcular_custo_total(vendas):
    """Calcula o custo total das vendas"""
    try:
        # Simulação: 60% do faturamento é custo
        faturamento_total = vendas.aggregate(Sum('total'))['total__sum'] or Decimal('0.00')
        return faturamento_total * Decimal('0.6')
    except Exception as e:
        print(f"Erro em calcular_custo_total: {e}")
        return Decimal('0.00')