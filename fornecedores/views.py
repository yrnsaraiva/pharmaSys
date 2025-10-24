from django.shortcuts import render, redirect, get_object_or_404
from .models import Fornecedor
from django.core.paginator import Paginator
from django.contrib import messages
from django.contrib.auth.decorators import login_required


# Listar fornecedores
@login_required
def fornecedores_list(request):
    # Obtém todos os fornecedores
    fornecedores = Fornecedor.objects.all()

    # Filtro por nome
    search = request.GET.get('search', '')
    if search:
        fornecedores = fornecedores.filter(nome__icontains=search)

    # Paginação: 5 fornecedores por página
    paginator = Paginator(fornecedores, 5)
    page_number = request.GET.get("page")
    page_obj = paginator.get_page(page_number)

    # Calcular range dinâmico
    current_page = page_obj.number
    total_pages = paginator.num_pages

    # mostra 2 antes e 2 depois
    start_page = max(current_page - 2, 1)
    end_page = min(current_page + 2, total_pages)
    custom_range = range(start_page, end_page + 1)

    return render(request, "fornecedores/fornecedores.html", {
        "fornecedores": page_obj,
        "page_obj": page_obj,
        "search": search,  # útil para manter o valor no input
        "custom_range": custom_range,
    })


# Criar fornecedor
@login_required
def cadastrar_fornecedor(request):
    if request.method == "POST":
        nome_empresa = request.POST.get("company-name")
        pessoa_contacto = request.POST.get("contact-person")
        nuit = request.POST.get("nuit")
        telefone = request.POST.get("phone")
        morada = request.POST.get("address")
        ativo = request.POST.get("active-status") == "on"  # Checkbox

        # Criação do fornecedor
        fornecedor = Fornecedor.objects.create(
            nome=nome_empresa,
            pessoa_de_contacto=pessoa_contacto,
            nuit=nuit,
            telefone=telefone,
            endereco=morada,
            status=ativo
        )
        print(fornecedor)
        fornecedor.save()

        redirect('listar_fornecedores')

    return render(request, "fornecedores/novo_fornecedor.html")


# Editar fornecedor
@login_required
def editar_fornecedor(request, fornecedor_id):
    fornecedor = get_object_or_404(Fornecedor, id=fornecedor_id)

    if request.method == "POST":
        fornecedor.nome_empresa = request.POST.get("company-name")
        fornecedor.pessoa_contacto = request.POST.get("contact-person")
        fornecedor.nuit = request.POST.get("nuit")
        fornecedor.categoria = request.POST.get("category")
        fornecedor.telefone = request.POST.get("phone")
        fornecedor.email = request.POST.get("email")
        fornecedor.morada = request.POST.get("address")
        fornecedor.ativo = request.POST.get("active-status") == "on"

        fornecedor.save()
        messages.success(request, "Fornecedor atualizado com sucesso!")
        return redirect("listar_fornecedores")

    context = {
        "fornecedor": fornecedor
    }
    return render(request, "fornecedores/novo_fornecedor.html", context)


# Excluir fornecedor
@login_required
def remover_fornecedor(request, fornecedor_id):
    fornecedor = get_object_or_404(Fornecedor, pk=fornecedor_id)
    fornecedor.delete()
    return redirect("listar_fornecedores")

