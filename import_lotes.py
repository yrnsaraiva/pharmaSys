# import_lotes_simples.py
import os
import django
import pandas as pd
from datetime import date

# Configuração do Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'pharmaSys.settings')
django.setup()

from productos.models import Produto, Lote


def importar_lotes_simples(arquivo="lotes.xlsx"):
    print("🚀 Iniciando importação...")

    hoje = date.today()

    try:
        df = pd.read_excel(arquivo)
        print(f"✅ {len(df)} linhas lidas")

        sucesso = 0
        erros = []

        for index, row in df.iterrows():
            try:
                # Produto
                nome_produto = str(row['produto']).strip()
                produto = Produto.objects.filter(nome__iexact=nome_produto).first()

                if not produto:
                    erros.append(f"Linha {index + 1}: Produto não encontrado")
                    continue

                # Data de validade
                data_validade = pd.to_datetime(row['data_validade']).date()

                # Quantidades
                nr_caixas = int(row.get('nr_caixas', 0))
                nr_carteiras = int(row.get('nr_carteiras', 0))

                # Criar lote
                lote = Lote.objects.create(
                    produto=produto,
                    nr_caixas=nr_caixas,
                    nr_carteiras=nr_carteiras,
                    data_validade=data_validade
                )

                print(
                    f"✅ Lote {lote.numero_lote} criado | "
                    f"{produto.nome} | validade: {data_validade}"
                )

                sucesso += 1

            except Exception as e:
                erros.append(f"Linha {index + 1}: {str(e)}")
                print(f"❌ Erro linha {index + 1}: {e}")

        # Relatório final
        print("\n📋 RESULTADO:")
        print(f"✅ Sucessos: {sucesso}")
        print(f"❌ Erros: {len(erros)}")

        if erros:
            print("\n📝 Erros detalhados:")
            for erro in erros[:5]:
                print(f"  - {erro}")

        # 🔴 LISTAR TODOS OS PRODUTOS EXPIRADOS (BASE DE DADOS)
        print("\n⛔ PRODUTOS COM VALIDADE EXPIRADA:")

        lotes_expirados = (
            Lote.objects
            .filter(data_validade__lt=hoje)
            .select_related('produto')
            .order_by('data_validade')
        )

        if not lotes_expirados.exists():
            print("✅ Nenhum produto expirado encontrado.")
        else:
            for lote in lotes_expirados:
                print(
                    f"🔴 {lote.produto.nome} | "
                    f"Lote: {lote.numero_lote} | "
                    f"Validade: {lote.data_validade}"
                )

    except Exception as e:
        print(f"❌ Erro geral: {e}")


if __name__ == "__main__":
    importar_lotes_simples()
