from django.contrib.auth.models import User
from django.db import models
from django.core.validators import MinValueValidator
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
    data_venda = models.DateTimeField(auto_now_add=True)
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


class ItemVenda(models.Model):
    venda = models.ForeignKey(Venda, on_delete=models.CASCADE, related_name="itens")
    produto = models.ForeignKey(Produto, on_delete=models.PROTECT)
    quantidade = models.PositiveIntegerField(validators=[MinValueValidator(1)])
    preco_unitario = models.DecimalField(max_digits=10, decimal_places=2, default=0)

    class Meta:
        verbose_name = 'Item de Venda'
        verbose_name_plural = 'Itens de Venda'

    def __str__(self):
        return f"{self.quantidade}x {self.produto.nome}"

    def save(self, *args, **kwargs):
        # Garante que o preço unitário seja definido no momento da criação
        if not self.preco_unitario and self.produto:
            self.preco_unitario = self.produto.preco_venda
        super().save(*args, **kwargs)

        # Atualiza automaticamente o total da venda
        if self.venda_id:  # só recalcula se a venda já existir
            self.venda.calcular_total()

    @property
    def subtotal(self):
        """Retorna o subtotal, evitando erro se preco_unitario ainda não existir."""
        if not self.preco_unitario or not self.quantidade:
            return 0
        return self.preco_unitario * self.quantidade
