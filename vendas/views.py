from django.shortcuts import render, redirect, get_object_or_404
from django.forms.models import model_to_dict
from django.contrib import messages
from django.db.models import Q, Sum
from django.core.paginator import Paginator
from django.db import transaction
from datetime import date
from django.contrib.auth.decorators import login_required
from django.utils import timezone
import decimal

# libs para imprimir
from django.template.loader import render_to_string
from PIL import Image, ImageDraw, ImageFont
import io
import base64

from .models import Produto, Venda, ItemVenda, Cliente, Lote
from core.decorators import admin_required, gerente_required, vendedor_required


@login_required
@vendedor_required
def listar_vendas(request):
    vendas = Venda.objects.all().order_by('-data_venda')

    search = request.GET.get('search', '')
    date_start = request.GET.get('date_start', '')
    date_end = request.GET.get('date_end', '')
    payment = request.GET.get('payment', '')

    if search:
        vendas = vendas.filter(
            Q(id__icontains=search) |
            Q(cliente__nome__icontains=search)
        )
    if date_start:
        vendas = vendas.filter(data_venda__date__gte=date_start)
    if date_end:
        vendas = vendas.filter(data_venda__date__lte=date_end)
    if payment:
        vendas = vendas.filter(forma_pagamento=payment)

    # Paginação
    paginator = Paginator(vendas, 5)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    # Calcular range dinâmico
    current_page = page_obj.number
    total_pages = paginator.num_pages
    start_page = max(current_page - 2, 1)
    end_page = min(current_page + 2, total_pages)
    custom_range = range(start_page, end_page + 1)

    context = {
        'vendas': vendas,
        'search': search,
        'date_start': date_start,
        'date_end': date_end,
        'payment': payment,
        'formas_pagamento': Venda.FORMA_PAGAMENTO_CHOICES,
        'page_obj': page_obj,
        "custom_range": custom_range,
    }
    return render(request, 'vendas/listar_vendas.html', context)





@login_required
@vendedor_required
def criar_venda(request):
    formas_pagamento = Venda.FORMA_PAGAMENTO_CHOICES
    clientes = Cliente.objects.all().order_by('nome')
    productos = Produto.objects.all().order_by('nome')

    cart = request.session.get('cart', [])
    total = 0
    subtotal = 0

    if request.method == 'POST':
        produto_id = request.POST.get('produto')
        unidade = request.POST.get('unidade', 'carteira')
        quantidade = int(request.POST.get('quantidade', 1))

        if produto_id:
            try:
                produto = Produto.objects.get(id=produto_id)
                estoque_total = produto.estoque_total  # ✅ CORREÇÃO: Property sem parênteses

                # Verificar se produto já está no carrinho
                produto_existente_index = None
                for i, item in enumerate(cart):
                    if str(item['id']) == str(produto_id) and item.get('unidade') == unidade:
                        produto_existente_index = i
                        break

                if produto_existente_index is not None:
                    # Produto existe - atualizar quantidade
                    nova_quantidade = cart[produto_existente_index]['quantidade'] + quantidade

                    if nova_quantidade <= estoque_total:
                        cart[produto_existente_index]['quantidade'] = nova_quantidade
                        cart[produto_existente_index]['subtotal'] = cart[produto_existente_index][
                                                                        'preco_venda'] * nova_quantidade
                        messages.success(request, f'Quantidade de {produto.nome} atualizada para {nova_quantidade}!')
                    else:
                        messages.error(request, f'Estoque insuficiente! Disponível: {estoque_total}')

                else:
                    # Produto não existe - adicionar novo
                    produto_dict = {
                        'id': produto.id,
                        'nome': produto.nome,
                        'categoria_nome': produto.categoria.nome if produto.categoria else 'Sem categoria',
                        'estoque_total': estoque_total,
                        'unidade': unidade,
                        'quantidade': quantidade,
                    }

                    # Cálculo do preço - ✅ CORREÇÃO CRÍTICA
                    if unidade == 'caixa':
                        produto_dict['preco_venda'] = float(produto.preco_venda)
                    else:
                        # ✅ CORREÇÃO: preco_carteira_calculado é property, não método
                        preco_carteira = produto.preco_carteira_calculado  # SEM PARÊNTESES
                        produto_dict['preco_venda'] = float(preco_carteira) if preco_carteira else 0.0

                    produto_dict['subtotal'] = produto_dict['preco_venda'] * quantidade

                    if quantidade <= estoque_total:
                        cart.append(produto_dict)
                        messages.success(request, f'Produto {produto.nome} adicionado ao carrinho!')
                    else:
                        messages.error(request, f'Estoque insuficiente! Disponível: {estoque_total}')

                # Salvar carrinho
                request.session['cart'] = cart
                request.session.modified = True

            except Produto.DoesNotExist:
                messages.error(request, 'Produto não encontrado!')
            except Exception as e:
                messages.error(request, f'Erro ao adicionar produto: {e}')

            return redirect('criar_venda')

    # Calcular totais
    for produto in cart:
        produto['subtotal'] = produto['preco_venda'] * produto.get('quantidade', 1)
        subtotal += produto['subtotal']

    total = subtotal

    context = {
        'cart': cart,
        'produtos': productos,
        'subtotal': subtotal,
        'total': total,
        'formas_pagamento': formas_pagamento,
        'clientes': clientes,
    }

    return render(request, 'vendas/criar_venda.html', context)


@login_required
@vendedor_required
def finalizar_venda(request):
    if request.method == "POST":
        cliente_id = request.POST.get("cliente")
        forma_pagamento = request.POST.get("forma_pagamento")
        atendente = request.user

        cliente = get_object_or_404(Cliente, id=int(cliente_id)) if cliente_id else None
        cart = request.session.get("cart", [])

        if not cart:
            messages.error(request, "Carrinho vazio! Adicione produtos antes de finalizar.")
            return redirect("criar_venda")

        try:
            with transaction.atomic():

                # Criar venda
                venda = Venda.objects.create(
                    cliente=cliente,
                    atendente=atendente,
                    forma_pagamento=forma_pagamento,
                    total=0
                )

                # Agrupar itens por produto
                from collections import defaultdict
                produtos_agrupados = defaultdict(lambda: {'caixas': 0, 'carteiras': 0, 'itens': []})

                for item in cart:
                    produto_id = item["id"]
                    if item["unidade"] == "caixa":
                        produtos_agrupados[produto_id]['caixas'] += item["quantidade"]
                    else:
                        produtos_agrupados[produto_id]['carteiras'] += item["quantidade"]
                    produtos_agrupados[produto_id]['itens'].append(item)

                # Processar cada produto agrupado
                for produto_id, dados in produtos_agrupados.items():
                    produto = get_object_or_404(Produto, id=produto_id)
                    carteiras_por_caixa = produto.carteiras_por_caixa or 1

                    # Total solicitado
                    total_unidades = dados['caixas'] * carteiras_por_caixa + dados['carteiras']

                    # Buscar lotes por validade
                    lotes = Lote.objects.select_for_update().filter(
                        produto=produto,
                        quantidade_disponivel__gt=0
                    ).order_by("data_validade")

                    quantidade_restante = total_unidades

                    for lote in lotes:
                        if quantidade_restante <= 0:
                            break

                        estoque_antes = lote.quantidade_disponivel

                        if estoque_antes <= quantidade_restante:
                            # LOTE TOTALMENTE CONSUMIDO
                            debitar = estoque_antes
                            quantidade_restante -= debitar

                            lote.quantidade_disponivel = 0
                            lote.nr_caixas = 0
                            lote.nr_carteiras = 0
                            lote.save()

                        else:
                            # DÉBITO PARCIAL
                            debitar = quantidade_restante
                            novo_estoque = estoque_antes - debitar

                            lote.quantidade_disponivel = novo_estoque
                            lote.nr_caixas, lote.nr_carteiras = lote.converter_para_caixas_carteiras(novo_estoque)
                            lote.save()

                            quantidade_restante = 0

                    # Falta de estoque
                    if quantidade_restante > 0:
                        raise Exception(
                            f"Estoque insuficiente para {produto.nome}. "
                            f"Faltam {quantidade_restante} unidades."
                        )

                    # Criar itens da venda
                    for item in dados['itens']:
                        ItemVenda.objects.create(
                            venda=venda,
                            produto=produto,
                            quantidade=item["quantidade"],
                            preco_unitario=item["preco_venda"],
                            unidade=item["unidade"]
                        )

                # Calcular total da venda
                venda.calcular_total()

                # Limpar carrinho
                request.session["cart"] = []
                request.session.modified = True

                messages.success(request, f"Venda #{venda.id} finalizada com sucesso!")
                return redirect("detalhes_venda", venda_id=venda.id)

        except Exception as e:
            messages.error(request, f"Erro ao finalizar venda: {e}")
            return redirect("criar_venda")

    return redirect("criar_venda")


@login_required
def remover_produto(request, produto_id):
    cart = request.session.get('cart', [])

    # ✅ CORREÇÃO: Converter para string para comparação segura
    produto_id_str = str(produto_id)
    cart = [item for item in cart if str(item['id']) != produto_id_str]

    request.session['cart'] = cart
    request.session.modified = True
    messages.success(request, 'Produto removido do carrinho!')
    return redirect('criar_venda')


@login_required
def atualizar_quantidade(request, produto_id):
    if request.method == 'POST':
        quantidade = int(request.POST.get('quantidade', 1))
        cart = request.session.get('cart', [])

        # ✅ CORREÇÃO: Converter para string para comparação segura
        produto_id_str = str(produto_id)

        for item in cart:
            if str(item['id']) == produto_id_str:
                # Verificar estoque antes de atualizar
                produto = Produto.objects.get(id=produto_id)
                estoque_total = produto.estoque_total  # ✅ CORREÇÃO: Property sem parênteses

                if quantidade > estoque_total:
                    messages.error(request, f'Estoque insuficiente! Disponível: {estoque_total}')
                    return redirect('criar_venda')

                item['quantidade'] = max(1, quantidade)
                item['subtotal'] = item['preco_venda'] * item['quantidade']
                break

        request.session['cart'] = cart
        request.session.modified = True

    return redirect('criar_venda')


@login_required
def cancelar_venda(request):
    if request.method == 'POST':
        request.session['cart'] = []
        request.session.modified = True
        messages.info(request, 'Venda cancelada!')

    return redirect('criar_venda')


@login_required
@admin_required
def remover_venda(request, venda_id):
    venda = get_object_or_404(Venda, pk=venda_id)
    itens = ItemVenda.objects.filter(venda=venda)

    try:
        with transaction.atomic():
            # Devolver ao estoque
            for item in itens:
                produto = item.produto

                # ✅ CORREÇÃO: Converter para unidades
                if item.unidade == "caixa":
                    quantidade_em_unidades = item.quantidade * (produto.carteiras_por_caixa or 1)
                else:
                    quantidade_em_unidades = item.quantidade

                # Adicionar ao primeiro lote válido
                lote = Lote.objects.filter(
                    produto=produto,
                    data_validade__gte=timezone.now().date()
                ).order_by('data_validade').first()

                if lote:
                    lote.quantidade_disponivel += quantidade_em_unidades
                    lote.save()
                else:
                    # Se não há lote válido, criar um novo
                    lote = Lote.objects.create(
                        produto=produto,
                        numero_lote=f"DEV_{venda_id}",
                        nr_caixas=0,
                        nr_carteiras=quantidade_em_unidades,
                        data_validade=timezone.now().date() + timezone.timedelta(days=365),
                        data_fabricacao=timezone.now().date()
                    )

            # Remover os itens e a venda
            itens.delete()
            venda.delete()

            messages.success(request, f"Venda #{venda_id} removida e estoque atualizado.")

    except Exception as e:
        messages.error(request, f"Erro ao remover venda: {e}")

    return redirect('listar_vendas')


@login_required
@vendedor_required
def detalhes_venda(request, venda_id):
    venda = get_object_or_404(Venda, pk=venda_id)
    itens = ItemVenda.objects.filter(venda=venda)

    return render(request, 'vendas/detalhes_venda.html', {
        'venda': venda,
        'itens': itens
    })
    
def imprimir_recibo_imagem(request, venda_id):
    venda = get_object_or_404(Venda, id=venda_id)
    recibo_texto = render_to_string('vendas/recibo_termico.txt', {'venda': venda})

    # Ajuste do tamanho da fonte e cálculo da altura
    try:
        font = ImageFont.truetype("Courier", 17)
        # font = ImageFont.load_default(size=18)
    except IOError:
        font = ImageFont.load_default(size=18)

    # Calcular a altura da imagem com base no texto
    largura = 400
    altura_texto = 0
    draw = ImageDraw.Draw(Image.new("RGB", (largura, 1)))  # Usar uma imagem temporária para medir o texto

    # Usar textbbox para calcular o tamanho do texto
    for linha in recibo_texto.split('\n'):
        _, _, _, altura_linha = draw.textbbox((0, 0), linha, font=font)  # Retorna as coordenadas da caixa delimitadora
        altura_texto += altura_linha + 6  # +4 para o espaçamento entre as linhas

    altura = max(altura_texto, 100)  # Garantir que a altura mínima seja 100px

    # Criar a imagem com a altura calculada
    img = Image.new("RGB", (largura, altura), "white")
    draw = ImageDraw.Draw(img)

    # Desenhar o texto
    draw.multiline_text((10, 10), recibo_texto, fill="black", font=font, spacing=4)

    # Salvar a imagem em Base64 para exibir no HTML
    buffer = io.BytesIO()
    img.save(buffer, format="PNG")
    buffer.seek(0)
    img_base64 = base64.b64encode(buffer.getvalue()).decode("utf-8")

    return render(request, 'vendas/imprimir_recibo.html', {'img_base64': img_base64})
