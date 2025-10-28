from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.db.models import Sum, Count, Q
from django.utils import timezone
from datetime import datetime, timedelta
from decimal import Decimal
import json
from collections import Counter

from vendas.models import Venda, ItemVenda
from productos.models import Produto, Categoria, Lote
from clientes.models import Cliente
from django.contrib.auth.models import User
from core.decorators import gerente_required


@login_required
@gerente_required
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

        # Dados para gráficos baseados no tipo de relatório
        if tipo_relatorio == 'sales':
            dados_grafico_vendas = obter_dados_grafico_vendas(vendas, data_inicio_obj, data_fim_obj)
            dados_grafico_rentabilidade = obter_dados_grafico_rentabilidade(vendas)
            dados_tabela = obter_dados_tabela(vendas)

        elif tipo_relatorio == 'bestsellers':
            dados_grafico_vendas = obter_dados_produtos_mais_vendidos(vendas)
            dados_grafico_rentabilidade = obter_dados_categorias_mais_vendidas(vendas)
            dados_tabela = obter_dados_tabela_produtos_mais_vendidos(vendas)

        elif tipo_relatorio == 'deadstock':
            dados_grafico_vendas = obter_dados_estoque_parado()
            dados_grafico_rentabilidade = obter_dados_categorias_estoque_parado()
            dados_tabela = obter_dados_tabela_estoque_parado()

        elif tipo_relatorio == 'profitability':
            dados_grafico_vendas = obter_dados_rentabilidade_periodo(vendas, data_inicio_obj, data_fim_obj)
            dados_grafico_rentabilidade = obter_dados_grafico_rentabilidade(vendas)
            dados_tabela = obter_dados_tabela_rentabilidade(vendas)
        else:
            # Fallback para vendas
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
            'dados_grafico_vendas': json.dumps({'categories': [], 'series': []}),
            'dados_grafico_rentabilidade': json.dumps({'series': []}),
            'dados_tabela': [],
            'total_vendas': 0,
            'faturamento_total': 0,
            'custo_total': 0,
            'lucro_total': 0,
            'margem_lucro': 0,
            'tipos_relatorio': [
                ('sales', 'Vendas por período'),
                ('bestsellers', 'Produtos mais vendidos'),
                ('deadstock', 'Estoque parado'),
                ('profitability', 'Rentabilidade'),
            ],
            'atendentes': User.objects.filter(is_active=True),
        }
        return render(request, 'relatorios/relatorios_avancados.html', context)


# ========== FUNÇÕES PARA VENDAS POR PERÍODO ==========

def obter_dados_grafico_vendas(vendas, data_inicio, data_fim):
    """Gera dados reais para o gráfico de vendas por período"""
    try:
        # Agrupar vendas por dia
        vendas_por_dia = {}
        current_date = data_inicio

        while current_date <= data_fim:
            vendas_por_dia[current_date] = Decimal('0.00')
            current_date += timedelta(days=1)

        # Preencher com dados reais
        for venda in vendas:
            data_venda = venda.data_venda.date()
            if data_venda in vendas_por_dia:
                vendas_por_dia[data_venda] += venda.total

        # Preparar dados para o gráfico
        categorias = []
        dados_vendas = []

        for data, total in sorted(vendas_por_dia.items()):
            categorias.append(data.strftime('%d/%m'))
            dados_vendas.append(float(total))

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
        return {'categories': [], 'series': []}


# ========== FUNÇÕES PARA PRODUTOS MAIS VENDIDOS ==========

def obter_dados_produtos_mais_vendidos(vendas):
    """Gera dados para gráfico de produtos mais vendidos"""
    try:
        itens_venda = ItemVenda.objects.filter(venda__in=vendas)

        produtos_mais_vendidos = itens_venda.values(
            'produto__nome'
        ).annotate(
            total_vendido=Sum('quantidade'),
            total_faturado=Sum('subtotal')
        ).order_by('-total_vendido')[:10]

        categorias = [item['produto__nome'] for item in produtos_mais_vendidos]
        dados_quantidade = [float(item['total_vendido'] or 0) for item in produtos_mais_vendidos]

        return {
            'categories': categorias,
            'series': [{
                'name': 'Quantidade Vendida',
                'data': dados_quantidade,
                'color': '#3b82f6'
            }]
        }
    except Exception as e:
        print(f"Erro em obter_dados_produtos_mais_vendidos: {e}")
        return {'categories': [], 'series': []}


def obter_dados_categorias_mais_vendidas(vendas):
    """Gera dados para gráfico de categorias mais vendidas"""
    try:
        itens_venda = ItemVenda.objects.filter(venda__in=vendas).select_related('produto__categoria')

        categorias_mais_vendidas = {}

        for item in itens_venda:
            categoria_nome = item.produto.categoria.nome if item.produto.categoria else "Sem Categoria"
            if categoria_nome not in categorias_mais_vendidas:
                categorias_mais_vendidas[categoria_nome] = 0
            categorias_mais_vendidas[categoria_nome] += item.quantidade

        # Converter para formato do gráfico
        dados = []
        cores = ['#22c55e', '#3b82f6', '#f59e0b', '#ef4444', '#8b5cf6', '#06b6d4', '#d946ef', '#84cc16']

        for i, (categoria, quantidade) in enumerate(
                sorted(categorias_mais_vendidas.items(), key=lambda x: x[1], reverse=True)[:8]):
            dados.append({
                'name': categoria,
                'y': float(quantidade),
                'color': cores[i] if i < len(cores) else '#94a3b8'
            })

        return {'series': [{'name': 'Quantidade', 'data': dados}]}

    except Exception as e:
        print(f"Erro em obter_dados_categorias_mais_vendidas: {e}")
        return {'series': []}


def obter_dados_tabela_produtos_mais_vendidos(vendas):
    """Gera dados para tabela de produtos mais vendidos"""
    try:
        itens_venda = ItemVenda.objects.filter(venda__in=vendas)

        produtos_data = itens_venda.values(
            'produto__nome',
            'produto__categoria__nome'
        ).annotate(
            quantidade_total=Sum('quantidade'),
            faturamento_total=Sum('subtotal')
        ).order_by('-quantidade_total')[:20]

        dados_tabela = []
        for produto in produtos_data:
            dados_tabela.append({
                'produto': produto['produto__nome'],
                'categoria': produto['produto__categoria__nome'] or 'Sem Categoria',
                'quantidade': produto['quantidade_total'],
                'faturamento': produto['faturamento_total'] or Decimal('0.00'),
                'tipo': 'produto'
            })

        return dados_tabela

    except Exception as e:
        print(f"Erro em obter_dados_tabela_produtos_mais_vendidos: {e}")
        return []


# ========== FUNÇÕES PARA ESTOQUE PARADO ==========

def obter_dados_estoque_parado():
    """Gera dados para gráfico de estoque parado"""
    try:
        # Produtos com estoque mas sem vendas nos últimos 90 dias
        noventa_dias_atras = timezone.now().date() - timedelta(days=90)

        produtos_com_estoque = Produto.objects.filter(
            lote__quantidade_disponivel__gt=0
        ).distinct()

        produtos_sem_vendas = []

        for produto in produtos_com_estoque:
            vendas_recentes = ItemVenda.objects.filter(
                produto=produto,
                venda__data_venda__gte=noventa_dias_atras
            ).exists()

            if not vendas_recentes:
                estoque_total = produto.estoque_total()
                if estoque_total > 0:
                    produtos_sem_vendas.append({
                        'nome': produto.nome,
                        'estoque': estoque_total,
                        'categoria': produto.categoria.nome if produto.categoria else 'Sem Categoria'
                    })

        # Ordenar por estoque (maior primeiro) e pegar top 10
        produtos_sem_vendas.sort(key=lambda x: x['estoque'], reverse=True)
        produtos_sem_vendas = produtos_sem_vendas[:10]

        categorias = [f"{produto['nome'][:15]}..." if len(produto['nome']) > 15 else produto['nome']
                      for produto in produtos_sem_vendas]
        dados_estoque = [float(produto['estoque']) for produto in produtos_sem_vendas]

        return {
            'categories': categorias,
            'series': [{
                'name': 'Estoque Parado',
                'data': dados_estoque,
                'color': '#ef4444'
            }]
        }

    except Exception as e:
        print(f"Erro em obter_dados_estoque_parado: {e}")
        return {'categories': [], 'series': []}


def obter_dados_categorias_estoque_parado():
    """Gera dados para gráfico de categorias com estoque parado"""
    try:
        noventa_dias_atras = timezone.now().date() - timedelta(days=90)

        categorias_estoque_parado = {}

        produtos_com_estoque = Produto.objects.filter(
            lote__quantidade_disponivel__gt=0
        ).distinct()

        for produto in produtos_com_estoque:
            vendas_recentes = ItemVenda.objects.filter(
                produto=produto,
                venda__data_venda__gte=noventa_dias_atras
            ).exists()

            if not vendas_recentes:
                categoria_nome = produto.categoria.nome if produto.categoria else "Sem Categoria"
                if categoria_nome not in categorias_estoque_parado:
                    categorias_estoque_parado[categoria_nome] = 0
                categorias_estoque_parado[categoria_nome] += produto.estoque_total()

        # Converter para formato do gráfico
        dados = []
        cores = ['#ef4444', '#f59e0b', '#84cc16', '#3b82f6', '#8b5cf6']

        for i, (categoria, estoque) in enumerate(
                sorted(categorias_estoque_parado.items(), key=lambda x: x[1], reverse=True)[:5]):
            dados.append({
                'name': categoria,
                'y': float(estoque),
                'color': cores[i] if i < len(cores) else '#94a3b8'
            })

        return {'series': [{'name': 'Estoque Parado', 'data': dados}]}

    except Exception as e:
        print(f"Erro em obter_dados_categorias_estoque_parado: {e}")
        return {'series': []}


def obter_dados_tabela_estoque_parado():
    """Gera dados para tabela de estoque parado"""
    try:
        noventa_dias_atras = timezone.now().date() - timedelta(days=90)

        produtos_com_estoque = Produto.objects.filter(
            lote__quantidade_disponivel__gt=0
        ).distinct()

        dados_tabela = []

        for produto in produtos_com_estoque:
            vendas_recentes = ItemVenda.objects.filter(
                produto=produto,
                venda__data_venda__gte=noventa_dias_atras
            ).exists()

            if not vendas_recentes:
                estoque_total = produto.estoque_total()
                ultima_venda = ItemVenda.objects.filter(
                    produto=produto
                ).order_by('-venda__data_venda').first()

                dados_tabela.append({
                    'produto': produto.nome,
                    'categoria': produto.categoria.nome if produto.categoria else 'Sem Categoria',
                    'estoque_atual': estoque_total,
                    'estoque_minimo': produto.estoque_minimo,
                    'ultima_venda': ultima_venda.venda.data_venda.date() if ultima_venda else 'Nunca',
                    'dias_sem_venda': '90+',
                    'tipo': 'estoque_parado'
                })

        # Ordenar por estoque (maior primeiro)
        dados_tabela.sort(key=lambda x: x['estoque_atual'], reverse=True)

        return dados_tabela[:20]

    except Exception as e:
        print(f"Erro em obter_dados_tabela_estoque_parado: {e}")
        return []


# ========== FUNÇÕES PARA RENTABILIDADE ==========

def obter_dados_rentabilidade_periodo(vendas, data_inicio, data_fim):
    """Gera dados para gráfico de rentabilidade por período"""
    try:
        # Agrupar por semana
        rentabilidade_por_semana = {}
        current_date = data_inicio
        semana_num = 1

        while current_date <= data_fim:
            fim_semana = min(current_date + timedelta(days=6), data_fim)

            vendas_semana = vendas.filter(
                data_venda__date__range=[current_date, fim_semana]
            )

            faturamento_semana = vendas_semana.aggregate(total=Sum('total'))['total'] or Decimal('0.00')
            custo_semana = faturamento_semana * Decimal('0.6')  # 60% de custo
            lucro_semana = faturamento_semana - custo_semana

            rentabilidade_por_semana[f"Sem {semana_num}"] = {
                'faturamento': faturamento_semana,
                'lucro': lucro_semana
            }

            current_date = fim_semana + timedelta(days=1)
            semana_num += 1

        categorias = list(rentabilidade_por_semana.keys())
        dados_lucro = [float(dados['lucro']) for dados in rentabilidade_por_semana.values()]
        dados_faturamento = [float(dados['faturamento']) for dados in rentabilidade_por_semana.values()]

        return {
            'categories': categorias,
            'series': [
                {
                    'name': 'Faturamento',
                    'data': dados_faturamento,
                    'color': '#3b82f6'
                },
                {
                    'name': 'Lucro',
                    'data': dados_lucro,
                    'color': '#10b981'
                }
            ]
        }

    except Exception as e:
        print(f"Erro em obter_dados_rentabilidade_periodo: {e}")
        return {'categories': [], 'series': []}


def obter_dados_tabela_rentabilidade(vendas):
    """Gera dados para tabela de rentabilidade"""
    try:
        # Agrupar por dia
        vendas_por_dia = {}
        for venda in vendas:
            data = venda.data_venda.date()
            if data not in vendas_por_dia:
                vendas_por_dia[data] = []
            vendas_por_dia[data].append(venda)

        dados_tabela = []
        for data, vendas_dia in sorted(vendas_por_dia.items(), reverse=True)[:7]:
            total_vendas_dia = sum(v.total for v in vendas_dia)
            custo_dia = total_vendas_dia * Decimal('0.6')
            lucro_dia = total_vendas_dia - custo_dia
            margem = (lucro_dia / total_vendas_dia * 100) if total_vendas_dia > 0 else Decimal('0.00')

            # Status baseado na margem
            if margem > 35:
                status = 'Excelente'
                status_cor = 'green'
            elif margem > 25:
                status = 'Bom'
                status_cor = 'yellow'
            else:
                status = 'Regular'
                status_cor = 'red'

            dados_tabela.append({
                'data': data.strftime('%d/%m/%Y'),
                'vendas': total_vendas_dia,
                'custo': custo_dia,
                'lucro': lucro_dia,
                'margem': margem,
                'status': status,
                'status_cor': status_cor,
                'tipo': 'rentabilidade'
            })

        return dados_tabela

    except Exception as e:
        print(f"Erro em obter_dados_tabela_rentabilidade: {e}")
        return []


# ========== FUNÇÕES COMPARTILHADAS ==========

def obter_dados_grafico_rentabilidade(vendas):
    """Gera dados para o gráfico de rentabilidade por categoria"""
    try:
        itens_venda = ItemVenda.objects.filter(venda__in=vendas).select_related('produto__categoria')

        lucro_por_categoria = {}
        for item in itens_venda:
            categoria_nome = item.produto.categoria.nome if item.produto.categoria else "Sem Categoria"
            lucro_item = item.subtotal * Decimal('0.4')  # 40% de margem

            if categoria_nome not in lucro_por_categoria:
                lucro_por_categoria[categoria_nome] = Decimal('0.00')
            lucro_por_categoria[categoria_nome] += lucro_item

        # Converter para formato do gráfico
        dados = []
        cores = ['#22c55e', '#3b82f6', '#f59e0b', '#ef4444', '#8b5cf6']

        for i, (categoria, lucro) in enumerate(
                sorted(lucro_por_categoria.items(), key=lambda x: x[1], reverse=True)[:5]):
            dados.append({
                'name': categoria,
                'y': float(lucro),
                'color': cores[i] if i < len(cores) else '#94a3b8'
            })

        return {'series': [{'name': 'Lucro', 'data': dados}]}

    except Exception as e:
        print(f"Erro em obter_dados_grafico_rentabilidade: {e}")
        return {'series': []}


def obter_dados_tabela(vendas):
    """Gera dados reais para a tabela de relatórios (vendas por período)"""
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
                    'atendentes': set()
                }
            vendas_por_dia[data]['vendas'].append(venda)
            vendas_por_dia[data]['total_vendas'] += venda.total
            vendas_por_dia[data]['atendentes'].add(venda.atendente)

        # Ordenar por data (mais recente primeiro)
        datas_ordenadas = sorted(vendas_por_dia.keys(), reverse=True)

        for data in datas_ordenadas[:7]:
            info = vendas_por_dia[data]
            total_vendas = info['total_vendas']

            # Calcular custo e lucro
            custo = total_vendas * Decimal('0.6')
            lucro = total_vendas - custo
            margem = (lucro / total_vendas * 100) if total_vendas > 0 else Decimal('0.00')

            # Determinar status
            if margem > 35:
                status = 'Excelente'
                status_cor = 'green'
            elif margem > 25:
                status = 'Bom'
                status_cor = 'yellow'
            else:
                status = 'Regular'
                status_cor = 'red'

            # Atendentes do dia
            atendentes_nomes = [a.get_full_name() or a.username for a in info['atendentes']]
            nome_atendente = ', '.join(atendentes_nomes) if atendentes_nomes else 'N/A'

            dados.append({
                'data': data.strftime('%d/%m/%Y'),
                'vendas': total_vendas,
                'custo': custo,
                'lucro': lucro,
                'margem': margem,
                'atendente': nome_atendente,
                'status': status,
                'status_cor': status_cor,
                'tipo': 'vendas_periodo'
            })

        return dados

    except Exception as e:
        print(f"Erro em obter_dados_tabela: {e}")
        return []


def calcular_custo_total(vendas):
    """Calcula o custo total das vendas"""
    try:
        faturamento_total = vendas.aggregate(Sum('total'))['total__sum'] or Decimal('0.00')
        return faturamento_total * Decimal('0.6')
    except Exception as e:
        print(f"Erro em calcular_custo_total: {e}")
        return Decimal('0.00')