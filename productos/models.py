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

    def clean(self):
        if self.preco_venda and self.preco_compra:
            if self.preco_venda < self.preco_compra:
                raise ValidationError("Preço de venda não pode ser menor que preço de compra")

        if self.carteiras_por_caixa == 0:
            raise ValidationError("Carteiras por caixa não pode ser zero")

    def is_medicamento(self):
        return self.categoria and self.categoria.tipo == "medicamento"



    @property
    def valor_investido_total(self):
        """Soma do valor de custo de todos os lotes ativos."""
        return sum(lote.valor_investido for lote in self.lote_set.filter(quantidade_disponivel__gt=0))

    @property
    def rendimento_total(self):
        """Soma do valor de venda de todos os lotes ativos."""
        return sum(lote.rendimento_potencial for lote in self.lote_set.filter(quantidade_disponivel__gt=0))

    @property
    def estoque_total(self):
        return self.lote_set.aggregate(
            total=Sum("quantidade_disponivel")
        )["total"] or 0

    @property
    def estoque_total_caixas_carteiras(self):
        total_unidades = self.estoque_total
        carteiras_por_caixa = self.carteiras_por_caixa or 1

        caixas = total_unidades // carteiras_por_caixa
        carteiras = total_unidades % carteiras_por_caixa

        return caixas, carteiras

    @property
    def status_estoque(self):
        qtd = self.estoque_total
        if qtd == 0:
            return "esgotado"
        elif qtd <= self.estoque_minimo:
            return "baixo"
        return "ok"

    @property
    def validade_mais_proxima(self):
        lote = self.lote_set.filter(
            quantidade_disponivel__gt=0,
            data_validade__gte=timezone.now().date()
        ).order_by("data_validade").first()

        return lote.data_validade if lote else None

    @property
    def preco_carteira_calculado(self):
        if self.preco_carteira:
            return self.preco_carteira

        if self.preco_venda and self.carteiras_por_caixa and self.carteiras_por_caixa > 0:
            preco_venda_decimal = Decimal(str(self.preco_venda))
            carteiras_decimal = Decimal(str(self.carteiras_por_caixa))
            calculado = preco_venda_decimal / carteiras_decimal
            return calculado.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

        return Decimal('0.00')

    @property
    def lotes_ativos(self):
        """Retorna quantos lotes ainda têm estoque."""
        return self.lote_set.filter(quantidade_disponivel__gt=0).count()


    def save(self, *args, **kwargs):
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

        if self.data_validade and self.data_validade < timezone.now().date():
            raise ValidationError("Data de validade não pode ser no passado")

    @property
    def total_unidades(self):
        carteiras_por_caixa = self.produto.carteiras_por_caixa or 1
        return (self.nr_caixas * carteiras_por_caixa) + self.nr_carteiras

    @property
    def valor_investido(self):
        return self.quantidade_disponivel * self.produto.preco_compra

    @property
    def rendimento_potencial(self):
        return self.quantidade_disponivel * self.produto.preco_venda

    def save(self, *args, **kwargs):

        # GERAR O NÚMERO DO LOTE AUTOMATICAMENTE NA CRIAÇÃO
        if not self.pk:
            prefixo = self.produto.nome[:2].upper()  # Ex: Paracetamol → PA
            total_lotes = Lote.objects.filter(produto=self.produto).count() + 1
            self.numero_lote = f"{prefixo}{total_lotes:02d}LT"  # Ex: PA01LT

        # validações
        self.clean()

        # atualizar quantidade disponível
        self.quantidade_disponivel = self.total_unidades

        super().save(*args, **kwargs)

    def converter_para_caixas_carteiras(self, unidades):
        carteiras_por_caixa = self.produto.carteiras_por_caixa or 1
        caixas = unidades // carteiras_por_caixa
        carteiras = unidades % carteiras_por_caixa
        return caixas, carteiras

    def baixar_estoque(self, unidades):
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
