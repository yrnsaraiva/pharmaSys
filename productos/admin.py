from django.contrib import admin
from django.contrib import messages
from import_export.admin import ImportExportModelAdmin
from import_export import fields, resources
from import_export.widgets import ForeignKeyWidget
from .models import Produto, Lote, Categoria

# ---------------------------------------------------
# Recurso para Produto - MELHORADO
# ---------------------------------------------------
class ProdutoResource(resources.ModelResource):
    categoria_nome = fields.Field(
        attribute='categoria',
        column_name='Categoria',
        widget=ForeignKeyWidget(Categoria, 'nome')
    )

    class Meta:
        model = Produto
        fields = ('id', 'nome', 'codigo_barras', 'carteiras_por_caixa', 
                 'categoria_nome', 'preco_compra', 'preco_venda', 
                 'estoque_minimo', 'controlado')
        export_order = ('id', 'nome', 'codigo_barras', 'carteiras_por_caixa',
                       'categoria_nome', 'preco_compra', 'preco_venda', 'controlado')
        
    def before_import(self, dataset, using_transactions, dry_run, **kwargs):
        """Validações antes da importação"""
        required_columns = ['nome', 'categoria_nome']
        missing_columns = [col for col in required_columns if col not in dataset.headers]
        
        if missing_columns:
            raise ValueError(f"Colunas obrigatórias faltando: {', '.join(missing_columns)}")

# ---------------------------------------------------
# Recurso para Lote - MELHORADO
# ---------------------------------------------------
class LoteResource(resources.ModelResource):
    produto_nome = fields.Field(
        attribute='produto',
        column_name='Produto',
        widget=ForeignKeyWidget(Produto, 'nome')
    )

    class Meta:
        model = Lote
        fields = ('produto_nome', 'numero_lote', 'nr_caixas', 
                 'data_fabricacao', 'data_validade')
        import_id_fields = ['numero_lote']
        skip_unchanged = True

    def __init__(self):
        super().__init__()
        self.produtos_criados = 0

    def before_import(self, dataset, using_transactions, dry_run, **kwargs):
        """Prepara para a importação"""
        self.produtos_criados = 0

    def after_import(self, dataset, result, using_transactions, dry_run, **kwargs):
        """Relatório após importação"""
        if not dry_run and self.produtos_criados > 0:
            messages.success(
                kwargs.get('request'), 
                f"Importação concluída! {self.produtos_criados} produtos criados automaticamente."
            )

    def before_import_row(self, row, **kwargs):
        """Corrige dados antes da importação"""
        # Validação de nr_caixas
        nr_caixas = row.get('nr_caixas', 1)
        if nr_caixas in ['', None, ' ']:
            row['nr_caixas'] = 1
        try:
            row['nr_caixas'] = max(1, int(float(nr_caixas)))  # Garante número positivo
        except (ValueError, TypeError):
            row['nr_caixas'] = 1

        # Correção de datas
        self._corrigir_datas(row)
        
        # Cria produto se necessário
        produto_nome = row.get('Produto')
        if produto_nome and not Produto.objects.filter(nome=produto_nome).exists():
            if self._criar_produto_automaticamente(produto_nome):
                self.produtos_criados += 1

    def _corrigir_datas(self, row):
        """Corrige formatos de data problemáticos"""
        problematic_dates = {
            '1900-01-04 00:00:00': '2025-01-04',
            '1930-09-01 00:00:00': '2030-09-01',
            '2020-02-01 00:00:00': '2025-02-01',
        }

        for date_field in ['data_fabricacao', 'data_validade']:
            if date_field in row and row[date_field]:
                date_str = str(row[date_field])
                
                # Aplica correções de datas problemáticas
                if date_str in problematic_dates:
                    row[date_field] = problematic_dates[date_str]
                elif ' 00:00:00' in date_str:
                    # Remove a parte do tempo
                    row[date_field] = date_str.replace(' 00:00:00', '')
                elif len(date_str) == 8 and date_str.isdigit():
                    # Converte formato DDMMYYYY
                    try:
                        day, month, year = date_str[:2], date_str[2:4], date_str[4:]
                        row[date_field] = f"20{year}-{month}-{day}"
                    except:
                        pass

    def _criar_produto_automaticamente(self, nome_produto):
        """Cria um produto básico automaticamente com validações"""
        try:
            # Valida nome do produto
            if not nome_produto or len(nome_produto.strip()) < 2:
                return False

            categoria = self._determinar_categoria(nome_produto)
            
            produto = Produto.objects.create(
                nome=nome_produto.strip(),
                categoria=categoria,
                preco_compra=5.00,
                preco_venda=10.00,
                preco_carteira=10.00,
                carteiras_por_caixa=1,
                estoque_minimo=5,
                controlado=self._eh_controlado(nome_produto),
                forma_farmaceutica=self._determinar_forma_farmaceutica(nome_produto),
                dosagem=self._extrair_dosagem(nome_produto),
                principio_ativo=self._extrair_principio_ativo(nome_produto)
            )
            print(f"✅ Produto criado automaticamente: {nome_produto}")
            return True
            
        except Exception as e:
            print(f"❌ Erro ao criar produto {nome_produto}: {e}")
            return False

    def _determinar_categoria(self, nome_produto):
        """Determina a categoria baseada no nome do produto com mais precisão"""
        nome_lower = nome_produto.lower()

        # Mapeamento mais abrangente de categorias
        categorias_map = {
            "Medicamentos": ['comp', 'caps', 'mg', 'xarope', 'injecao', 'pomada', 
                           'supositorio', 'comprimido', 'medicamento', 'remédio'],
            "Higiene": ['sabonete', 'shampoo', 'condicionador', 'desodorante', 
                       'creme', 'gel', 'pasta', 'escova', 'fio dental'],
            "Perfumaria": ['colonia', 'perfume', 'fragrância', 'eau', 'spray'],
            "Suplementos": ['vitamina', 'omega', 'mineral', 'suplemento', 'whey', 'proteína'],
            "Conveniência": ['fralda', 'algodao', 'penso', 'preservativo', 'biberon', 
                           'termometro', 'luva', 'mascara']
        }

        for categoria_nome, keywords in categorias_map.items():
            if any(keyword in nome_lower for keyword in keywords):
                return Categoria.objects.get_or_create(
                    nome=categoria_nome, 
                    tipo=categoria_nome.lower()
                )[0]
        
        # Default para medicamento
        return Categoria.objects.get_or_create(
            nome="Medicamentos", 
            tipo="medicamento"
        )[0]

    # ... (mantém os métodos _eh_controlado, _determinar_forma_farmaceutica, 
    # _extrair_dosagem, _extrair_principio_ativo existentes)

    def import_obj(self, obj, data, dry_run):
        """Processa cada linha de importação com melhor tratamento de erro"""
        try:
            produto_nome = data.get('Produto')
            if not produto_nome:
                return None

            # Verifica se o produto existe após tentativa de criação
            if not Produto.objects.filter(nome=produto_nome).exists():
                print(f"⚠️  Ignorando - Produto não encontrado: {produto_nome}")
                return None

            return super().import_obj(obj, data, dry_run)
            
        except Exception as e:
            print(f"❌ Erro ao importar linha: {e}")
            return None

# ---------------------------------------------------
# Admin Categoria - MELHORADO
# ---------------------------------------------------
@admin.register(Categoria)
class CategoriaAdmin(admin.ModelAdmin):
    list_display = ('nome', 'tipo', 'produtos_count', 'descricao_curta')
    list_filter = ('tipo',)
    search_fields = ('nome', 'descricao')
    list_editable = ('tipo',)
    list_per_page = 20

    def descricao_curta(self, obj):
        return obj.descricao[:50] + "..." if obj.descricao else "-"
    descricao_curta.short_description = "Descrição"

    def produtos_count(self, obj):
        return obj.produto_set.count()
    produtos_count.short_description = "Produtos"

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
    
    fieldsets = (
        ('Informações Básicas', {
            'fields': ('nome', 'codigo_barras', 'categoria', 'fornecedor', 'estoque_minimo')
        }),
        ('Preços', {
            'fields': ('preco_venda', 'preco_compra', 'preco_carteira'),
            'description': 'Preços em R$'
        }),
        ('Detalhes Farmacêuticos', {
            'fields': ('forma_farmaceutica', 'carteiras_por_caixa', 'principio_ativo', 
                      'controlado', 'dosagem', 'nivel_prescricao'),
            'classes': ('collapse',)
        }),
        ('Metadados', {
            'fields': ('data_criacao', 'data_atualizacao'),
            'classes': ('collapse',)
        }),
    )

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

    def dias_para_vencer(self, obj):
        if obj.data_validade:
            from datetime import date
            dias = (obj.data_validade - date.today()).days
            if dias < 0:
                return f"Vencido ({abs(dias)} dias)"
            elif dias < 30:
                return f"⚠️ {dias} dias"
            else:
                return f"{dias} dias"
        return "-"
    dias_para_vencer.short_description = 'Vencimento'
