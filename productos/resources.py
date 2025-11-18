# productos/resources.py
from import_export import resources, fields
from import_export.widgets import ForeignKeyWidget, DateWidget
from .models import Produto, Lote, Categoria

class CategoriaResource(resources.ModelResource):
    class Meta:
        model = Categoria
        import_id_fields = ['nome']
        fields = ('id', 'nome', 'tipo', 'descricao')
        skip_unchanged = True
        report_skipped = True

class ProdutoResource(resources.ModelResource):
    categoria = fields.Field(
        column_name='categoria',
        attribute='categoria',
        widget=ForeignKeyWidget(Categoria, 'nome')
    )
    
    class Meta:
        model = Produto
        import_id_fields = ['codigo_barras']
        fields = ('id', 'nome', 'codigo_barras', 'categoria', 'preco_venda', 
                 'preco_compra', 'preco_carteira', 'forma_farmaceutica', 
                 'principio_ativo', 'controlado', 'dosagem', 'nivel_prescricao', 
                 'estoque_minimo', 'fornecedor')
        skip_unchanged = True
        report_skipped = True

class LoteResource(resources.ModelResource):
    produto = fields.Field(
        column_name='produto',
        attribute='produto',
        widget=ForeignKeyWidget(Produto, 'nome')
    )
    
    data_fabricacao = fields.Field(
        column_name='data_fabricacao',
        attribute='data_fabricacao',
        widget=DateWidget(format='%Y-%m-%d %H:%M:%S')
    )
    
    data_validade = fields.Field(
        column_name='data_validade',
        attribute='data_validade',
        widget=DateWidget(format='%Y-%m-%d %H:%M:%S')
    )
    
    class Meta:
        model = Lote
        fields = ('id', 'numero_lote', 'produto', 'nr_caixas', 'quantidade_disponivel', 
                 'data_validade', 'data_fabricacao')
        import_id_fields = ['numero_lote']
        skip_unchanged = True
        report_skipped = True
