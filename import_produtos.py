import os
import django
import pandas as pd
from datetime import datetime

# Configuração do Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'pharmaSys.settings')
django.setup()

from productos.models import Produto, Lote

print("🚀 Iniciando importação de lotes...")

# Listas para controlar sucessos e falhas
lotes_sucesso = []
lotes_erro = []

try:
    ARQUIVO = "lotes.csv.xlsx"
    df = pd.read_excel(ARQUIVO)
    print(f"📊 Arquivo Excel lido com sucesso. {len(df)} linhas encontradas.")
except FileNotFoundError:
    print(f"❌ Arquivo '{ARQUIVO}' não encontrado!")
    print("💡 Verifique se o arquivo está na mesma pasta do script")
    exit()
except Exception as e:
    print(f"❌ Erro ao ler arquivo: {e}")
    exit()

# Normalizar colunas
df.columns = df.columns.str.strip().str.lower()
print(f"📝 Colunas encontradas: {list(df.columns)}")

# Verificar colunas obrigatórias
colunas_necessarias = ['produto', 'data_validade', 'nr_caixas']
colunas_faltantes = [col for col in colunas_necessarias if col not in df.columns]

if colunas_faltantes:
    print(f"❌ Faltam colunas obrigatórias: {colunas_faltantes}")
    exit()

print("✅ Todas as colunas obrigatórias presentes!")

for index, row in df.iterrows():
    print(f"--- Processando linha {index + 1} ---")

    try:
        nome_produto = str(row['produto']).strip()

        if not nome_produto:
            print(f"   ❌ Nome do produto vazio na linha {index + 1}")
            lotes_erro.append({
                'linha': index + 1,
                'produto': 'NOME VAZIO',
                'erro': 'Nome do produto está vazio'
            })
            continue

        produto = Produto.objects.filter(nome__iexact=nome_produto).first()

        if not produto:
            print(f"   ❌ Produto '{nome_produto}' não encontrado")
            lotes_erro.append({
                'linha': index + 1,
                'produto': nome_produto,
                'erro': 'Produto não encontrado no sistema'
            })
            continue

        # ✅ CORREÇÃO: Garantir que o produto tenha carteiras_por_caixa definido
        if not produto.carteiras_por_caixa or produto.carteiras_por_caixa <= 0:
            print(f"   ⚠️  Produto '{produto.nome}' sem carteiras_por_caixa, definindo como 1")
            produto.carteiras_por_caixa = 1
            produto.save()

        # Processar datas
        data_fabricacao = None
        data_validade = None

        try:
            if 'data_fabricacao' in df.columns and pd.notna(row['data_fabricacao']):
                data_fabricacao = pd.to_datetime(row['data_fabricacao']).date()
                print(f"   📅 Data fabricação: {data_fabricacao}")
        except Exception as e:
            print(f"   ⚠️  Data de fabricação inválida: {e}")

        try:
            if pd.notna(row['data_validade']):
                data_validade = pd.to_datetime(row['data_validade']).date()
                print(f"   📅 Data validade: {data_validade}")

                # Verificar se data de validade não está expirada
                if data_validade < datetime.now().date():
                    print(f"   ⚠️  AVISO: Lote com data de validade expirada")
        except Exception as e:
            print(f"   ❌ Data de validade inválida: {e}")
            lotes_erro.append({
                'linha': index + 1,
                'produto': nome_produto,
                'erro': f'Data de validade inválida: {e}'
            })
            continue

        # Processar número de caixas
        try:
            nr_caixas = int(row['nr_caixas']) if pd.notna(row['nr_caixas']) else 1
            if nr_caixas <= 0:
                nr_caixas = 1
                print(f"   ⚠️  Número de caixas inválido, usando 1")
        except (ValueError, TypeError) as e:
            nr_caixas = 1
            print(f"   ⚠️  Número de caixas inválido, usando 1: {e}")

        numero_lote = f"L{index + 1:04d}"
        print(f"   🔢 Número do lote: {numero_lote}")

        # ✅ CORREÇÃO: Calcular quantidade_disponivel ANTES de criar o lote
        carteiras_por_caixa = produto.carteiras_por_caixa or 1
        quantidade_disponivel = nr_caixas * carteiras_por_caixa

        print(f"   📦 {nr_caixas} caixas × {carteiras_por_caixa} carteiras/caixa = {quantidade_disponivel} unidades")

        # Criar o lote
        lote = Lote.objects.create(
            produto=produto,
            numero_lote=numero_lote,
            nr_caixas=nr_caixas,
            data_fabricacao=data_fabricacao,
            data_validade=data_validade,
            quantidade_disponivel=quantidade_disponivel  # ✅ DEFINIR EXPLICITAMENTE
        )

        lotes_sucesso.append({
            'linha': index + 1,
            'produto': produto.nome,
            'lote': numero_lote,
            'caixas': nr_caixas,
            'unidades': quantidade_disponivel,
            'validade': data_validade
        })

        print(f"   ✅ Lote {numero_lote} criado para {produto.nome}")
        print(f"   📊 Estoque atualizado: {quantidade_disponivel} unidades disponíveis")

    except Exception as e:
        print(f"   ❌ Erro na linha {index + 1}: {e}")
        lotes_erro.append({
            'linha': index + 1,
            'produto': nome_produto if 'nome_produto' in locals() else 'DESCONHECIDO',
            'erro': str(e)
        })

# RELATÓRIO FINAL
print("\n" + "=" * 60)
print("📋 RELATÓRIO DA IMPORTAÇÃO DE LOTES")
print("=" * 60)

print(f"\n✅ SUCESSOS: {len(lotes_sucesso)} lotes criados")
if lotes_sucesso:
    print("\nLotes importados com sucesso:")
    for success in lotes_sucesso:
        validade_str = success['validade'].strftime("%d/%m/%Y") if success['validade'] else "Não definida"
        print(f"  📍 Linha {success['linha']}: {success['produto']}")
        print(
            f"        Lote: {success['lote']} | Caixas: {success['caixas']} | Unidades: {success['unidades']} | Validade: {validade_str}")

print(f"\n❌ ERROS: {len(lotes_erro)} lotes com problemas")
if lotes_erro:
    print("\nLotes com erro:")
    for erro in lotes_erro:
        print(f"  📍 Linha {erro['linha']}: {erro['produto']}")
        print(f"        Erro: {erro['erro']}")

print(f"\n📊 ESTATÍSTICAS:")
print(f"  • Total de linhas no Excel: {len(df)}")
print(f"  • Lotes criados com sucesso: {len(lotes_sucesso)}")
print(f"  • Lotes com erro: {len(lotes_erro)}")
print(f"  • Taxa de sucesso: {(len(lotes_sucesso) / len(df)) * 100:.1f}%")

# VERIFICAÇÃO FINAL DO ESTOQUE
print(f"\n🔍 VERIFICAÇÃO FINAL DO ESTOQUE:")
produtos_com_estoque = Produto.objects.filter(lote__quantidade_disponivel__gt=0).distinct()
print(f"  • Produtos com estoque disponível: {produtos_com_estoque.count()}")

if produtos_com_estoque.count() > 0:
    print(f"\n📦 Produtos disponíveis para venda:")
    for produto in produtos_com_estoque:
        estoque_total = produto.estoque_total()
        print(f"  ✅ {produto.nome}: {estoque_total} unidades")

print("=" * 60)
print("🎯 Importação de lotes concluída!")