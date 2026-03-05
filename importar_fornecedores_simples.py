import os
import sys
import django
import pandas as pd

# Configuração do Django
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'pharmaSys.settings')
django.setup()

from fornecedores.models import Fornecedor

print("=" * 50)
print("🚀 IMPORTADOR SIMPLES DE FORNECEDORES")
print("(Apenas nomes)")
print("=" * 50)


def importar_nomes_fornecedores():
    """
    Importa apenas nomes de fornecedores de um arquivo Excel/CSV
    """

    # Configurações
    ARQUIVO = "fornecedores.xlsx"  # Pode ser .xlsx ou .csv

    # Listas para controle
    fornecedores_criados = []
    fornecedores_duplicados = []
    fornecedores_com_erro = []

    try:
        print(f"\n📁 Lendo arquivo: {ARQUIVO}")

        # Verificar extensão do arquivo
        if ARQUIVO.endswith('.xlsx') or ARQUIVO.endswith('.xls'):
            df = pd.read_excel(ARQUIVO)
        elif ARQUIVO.endswith('.csv'):
            df = pd.read_csv(ARQUIVO, encoding='utf-8')
        else:
            print(f"❌ Formato de arquivo não suportado: {ARQUIVO}")
            print("💡 Use .xlsx, .xls ou .csv")
            return

        print(f"✅ Arquivo lido! {len(df)} nomes encontrados.")

        # Mostrar primeiras linhas
        print(f"\n📝 Primeiros 5 nomes do arquivo:")
        for i, row in df.head(5).iterrows():
            print(f"   {i + 1}. {row.iloc[0] if len(row) > 0 else 'VAZIO'}")

        print("\n" + "=" * 50)
        print("🔄 PROCESSANDO NOMES...")
        print("=" * 50)

        # Identificar coluna com nomes
        coluna_nomes = None

        # Tentar encontrar automaticamente a coluna de nomes
        possiveis_colunas = ['nome', 'fornecedor', 'empresa', 'name', 'company', 'fornecedores']

        for col in df.columns:
            col_lower = str(col).lower().strip()
            for possivel in possiveis_colunas:
                if possivel in col_lower:
                    coluna_nomes = col
                    break
            if coluna_nomes:
                break

        # Se não encontrou, usar primeira coluna
        if not coluna_nomes and len(df.columns) > 0:
            coluna_nomes = df.columns[0]
            print(f"⚠️  Coluna de nomes não identificada, usando primeira coluna: '{coluna_nomes}'")
        elif not coluna_nomes:
            print("❌ Nenhuma coluna encontrada no arquivo!")
            return

        print(f"\n📊 Coluna usada para nomes: '{coluna_nomes}'")

        # Processar cada linha
        for index, row in df.iterrows():
            linha_num = index + 2  # +2 porque Excel começa em 1 e header é linha 1

            try:
                # Obter nome do fornecedor
                nome_bruto = row[coluna_nomes] if coluna_nomes in row else None

                # Verificar se o valor não é nulo/vazio
                if pd.isna(nome_bruto) or str(nome_bruto).strip() == "":
                    fornecedores_com_erro.append({
                        'linha': linha_num,
                        'nome': 'VAZIO',
                        'erro': 'Nome vazio ou nulo'
                    })
                    print(f"   ❌ Linha {linha_num}: NOME VAZIO")
                    continue

                # Limpar e formatar nome
                nome = str(nome_bruto).strip()
                nome_formatado = ' '.join(nome.split())  # Remove espaços extras
                nome_formatado = nome_formatado.title()  # Capitaliza palavras

                # Verificar se já existe (insensível a maiúsculas/minúsculas)
                fornecedor_existente = Fornecedor.objects.filter(
                    nome__iexact=nome_formatado
                ).first()

                if fornecedor_existente:
                    fornecedores_duplicados.append({
                        'linha': linha_num,
                        'nome': nome_formatado,
                        'fornecedor_existente': fornecedor_existente
                    })
                    print(f"   ⚠️  Linha {linha_num}: '{nome_formatado}' - JÁ EXISTE")
                else:
                    # Criar fornecedor com valores padrão
                    novo_fornecedor = Fornecedor(
                        nome=nome_formatado,
                        pessoa_de_contacto="A definir",
                        nuit=f"TEMPORARIO_{linha_num:04d}",  # NUIT temporário
                        telefone="841111111",  # Telefone padrão
                        endereco="A definir",
                        status=True  # Ativo por padrão
                    )

                    novo_fornecedor.save()

                    fornecedores_criados.append({
                        'linha': linha_num,
                        'nome': nome_formatado,
                        'fornecedor': novo_fornecedor
                    })

                    print(f"   ✅ Linha {linha_num}: '{nome_formatado}' - CRIADO")

            except Exception as e:
                fornecedores_com_erro.append({
                    'linha': linha_num,
                    'nome': str(nome_bruto)[:50] if nome_bruto else 'ERRO',
                    'erro': str(e)
                })
                print(f"   ❌ Linha {linha_num}: ERRO - {e}")

        # RELATÓRIO FINAL
        print("\n" + "=" * 50)
        print("📋 RELATÓRIO DA IMPORTAÇÃO")
        print("=" * 50)

        print(f"\n📊 ESTATÍSTICAS:")
        print(f"   • Total de nomes no arquivo: {len(df)}")
        print(f"   • Fornecedores criados: {len(fornecedores_criados)}")
        print(f"   • Fornecedores duplicados (já existiam): {len(fornecedores_duplicados)}")
        print(f"   • Linhas com erro: {len(fornecedores_com_erro)}")

        if fornecedores_criados:
            print(f"\n✅ FORNECEDORES CRIADOS ({len(fornecedores_criados)}):")
            for i, item in enumerate(fornecedores_criados[:10], 1):  # Mostrar apenas 10 primeiros
                print(f"   {i:2d}. {item['nome']}")

            if len(fornecedores_criados) > 10:
                print(f"   ... e mais {len(fornecedores_criados) - 10} fornecedores")

        if fornecedores_duplicados:
            print(f"\n⚠️  FORNECEDORES DUPLICADOS ({len(fornecedores_duplicados)}):")
            for i, item in enumerate(fornecedores_duplicados[:10], 1):
                print(f"   {i:2d}. {item['nome']}")

            if len(fornecedores_duplicados) > 10:
                print(f"   ... e mais {len(fornecedores_duplicados) - 10} duplicados")

        if fornecedores_com_erro:
            print(f"\n❌ LINHAS COM ERRO ({len(fornecedores_com_erro)}):")
            for item in fornecedores_com_erro:
                print(f"   • Linha {item['linha']}: {item['nome']} - {item['erro']}")

        # DICA: Como completar os dados depois
        print(f"\n💡 DICA IMPORTANTE:")
        print(f"   Você criou {len(fornecedores_criados)} fornecedores com dados temporários.")
        print(f"   Acesse o admin do Django para completar:")
        print(f"   • Pessoa de contacto")
        print(f"   • NUIT correto")
        print(f"   • Telefone")
        print(f"   • Email")
        print(f"   • Endereço")

        print("\n" + "=" * 50)
        print("🎯 IMPORTAÇÃO CONCLUÍDA!")
        print("=" * 50)

    except FileNotFoundError:
        print(f"\n❌ ERRO: Arquivo '{ARQUIVO}' não encontrado!")
        print("\n💡 Crie um arquivo chamado 'fornecedores.xlsx' ou 'fornecedores.csv'")
        print("   com uma coluna contendo os nomes dos fornecedores.")

        # Mostrar exemplo
        print(f"\n📝 EXEMPLO DE ARQUIVO (Excel ou CSV):")
        print("   Coluna A: 'nome'")
        print("   Linha 2: 'Farmacia Central'")
        print("   Linha 3: 'Distribuidora Med'")
        print("   Linha 4: 'Laboratorio Saúde'")

    except Exception as e:
        print(f"\n❌ ERRO INESPERADO: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    # Instruções simples
    print("\n📋 INSTRUÇÕES:")
    print("1. Crie um arquivo chamado 'fornecedores.xlsx' ou 'fornecedores.csv'")
    print("2. Coloque os nomes dos fornecedores em uma coluna")
    print("3. Salve na mesma pasta deste script")
    print("4. Execute o script")

    print("\n🔧 Os fornecedores serão criados com:")
    print("   • Nome: do arquivo")
    print("   • NUIT: temporário (TEMPORARIO_XXXX)")
    print("   • Telefone: 841111111")
    print("   • Status: Ativo")
    print("   • Outros campos: 'A definir'")

    print("\n⚠️  IMPORTANTE: Complete os dados depois pelo admin do Django!")

    resposta = input("\n⏰ Pressione Enter para continuar ou 'n' para cancelar: ")

    if resposta.lower() != 'n':
        importar_nomes_fornecedores()
    else:
        print("❌ Importação cancelada.")