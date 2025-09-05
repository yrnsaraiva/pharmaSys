from django.db import models
from django.db.models import Sum
from datetime import date

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
    codigo_barras = models.CharField(max_length=50, unique=True)
    preco_venda = models.DecimalField(max_digits=10, decimal_places=2)
    preco_compra = models.DecimalField(max_digits=10, decimal_places=2)
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
        return f'{self.nome} - {self.codigo_barras}'

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


class Lote(models.Model):
    produto = models.ForeignKey(Produto, on_delete=models.CASCADE)
    numero_lote = models.CharField(max_length=50)
    quantidade_disponivel = models.PositiveIntegerField()
    data_validade = models.DateField()  # Opcional para não-medicamentos (ex.: shampoo)
    data_fabricacao = models.DateField(blank=True, null=True)

    def __str__(self):
        return f"Lote {self.numero_lote} - {self.produto.nome}"
