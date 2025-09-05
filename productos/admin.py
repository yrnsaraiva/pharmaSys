from django.contrib import admin

from productos.models import Produto, Lote, Categoria


@admin.register(Categoria)
class CategoriaAdmin(admin.ModelAdmin):
    list_display = ('nome', 'tipo', 'descricao_curta')
    list_filter = ('tipo',)  # Filtro por tipo (medicamento, higiene, etc.)
    search_fields = ('nome', 'descricao')  # Busca por nome ou descrição
    list_editable = ('tipo',)  # Permite editar o tipo diretamente na lista

    # Exibe uma versão resumida da descrição
    def descricao_curta(self, obj):
        return obj.descricao[:50] + "..." if obj.descricao else "-"
    descricao_curta.short_description = "Descrição"


@admin.register(Produto)
class ProdutoAdmin(admin.ModelAdmin):
    list_display = ('nome', 'codigo_barras', 'categoria', 'preco_venda', 'estoque_atual', 'controlado')
    list_filter = ('categoria__tipo', 'controlado', 'forma_farmaceutica', 'nivel_prescricao')  # Filtro por tipo (medicamento, higiene, etc.)
    search_fields = ('nome', 'codigo_barras', 'principio_ativo')  # Busca flexível
    fieldsets = (
        ('Informações Básicas', {
            'fields': ('nome', 'categoria', 'fornecedor', 'codigo_barras')
        }),
        ('Preços', {
            'fields': ('preco_venda', 'preco_compra', 'estoque_minimo')
        }),
        ('Detalhes Farmacêuticos', {
            'fields': ('principio_ativo', 'controlado', 'forma_farmaceutica', 'dosagem', 'nivel_prescricao',),
            'description': 'Preencher apenas se for medicamento.',
            'classes': ('collapse',)  # Opcional: recolhe a seção
        }),
    )

    def estoque_atual(self, obj):
        return sum(lote.quantidade_disponivel for lote in obj.lote_set.all())
    estoque_atual.short_description = 'Estoque'


@admin.register(Lote)
class LoteAdmin(admin.ModelAdmin):
    list_display = ('numero_lote', 'quantidade_disponivel', 'data_validade')
    list_filter = ('produto__categoria__tipo',)  # Filtrar por tipo de produto

