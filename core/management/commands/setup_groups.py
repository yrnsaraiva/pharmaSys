# core/management/commands/setup_groups.py
from django.core.management.base import BaseCommand
from django.contrib.auth.models import Group, Permission
from django.contrib.contenttypes.models import ContentType


class Command(BaseCommand):
    help = 'Cria os grupos de usuários (Admin, Gerente, Vendedor) com suas permissões'

    def handle(self, *args, **options):

        # ========== GRUPO ADMIN ==========
        admin_group, created = Group.objects.get_or_create(name='Admin')
        if created:
            # Admin tem TODAS as permissões
            all_permissions = Permission.objects.all()
            admin_group.permissions.set(all_permissions)
            self.stdout.write(self.style.SUCCESS('✅ Grupo ADMIN criado com TODAS as permissões'))
        else:
            self.stdout.write(self.style.WARNING('⚠️  Grupo ADMIN já existe'))

        # ========== GRUPO GERENTE ==========
        gerente_group, created = Group.objects.get_or_create(name='Gerente')
        if created:
            perms_gerente = [
                # ===== PRODUCTOS =====
                'view_produto', 'add_produto', 'change_produto',
                'view_categoria', 'add_categoria', 'change_categoria', 'delete_categoria',
                'view_lote', 'add_lote', 'change_lote', 'delete_lote',

                # ===== CLIENTES =====
                'view_cliente', 'add_cliente', 'change_cliente',

                # ===== FORNECEDORES =====
                'view_fornecedor', 'add_fornecedor', 'change_fornecedor',

                # ===== VENDAS =====
                'view_venda', 'add_venda', 'change_venda', 'cancelar_venda',

                # ===== SISTEMA =====
                'view_dashboard', 'view_relatorios',
            ]

            for perm in perms_gerente:
                try:
                    permission = Permission.objects.get(codename=perm)
                    gerente_group.permissions.add(permission)
                except Permission.DoesNotExist:
                    self.stdout.write(self.style.WARNING(f'⚠️  Permissão {perm} não encontrada'))

            self.stdout.write(self.style.SUCCESS('✅ Grupo GERENTE criado com permissões administrativas'))
        else:
            self.stdout.write(self.style.WARNING('⚠️  Grupo GERENTE já existe'))

        # ========== GRUPO VENDEDOR ==========
        vendedor_group, created = Group.objects.get_or_create(name='Vendedor')
        if created:
            perms_vendedor = [
                # ===== PRODUCTOS =====
                'view_produto', 'view_categoria',

                # ===== CLIENTES =====
                'view_cliente',

                # ===== VENDAS =====
                'view_venda', 'add_venda', 'cancelar_venda',

                # ===== SISTEMA =====
                'view_dashboard',
            ]

            for perm in perms_vendedor:
                try:
                    permission = Permission.objects.get(codename=perm)
                    vendedor_group.permissions.add(permission)
                except Permission.DoesNotExist:
                    self.stdout.write(self.style.WARNING(f'⚠️  Permissão {perm} não encontrada'))

            self.stdout.write(self.style.SUCCESS('✅ Grupo VENDEDOR criado com permissões básicas'))
        else:
            self.stdout.write(self.style.WARNING('⚠️  Grupo VENDEDOR já existe'))

        self.stdout.write(self.style.SUCCESS('🎉 SISTEMA DE NÍVEIS CRIADO COM SUCESSO!'))
        self.stdout.write('👉 Agora atribua usuários aos grupos pelo Django Admin')