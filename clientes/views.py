from django.http import JsonResponse
from django.core.paginator import Paginator
from django.shortcuts import render, redirect, get_object_or_404
from pyexpat.errors import messages
from django.contrib.auth.decorators import login_required
from django.db.models import Sum, Count

from .models import Cliente
from vendas.models import ItemVenda, Venda
from core.decorators import admin_required, gerente_required, vendedor_required
from django.db.models import Sum, Count, F


# ---------- CRIAR CLIENTE ----------
@login_required
@vendedor_required
def criar_cliente(request):
    if request.method == "POST":
        nome_cliente = request.POST.get('nome')
        telefone_cliente = request.POST.get("phone") or request.POST.get("telefone", "")
        email_cliente = request.POST.get("email", "")
        endereco_cliente = request.POST.get("endereco", "")

        # Validar campos obrigatórios
        if not nome_cliente:
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return JsonResponse({
                    'success': False,
                    'errors': 'Nome é obrigatório'
                })
            else:
                # Para requisição normal, mostrar erro na página
                return render(request, "clientes/novos_clientes.html", {
                    'error': 'Nome é obrigatório'
                })

        # Criação do cliente
        try:
            cliente = Cliente.objects.create(
                nome=nome_cliente,
                telefone=telefone_cliente,
                email=email_cliente if email_cliente else None,
                endereco=endereco_cliente if endereco_cliente else None
            )

            # Se for requisição AJAX (modal), retornar JSON
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return JsonResponse({
                    'success': True,
                    'cliente_id': cliente.id,
                    'cliente_nome': cliente.nome,
                    'cliente_telefone': cliente.telefone or '',
                    'message': 'Cliente criado com sucesso!'
                })
            else:
                # Se for requisição normal, redirecionar
                return redirect("listar_cliente")

        except Exception as e:
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return JsonResponse({
                    'success': False,
                    'errors': f'Erro ao criar cliente: {str(e)}'
                })
            else:
                return render(request, "clientes/novos_clientes.html", {
                    'error': f'Erro ao criar cliente: {str(e)}'
                })

    # Se for GET, renderizar o template normal
    return render(request, "clientes/novos_clientes.html")


# ---------- LISTAR CLIENTES ----------
@login_required
@vendedor_required
def listar_cliente(request):
    # Obtém todos os clientes
    cliente = Cliente.objects.all()
    # Filtro por nome
    search = request.GET.get('search', '')
    if search:
        cliente = Cliente.objects.filter(nome__icontains=search)

    # Paginação: 5 clientes por página
    paginator = Paginator(cliente, 5)
    page_number = request.GET.get("page")
    page_obj = paginator.get_page(page_number)

    # Calcular range dinâmico
    current_page = page_obj.number
    total_pages = paginator.num_pages

    # mostra 2 antes e 2 depois
    start_page = max(current_page - 2, 1)
    end_page = min(current_page + 2, total_pages)
    custom_range = range(start_page, end_page + 1)

    return render(request, "clientes/clientes.html", {
        "cliente": page_obj,
        "page_obj": page_obj,
        "search": search,  # útil para manter o valor no input
        "custom_range": custom_range,
    })


# ---------- EDITAR CLIENTE ----------
@login_required
@vendedor_required
def editar_cliente(request, cliente_id):
    cliente = get_object_or_404(Cliente, id=cliente_id)

    if request.method == "POST":
        cliente.nome = request.POST.get('nome')
        cliente.telefone = request.POST.get("telefone")
        cliente.email = request.POST.get("email")
        cliente.endereco = request.POST.get("endereco")

        cliente.save()
        return redirect("listar_cliente")

    context = {
        "cliente": cliente,
    }
    return render(request, "clientes/novos_clientes.html", context)


@login_required
@admin_required
def deletar_cliente(request, cliente_id):
    cliente = get_object_or_404(Cliente, pk=cliente_id)
    cliente.delete()
    return redirect("listar_cliente")


@vendedor_required
def detalhes_cliente(request, cliente_id):
    cliente = get_object_or_404(Cliente, id=cliente_id)

    # 🔹 Todas as vendas do cliente
    vendas = Venda.objects.filter(cliente=cliente).order_by('-data_venda')

    # 🔹 Estatísticas
    total_compras = vendas.count()
    total_gasto = vendas.aggregate(total=Sum('total'))['total'] or 0
    ultima_compra = vendas.first()

    # 🔹 Produtos mais comprados por esse cliente
    produtos_populares = (
        ItemVenda.objects
        .filter(venda__cliente=cliente)
        .values('produto__nome')
        .annotate(
            qtd_total=Sum('quantidade'),
            total_gasto=Sum(F('quantidade') * F('preco_unitario'))
        )
        .order_by('-qtd_total')[:5]
    )

    context = {
        'cliente': cliente,
        'vendas': vendas,
        'total_compras': total_compras,
        'total_gasto': total_gasto,
        'ultima_compra': ultima_compra,
        'produtos_populares': produtos_populares,
    }

    return render(request, 'clientes/detalhes_clientes.html', context)
