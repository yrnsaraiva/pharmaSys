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
    ARQUIVO = "lotes.xlsx"
    df = pd.read_excel(ARQUIVO)
    print(f"📊 Arquivo Excel lido com sucesso. {len(df)} linhas encontradas.")

    # Mostrar primeiras linhas para debug
    print(f"📝 Primeiras 3 linhas do arquivo:")
    print(df.head(3))

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

# Verificar se há dados no arquivo
if df.empty:
    print("❌ Arquivo Excel está vazio!")
    exit()

# Verificar colunas obrigatórias
colunas_necessarias = ['produto', 'data_validade']
colunas_faltantes = [col for col in colunas_necessarias if col not in df.columns]

if colunas_faltantes:
    print(f"❌ Faltam colunas obrigatórias: {colunas_faltantes}")
    print(f"💡 Colunas disponíveis: {list(df.columns)}")
    exit()

print("✅ Todas as colunas obrigatórias presentes!")

# Contador de progresso
total_linhas = len(df)
print(f"🔄 Processando {total_linhas} lotes...")

for index, row in df.iterrows():
    print(f"\n--- Processando linha {index + 1}/{total_linhas} ---")

    try:
        # Tratamento do nome do produto
        nome_produto = str(row['produto']).strip() if pd.notna(row['produto']) else ""

        if not nome_produto or nome_produto.lower() in ['nan', 'null', '']:
            print(f"   ❌ Nome do produto vazio ou inválido na linha {index + 1}")
            lotes_erro.append({
                'linha': index + 1,
                'produto': 'NOME VAZIO/INVÁLIDO',
                'erro': 'Nome do produto está vazio ou inválido'
            })
            continue

        # Buscar produto no sistema
        produto = Produto.objects.filter(nome__iexact=nome_produto).first()

        if not produto:
            print(f"   🔍 Produto '{nome_produto}' não encontrado, tentando busca parcial...")
            # Tentar busca parcial
            produto = Produto.objects.filter(nome__icontains=nome_produto).first()

        if not produto:
            print(f"   ❌ Produto '{nome_produto}' não encontrado no sistema")
            lotes_erro.append({
                'linha': index + 1,
                'produto': nome_produto,
                'erro': 'Produto não encontrado no sistema'
            })
            continue

        print(f"   ✅ Produto encontrado: {produto.nome} (ID: {produto.id})")
        print(f"   📦 Carteiras por caixa: {produto.carteiras_por_caixa}")

        # PROCESSAR NÚMERO DO LOTE
        if 'numero_lote' in df.columns and pd.notna(row['numero_lote']):
            numero_lote = str(row['numero_lote']).strip()
            # Verificar se lote já existe
            lote_existente = Lote.objects.filter(
                produto=produto,
                numero_lote=numero_lote
            ).first()

            if lote_existente:
                print(f"   ⚠️  Lote {numero_lote} já existe para este produto. Atualizando...")
                # Podemos atualizar ou pular - aqui vou pular para não duplicar
                lotes_erro.append({
                    'linha': index + 1,
                    'produto': nome_produto,
                    'erro': f'Lote {numero_lote} já existe para este produto'
                })
                continue
        else:
            # Gerar número de lote automático
            data_atual = datetime.now().strftime("%y%m%d")
            numero_lote = f"L{data_atual}-{index + 1:03d}"

        print(f"   🔢 Número do lote: {numero_lote}")

        # PROCESSAR DATAS
        data_fabricacao = None
        data_validade = None

        # Data de fabricação (opcional)
        if 'data_fabricacao' in df.columns and pd.notna(row['data_fabricacao']):
            try:
                data_fabricacao = pd.to_datetime(row['data_fabricacao']).date()
                print(f"   📅 Data fabricação: {data_fabricacao}")
            except Exception as e:
                print(f"   ⚠️  Data de fabricação inválida: {e}")

        # Data de validade (obrigatória)
        try:
            if pd.notna(row['data_validade']):
                data_validade = pd.to_datetime(row['data_validade']).date()
                print(f"   📅 Data validade: {data_validade}")

                # Verificar se data de validade não está expirada
                if data_validade < datetime.now().date():
                    print(f"   ⚠️  AVISO: Lote com data de validade expirada ({data_validade})")
            else:
                raise ValueError("Data de validade é obrigatória")

        except Exception as e:
            print(f"   ❌ Data de validade inválida: {e}")
            lotes_erro.append({
                'linha': index + 1,
                'produto': nome_produto,
                'erro': f'Data de validade inválida: {e}'
            })
            continue

        # PROCESSAR NÚMERO DE CAIXAS
        try:
            if 'nr_caixas' in df.columns and pd.notna(row['nr_caixas']):
                nr_caixas = int(float(row['nr_caixas']))
                if nr_caixas <= 0:
                    nr_caixas = 1
                    print(f"   ⚠️  Número de caixas inválido, usando 1")
            else:
                nr_caixas = 1
                print(f"   ⚠️  Número de caixas não informado, usando 1")
        except (ValueError, TypeError) as e:
            nr_caixas = 1
            print(f"   ⚠️  Número de caixas inválido, usando 1: {e}")

        # ✅ CALCULAR QUANTIDADE QUE SERÁ CRIADA AUTOMATICAMENTE
        carteiras_por_caixa = produto.carteiras_por_caixa or 1
        quantidade_calculada = nr_caixas * carteiras_por_caixa

        print(
            f"   📦 {nr_caixas} caixas × {carteiras_por_caixa} carteiras/caixa = {quantidade_calculada} unidades (calculado automaticamente)")

        # CRIAR O LOTE (SEM quantidade_disponivel - será calculado no save())
        lote = Lote.objects.create(
            produto=produto,
            numero_lote=numero_lote,
            nr_caixas=nr_caixas,
            data_fabricacao=data_fabricacao,
            data_validade=data_validade
            # ✅ quantidade_disponivel será calculado automaticamente no save() do modelo
        )

        # ✅ VERIFICAR QUANTIDADE REALMENTE CALCULADA
        quantidade_real = lote.quantidade_disponivel
        print(f"   ✅ LOTE CRIADO: {numero_lote} para {produto.nome}")
        print(f"   📊 Caixas: {nr_caixas} | Unidades calculadas: {quantidade_real}")
        print(f"   📅 Validade: {data_validade}")

        lotes_sucesso.append({
            'linha': index + 1,
            'produto': produto.nome,
            'lote': numero_lote,
            'caixas': nr_caixas,
            'unidades': quantidade_real,  # Usa a quantidade real calculada
            'validade': data_validade
        })

    except Exception as e:
        print(f"   ❌ Erro crítico na linha {index + 1}: {e}")
        import traceback

        print(f"   🔍 Detalhes: {traceback.format_exc()}")
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
        validade_str = success['validade'].strftime("%d/%m/%Y")
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
taxa_sucesso = (len(lotes_sucesso) / len(df)) * 100 if len(df) > 0 else 0
print(f"  • Taxa de sucesso: {taxa_sucesso:.1f}%")

# VERIFICAÇÃO FINAL DO ESTOQUE
print(f"\n🔍 VERIFICAÇÃO FINAL DO ESTOQUE:")
produtos_com_estoque = Produto.objects.filter(lote__quantidade_disponivel__gt=0).distinct()
total_unidades = sum(lote.quantidade_disponivel for lote in Lote.objects.all())

print(f"  • Produtos com estoque disponível: {produtos_com_estoque.count()}")
print(f"  • Total de unidades em estoque: {total_unidades}")
print(f"  • Total de lotes no sistema: {Lote.objects.count()}")

if produtos_com_estoque.count() > 0:
    print(f"\n📦 Produtos disponíveis para venda:")
    for produto in produtos_com_estoque[:10]:  # Mostrar apenas os 10 primeiros
        estoque_total = produto.estoque_total()
        status = produto.status_estoque()
        status_emoji = "✅" if status == "ok" else "⚠️" if status == "baixo" else "❌"
        print(f"  {status_emoji} {produto.nome}: {estoque_total} unidades ({status})")

    if produtos_com_estoque.count() > 10:
        print(f"  ... e mais {produtos_com_estoque.count() - 10} produtos")

# LOTES PRÓXIMOS DO VENCIMENTO (30 dias)
print(f"\n⚠️  LOTES PRÓXIMOS DO VENCIMENTO (próximos 30 dias):")
data_limite = datetime.now().date() + pd.Timedelta(days=30)
lotes_proximo_vencimento = Lote.objects.filter(
    data_validade__gte=datetime.now().date(),
    data_validade__lte=data_limite
).order_by('data_validade')

if lotes_proximo_vencimento.exists():
    for lote in lotes_proximo_vencimento:
        dias_para_vencer = (lote.data_validade - datetime.now().date()).days
        print(
            f"  ⏳ {lote.produto.nome} - Lote {lote.numero_lote}: vence em {dias_para_vencer} dias ({lote.data_validade})")
else:
    print(f"  ✅ Nenhum lote próximo do vencimento")

print("=" * 60)
print("🎯 Importação de lotes concluída!")