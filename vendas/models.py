from decimal import Decimal

from django.contrib.auth.models import User
from django.db import models
from django.core.validators import MinValueValidator
from django.utils import timezone
from clientes.models import Cliente
from productos.models import Lote, Produto


class Venda(models.Model):
    FORMA_PAGAMENTO_CHOICES = [
        ("dinheiro", "Dinheiro"),
        ("mpesa", "M-Pesa"),
        ("emola", "E-Mola"),
        ('pos', 'POS'),
        ("transferencia", "Transferencia Bancaria"),
    ]

    cliente = models.ForeignKey(Cliente, on_delete=models.SET_NULL, null=True, blank=True)
    atendente = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    data_venda = models.DateTimeField(default=timezone.now)  # ✅ CORRETO
    data_atualizacao = models.DateTimeField(auto_now=True)
    total = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    forma_pagamento = models.CharField(max_length=20, choices=FORMA_PAGAMENTO_CHOICES)

    class Meta:
        ordering = ['-data_venda']
        permissions = [
            ("cancelar_venda", "Pode cancelar vendas"),
            ("reembolsar_venda", "Pode reembolsar vendas"),
            ("emitir_nfe", "Pode emitir NFE"),
        ]

    def calcular_total(self):
        total = sum(item.subtotal for item in self.itens.all())
        self.total = total
        self.save(update_fields=["total"])
        return self.total

    def __str__(self):
        cliente_nome = self.cliente.nome if self.cliente else 'Consumidor não identificado'
        return f"Venda #{self.id} - {cliente_nome}"


from django.utils import timezone


class ItemVenda(models.Model):
    UNIDADE_CHOICES = [
        ("caixa", "Caixa"),
        ("carteira", "Carteira"),
    ]

    venda = models.ForeignKey(Venda, on_delete=models.CASCADE, related_name="itens")
    produto = models.ForeignKey(Produto, on_delete=models.PROTECT)
    quantidade = models.PositiveIntegerField(validators=[MinValueValidator(1)])
    preco_unitario = models.DecimalField(max_digits=10, decimal_places=2)
    unidade = models.CharField(max_length=10, choices=UNIDADE_CHOICES, default="carteira")

    # ✅ SOLUÇÃO SIMPLES: Usar default em vez de auto_now_add
    data_criacao = models.DateTimeField(default=timezone.now)

    class Meta:
        ordering = ['-data_criacao']

    def save(self, *args, **kwargs):
        """Define preço unitário se não estiver definido"""
        if not self.preco_unitario and self.produto:
            if self.unidade == "caixa":
                self.preco_unitario = self.produto.preco_venda
            else:  # carteira
                self.preco_unitario = self.produto.preco_carteira_calculado

        super().save(*args, **kwargs)

    @property
    def subtotal(self):
        return (self.preco_unitario or Decimal('0.00')) * (self.quantidade or 1)

    def __str__(self):
        return f"{self.quantidade} {self.unidade}(s) de {self.produto.nome}"