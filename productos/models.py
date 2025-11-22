from django.db import models
from django.db.models import Sum
from datetime import date
from decimal import Decimal, ROUND_CEILING

from fornecedores.models import Fornecedor


class Categoria(models.Model):
    nome = models.CharField(max_length=50)
    tipo = models.CharField(  # Define se é medicamento ou não
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


class Produto(models.Model):
    nome = models.CharField(max_length=100)
    categoria = models.ForeignKey(Categoria, on_delete=models.SET_NULL, null=True)
    fornecedor = models.ForeignKey(Fornecedor, on_delete=models.SET_NULL, null=True)
    codigo_barras = models.CharField(max_length=50, unique=False, null=True, blank=True)

    preco_compra = models.DecimalField(max_digits=10, decimal_places=2)
    preco_venda = models.DecimalField(max_digits=10, decimal_places=2)
    preco_carteira = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)

    carteiras_por_caixa = models.PositiveIntegerField(default=1, null=True, blank=True)
    estoque_minimo = models.PositiveIntegerField(default=10)

    # Campos específicos para medicamentos (opcionais)
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
    # Dosagem (ex: "500mg", "20mg/mL")
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
    controlado = models.BooleanField(default=False)  # Só relevante se for medicamento

    def __str__(self):
        return f'{self.nome} - {self.codigo_barras or "sem código"}'

    def is_medicamento(self):
        return self.categoria.tipo == "medicamento"

    def estoque_total(self):
        """Soma a quantidade disponível em todos os lotes."""
        return self.lote_set.aggregate(total=Sum("quantidade_disponivel"))["total"] or 0

    def status_estoque(self):
        """Verifica o status baseado no estoque mínimo"""
        qtd = self.estoque_total()
        if qtd == 0:
            return "esgotado"
        elif qtd < self.estoque_minimo:
            return "baixo"
        return "ok"

    def validade_mais_proxima(self):
        """Retorna a validade mais próxima (para exibir na tabela)"""
        lote = self.lote_set.filter(data_validade__gte=date.today()).order_by("data_validade").first()
        return lote.data_validade if lote else None

    # CORREÇÃO - No modelo Produto, substitua o método:
    def preco_carteira_calculado(self):
        """Calcula o preço da carteira se não estiver definido"""
        if self.preco_carteira:
            return self.preco_carteira
        elif self.preco_venda and self.carteiras_por_caixa and self.carteiras_por_caixa > 0:
            preco_venda_decimal = Decimal(str(self.preco_venda))
            carteiras_decimal = Decimal(str(self.carteiras_por_caixa))
            return (preco_venda_decimal / carteiras_decimal).quantize(Decimal("0.01"))
        else:
            return Decimal('0.00')

    def save(self, *args, **kwargs):
        # Só calcula se preco_carteira não estiver definido
        if self.preco_venda and self.carteiras_por_caixa:
            if not self.preco_carteira:
                preco_venda_decimal = Decimal(str(self.preco_venda))
                carteiras_decimal = Decimal(str(self.carteiras_por_caixa))
                self.preco_carteira = (preco_venda_decimal / carteiras_decimal).quantize(Decimal("1."),
                                                                                         rounding=ROUND_CEILING)
        super().save(*args, **kwargs)

    def estoque_total(self):
        """Retorna o estoque total somando todos os lotes"""
        lotes = self.lote_set.all()  # Assumindo que Lote tem ForeignKey para Produto
        return sum(lote.quantidade_disponivel for lote in lotes)

    def total_nr_caixas(self):
        """Retorna a soma de nr_caixas de todos os lotes"""
        return self.lote_set.aggregate(total=Sum('nr_caixas'))['total'] or 0

    def status_estoque(self):
        """Retorna o status do estoque"""
        estoque_total = self.estoque_total()
        if estoque_total == 0:
            return "sem_estoque"
        elif estoque_total <= self.estoque_minimo:
            return "baixo"
        else:
            return "ok"

class Lote(models.Model):
    produto = models.ForeignKey(Produto, on_delete=models.CASCADE)
    numero_lote = models.CharField(max_length=50)
    nr_caixas = models.PositiveIntegerField(default=1)
    quantidade_disponivel = models.PositiveIntegerField(editable=False, null=True, blank=True)
    data_validade = models.DateField()
    data_fabricacao = models.DateField(blank=True, null=True)

    def save(self, *args, **kwargs):
        # Inicializa estoque apenas se ainda não tiver valor
        if self.quantidade_disponivel is None:
            if self.produto and self.produto.carteiras_por_caixa:
                self.quantidade_disponivel = self.nr_caixas * self.produto.carteiras_por_caixa
            else:
                self.quantidade_disponivel = self.nr_caixas
        super().save(*args, **kwargs)

    def __str__(self):
        return f"Lote {self.numero_lote} - {self.produto.nome}"

