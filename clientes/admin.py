from django.contrib import admin

from clientes.models import Cliente


@admin.register(Cliente)
class ClienteAdmin(admin.ModelAdmin):
    list_display = ('nome', 'telefone', 'email', 'total_compras')
    search_fields = ('nome', 'telefone')  # Busca flexível
    list_filter = ('data_cadastro',)  # Filtro por data de cadastro
    readonly_fields = ('data_cadastro',)  # Data não editável

    # Exibe o total de compras do cliente (relacionamento reverso com Venda)
    def total_compras(self, obj):
        return obj.venda_set.count()
    total_compras.short_description = "Compras"

