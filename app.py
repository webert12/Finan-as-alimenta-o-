import streamlit as st
import sqlite3
import pandas as pd

# =====================================================================
# 1. CONFIGURAÇÃO DO BANCO DE DADOS (SQLite)
# =====================================================================
def conectar_bd():
    conn = sqlite3.connect("sistema_alimentos.db")
    return conn

def criar_tabelas():
    conn = conectar_bd()
    cursor = conn.cursor()
    
    # Tabela de Estoque de Ingredientes (com preço de custo atualizável)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS estoque (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            ingrediente TEXT UNIQUE,
            quantidade REAL,
            preco_custo REAL DEFAULT 0.0
        )
    """)
    
    # Tabela de Vendas
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS vendas (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            produto TEXT,
            valor REAL,
            data_venda TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    conn.commit()
    conn.close()

criar_tabelas()

# =====================================================================
# 2. DICIONÁRIO DE INGREDIENTES EM MASSA (Valores de mercado por unidade/medida)
# =====================================================================
# Lista baseada em custos médios reais por porção utilizada no lanche
INGREDIENTES_PADRAO = {
    "pao de hamburguer (unid)": {"qtd": 50.0, "custo": 0.80},
    "bife de hamburguer 120g (unid)": {"qtd": 40.0, "custo": 2.20},
    "mussarela (fatia)": {"qtd": 100.0, "custo": 0.70},
    "presunto (fatia)": {"qtd": 100.0, "custo": 0.50},
    "bacon (fatia/porção)": {"qtd": 60.0, "custo": 1.20},
    "calabresa (porção)": {"qtd": 40.0, "custo": 1.10},
    "ovo (unid)": {"qtd": 30.0, "custo": 0.55},
    "alface (porção)": {"qtd": 50.0, "custo": 0.15},
    "tomate (fatia)": {"qtd": 80.0, "custo": 0.20},
    "cebola caramelizada (porção)": {"qtd": 40.0, "custo": 0.30},
    "maionese artesanal (porção)": {"qtd": 50.0, "custo": 0.40},
    "catupiry (porção)": {"qtd": 30.0, "custo": 0.90},
    "cheddar fatiado (fatia)": {"qtd": 40.0, "custo": 1.00},
    "batata palha (porção)": {"qtd": 40.0, "custo": 0.35},
    "salsicha (unid)": {"qtd": 30.0, "custo": 0.60},
}

# =====================================================================
# 3. DICIONÁRIO DE RECEITAS (Fórmula do Lanche)
# =====================================================================
# Mapeados de acordo com os novos nomes padronizados
RECEITAS = {
    "X-Salada": {
        "pao de hamburguer (unid)": 1,
        "bife de hamburguer 120g (unid)": 1,
        "mussarela (fatia)": 1,
        "presunto (fatia)": 1,
        "alface (porção)": 1,
        "tomate (fatia)": 1
    },
    "X-Burguer": {
        "pao de hamburguer (unid)": 1,
        "bife de hamburguer 120g (unid)": 1,
        "mussarela (fatia)": 1
    },
    "X-Bacon": {
        "pao de hamburguer (unid)": 1,
        "bife de hamburguer 120g (unid)": 1,
        "mussarela (fatia)": 1,
        "bacon (fatia/porção)": 2
    }
}

# Preço de venda dos produtos
PRECOS = {
    "X-Salada": 18.50,
    "X-Burguer": 15.00,
    "X-Bacon": 22.00
}

# =====================================================================
# 4. INTERFACE E LÓGICA NO STREAMLIT
# =====================================================================
st.set_page_config(page_title="Sistema Financeiro Alimentos", layout="wide")
st.title("🍔 Sistema Financeiro Alimentos")
st.subheader("Controle de Vendas, Estoque e Lucros")

# Criando abas no Streamlit
aba_vendas, aba_estoque, aba_financeiro = st.tabs(["🛒 Frente de Caixa", "📦 Controle de Estoque", "📊 Financeiro"])

# ---------------------------------------------------------------------
# ABA 1: FRENTE DE CAIXA (VENDAS E BAIXA NO ESTOQUE)
# ---------------------------------------------------------------------
with aba_vendas:
    st.header("Nova Venda")
    
    lanche_selecionado = st.selectbox("Selecione o Lanche:", list(RECEITAS.keys()))
    valor_lanche = PRECOS[lanche_selecionado]
    st.write(f"**Preço de Venda:** R$ {valor_lanche:.2f}")
    
    if st.button("Confirmar Pagamento e Finalizar Venda"):
        conn = conectar_bd()
        cursor = conn.cursor()
        
        # Verificar se há estoque suficiente antes de vender
        estoque_insuficiente = False
        ingredientes_necessarios = RECEITAS[lanche_selecionado]
        
        for ingrediente, qtd_necessaria in ingredientes_necessarios.items():
            cursor.execute("SELECT quantidade FROM estoque WHERE ingrediente = ?", (ingrediente,))
            resultado = cursor.fetchone()
            
            if resultado is None or resultado[0] < qtd_necessaria:
                estoque_insuficiente = True
                st.error(f"Estoque insuficiente ou não cadastrado: **{ingrediente}**!")
                break
        
        # Se tiver estoque, processa a venda
        if not estoque_insuficiente:
            # 1. Dá baixa nos ingredientes
            for ingrediente, qtd_necessaria in ingredientes_necessarios.items():
                cursor.execute("""
                    UPDATE estoque 
                    SET quantidade = quantidade - ? 
                    WHERE ingrediente = ?
                """, (qtd_necessaria, ingrediente))
            
            # 2. Registra a venda
            cursor.execute("INSERT INTO vendas (produto, valor) VALUES (?, ?)", (lanche_selecionado, valor_lanche))
            
            conn.commit()
            st.success(f"✔️ Venda de {lanche_selecionado} realizada com sucesso! Estoque atualizado.")
            
        conn.close()
        st.rerun

# ---------------------------------------------------------------------
# ABA 2: CONTROLE DE ESTOQUE (ADICIONAR INGREDIENTES E CARGA EM MASSA)
# ---------------------------------------------------------------------
with aba_estoque:
    st.header("Gerenciamento de Insumos")
    
    # Seção de atalho para Carga em Massa
    st.info("💡 **Dica de Inicialização:** Clique no botão abaixo para preencher o estoque instantaneamente com a lista padrão de mercado!")
    if st.button("⚡ Inserir/Resetar Lista de Ingredientes em Massa"):
        conn = conectar_bd()
        cursor = conn.cursor()
        for nome, dados in INGREDIENTES_PADRAO.items():
            cursor.execute("""
                INSERT INTO estoque (ingrediente, quantidade, preco_custo) 
                VALUES (?, ?, ?)
                ON CONFLICT(ingrediente) 
                DO UPDATE SET quantidade = quantidade + excluded.quantidade,
                              preco_custo = excluded.preco_custo
            """, (nome, dados["qtd"], dados["custo"]))
        conn.commit()
        conn.close()
        st.success("Lista de insumos injetada com sucesso!")
        st.rerun()

    st.markdown("---")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("Adicionar/Atualizar Item Manual")
        novo_item = st.text_input("Nome do Ingrediente:").lower().strip()
        qtd_item = st.number_input("Quantidade a Adicionar:", min_value=0.0, step=1.0)
        custo_item = st.number_input("Preço de Custo Unitário (R$):", min_value=0.0, step=0.10)
        
        if st.button("Atualizar Estoque Manual"):
            if novo_item:
                conn = conectar_bd()
                cursor = conn.cursor()
                cursor.execute("""
                    INSERT INTO estoque (ingrediente, quantidade, preco_custo) 
                    VALUES (?, ?, ?)
                    ON CONFLICT(ingrediente) 
                    DO UPDATE SET quantidade = quantidade + excluded.quantidade,
                                  preco_custo = excluded.preco_custo
                """, (novo_item, qtd_item, custo_item))
                conn.commit()
                conn.close()
                st.success(f"Estoque atualizado: {novo_item}")
                st.rerun()
            else:
                st.warning("Digite o nome do ingrediente.")

    with col2:
        st.subheader("Posição Atual do Estoque")
        conn = conectar_bd()
        df_estoque = pd.read_sql_query("""
            SELECT ingrediente AS Ingrediente, 
                   quantidade AS [Qtd em Estoque], 
                   'R$ ' || PRINTF('%.2f', preco_custo) AS [Custo Unitário] 
            FROM estoque
        """, conn)
        conn.close()
        
        if not df_estoque.empty:
            st.dataframe(df_estoque, use_container_width=True)
        else:
            st.info("Nenhum ingrediente cadastrado.")

# ---------------------------------------------------------------------
# ABA 3: FINANCEIRO (FUTUROS GASTOS E LUCROS)
# ---------------------------------------------------------------------
with aba_financeiro:
    st.header("Painel de Resultados")
    
    conn = conectar_bd()
    df_vendas = pd.read_sql_query("SELECT * FROM vendas", conn)
    conn.close()
    
    if not df_vendas.empty:
        faturamento_total = df_vendas["valor"].sum()
        total_vendas = len(df_vendas)
        
        # Métricas em destaque
        m1, m2 = st.columns(2)
        m1.metric("Faturamento Total", f"R$ {faturamento_total:.2f}")
        m2.metric("Total de Pedidos", total_vendas)
        
        st.subheader("Histórico de Vendas Recentes")
        st.dataframe(df_vendas.sort_values(by="id", ascending=False), use_container_width=True)
    else:
        st.info("Nenhuma venda realizada ainda.")
