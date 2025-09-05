from django.contrib import admin

from fornecedores.models import Fornecedor


@admin.register(Fornecedor)
class FornecedorAdmin(admin.ModelAdmin):
    list_display = ('nome', 'nuit', 'telefone', 'status', 'produtos_fornecidos')
    search_fields = ('nome', 'nuit')  # Busca por nome ou nuit
    list_filter = ('produto__categoria__tipo',)  # Filtro por tipo de produto fornecido

    # Exibe a quantidade de produtos vinculados
    def produtos_fornecidos(self, obj):
        return obj.produto_set.count()
    produtos_fornecidos.short_description = "Produtos"

    # Layout de edição avançado
    fieldsets = (
        ('Dados Básicos', {
            'fields': ('nome', 'pessoa_de_contacto', 'nuit', 'status')
        }),
        ('Contato', {
            'fields': ('telefone', 'endereco'),
            'classes': ('collapse',)  # Seção recolhível
        }),
    )