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
    
    # Tabela de Estoque de Ingredientes
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS estoque (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            ingrediente TEXT UNIQUE,
            quantidade REAL
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
# 2. DICIONÁRIO DE RECEITAS (Fórmula do Lanche)
# =====================================================================
# Aqui definimos o que cada lanche gasta do estoque
RECEITAS = {
    "X-Salada": {
        "pao": 1,
        "bife": 1,
        "mussarela": 1,
        "presunto": 1,
        "alface": 1,
        "tomate": 1
    },
    "X-Burguer": {
        "pao": 1,
        "bife": 1,
        "mussarela": 1
    }
}

# Preço de venda dos produtos
PRECOS = {
    "X-Salada": 18.50,
    "X-Burguer": 15.00
}

# =====================================================================
# 3. INTERFACE E LÓGICA NO STREAMLIT
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
    st.write(f"**Preço:** R$ {valor_lanche:.2f}")
    
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
                st.error(f"Estoque insuficiente de: **{ingrediente}**!")
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

# ---------------------------------------------------------------------
# ABA 2: CONTROLE DE ESTOQUE (ADICIONAR INGREDIENTES)
# ---------------------------------------------------------------------
with aba_estoque:
    st.header("Gerenciamento de Insumos")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("Adicionar/Atualizar Item")
        novo_item = st.text_input("Nome do Ingrediente (Ex: pao, bife, mussarela):").lower().strip()
        qtd_item = st.number_input("Quantidade a Adicionar:", min_value=0.0, step=1.0)
        
        if st.button("Atualizar Estoque"):
            if novo_item:
                conn = conectar_bd()
                cursor = conn.cursor()
                # Se já existe, soma. Se não, insere.
                cursor.execute("""
                    INSERT INTO estoque (ingrediente, quantidade) 
                    VALUES (?, ?)
                    ON CONFLICT(ingrediente) 
                    DO UPDATE SET quantidade = quantidade + excluded.quantidade
                """, (novo_item, qtd_item))
                conn.commit()
                conn.close()
                st.success(f"Estoque atualizado: {novo_item} +{qtd_item}")
                st.rerun()
            else:
                st.warning("Digite o nome do ingrediente.")

    with col2:
        st.subheader("Posição Atual do Estoque")
        conn = conectar_bd()
        df_estoque = pd.read_sql_query("SELECT ingrediente AS Ingrediente, quantidade AS Qtd FROM estoque", conn)
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
