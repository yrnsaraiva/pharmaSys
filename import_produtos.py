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
produtos_erro_detalhado = []  # Lista aprimorada para armazenar erros detalhados

try:
    ARQUIVO = "produtos.xlsx"
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

    # Dicionário para armazenar campos problemáticos desta linha
    campos_com_defeito = {}
    produto_nome = None

    try:
        # Tratamento do nome do produto
        nome_produto = str(row['nome']).strip() if pd.notna(row['nome']) else ""
        produto_nome = nome_produto

        if not nome_produto or nome_produto.lower() in ['nan', 'null', '']:
            campos_com_defeito['nome'] = 'Campo vazio ou inválido'
            produtos_erro_detalhado.append({
                'linha': index + 1,
                'produto': 'NOME VAZIO/INVÁLIDO',
                'campos_com_defeito': campos_com_defeito.copy(),
                'erro_geral': 'Nome do produto está vazio ou inválido'
            })
            continue

        # Verificar se produto já existe
        produto_existente = Produto.objects.filter(nome__iexact=nome_produto).first()
        if produto_existente:
            campos_com_defeito['nome'] = f'Produto já existe (ID: {produto_existente.id})'
            produtos_erro_detalhado.append({
                'linha': index + 1,
                'produto': nome_produto,
                'campos_com_defeito': campos_com_defeito.copy(),
                'erro_geral': 'Produto já existe no sistema'
            })
            continue

        print(f"   📝 Processando: {nome_produto}")

        # PROCESSAR CATEGORIA
        nome_categoria = str(row['categoria']).strip() if pd.notna(row['categoria']) else "Geral"
        tipo_categoria = row.get('tipo', 'medicamento') if 'tipo' in df.columns else 'medicamento'

        if not nome_categoria or nome_categoria.lower() in ['nan', 'null', '']:
            campos_com_defeito['categoria'] = 'Categoria inválida ou vazia'
            nome_categoria = "Geral"

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

        if not nome_fornecedor or nome_fornecedor.lower() in ['nan', 'null', '']:
            campos_com_defeito['fornecedor'] = 'Nome do fornecedor vazio'
            produtos_erro_detalhado.append({
                'linha': index + 1,
                'produto': nome_produto,
                'campos_com_defeito': campos_com_defeito.copy(),
                'erro_geral': 'Nome do fornecedor está vazio'
            })
            continue

        fornecedor = Fornecedor.objects.filter(nome__icontains=nome_fornecedor).first()

        if not fornecedor:
            campos_com_defeito['fornecedor'] = f'Fornecedor "{nome_fornecedor}" não encontrado no sistema'
            produtos_erro_detalhado.append({
                'linha': index + 1,
                'produto': nome_produto,
                'campos_com_defeito': campos_com_defeito.copy(),
                'erro_geral': f'Fornecedor "{nome_fornecedor}" não encontrado no sistema'
            })
            continue

        print(f"   ✅ Fornecedor encontrado: {fornecedor.nome}")

        # PROCESSAR PREÇOS
        preco_compra_erro = False
        preco_venda_erro = False

        try:
            preco_compra = Decimal(str(row['preco_compra'])).quantize(Decimal('0.01'))
            if preco_compra <= 0:
                campos_com_defeito['preco_compra'] = f'Valor inválido: {preco_compra}. Deve ser maior que zero'
                preco_compra_erro = True
        except (ValueError, TypeError, Exception) as e:
            campos_com_defeito['preco_compra'] = f'Erro na conversão: {e}. Valor original: {row["preco_compra"]}'
            preco_compra_erro = True

        try:
            preco_venda = Decimal(str(row['preco_venda'])).quantize(Decimal('0.01'))
            if preco_venda <= 0:
                campos_com_defeito['preco_venda'] = f'Valor inválido: {preco_venda}. Deve ser maior que zero'
                preco_venda_erro = True
        except (ValueError, TypeError, Exception) as e:
            campos_com_defeito['preco_venda'] = f'Erro na conversão: {e}. Valor original: {row["preco_venda"]}'
            preco_venda_erro = True

        # Verificar se há erros nos preços
        if preco_compra_erro or preco_venda_erro:
            produtos_erro_detalhado.append({
                'linha': index + 1,
                'produto': nome_produto,
                'campos_com_defeito': campos_com_defeito.copy(),
                'erro_geral': 'Erro nos campos de preço'
            })
            continue

        # Verificar relação entre preços
        if preco_venda <= preco_compra:
            campos_com_defeito[
                'relacao_precos'] = f'Preço de venda ({preco_venda}) menor ou igual ao preço de compra ({preco_compra})'
            print(f"   ⚠️  AVISO: Preço de venda menor ou igual ao preço de compra")

        # ✅ PROCESSAR PREÇO CARTEIRA
        preco_carteira = None
        calculado_automaticamente = False

        if 'preco_carteira' in df.columns and pd.notna(row['preco_carteira']):
            try:
                preco_carteira = Decimal(str(row['preco_carteira'])).quantize(Decimal('0.01'))
                if preco_carteira <= 0:
                    campos_com_defeito['preco_carteira'] = f'Valor inválido: {preco_carteira}. Deve ser maior que zero'
                    preco_carteira = None
                else:
                    print(f"   💳 Preço carteira definido: {preco_carteira}")
            except (ValueError, TypeError, Exception) as e:
                campos_com_defeito[
                    'preco_carteira'] = f'Erro na conversão: {e}. Valor original: {row["preco_carteira"]}'
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
                campos_com_defeito['carteiras_por_caixa'] = f'Valor inválido: {carteiras_por_caixa}. Usando 1'
                carteiras_por_caixa = 1
                print(f"   ⚠️  Carteiras por caixa inválido, usando 1")
        except Exception as e:
            campos_com_defeito[
                'carteiras_por_caixa'] = f'Erro na conversão: {e}. Valor original: {carteiras_por_caixa}. Usando 1'
            carteiras_por_caixa = 1
            print(f"   ⚠️  Carteiras por caixa inválido, usando 1")

        # ✅ CALCULAR PREÇO CARTEIRA SE NECESSÁRIO
        if calculado_automaticamente and carteiras_por_caixa > 0:
            try:
                preco_carteira = (preco_venda / Decimal(carteiras_por_caixa)).quantize(Decimal('0.01'))
                if preco_carteira <= 0:
                    campos_com_defeito[
                        'preco_carteira_calculado'] = f'Cálculo resultou em valor inválido: {preco_carteira}'
                    preco_carteira = None
                else:
                    print(f"   💳 Preço carteira calculado: {preco_venda} / {carteiras_por_caixa} = {preco_carteira}")
            except Exception as e:
                campos_com_defeito['preco_carteira_calculado'] = f'Erro no cálculo: {e}'
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
                campos_com_defeito['codigo_barras'] = f'Código de barras duplicado: {codigo_barras}. Gerando novo...'
                print(f"   ⚠️  Código de barras '{codigo_barras}' já existe. Gerando novo...")
                codigo_barras = f"CB_{index + 1:06d}"

        # PROCESSAR ESTOQUE MÍNIMO
        estoque_minimo = row.get('estoque_minimo', 10)
        try:
            estoque_minimo = int(estoque_minimo) if pd.notna(estoque_minimo) else 10
            if estoque_minimo < 0:
                campos_com_defeito['estoque_minimo'] = f'Valor inválido: {estoque_minimo}. Usando 10'
                estoque_minimo = 10
        except Exception as e:
            campos_com_defeito[
                'estoque_minimo'] = f'Erro na conversão: {e}. Valor original: {estoque_minimo}. Usando 10'
            estoque_minimo = 10

        # PROCESSAR CAMPOS ESPECÍFICOS DE MEDICAMENTOS
        if 'forma_farmaceutica' in df.columns:
            forma_farmaceutica = row.get('forma_farmaceutica') if pd.notna(row['forma_farmaceutica']) else None
        else:
            forma_farmaceutica = None

        if 'dosagem' in df.columns:
            dosagem = row.get('dosagem') if pd.notna(row['dosagem']) else None
        else:
            dosagem = None

        nivel_prescricao = row.get('nivel_prescricao', 'niv0') if 'nivel_prescricao' in df.columns else 'niv0'

        if 'principio_ativo' in df.columns:
            principio_ativo = row.get('principio_ativo') if pd.notna(row['principio_ativo']) else None
        else:
            principio_ativo = None

        controlado = False
        if 'controlado' in df.columns and pd.notna(row['controlado']):
            controlado_val = str(row['controlado']).lower().strip()
            controlado = controlado_val in ['sim', 'true', '1', 'yes', 's']

        # Se houver campos com defeito mas não críticos, registrar avisos
        if campos_com_defeito:
            print(f"   ⚠️  AVISOS: {len(campos_com_defeito)} campo(s) com problemas não críticos:")
            for campo, problema in campos_com_defeito.items():
                print(f"       • {campo}: {problema}")

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

        # Adicionar o erro à lista detalhada
        produtos_erro_detalhado.append({
            'linha': index + 1,
            'produto': produto_nome if produto_nome else 'DESCONHECIDO',
            'campos_com_defeito': campos_com_defeito.copy(),
            'erro_geral': f'Erro crítico: {str(e)}',
            'traceback': traceback.format_exc()
        })

# RELATÓRIO FINAL
print("\n" + "=" * 80)
print("📋 RELATÓRIO DETALHADO DA IMPORTAÇÃO DE PRODUTOS")
print("=" * 80)

print(f"\n✅ SUCESSOS: {len(produtos_sucesso)} produtos criados")
if produtos_sucesso:
    print("\nProdutos importados com sucesso:")
    for success in produtos_sucesso:
        preco_carteira_str = success['preco_carteira'] if success['preco_carteira'] else "Calculado automaticamente"
        print(f"  📍 Linha {success['linha']}: {success['produto']}")
        print(f"        Categoria: {success['categoria']} | Fornecedor: {success['fornecedor']}")
        print(f"        Preço compra: {success['preco_compra']} | Preço venda: {success['preco_venda']}")
        print(f"        Preço carteira: {preco_carteira_str} | Carteiras/caixa: {success['carteiras_por_caixa']}")

print(f"\n❌ ERROS: {len(produtos_erro_detalhado)} produtos com problemas")
if produtos_erro_detalhado:
    print("\n📊 DETALHAMENTO DOS ERROS POR CAMPO:")

    # Contagem de erros por tipo de campo
    erros_por_campo = {}
    for erro in produtos_erro_detalhado:
        for campo, problema in erro['campos_com_defeito'].items():
            if campo not in erros_por_campo:
                erros_por_campo[campo] = []
            erros_por_campo[campo].append({
                'linha': erro['linha'],
                'produto': erro['produto'],
                'problema': problema
            })

    # Mostrar erros agrupados por campo
    if erros_por_campo:
        print("\n  🔍 ERROS POR TIPO DE CAMPO:")
        for campo, erros in erros_por_campo.items():
            print(f"\n    📌 CAMPO: {campo.upper()} ({len(erros)} ocorrência(s)):")
            for erro in erros:
                print(f"        • Linha {erro['linha']} - '{erro['produto']}': {erro['problema']}")

    # Mostrar todos os produtos com erro
    print("\n  📋 TODOS OS PRODUTOS COM ERRO:")
    for erro in produtos_erro_detalhado:
        print(f"\n    📍 Linha {erro['linha']}: {erro['produto']}")
        print(f"        Erro geral: {erro['erro_geral']}")

        if erro['campos_com_defeito']:
            print(f"        Campos com defeito:")
            for campo, problema in erro['campos_com_defeito'].items():
                print(f"          • {campo}: {problema}")

        # Mostrar valores originais da linha para debug
        try:
            linha_excel = df.iloc[erro['linha'] - 1]
            print(f"        Valores originais na planilha:")
            for col in df.columns:
                valor = linha_excel[col]
                if pd.notna(valor):
                    print(f"          • {col}: {valor}")
        except:
            pass

print(f"\n📊 ESTATÍSTICAS:")
print(f"  • Total de linhas no Excel: {len(df)}")
print(f"  • Produtos criados com sucesso: {len(produtos_sucesso)}")
print(f"  • Produtos com erro: {len(produtos_erro_detalhado)}")
taxa_sucesso = (len(produtos_sucesso) / len(df)) * 100 if len(df) > 0 else 0
print(f"  • Taxa de sucesso: {taxa_sucesso:.1f}%")

# Estatísticas de erros
if produtos_erro_detalhado:
    total_campos_com_erro = sum(len(erro['campos_com_defeito']) for erro in produtos_erro_detalhado)
    print(f"  • Total de campos com defeito identificados: {total_campos_com_erro}")

    # Campos mais problemáticos
    campos_problematicos = {}
    for erro in produtos_erro_detalhado:
        for campo in erro['campos_com_defeito']:
            campos_problematicos[campo] = campos_problematicos.get(campo, 0) + 1

    if campos_problematicos:
        print(f"\n  🎯 CAMPOS MAIS PROBLEMÁTICOS:")
        for campo, count in sorted(campos_problematicos.items(), key=lambda x: x[1], reverse=True):
            print(f"    • {campo}: {count} ocorrência(s)")

# VERIFICAÇÃO FINAL
print(f"\n🔍 VERIFICAÇÃO FINAL:")
total_produtos = Produto.objects.count()
categorias_count = Categoria.objects.count()
produtos_com_preco_carteira = Produto.objects.filter(preco_carteira__isnull=False).count()
print(f"  • Total de produtos no sistema: {total_produtos}")
print(f"  • Total de categorias: {categorias_count}")
print(f"  • Produtos com preço carteira definido: {produtos_com_preco_carteira}")

# Exportar relatório de erros para um arquivo (opcional)
if produtos_erro_detalhado:
    try:
        relatorio_erros = []
        for erro in produtos_erro_detalhado:
            relatorio_erros.append({
                'Linha': erro['linha'],
                'Produto': erro['produto'],
                'Erro Geral': erro['erro_geral'],
                'Campos com Defeito': ', '.join([f"{k}: {v}" for k, v in erro['campos_com_defeito'].items()]) if erro[
                    'campos_com_defeito'] else 'Nenhum'
            })

        df_erros = pd.DataFrame(relatorio_erros)
        df_erros.to_excel('relatorio_erros_importacao.xlsx', index=False)
        print(f"\n💾 Relatório de erros salvo em: 'relatorio_erros_importacao.xlsx'")
    except Exception as e:
        print(f"\n⚠️  Não foi possível salvar relatório de erros: {e}")

print("=" * 80)
print("🎯 Importação de produtos concluída!")