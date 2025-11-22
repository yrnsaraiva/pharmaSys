import os
import django
import pandas as pd
from decimal import Decimal

# Configuração do Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'pharmaSys.settings')
django.setup()

from productos.models import Produto, Categoria
from fornecedores.models import Fornecedor

print("🚀 Iniciando importação de produtos...")

# Listas para controlar sucessos e falhas
produtos_sucesso = []
produtos_erro = []

try:
    ARQUIVO = "Produto-2025-11-17-oooooo.xlsx"
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
colunas_necessarias = ['nome', 'categoria', 'fornecedor', 'preco_compra', 'preco_venda']
colunas_faltantes = [col for col in colunas_necessarias if col not in df.columns]

if colunas_faltantes:
    print(f"❌ Faltam colunas obrigatórias: {colunas_faltantes}")
    print(f"💡 Colunas disponíveis: {list(df.columns)}")
    exit()

print("✅ Todas as colunas obrigatórias presentes!")

# Contador de progresso
total_linhas = len(df)
print(f"🔄 Processando {total_linhas} produtos...")

for index, row in df.iterrows():
    print(f"\n--- Processando linha {index + 1}/{total_linhas} ---")

    try:
        # Tratamento do nome do produto
        nome_produto = str(row['nome']).strip() if pd.notna(row['nome']) else ""

        if not nome_produto or nome_produto.lower() in ['nan', 'null', '']:
            print(f"   ❌ Nome do produto vazio ou inválido na linha {index + 1}")
            produtos_erro.append({
                'linha': index + 1,
                'produto': 'NOME VAZIO/INVÁLIDO',
                'erro': 'Nome do produto está vazio ou inválido'
            })
            continue

        # Verificar se produto já existe
        produto_existente = Produto.objects.filter(nome__iexact=nome_produto).first()
        if produto_existente:
            print(f"   ⚠️  Produto '{nome_produto}' já existe. Pulando...")
            produtos_erro.append({
                'linha': index + 1,
                'produto': nome_produto,
                'erro': 'Produto já existe no sistema'
            })
            continue

        print(f"   📝 Processando: {nome_produto}")

        # PROCESSAR CATEGORIA
        nome_categoria = str(row['categoria']).strip() if pd.notna(row['categoria']) else "Geral"
        tipo_categoria = row.get('tipo', 'medicamento') if 'tipo' in df.columns else 'medicamento'

        categoria, created = Categoria.objects.get_or_create(
            nome=nome_categoria,
            defaults={
                'tipo': tipo_categoria,
                'descricao': f"Categoria para {nome_categoria}"
            }
        )

        if created:
            print(f"   ✅ Nova categoria criada: {categoria.nome} ({categoria.tipo})")
        else:
            print(f"   ✅ Categoria encontrada: {categoria.nome}")

        # PROCESSAR FORNECEDOR
        nome_fornecedor = str(row['fornecedor']).strip() if pd.notna(row['fornecedor']) else ""

        if not nome_fornecedor:
            print(f"   ❌ Nome do fornecedor vazio na linha {index + 1}")
            produtos_erro.append({
                'linha': index + 1,
                'produto': nome_produto,
                'erro': 'Nome do fornecedor está vazio'
            })
            continue

        fornecedor = Fornecedor.objects.filter(nome__icontains=nome_fornecedor).first()

        if not fornecedor:
            print(f"   ❌ Fornecedor '{nome_fornecedor}' não encontrado")
            produtos_erro.append({
                'linha': index + 1,
                'produto': nome_produto,
                'erro': f'Fornecedor "{nome_fornecedor}" não encontrado no sistema'
            })
            continue

        print(f"   ✅ Fornecedor encontrado: {fornecedor.nome}")

        # PROCESSAR PREÇOS
        try:
            preco_compra = Decimal(str(row['preco_compra'])).quantize(Decimal('0.01'))
            preco_venda = Decimal(str(row['preco_venda'])).quantize(Decimal('0.01'))

            if preco_compra <= 0 or preco_venda <= 0:
                raise ValueError("Preços devem ser maiores que zero")

            if preco_venda <= preco_compra:
                print(f"   ⚠️  AVISO: Preço de venda menor ou igual ao preço de compra")

        except (ValueError, TypeError) as e:
            print(f"   ❌ Erro nos preços: {e}")
            produtos_erro.append({
                'linha': index + 1,
                'produto': nome_produto,
                'erro': f'Erro nos preços: {e}'
            })
            continue

        # ✅ PROCESSAR PREÇO CARTEIRA
        preco_carteira = None
        calculado_automaticamente = False

        if 'preco_carteira' in df.columns and pd.notna(row['preco_carteira']):
            try:
                preco_carteira = Decimal(str(row['preco_carteira'])).quantize(Decimal('0.01'))
                print(f"   💳 Preço carteira definido: {preco_carteira}")
            except (ValueError, TypeError):
                preco_carteira = None
                print(f"   ⚠️  Preço carteira inválido, será calculado automaticamente")

        # Se preco_carteira não foi definido, vamos calcular depois
        if not preco_carteira:
            calculado_automaticamente = True
            print(f"   💳 Preço carteira será calculado automaticamente")

        # PROCESSAR CARTEIRAS POR CAIXA
        carteiras_por_caixa = row.get('carteiras_por_caixa', 1)
        try:
            carteiras_por_caixa = int(carteiras_por_caixa) if pd.notna(carteiras_por_caixa) else 1
            if carteiras_por_caixa <= 0:
                carteiras_por_caixa = 1
                print(f"   ⚠️  Carteiras por caixa inválido, usando 1")
        except:
            carteiras_por_caixa = 1
            print(f"   ⚠️  Carteiras por caixa inválido, usando 1")

        # ✅ CALCULAR PREÇO CARTEIRA SE NECESSÁRIO
        if calculado_automaticamente and carteiras_por_caixa > 0:
            try:
                preco_carteira = (preco_venda / Decimal(carteiras_por_caixa)).quantize(Decimal('0.01'))
                print(f"   💳 Preço carteira calculado: {preco_venda} / {carteiras_por_caixa} = {preco_carteira}")
            except:
                preco_carteira = None
                print(f"   ⚠️  Não foi possível calcular o preço carteira")

        print(
            f"   💰 Preço compra: {preco_compra} | Preço venda: {preco_venda} | Preço carteira: {preco_carteira or 'N/A'}")

        # PROCESSAR CÓDIGO DE BARRAS
        codigo_barras = ""
        if 'codigo_barras' in df.columns and pd.notna(row['codigo_barras']):
            codigo_barras = str(row['codigo_barras']).strip()
            # Verificar se código de barras já existe
            if codigo_barras and Produto.objects.filter(codigo_barras=codigo_barras).exists():
                print(f"   ⚠️  Código de barras '{codigo_barras}' já existe. Gerando novo...")
                codigo_barras = f"CB_{index + 1:06d}"

        # PROCESSAR OUTROS CAMPOS
        estoque_minimo = row.get('estoque_minimo', 10)
        try:
            estoque_minimo = int(estoque_minimo) if pd.notna(estoque_minimo) else 10
        except:
            estoque_minimo = 10

        # PROCESSAR CAMPOS ESPECÍFICOS DE MEDICAMENTOS
        forma_farmaceutica = row.get('forma_farmaceutica') if 'forma_farmaceutica' in df.columns else None
        dosagem = row.get('dosagem') if 'dosagem' in df.columns else None
        nivel_prescricao = row.get('nivel_prescricao', 'niv0') if 'nivel_prescricao' in df.columns else 'niv0'
        principio_ativo = row.get('principio_ativo') if 'principio_ativo' in df.columns else None

        controlado = False
        if 'controlado' in df.columns and pd.notna(row['controlado']):
            controlado_val = str(row['controlado']).lower().strip()
            controlado = controlado_val in ['sim', 'true', '1', 'yes', 's']

        # CRIAR O PRODUTO
        produto = Produto(
            nome=nome_produto,
            categoria=categoria,
            fornecedor=fornecedor,
            codigo_barras=codigo_barras,
            preco_compra=preco_compra,
            preco_venda=preco_venda,
            preco_carteira=preco_carteira,  # ✅ AGORA INCLUÍDO
            carteiras_por_caixa=carteiras_por_caixa,
            estoque_minimo=estoque_minimo,
            forma_farmaceutica=forma_farmaceutica,
            dosagem=dosagem,
            nivel_prescricao=nivel_prescricao,
            principio_ativo=principio_ativo,
            controlado=controlado
        )

        produto.save()

        print(f"   ✅ PRODUTO CRIADO: {produto.nome}")
        print(f"   📊 Categoria: {categoria.nome} | Fornecedor: {fornecedor.nome}")
        print(f"   💰 Preços: Cmp {preco_compra} | Vnd {preco_venda} | Cart {preco_carteira or 'N/A'}")
        print(f"   📦 Carteiras por caixa: {carteiras_por_caixa} | Estoque mínimo: {estoque_minimo}")

        produtos_sucesso.append({
            'linha': index + 1,
            'produto': produto.nome,
            'categoria': categoria.nome,
            'fornecedor': fornecedor.nome,
            'preco_compra': preco_compra,
            'preco_venda': preco_venda,
            'preco_carteira': preco_carteira,
            'carteiras_por_caixa': carteiras_por_caixa
        })

    except Exception as e:
        print(f"   ❌ Erro crítico na linha {index + 1}: {e}")
        import traceback

        print(f"   🔍 Detalhes: {traceback.format_exc()}")
        produtos_erro.append({
            'linha': index + 1,
            'produto': nome_produto if 'nome_produto' in locals() else 'DESCONHECIDO',
            'erro': str(e)
        })

# RELATÓRIO FINAL
print("\n" + "=" * 60)
print("📋 RELATÓRIO DA IMPORTAÇÃO DE PRODUTOS")
print("=" * 60)

print(f"\n✅ SUCESSOS: {len(produtos_sucesso)} produtos criados")
if produtos_sucesso:
    print("\nProdutos importados com sucesso:")
    for success in produtos_sucesso:
        preco_carteira_str = success['preco_carteira'] if success['preco_carteira'] else "Calculado automaticamente"
        print(f"  📍 Linha {success['linha']}: {success['produto']}")
        print(f"        Categoria: {success['categoria']} | Fornecedor: {success['fornecedor']}")
        print(f"        Preço compra: {success['preco_compra']} | Preço venda: {success['preco_venda']}")
        print(f"        Preço carteira: {preco_carteira_str} | Carteiras/caixa: {success['carteiras_por_caixa']}")

print(f"\n❌ ERROS: {len(produtos_erro)} produtos com problemas")
if produtos_erro:
    print("\nProdutos com erro:")
    for erro in produtos_erro:
        print(f"  📍 Linha {erro['linha']}: {erro['produto']}")
        print(f"        Erro: {erro['erro']}")

print(f"\n📊 ESTATÍSTICAS:")
print(f"  • Total de linhas no Excel: {len(df)}")
print(f"  • Produtos criados com sucesso: {len(produtos_sucesso)}")
print(f"  • Produtos com erro: {len(produtos_erro)}")
taxa_sucesso = (len(produtos_sucesso) / len(df)) * 100 if len(df) > 0 else 0
print(f"  • Taxa de sucesso: {taxa_sucesso:.1f}%")

# VERIFICAÇÃO FINAL
print(f"\n🔍 VERIFICAÇÃO FINAL:")
total_produtos = Produto.objects.count()
categorias_count = Categoria.objects.count()
produtos_com_preco_carteira = Produto.objects.filter(preco_carteira__isnull=False).count()
print(f"  • Total de produtos no sistema: {total_produtos}")
print(f"  • Total de categorias: {categorias_count}")
print(f"  • Produtos com preço carteira definido: {produtos_com_preco_carteira}")

print("=" * 60)
print("🎯 Importação de produtos concluída!")