from django.core.paginator import Paginator
from django.shortcuts import render, redirect, get_object_or_404
from pyexpat.errors import messages
from django.contrib.auth.decorators import login_required
from django.db.models import Sum, Count

from .models import Cliente
from vendas.models import ItemVenda, Venda


# ---------- CRIAR CLIENTE ----------
@login_required
def criar_cliente(request):
    if request.method == "POST":
        nome_cliente = request.POST.get('nome')
        telefone_cliente = request.POST.get("phone")
        email_cliente = request.POST.get("email")

        # Criação do fornecedor
        cliente = Cliente.objects.create(
            nome=nome_cliente,
            telefone=telefone_cliente,
            email=email_cliente,

        )
        print(cliente)
        cliente.save()

        return redirect("listar_cliente")

    return render(request, "clientes/novos_clientes.html")


# ---------- LISTAR CLIENTES ----------
@login_required
def listar_cliente(request):
    # Obtém todos os fornecedores
    cliente = Cliente.objects.all()
    # Filtro por nome
    search = request.GET.get('search', '')
    if search:
        cliente = Cliente.objects.filter(nome__icontains=search)

    # Paginação: 5 fornecedores por página
    paginator = Paginator(cliente, 5)
    page_number = request.GET.get("page")
    page_obj = paginator.get_page(page_number)

    return render(request, "clientes/clientes.html", {
        "cliente": page_obj,
        "page_obj": page_obj,
        "search": search,  # útil para manter o valor no input
    })


# ---------- EDITAR CLIENTE ----------
@login_required
def editar_cliente(request, cliente_id):
    cliente = get_object_or_404(Cliente, id=cliente_id)

    if request.method == "POST":
        cliente.nome = request.POST.get('nome')
        cliente.telefone = request.POST.get("telefone")
        cliente.email = request.POST.get("email")

        cliente.save()
        return redirect("listar_cliente")

    context = {
        "cliente": cliente,
    }
    return render(request, "clientes/novos_clientes.html", context)


@login_required
def deletar_cliente(request, cliente_id):
    cliente = get_object_or_404(Cliente, pk=cliente_id)
    cliente.delete()
    return redirect("listar_cliente")


@login_required
def detalhes_cliente(request, cliente_id):
    cliente = get_object_or_404(Cliente, pk=cliente_id)

    # Estatísticas
    vendas = Venda.objects.filter(cliente=cliente)
    total_compras = vendas.count()
    total_gasto = vendas.aggregate(Sum('total'))['total__sum'] or 0
    ultima_compra = vendas.order_by('-data_venda').first()

    # Produtos mais comprados
    produtos_populares = (
        ItemVenda.objects.filter(venda__cliente=cliente)
        .values('produto__nome')
        .annotate(qtd=Sum('quantidade'))
        .order_by('-qtd')[:5]
    )

    context = {
        'cliente': cliente,
        'total_compras': total_compras,
        'total_gasto': total_gasto,
        'ultima_compra': ultima_compra,
        'produtos_populares': produtos_populares,
        'vendas': vendas[:10],  # últimas 10 compras
    }
    return render(request, 'clientes/detalhes_clientes.html', context)