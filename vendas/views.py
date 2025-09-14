from django.shortcuts import render, redirect, get_object_or_404
from django.forms.models import model_to_dict
from django.contrib import messages
from django.db.models import Q
from django.core.paginator import Paginator
from django.db import transaction
from datetime import date
from django.contrib.auth.decorators import login_required
import decimal
# libs para imprimir
from django.template.loader import render_to_string
from PIL import Image, ImageDraw, ImageFont
import io
import base64

from .models import Produto, Venda, ItemVenda, Cliente, Lote


@login_required
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
    paginator = Paginator(vendas, 5)  # 5 vendas por página
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    # Calcular range dinâmico
    current_page = page_obj.number
    total_pages = paginator.num_pages

    # mostra 2 antes e 2 depois
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


@login_required
def criar_venda(request):
    formas_pagamento = Venda.FORMA_PAGAMENTO_CHOICES
    clientes = Cliente.objects.all().order_by('nome')
    productos = Produto.objects.all().order_by('nome')
    cart = request.session.get('cart', [])
    total = 0
    subtotal = 0

    if request.method == 'POST':
        produto_id = request.POST.get('produto')  # campo do select2
        unidade = request.POST.get('unidade', 'carteira')  # default carteira

        if produto_id:
            try:
                produto = Produto.objects.get(id=produto_id)

                # Verificar estoque total considerando lotes válidos
                estoque_total = produto.estoque_total()
                if estoque_total <= 0:
                    messages.error(request, f'Produto {produto.nome} sem estoque!')
                    return redirect('criar_venda')

                # Converter o modelo para dicionário
                produto_dict = model_to_dict(produto)

                # Converter campos Decimal para float
                for key, value in produto_dict.items():
                    if isinstance(value, decimal.Decimal):
                        produto_dict[key] = float(value)

                # Adicionar informações extras
                produto_dict['categoria_nome'] = produto.categoria.nome if produto.categoria else ''
                produto_dict['estoque_total'] = estoque_total
                produto_dict['unidade'] = unidade  # 👈 adicionar unidade

                # Definir preço de venda conforme unidade
                if unidade == 'caixa':
                    produto_dict['preco_venda'] = float(produto.preco_venda)
                else:  # carteira
                    produto_dict['preco_venda'] = float(produto.preco_carteira_calculado())

                # Verificar se o produto já está no carrinho com a mesma unidade
                produto_existente = None
                for item in cart:
                    if item['id'] == produto_dict['id'] and item.get('unidade') == unidade:
                        produto_existente = item
                        break

                if produto_existente:
                    # Verificar se não excede o estoque
                    if produto_existente['quantidade'] + 1 > estoque_total:
                        messages.error(request,
                                       f'Estoque insuficiente para {produto.nome}! Disponível: {estoque_total}')
                    else:
                        produto_existente['quantidade'] += 1
                        produto_existente['subtotal'] = produto_existente['preco_venda'] * produto_existente['quantidade']
                        messages.success(request, f'Quantidade de {produto.nome} ({unidade}) aumentada!')
                else:
                    produto_dict['quantidade'] = 1
                    produto_dict['subtotal'] = produto_dict['preco_venda']
                    cart.append(produto_dict)
                    messages.success(request, f'Produto {produto.nome} ({unidade}) adicionado ao carrinho!')

                request.session['cart'] = cart
                request.session.modified = True

            except Produto.DoesNotExist:
                messages.error(request, 'Produto não encontrado!')

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
def finalizar_venda(request):
    if request.method == "POST":
        cliente_id = request.POST.get("cliente")
        forma_pagamento = request.POST.get("forma_pagamento")
        atendente = request.user

        cliente = None
        if cliente_id:
            cliente = get_object_or_404(Cliente, id=int(cliente_id))

        # Cria venda com total inicial 0 (será calculado depois)
        venda = Venda.objects.create(
            cliente=cliente,
            atendente=atendente,
            forma_pagamento=forma_pagamento,
            total=0
        )

        cart = request.session.get("cart", [])

        try:
            with transaction.atomic():
                for item in cart:
                    produto = get_object_or_404(Produto, id=item["id"])
                    ItemVenda.objects.create(
                        venda=venda,
                        produto=produto,
                        quantidade=item["quantidade"],
                        preco_unitario=item["preco_venda"],
                        unidade=item["unidade"]
                    )

                # Recalcular total da venda
                venda.calcular_total()

        except ValueError as e:
            messages.error(request, f"Erro ao finalizar venda: {e}")
            return redirect("criar_venda")

        # Limpar carrinho
        request.session["cart"] = []
        request.session.modified = True

        messages.success(request, f"Venda #{venda.id} finalizada com sucesso!")
        return redirect("detalhes_venda", venda_id=venda.id)  # ou para qualquer página de vendas


def atualizar_estoque_lotes(produto, quantidade_vendida):
    """Atualiza o estoque usando o sistema FIFO (First In, First Out)"""
    # Obter lotes válidos ordenados por validade (mais antigos primeiro)
    lotes = Lote.objects.filter(
        produto=produto,
        quantidade_disponivel__gt=0,
        data_validade__gte=date.today()
    ).order_by('data_validade')

    quantidade_restante = quantidade_vendida

    for lote in lotes:
        if quantidade_restante <= 0:
            break

        if lote.quantidade_disponivel >= quantidade_restante:
            # Lote tem quantidade suficiente
            lote.quantidade_disponivel -= quantidade_restante
            lote.save()
            quantidade_restante = 0
        else:
            # Usar todo este lote e passar para o próximo
            quantidade_restante -= lote.quantidade_disponivel
            lote.quantidade_disponivel = 0
            lote.save()

    if quantidade_restante > 0:
        # Se ainda sobrou quantidade, significa que o estoque era insuficiente
        raise Exception(f'Estoque insuficiente para {produto.nome}. Faltaram {quantidade_restante} unidades')


@login_required
def remover_produto(request, produto_id):
    cart = request.session.get('cart', [])
    cart = [item for item in cart if item['id'] != produto_id]
    request.session['cart'] = cart
    request.session.modified = True
    messages.success(request, 'Produto removido do carrinho!')
    return redirect('criar_venda')


def atualizar_quantidade(request, produto_id):
    if request.method == 'POST':
        quantidade = int(request.POST.get('quantidade', 1))
        cart = request.session.get('cart', [])

        for item in cart:
            if item['id'] == produto_id:
                # Verificar estoque antes de atualizar
                produto = Produto.objects.get(id=produto_id)
                estoque_total = produto.estoque_total()

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
def remover_venda(request, venda_id):
    venda = get_object_or_404(Venda, pk=venda_id)
    itens = ItemVenda.objects.filter(venda=venda)

    # Devolver ao estoque
    for item in itens:
        produto = item.produto
        quantidade = item.quantidade

        # Pega os lotes do produto (ordenados por validade inversa, para devolver no mais recente primeiro)
        lotes = Lote.objects.filter(produto=produto).order_by('-data_validade')

        quantidade_restante = quantidade
        for lote in lotes:
            if quantidade_restante <= 0:
                break
            lote.quantidade_disponivel += quantidade_restante
            lote.save()
            quantidade_restante = 0

        # Se não houver lote, pode lançar exceção ou apenas ignorar
        if quantidade_restante > 0:
            messages.warning(request, f"Não foi possível devolver {quantidade_restante} unidades de {produto.nome} (sem lote disponível).")

    # Agora sim remover os itens e a venda
    itens.delete()
    venda.delete()

    messages.success(request, f"Venda #{venda_id} removida e estoque atualizado.")
    return redirect('listar_vendas')


@login_required
def detalhes_venda(request, venda_id):
    venda = get_object_or_404(Venda, pk=venda_id)
    itens = ItemVenda.objects.filter(venda=venda)
    return render(request, 'vendas/detalhes_venda.html', {
        'venda': venda,
        'itens': itens
    })
