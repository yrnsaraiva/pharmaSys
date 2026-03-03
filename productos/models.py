import os

from django.db.models import Sum, F
from decimal import Decimal, ROUND_HALF_UP
from fornecedores.models import Fornecedor
from django.core.exceptions import ValidationError
from django.db import models
from django.utils import timezone




class Categoria(models.Model):
    nome = models.CharField(max_length=50)
    tipo = models.CharField(
        max_length=20,
        choices=[
            ("medicamento", "Medicamento"),
            ("higiene", "Higiene"),
            ("perfumaria", "Perfumaria"),
            ("suplemento", "Suplemento"),
            ("conveniencia", "Convêniencia"),
        ],
        default="medicamento"
    )
    descricao = models.TextField(blank=True)

    def __str__(self):
        return f"{self.nome} ({self.tipo})"

    class Meta:
        verbose_name = "Categoria"
        verbose_name_plural = "Categorias"
        ordering = ['nome']

class Produto(models.Model):
    nome = models.CharField(max_length=100)
    categoria = models.ForeignKey(Categoria, on_delete=models.SET_NULL, null=True)
    fornecedor = models.ForeignKey(Fornecedor, on_delete=models.SET_NULL, null=True)
    codigo_barras = models.CharField(max_length=50, unique=False, null=True, blank=True)

    preco_compra = models.DecimalField(max_digits=10, decimal_places=2)
    preco_venda = models.DecimalField(max_digits=10, decimal_places=2)
    preco_carteira = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)

    carteiras_por_caixa = models.PositiveIntegerField(default=1)
    estoque_minimo = models.PositiveIntegerField(default=10)

    FORMA_FARMACEUTICA_CHOICES = [
        ('comprimido', 'Comprimido'),
        ('capsula', 'Cápsula'),
        ('xarope', 'Xarope'),
        ('injecao', 'Injetável'),
        ('pomada', 'Pomada'),
        ('supositorio', 'Supositório'),
        ('spray', 'Spray'),
        ('outro', 'Outro'),
    ]
    forma_farmaceutica = models.CharField(
        max_length=50,
        choices=FORMA_FARMACEUTICA_CHOICES,
        blank=True,
        null=True
    )
    dosagem = models.CharField(max_length=50, blank=True, null=True)

    NIVEL_PRESCRICAO_CHOICES = [
        ('niv0', 'Niv 0'),
        ('niv1', 'Niv 1'),
        ('niv2', 'Niv 2'),
        ('niv3', 'Niv 3'),
        ('niv4', 'Niv 4'),
    ]
    nivel_prescricao = models.CharField(
        max_length=50,
        choices=NIVEL_PRESCRICAO_CHOICES,
        default='niv0',
        blank=True,
        null=True
    )
    principio_ativo = models.CharField(max_length=100, blank=True, null=True)
    controlado = models.BooleanField(default=False)

    def __str__(self):
        return f'{self.nome} - {self.codigo_barras or "sem código"}'

    class Meta:
        verbose_name = "Produto"
        verbose_name_plural = "Produtos"
        ordering = ['nome']

    # ============================================
    # PROPRIEDADES DE ESTOQUE (APENAS LOTES NÃO VENCIDOS)
    # ============================================

    @property
    def estoque_disponivel(self):
        """Retorna apenas o estoque de lotes não vencidos (para vendas)"""
        return self.lote_set.filter(
            quantidade_disponivel__gt=0,
            data_validade__gt=timezone.now().date()
        ).aggregate(total=Sum('quantidade_disponivel'))['total'] or 0

    @property
    def tem_estoque(self):
        """Verifica se há pelo menos uma unidade em lote não vencido"""
        return self.estoque_disponivel > 0

    @property
    def lotes_ativos(self):
        """Retorna quantos lotes NÃO VENCIDOS ainda têm estoque."""
        return self.lote_set.filter(
            quantidade_disponivel__gt=0,
            data_validade__gt=timezone.now().date()
        ).count()

    @property
    def valor_investido(self):
        """Soma do valor de custo de todos os lotes NÃO VENCIDOS."""
        lotes_validos = self.lote_set.filter(
            quantidade_disponivel__gt=0,
            data_validade__gt=timezone.now().date()
        )
        return sum(lote.valor_investido for lote in lotes_validos)

    @property
    def rendimento_potencial(self):
        """Soma do valor de venda de todos os lotes NÃO VENCIDOS."""
        lotes_validos = self.lote_set.filter(
            quantidade_disponivel__gt=0,
            data_validade__gt=timezone.now().date()
        )
        return sum(lote.rendimento_potencial for lote in lotes_validos)

    @property
    def estoque_em_caixas_carteiras(self):
        """Retorna tupla (caixas, carteiras) apenas de lotes NÃO VENCIDOS"""
        total_unidades = self.estoque_disponivel
        carteiras_por_caixa = self.carteiras_por_caixa or 1

        caixas = total_unidades // carteiras_por_caixa
        carteiras = total_unidades % carteiras_por_caixa

        return caixas, carteiras

    @property
    def status_estoque(self):
        """Status baseado apenas em estoque NÃO VENCIDO"""
        qtd = self.estoque_disponivel
        if qtd == 0:
            return "esgotado"
        elif qtd <= self.estoque_minimo:
            return "baixo"
        return "ok"

    @property
    def validade_proxima(self):
        """Data de validade mais próxima entre lotes NÃO VENCIDOS"""
        lote = self.lote_set.filter(
            quantidade_disponivel__gt=0,
            data_validade__gt=timezone.now().date()
        ).order_by("data_validade").first()

        return lote.data_validade if lote else None

    @property
    def dias_ate_validade(self):
        """Dias até a validade mais próxima (para alertas)"""
        if self.validade_proxima:
            delta = self.validade_proxima - timezone.now().date()
            return delta.days
        return None

    @property
    def alerta_validade(self):
        """Retorna mensagem de alerta se validade próxima (menos de 30 dias)"""
        dias = self.dias_ate_validade
        if dias is not None and dias <= 30:
            return f"⚠️ Vence em {dias} dias"
        return None

    # ============================================
    # PROPRIEDADES DE ESTOQUE VENCIDO (APENAS INFO GERENCIAL)
    # ============================================

    @property
    def estoque_vencido(self):
        """Retorna o estoque de lotes vencidos (apenas para informação gerencial)"""
        return self.lote_set.filter(
            quantidade_disponivel__gt=0,
            data_validade__lte=timezone.now().date()
        ).aggregate(total=Sum('quantidade_disponivel'))['total'] or 0

    @property
    def tem_vencido(self):
        """Verifica se há lotes vencidos com estoque (para alertas)"""
        return self.lote_set.filter(
            quantidade_disponivel__gt=0,
            data_validade__lte=timezone.now().date()
        ).exists()

    @property
    def lotes_vencidos(self):
        """Retorna quantos lotes vencidos ainda têm estoque."""
        return self.lote_set.filter(
            quantidade_disponivel__gt=0,
            data_validade__lte=timezone.now().date()
        ).count()

    @property
    def prejuizo_vencido(self):
        """Valor investido em lotes vencidos (prejuízo)"""
        lotes_vencidos = self.lote_set.filter(
            quantidade_disponivel__gt=0,
            data_validade__lte=timezone.now().date()
        )
        return sum(lote.valor_investido for lote in lotes_vencidos)

    # ============================================
    # PROPRIEDADES DE PREÇO
    # ============================================

    @property
    def preco_carteira_calculado(self):
        """Calcula o preço da carteira baseado no preço da caixa"""
        if self.preco_carteira:
            return self.preco_carteira

        if self.preco_venda and self.carteiras_por_caixa and self.carteiras_por_caixa > 0:
            preco_venda_decimal = Decimal(str(self.preco_venda))
            carteiras_decimal = Decimal(str(self.carteiras_por_caixa))
            calculado = preco_venda_decimal / carteiras_decimal
            return calculado.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

        return Decimal('0.00')

    @property
    def margem_lucro_percentual(self):
        """Retorna a margem de lucro percentual"""
        if self.preco_compra and self.preco_compra > 0:
            lucro = self.preco_venda - self.preco_compra
            return round((lucro / self.preco_compra) * 100, 2)
        return 0

    @property
    def margem_lucro_carteira_percentual(self):
        """Retorna a margem de lucro percentual da carteira"""
        if self.preco_compra and self.preco_carteira_calculado:
            custo_unitario = self.preco_compra / self.carteiras_por_caixa
            lucro = self.preco_carteira_calculado - custo_unitario
            return round((lucro / custo_unitario) * 100, 2)
        return 0

    # ============================================
    # MÉTODOS
    # ============================================

    def clean(self):
        """Validações do modelo"""
        if self.preco_venda and self.preco_compra:
            if self.preco_venda < self.preco_compra:
                raise ValidationError("Preço de venda não pode ser menor que preço de compra")

        if self.carteiras_por_caixa == 0:
            raise ValidationError("Carteiras por caixa não pode ser zero")

    def is_medicamento(self):
        """Verifica se o produto é um medicamento"""
        return self.categoria and self.categoria.tipo == "medicamento"

    def save(self, *args, **kwargs):
        """Override do save para calcular preço da carteira automaticamente"""
        self.clean()

        if not self.preco_carteira and self.preco_venda and self.carteiras_por_caixa:
            self.preco_carteira = self.preco_carteira_calculado

        super().save(*args, **kwargs)




class Lote(models.Model):
    produto = models.ForeignKey(Produto, on_delete=models.CASCADE)
    numero_lote = models.CharField(max_length=50, editable=False)  # impede edição manual
    nr_caixas = models.PositiveIntegerField(default=0)
    nr_carteiras = models.PositiveIntegerField(default=0)
    quantidade_disponivel = models.PositiveIntegerField(default=0)
    data_validade = models.DateField()
    data_fabricacao = models.DateField(blank=True, null=True)
    data_criacao = models.DateTimeField(auto_now_add=True)
    data_atualizacao = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Lote {self.numero_lote} - {self.produto.nome}"

    class Meta:
        verbose_name = "Lote"
        verbose_name_plural = "Lotes"
        ordering = ['data_validade']

    def clean(self):
        if self.data_validade and self.data_fabricacao:
            if self.data_validade <= self.data_fabricacao:
                raise ValidationError("Data de validade deve ser posterior à data de fabricação")

        # ✅ MODIFICADO: Permitir datas passadas em ambiente de desenvolvimento
        from django.conf import settings

        # Só valida data passada se NÃO estiver em DEBUG
        if not settings.DEBUG:
            if self.data_validade and self.data_validade < timezone.now().date():
                raise ValidationError("Data de validade não pode ser no passado")

    

    @property
    def total_unidades(self):
        carteiras_por_caixa = self.produto.carteiras_por_caixa or 1
        return (self.nr_caixas * carteiras_por_caixa) + self.nr_carteiras

    @property
    def valor_investido(self):
        return self.nr_caixas * self.produto.preco_compra


    @property
    def rendimento_potencial(self):
        """
        Rendimento potencial do lote:
        (preço da caixa × número de caixas) + (preço da carteira × número de carteiras)
        """
        preco_caixa = self.produto.preco_venda
        preco_carteira = self.produto.preco_carteira_calculado or 0
        return (self.nr_caixas * preco_caixa) + (self.nr_carteiras * preco_carteira)

    def save(self, *args, **kwargs):
        # GERAR O NÚMERO DO LOTE AUTOMATICAMENTE NA CRIAÇÃO
        if not self.pk:
            prefixo = self.produto.nome[:3].upper()  # Ex: Paracetamol → PA
            hoje = timezone.now().date()
            ano = hoje.strftime("%Y")
            mes = hoje.strftime("%m")
            total_lotes = Lote.objects.filter(produto=self.produto).count() + 1
            sequencia = f"{total_lotes:02d}"
            self.numero_lote = f"{prefixo}{ano}{mes}{sequencia}LT"  # Ex: PA20251201LT

        # validações
        self.clean()

        # atualizar quantidade disponível (se tiver campo no modelo)
        if hasattr(self, 'quantidade_disponivel'):
            self.quantidade_disponivel = (self.nr_caixas * getattr(self.produto, 'carteiras_por_caixa',
                                                                   1)) + self.nr_carteiras

        super().save(*args, **kwargs)

    def converter_para_caixas_carteiras(self, unidades):
        carteiras_por_caixa = self.produto.carteiras_por_caixa or 1
        caixas = unidades // carteiras_por_caixa
        carteiras = unidades % carteiras_por_caixa
        return caixas, carteiras

    def baixar_estoque(self, unidades):
        # ✅ VERIFICAR SE O LOTE ESTÁ VENCIDO
        if self.data_validade < timezone.now().date():
            raise ValidationError(
                f"Não é possível vender deste lote! "
                f"Lote {self.numero_lote} venceu em {self.data_validade}"
            )

        if unidades > self.quantidade_disponivel:
            raise ValidationError(f"Estoque insuficiente. Disponível: {self.quantidade_disponivel}")

        self.quantidade_disponivel -= unidades

        if self.quantidade_disponivel == 0:
            self.nr_caixas = 0
            self.nr_carteiras = 0
        else:
            self.nr_caixas, self.nr_carteiras = self.converter_para_caixas_carteiras(
                self.quantidade_disponivel
            )

        self.save(update_fields=[
            'quantidade_disponivel',
            'nr_caixas',
            'nr_carteiras',
            'data_atualizacao'
        ])
        return True
