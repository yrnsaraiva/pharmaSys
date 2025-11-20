from .models import Produto, Categoria, Fornecedor, Lote
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.core.paginator import Paginator
from django.db.models import Q
from django.contrib.auth.decorators import login_required
from core.decorators import admin_required, gerente_required, vendedor_required
from django.utils import timezone
from io import BytesIO
from django.http import HttpResponse
from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side



# Listar categorias




@login_required
@gerente_required
def categorias_list(request):
    categorias = Categoria.objects.all().order_by('nome')

    search = request.GET.get('search', '')
    if search:
        categorias = categorias.filter(nome__icontains=search)

    paginator = Paginator(categorias, 5)
    page_number = request.GET.get("page")
    page_obj = paginator.get_page(page_number)

    # Calcular range dinâmico
    current_page = page_obj.number
    total_pages = paginator.num_pages

    # mostra 2 antes e 2 depois
    start_page = max(current_page - 2, 1)
    end_page = min(current_page + 2, total_pages)
    custom_range = range(start_page, end_page + 1)

    return render(request, "productos/categorias.html", {
        "categorias": page_obj,
        "page_obj": page_obj,
        "search": search,
        "custom_range": custom_range,
    })


@login_required
@gerente_required
def criar_categoria(request):
    if request.method == "POST":
        nome = request.POST.get("nome")
        tipo = request.POST.get("tipo")
        descricao = request.POST.get("descricao")

        categoria = Categoria.objects.create(
            nome=nome,
            tipo=tipo,
            descricao=descricao
        )
        print(categoria)
        categoria.save()

        return redirect('categorias_list')

    return render(request, "productos/nova_categoria.html")


# Excluir categoria
@login_required
@gerente_required
def remover_categoria(request, categoria_id):
    categoria = get_object_or_404(Categoria, pk=categoria_id)
    categoria.delete()
    return redirect("categorias_list")


# Listar productos
@login_required
@vendedor_required
def productos_list(request):
    # Obtém todos os productos
    productos = Produto.objects.all().order_by('nome')

    # Filtros
    search = request.GET.get('search', '')
    categoria = request.GET.get('categoria', '')
    status = request.GET.get('status', '')

    if search:
        productos = productos.filter(
            Q(nome__icontains=search) |
            Q(codigo_barras__icontains=search)
        )

    if categoria and categoria != "Todas":
        productos = productos.filter(categoria__nome__icontains=categoria)

    if status and status != "Todos":
        # Filtra usando o método status_estoque
        productos = [p for p in productos if p.status_estoque() == status.lower()]

    # Paginação: 5 productos por página
    paginator = Paginator(productos, 5)
    page_number = request.GET.get("page")
    page_obj = paginator.get_page(page_number)

    # Calcular range dinâmico
    current_page = page_obj.number
    total_pages = paginator.num_pages

    # mostra 2 antes e 2 depois
    start_page = max(current_page - 2, 1)
    end_page = min(current_page + 2, total_pages)
    custom_range = range(start_page, end_page + 1)

    # Categorias distintas para o select
    categorias = Produto.objects.values_list('categoria__nome', flat=True).distinct()

    context = {
        "productos": page_obj,
        "page_obj": page_obj,
        "search": search,
        "categoria": categoria,
        "status": status,
        "categorias": categorias,
        "custom_range": custom_range,
    }

    return render(request, "productos/productos.html", context)


@login_required
@gerente_required
def cadastrar_producto(request):
    categorias = Categoria.objects.all()
    fornecedores = Fornecedor.objects.all()

    if request.method == "POST":
        nome = request.POST.get("nome")
        categoria_id = request.POST.get("categoria")
        fornecedor_id = request.POST.get("fornecedor")
        codigo_barras = request.POST.get("codigo_barras")
        preco_venda = request.POST.get("preco_venda")
        preco_compra = request.POST.get("preco_compra")
        estoque_minimo = request.POST.get("estoque_minimo")
        carteiras_por_caixa = request.POST.get("carteiras_por_caixa")
        preco_carteira = request.POST.get("preco_carteira")

        # campos opcionais
        forma_farmaceutica = request.POST.get("forma_farmaceutica") or None
        dosagem = request.POST.get("dosagem") or None
        nivel_prescricao = request.POST.get("nivel_prescricao") or None
        principio_ativo = request.POST.get("principio_ativo") or None
        controlado = request.POST.get("controlado") == "on"

        categoria = get_object_or_404(Categoria, id=categoria_id) if categoria_id else None
        fornecedor = get_object_or_404(Fornecedor, id=fornecedor_id) if fornecedor_id else None

        produto = Produto(
            nome=nome,
            categoria=categoria,
            fornecedor=fornecedor,
            codigo_barras=codigo_barras,
            preco_venda=preco_venda,
            preco_compra=preco_compra,
            preco_carteira=preco_carteira,
            estoque_minimo=estoque_minimo,
            carteiras_por_caixa=carteiras_por_caixa,
            forma_farmaceutica=forma_farmaceutica,
            dosagem=dosagem,
            nivel_prescricao=nivel_prescricao,
            principio_ativo=principio_ativo,
            controlado=controlado,
        )
        produto.save()

        messages.success(request, "✅ Produto cadastrado com sucesso!")
        return redirect("productos_list")

    return render(request, "productos/novo_produto.html", {
        "categorias": categorias,
        "fornecedores": fornecedores,
        "Producto": Produto,
        "producto": {}

    })


# Excluir producto
@login_required
@admin_required
def remover_producto(request, producto_id):
    producto = get_object_or_404(Produto, pk=producto_id)
    producto.delete()
    return redirect("productos_list")

@login_required
@admin_required
def editar_producto(request, producto_id):
    producto = get_object_or_404(Produto, pk=producto_id)
    categorias = Categoria.objects.all()
    fornecedores = Fornecedor.objects.all()

    context = {'producto': producto,
               "categorias": categorias,
               "fornecedores": fornecedores,
               "Producto": Produto
               }

    if request.method == "POST":
        # Campos obrigatórios
        producto.nome = request.POST.get("nome")
        categoria_id = request.POST.get("categoria")
        fornecedor_id = request.POST.get("fornecedor")
        producto.codigo_barras = request.POST.get("codigo_barras")
        producto.preco_venda = float(request.POST.get("preco_venda") or 0)
        producto.preco_compra = float(request.POST.get("preco_compra") or 0)
        producto.estoque_minimo = int(request.POST.get("estoque_minimo") or 0)
        producto.carteiras_por_caixa = int(request.POST.get("carteiras_por_caixa") or 0)
        producto.preco_carteira = float(request.POST.get("preco_carteira") or 0) if request.POST.get(
            "preco_carteira") else None

        # Campos opcionais
        producto.forma_farmaceutica = request.POST.get("forma_farmaceutica") or None
        producto.dosagem = request.POST.get("dosagem") or None
        producto.nivel_prescricao = request.POST.get("nivel_prescricao") or None
        producto.principio_ativo = request.POST.get("principio_ativo") or None
        producto.controlado = request.POST.get("controlado") == "on"

        # Relacionamentos
        producto.categoria = get_object_or_404(Categoria, id=categoria_id) if categoria_id else None
        producto.fornecedor = get_object_or_404(Fornecedor, id=fornecedor_id) if fornecedor_id else None

        producto.save()
        messages.success(request, "✅ Produto atualizado com sucesso!")
        return redirect('productos_list')

    return render(request, 'productos/novo_produto.html', context)


@login_required
@gerente_required  # 👈 Apenas Admin e Gerente
def listar_lotes(request):
    search = request.GET.get("search", "")
    lotes = Lote.objects.select_related("produto").all()

    if search:
        lotes = lotes.filter(produto__nome__icontains=search)

    paginator = Paginator(lotes, 10)  # 10 lotes por página
    page_number = request.GET.get("page")
    page_obj = paginator.get_page(page_number)

    # Calcular range dinâmico
    current_page = page_obj.number
    total_pages = paginator.num_pages

    # mostra 2 antes e 2 depois
    start_page = max(current_page - 2, 1)
    end_page = min(current_page + 2, total_pages)
    custom_range = range(start_page, end_page + 1)

    context = {
        "page_obj": page_obj,
        "request": request,
        "custom_range": custom_range,
    }
    return render(request, "productos/lotes.html", context)


@login_required
@gerente_required  # 👈 Apenas Admin e Gerente
def criar_lote(request):
    if request.method == "POST":
        produto_id = request.POST.get("produto")
        numero_lote = request.POST.get("numero_lote")
        nr_caixas = request.POST.get("nr_caixas")  # novo campo: nº de caixas
        data_validade = request.POST.get("data_validade")
        data_fabricacao = request.POST.get("data_fabricacao")

        produto = get_object_or_404(Produto, id=produto_id)

        # Calcula quantidade_disponivel em carteiras
        try:
            nr_caixas = int(nr_caixas)
        except (TypeError, ValueError):
            nr_caixas = 0

        quantidade_disponivel = nr_caixas * (produto.carteiras_por_caixa or 1)

        lote = Lote.objects.create(
            produto=produto,
            numero_lote=numero_lote,
            nr_caixas=nr_caixas,
            quantidade_disponivel=quantidade_disponivel,
            data_validade=data_validade or None,
            data_fabricacao=data_fabricacao or None,
        )
        return redirect("listar_lotes")

    context = {
        "produtos": Produto.objects.all()
    }
    return render(request, "productos/novo_lote.html", context)


@login_required
@gerente_required  # 👈 Apenas Admin e Gerente
def remover_lote(request, pk):
    lote = get_object_or_404(Lote, pk=pk)
    lote.delete()
    return redirect("listar_lotes")




