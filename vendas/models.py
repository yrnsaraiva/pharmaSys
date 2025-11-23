from django.contrib.auth.models import User
from django.db import models
from django.db import transaction
from django.core.validators import MinValueValidator
from django.utils import timezone  # ✅ ADICIONE ESTA LINHA
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
    data_venda = models.DateTimeField(default=timezone.now)  # ✅ AGORA FUNCIONA
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
    UNIDADE_CHOICES = [
        ("caixa", "Caixa"),
        ("carteira", "Carteira"),
    ]

    venda = models.ForeignKey(Venda, on_delete=models.CASCADE, related_name="itens")
    produto = models.ForeignKey(Produto, on_delete=models.PROTECT)
    quantidade = models.PositiveIntegerField(validators=[MinValueValidator(1)])
    preco_unitario = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    unidade = models.CharField(max_length=10, choices=UNIDADE_CHOICES, default="carteira")

    def __str__(self):
        return f"{self.quantidade} {self.unidade}(s) de {self.produto.nome}"

    def save(self, *args, **kwargs):
        # Definir preco_unitario se não existir
        if not self.preco_unitario and self.produto:
            if self.unidade == "caixa":
                self.preco_unitario = self.produto.preco_venda
            else:  # carteira
                self.preco_unitario = self.produto.preco_carteira_calculado()

        super().save(*args, **kwargs)

        # Baixa estoque após salvar o item
        if self.venda_id:
            self.baixar_estoque()
            self.venda.calcular_total()

    def baixar_estoque(self):
        qtd = self.quantidade
        if self.unidade == "caixa":
            qtd *= (self.produto.carteiras_por_caixa or 1)

        print(f"[DEBUG] Baixando estoque de {self.produto.nome}: {qtd} unidades")

        with transaction.atomic():
            lotes = self.produto.lote_set.select_for_update().filter(
                quantidade_disponivel__gt=0
            ).order_by("data_validade", "id")

            for lote in lotes:
                if qtd <= 0:
                    break

                if lote.quantidade_disponivel >= qtd:
                    lote.quantidade_disponivel -= qtd
                    # Atualiza nr_caixas
                    if self.produto.carteiras_por_caixa:
                        lote.nr_caixas = lote.quantidade_disponivel // self.produto.carteiras_por_caixa
                    else:
                        lote.nr_caixas = lote.quantidade_disponivel
                    lote.save(update_fields=["quantidade_disponivel", "nr_caixas"])
                    qtd = 0
                else:
                    qtd -= lote.quantidade_disponivel
                    lote.quantidade_disponivel = 0
                    lote.nr_caixas = 0
                    lote.save(update_fields=["quantidade_disponivel", "nr_caixas"])

            if qtd > 0:
                raise ValueError(f"Estoque insuficiente para {self.produto.nome}!")

    @property
    def subtotal(self):
        return (self.preco_unitario or 0) * (self.quantidade or 0)
