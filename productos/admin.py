from django.contrib import admin
from import_export import resources
from import_export.admin import ImportExportModelAdmin
from import_export.formats import base_formats
from productos.models import Produto, Lote, Categoria
from productos.resources import CategoriaResource, ProdutoResource, LoteResource

@admin.register(Categoria)
class CategoriaAdmin(ImportExportModelAdmin):
    resource_class = CategoriaResource
    list_display = ('nome', 'tipo', 'descricao_curta')
    list_filter = ('tipo',)
    search_fields = ('nome', 'descricao')
    list_editable = ('tipo',)
    
    # Formatos de exportação suportados
    formats = [base_formats.XLSX, base_formats.CSV]

    def descricao_curta(self, obj):
        return obj.descricao[:50] + "..." if obj.descricao else "-"
    descricao_curta.short_description = "Descrição"

@admin.register(Produto)
class ProdutoAdmin(ImportExportModelAdmin):
    resource_class = ProdutoResource
    list_display = ('nome', 'codigo_barras', 'categoria', 'preco_venda', 'estoque_atual', 'controlado')
    list_filter = ('categoria__tipo', 'controlado', 'forma_farmaceutica', 'nivel_prescricao')
    search_fields = ('nome', 'codigo_barras', 'principio_ativo')
    
    # Formatos de exportação suportados
    formats = [base_formats.XLSX, base_formats.CSV]
    
    fieldsets = (
        ('Informações Básicas', {
            'fields': ('nome', 'codigo_barras', 'categoria', 'fornecedor', 'estoque_minimo')
        }),
        ('Preços', {
            'fields': ('preco_venda', 'preco_compra', 'preco_carteira')
        }),
        ('Detalhes Farmacêuticos', {
            'fields': ('forma_farmaceutica', 'carteiras_por_caixa', 'principio_ativo', 
                      'controlado', 'dosagem', 'nivel_prescricao'),
            'description': 'Preencher apenas se for medicamento.',
            'classes': ('collapse',)
        }),
    )

    def estoque_atual(self, obj):
        return sum(lote.quantidade_disponivel for lote in obj.lote_set.all())
    estoque_atual.short_description = 'Estoque'

@admin.register(Lote)
class LoteAdmin(ImportExportModelAdmin):
    resource_class = LoteResource
    list_display = ('numero_lote', 'produto', 'nr_caixas', 'quantidade_disponivel', 'data_validade', 'dias_para_vencer')
    list_filter = ('produto__categoria__tipo', 'data_validade')
    search_fields = ('numero_lote', 'produto__nome')
    
    # Formatos de exportação suportados
    formats = [base_formats.XLSX, base_formats.CSV]
    
    # Ordenar por data de validade (mais próximos de vencer primeiro)
    ordering = ('data_validade',)
    
    # Ações personalizadas
    actions = ['marcar_como_vencido']
    
    def dias_para_vencer(self, obj):
        from django.utils import timezone
        hoje = timezone.now().date()
        dias = (obj.data_validade - hoje).days
        if dias < 0:
            return f"Vencido há {abs(dias)} dias"
        elif dias == 0:
            return "Vence hoje!"
        elif dias <= 30:
            return f"{dias} dias (⚠️ Próximo)"
        else:
            return f"{dias} dias"
    dias_para_vencer.short_description = "Dias para vencer"
    
    def marcar_como_vencido(self, request, queryset):
        # Implementar lógica para marcar lotes como vencidos
        updated = queryset.update(quantidade_disponivel=0)
        self.message_user(request, f"{updated} lotes marcados como vencidos.")
    marcar_como_vencido.short_description = "Marcar lotes selecionados como vencidos"
