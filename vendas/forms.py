from django import forms
from django.core.exceptions import ValidationError

from clientes.models import Cliente
from productos.models import Produto
from vendas.models import ItemVenda, Venda


class ItemVendaForm(forms.ModelForm):
    produto_codigo = forms.CharField(max_length=50, label="Código do Produto")

    class Meta:
        model = ItemVenda
        fields = ['produto_codigo', 'quantidade', 'desconto']
        widgets = {
            'quantidade': forms.NumberInput(attrs={'min': 1, 'class': 'form-control'}),
            'desconto': forms.NumberInput(attrs={'min': 0, 'step': 0.01, 'class': 'form-control'}),
        }

    def clean_produto_codigo(self):
        codigo = self.cleaned_data['produto_codigo']
        try:
            produto = Produto.objects.get(codigo_barras=codigo)
        except Produto.DoesNotExist:
            raise ValidationError("Produto não encontrado")

        return produto

    def clean(self):
        cleaned_data = super().clean()
        produto = cleaned_data.get('produto_codigo')
        quantidade = cleaned_data.get('quantidade')

        if produto and quantidade:
            # Verifica se é medicamento controlado
            if produto.controlado and quantidade > 1:
                self.add_error('quantidade', 'Medicamentos controlados têm limite de 1 unidade por venda')

            # Verifica estoque
            estoque = produto.estoque_total()
            if estoque < quantidade:
                self.add_error('quantidade', f'Estoque insuficiente. Disponível: {estoque}')

        return cleaned_data


class VendaForm(forms.ModelForm):
    cliente_telefone = forms.CharField(max_length=15, required=False, label="Telefone do Cliente")

    class Meta:
        model = Venda
        fields = ['cliente_telefone', 'forma_pagamento', 'observacoes']
        widgets = {
            'forma_pagamento': forms.Select(attrs={'class': 'form-control'}),
            'observacoes': forms.Textarea(attrs={'class': 'form-control', 'rows': 2}),
        }

    def clean_cliente_telefone(self):
        telefone = self.cleaned_data['cliente_telefone']
        if telefone:
            try:
                cliente = Cliente.objects.get(telefone=telefone)
                return cliente
            except Cliente.DoesNotExist:
                # Cria cliente rápido se não existir
                nome = f"Cliente {telefone}"
                cliente = Cliente.objects.create(nome=nome, telefone=telefone)
                return cliente
        return None