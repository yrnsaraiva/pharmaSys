from django.contrib import admin
from import_export.admin import ImportExportModelAdmin
from import_export import fields, resources
from import_export.widgets import ForeignKeyWidget
from .models import Produto, Lote, Categoria

# ---------------------------------------------------
# Recurso para Produto - VERSÃO SIMPLIFICADA
# ---------------------------------------------------
class ProdutoResource(resources.ModelResource):
    categoria_nome = fields.Field(
        attribute='categoria',
        column_name='Categoria',
        widget=ForeignKeyWidget(Categoria, 'nome')
    )

    class Meta:
        model = Produto
        fields = ('id', 'nome', 'codigo_barras', 'carteiras_por_caixa','categoria_nome', 'preco_compra', 'preco_venda', 'estoque_minimo','controlado')
        export_order = ('id', 'nome', 'codigo_barras', 'carteiras_por_caixa','categoria_nome', 'preco_compra', 'preco_venda', 'controlado')

# ---------------------------------------------------
# Recurso para Lote - VERSÃO SIMPLIFICADA
# ---------------------------------------------------
class LoteResource(resources.ModelResource):
    produto_nome = fields.Field(
        attribute='produto',
        column_name='Produto',
        widget=ForeignKeyWidget(Produto, 'nome')
    )

    class Meta:
        model = Lote
        fields = ('produto_nome', 'numero_lote', 'nr_caixas', 'data_fabricacao', 'data_validade')
        import_id_fields = ['numero_lote']
        skip_unchanged = True

    def before_import_row(self, row, **kwargs):
        """Corrige dados antes da importação e cria produtos se necessário"""
        # Garantir que nr_caixas seja número
        if 'nr_caixas' in row:
            nr_caixas = row['nr_caixas']
            if nr_caixas in ['', None, ' ']:
                row['nr_caixas'] = 1
            try:
                row['nr_caixas'] = int(float(nr_caixas))
            except (ValueError, TypeError):
                row['nr_caixas'] = 1

        # Corrigir datas problemáticas específicas do seu arquivo
        problematic_dates = {
            '1900-01-04 00:00:00': '2025-01-04',
            '1930-09-01 00:00:00': '2030-09-01',
            '2020-02-01 00:00:00': '2025-02-01',
        }

        for date_field in ['data_fabricacao', 'data_validade']:
            if date_field in row and row[date_field]:
                date_str = str(row[date_field])
                if date_str in problematic_dates:
                    row[date_field] = problematic_dates[date_str]
                elif ' 00:00:00' in date_str:
                    # Remove a parte do tempo
                    row[date_field] = date_str.replace(' 00:00:00', '')

        # ✅ CRIA PRODUTO SE NÃO EXISTIR
        produto_nome = row.get('Produto')
        if produto_nome and not Produto.objects.filter(nome=produto_nome).exists():
            self._criar_produto_automaticamente(produto_nome)

    def _criar_produto_automaticamente(self, nome_produto):
        """Cria um produto básico automaticamente"""
        try:
            # Determinar categoria baseada no nome do produto
            categoria = self._determinar_categoria(nome_produto)

            # Criar produto com valores padrão
            produto = Produto.objects.create(
                nome=nome_produto,
                categoria=categoria,
                preco_compra=5.00,  # Valor padrão
                preco_venda=10.00,  # Valor padrão
                preco_carteira=10.00,
                carteiras_por_caixa=1,
                estoque_minimo=5,
                controlado=self._eh_controlado(nome_produto),
                forma_farmaceutica=self._determinar_forma_farmaceutica(nome_produto),
                dosagem=self._extrair_dosagem(nome_produto),
                principio_ativo=self._extrair_principio_ativo(nome_produto)
            )
            print(f"✅ Produto criado automaticamente: {nome_produto}")
            return produto
        except Exception as e:
            print(f"❌ Erro ao criar produto {nome_produto}: {e}")
            return None

    def _determinar_categoria(self, nome_produto):
        """Determina a categoria baseada no nome do produto"""
        nome_lower = nome_produto.lower()

        # Palavras-chave para cada categoria
        medicamento_keywords = ['comp', 'caps', 'mg', 'xarope', 'injecao', 'pomada', 'supositorio', 'comprimido']
        higiene_keywords = ['sabonete', 'shampoo', 'condicionador', 'desodorante', 'creme', 'gel', 'pasta']
        perfumaria_keywords = ['colonia', 'perfume', 'fragrância']
        suplemento_keywords = ['vitamina', 'omega', 'mineral', 'suplemento']
        conveniencia_keywords = ['fralda', 'algodao', 'penso', 'preservativo', 'biberon']

        if any(keyword in nome_lower for keyword in medicamento_keywords):
            return Categoria.objects.get_or_create(nome="Medicamentos", tipo="medicamento")[0]
        elif any(keyword in nome_lower for keyword in higiene_keywords):
            return Categoria.objects.get_or_create(nome="Higiene", tipo="higiene")[0]
        elif any(keyword in nome_lower for keyword in perfumaria_keywords):
            return Categoria.objects.get_or_create(nome="Perfumaria", tipo="perfumaria")[0]
        elif any(keyword in nome_lower for keyword in suplemento_keywords):
            return Categoria.objects.get_or_create(nome="Suplementos", tipo="suplemento")[0]
        elif any(keyword in nome_lower for keyword in conveniencia_keywords):
            return Categoria.objects.get_or_create(nome="Conveniência", tipo="conveniencia")[0]
        else:
            # Default para medicamento
            return Categoria.objects.get_or_create(nome="Medicamentos", tipo="medicamento")[0]

    def _eh_controlado(self, nome_produto):
        """Verifica se o produto é controlado baseado no nome"""
        controlados_keywords = ['diazepam', 'lorazepam', 'clonazepam', 'rivotril', 'codeína', 'tramadol', 'morfina']
        return any(keyword in nome_produto.lower() for keyword in controlados_keywords)

    def _determinar_forma_farmaceutica(self, nome_produto):
        """Determina a forma farmacêutica baseada no nome"""
        nome_lower = nome_produto.lower()

        formas = {
            'comprimido': ['comp', 'comprimido', 'cp'],
            'capsula': ['caps', 'cápsula', 'capsula'],
            'xarope': ['xarope', 'xp', 'suspensao', 'solução'],
            'injecao': ['injetavel', 'injecao', 'ampola'],
            'pomada': ['pomada', 'creme', 'gel'],
            'supositorio': ['supositorio'],
            'spray': ['spray', 'aerosol']
        }

        for forma, keywords in formas.items():
            if any(keyword in nome_lower for keyword in keywords):
                return forma
        return 'outro'

    def _extrair_dosagem(self, nome_produto):
        """Extrai dosagem do nome do produto"""
        import re
        # Procura por padrões como "500 mg", "10mg", "20 mg/mL"
        padroes = [
            r'(\d+)\s*mg',
            r'(\d+)mg',
            r'(\d+)\s*mg/ml',
            r'(\d+)\s*%'
        ]

        for padrao in padroes:
            match = re.search(padrao, nome_produto, re.IGNORECASE)
            if match:
                return match.group(0)
        return None

    def _extrair_principio_ativo(self, nome_produto):
        """Tenta extrair o princípio ativo do nome"""
        # Remove marcas e formas farmacêuticas comuns
        palavras_remover = ['comp', 'caps', 'mg', 'xarope', 'pomada', 'creme', 'gel', 'spray', 'supositorio']
        nome_limpo = nome_produto.lower()

        for palavra in palavras_remover:
            nome_limpo = nome_limpo.replace(palavra, '')

        # Remove números e espaços extras
        import re
        nome_limpo = re.sub(r'\d+', '', nome_limpo)
        nome_limpo = ' '.join(nome_limpo.split())

        return nome_limpo.title() if nome_limpo.strip() else None

    def import_obj(self, obj, data, dry_run):
        """Processa cada linha de importação"""
        try:
            produto_nome = data.get('Produto')
            if not produto_nome:
                print(f"⚠️  Ignorando - Nome do produto vazio")
                return None

            # Verifica se o produto existe (deveria ter sido criado no before_import_row)
            if not Produto.objects.filter(nome=produto_nome).exists():
                print(f"⚠️  Ignorando - Produto não encontrado após tentativa de criação: {produto_nome}")
                return None

            return super().import_obj(obj, data, dry_run)
        except Exception as e:
            print(f"⚠️  Erro ao importar linha: {e}")
            return None
# ---------------------------------------------------
# Admin Categoria (mantido igual)
# ---------------------------------------------------
@admin.register(Categoria)
class CategoriaAdmin(admin.ModelAdmin):
    list_display = ('nome', 'tipo', 'descricao_curta')
    list_filter = ('tipo',)
    search_fields = ('nome', 'descricao')
    list_editable = ('tipo',)

    def descricao_curta(self, obj):
        return obj.descricao[:50] + "..." if obj.descricao else "-"
    descricao_curta.short_description = "Descrição"

# ---------------------------------------------------
# Admin Produto com import/export (mantido igual)
# ---------------------------------------------------
@admin.register(Produto)
class ProdutoAdmin(ImportExportModelAdmin):
    resource_class = ProdutoResource
    list_display = ('nome', 'codigo_barras', 'categoria', 'preco_venda', 'estoque_atual', 'controlado')
    list_filter = ('categoria__tipo', 'controlado', 'forma_farmaceutica', 'nivel_prescricao')
    search_fields = ('nome', 'codigo_barras', 'principio_ativo')
    fieldsets = (
        ('Informações Básicas', {
            'fields': ('nome', 'codigo_barras', 'categoria', 'fornecedor', 'estoque_minimo')
        }),
        ('Preços', {
            'fields': ('preco_venda', 'preco_compra', 'preco_carteira')
        }),
        ('Detalhes Farmacêuticos', {
            'fields': ('forma_farmaceutica', 'carteiras_por_caixa', 'principio_ativo', 'controlado', 'dosagem', 'nivel_prescricao',),
            'description': 'Preencher apenas se for medicamento.',
            'classes': ('collapse',)
        }),
    )

    def estoque_atual(self, obj):
        return sum(lote.quantidade_disponivel for lote in obj.lote_set.all())
    estoque_atual.short_description = 'Estoque'

# ---------------------------------------------------
# Admin Lote (mantido igual)
# ---------------------------------------------------
@admin.register(Lote)
class LoteAdmin(ImportExportModelAdmin):
    resource_class = LoteResource
    list_display = ('numero_lote', 'produto', 'nr_caixas', 'quantidade_disponivel', 'data_validade')
    list_filter = ('produto__categoria__tipo',)
    search_fields = ('numero_lote', 'produto__nome')
