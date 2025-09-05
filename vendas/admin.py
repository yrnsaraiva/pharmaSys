


from django.contrib import admin
from django.db.models import Sum, F, DecimalField, ExpressionWrapper
from vendas.models import Venda, ItemVenda


class ItemVendaInline(admin.TabularInline):
    model = ItemVenda
    extra = 1
    fields = ('produto', 'quantidade', 'preco_unitario', 'subtotal')
    readonly_fields = ('subtotal',)
    autocomplete_fields = ('produto',)


@admin.register(Venda)
class VendaAdmin(admin.ModelAdmin):
    autocomplete_fields = ['cliente']
    inlines = (ItemVendaInline,)
    list_display = ('id', 'cliente', 'data_venda', 'forma_pagamento', 'total_venda',)
    list_filter = ('data_venda', 'forma_pagamento')
    search_fields = ('cliente__nome', 'id')

    def total_venda(self, obj):
        total = obj.itens.aggregate(
            t=Sum(
                ExpressionWrapper(
                    F("quantidade") * F("preco_unitario"),
                    output_field=DecimalField()
                )
            )
        )["t"]
        return total or 0

    total_venda.short_description = "Total (MZN)"


@admin.register(ItemVenda)
class ItemVendaAdmin(admin.ModelAdmin):
    list_display = ('venda', 'produto', 'quantidade', 'subtotal')
    list_filter = ('produto__categoria__tipo',)
