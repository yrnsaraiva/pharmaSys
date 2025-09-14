# services.py
from .models import Produto, Lote


def cadastrar_lote_em_caixas(produto, numero_lote, nr_caixas, data_validade, data_fabricacao=None):
    if not produto.carteiras_por_caixa or produto.carteiras_por_caixa <= 0:
        raise ValueError("O produto precisa ter 'carteiras_por_caixa' definido.")

    quantidade_carteiras = nr_caixas * produto.carteiras_por_caixa

    lote = Lote.objects.create(
        produto=produto,
        numero_lote=numero_lote,
        quantidade_disponivel=quantidade_carteiras,
        data_validade=data_validade,
        data_fabricacao=data_fabricacao
    )
    return lote
