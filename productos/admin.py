from django.contrib import admin
from django.contrib import messages
from import_export.admin import ImportExportModelAdmin
from import_export import fields, resources
from import_export.widgets import ForeignKeyWidget
from .models import Produto, Lote, Categoria


# ---------------------------------------------------
# Admin Produto - MELHORADO
# ---------------------------------------------------
@admin.register(Produto)
class ProdutoAdmin(ImportExportModelAdmin):
    resource_class = ProdutoResource
    list_display = ('nome', 'codigo_barras', 'categoria', 'preco_venda', 
                   'estoque_atual', 'controlado', 'data_criacao')
    list_filter = ('categoria__tipo', 'controlado', 'forma_farmaceutica', 
                  'nivel_prescricao', 'data_criacao')
    search_fields = ('nome', 'codigo_barras', 'principio_ativo')
    readonly_fields = ('data_criacao', 'data_atualizacao')
    list_per_page = 50
    
 

    def estoque_atual(self, obj):
        return sum(lote.quantidade_disponivel for lote in obj.lote_set.all())
    estoque_atual.short_description = 'Estoque'

# ---------------------------------------------------
# Admin Lote - MELHORADO
# ---------------------------------------------------
@admin.register(Lote)
class LoteAdmin(ImportExportModelAdmin):
    resource_class = LoteResource
    list_display = ('numero_lote', 'produto', 'nr_caixas', 'quantidade_disponivel', 
                   'data_validade', 'dias_para_vencer')
    list_filter = ('produto__categoria__tipo', 'data_validade')
    search_fields = ('numero_lote', 'produto__nome')
    readonly_fields = ('data_criacao',)
    date_hierarchy = 'data_validade'
    list_per_page = 50

   
