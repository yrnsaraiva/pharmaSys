# core/signals.py
from django.db.models.signals import post_migrate
from django.dispatch import receiver
from django.contrib.auth.models import Group, Permission
from django.apps import apps


@receiver(post_migrate)
def criar_grupos_automaticamente(sender, **kwargs):
    """
    Cria os grupos automaticamente após as migrações
    """
    # Só executa se o modelo Group já estiver criado
    if not apps.is_installed('django.contrib.auth'):
        return

    print("🔄 Configurando grupos de usuários...")

    # ========== GRUPO ADMIN ==========
    admin_group, created = Group.objects.get_or_create(name='Admin')
    if created:
        # Admin tem TODAS as permissões
        all_permissions = Permission.objects.all()
        admin_group.permissions.set(all_permissions)
        print("✅ Grupo ADMIN criado com TODAS as permissões")

    # ========== GRUPO GERENTE ==========
    gerente_group, created = Group.objects.get_or_create(name='Gerente')
    if created:
        permissoes_gerente = [
            # Productos
            'view_produto', 'add_produto', 'change_produto',
            'view_categoria', 'add_categoria', 'change_categoria', 'delete_categoria',
            'view_lote', 'add_lote', 'change_lote', 'delete_lote',
            # Clientes
            'view_cliente', 'add_cliente', 'change_cliente',
            # Fornecedores
            'view_fornecedor', 'add_fornecedor', 'change_fornecedor',
            # Vendas
            'view_venda', 'add_venda', 'change_venda', 'cancelar_venda',
        ]

        for codename in permissoes_gerente:
            try:
                perm = Permission.objects.get(codename=codename)
                gerente_group.permissions.add(perm)
            except Permission.DoesNotExist:
                print(f"⚠️  Permissão não encontrada: {codename}")

        print("✅ Grupo GERENTE criado")

    # ========== GRUPO VENDEDOR ==========
    vendedor_group, created = Group.objects.get_or_create(name='Vendedor')
    if created:
        permissoes_vendedor = [
            'view_produto', 'view_categoria',
            'view_cliente',
            'view_venda', 'add_venda', 'cancelar_venda',
        ]

        for codename in permissoes_vendedor:
            try:
                perm = Permission.objects.get(codename=codename)
                vendedor_group.permissions.add(perm)
            except Permission.DoesNotExist:
                print(f"⚠️  Permissão não encontrada: {codename}")

        print("✅ Grupo VENDEDOR criado")

    print("🎉 Grupos configurados automaticamente!")