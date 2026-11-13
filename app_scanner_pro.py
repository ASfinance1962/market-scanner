python
import streamlit as st
import yfinance as yf
import pandas as pd
import ta

# Configuração da Página Comercial
st.set_page_config(page_title="MarketScanner Pro | Ações, Dividendos & Cripto", layout="wide")

# ==========================================
# AVISO LEGAL OBRIGATÓRIO (COMPLIANCE)
# ==========================================
st.warning(
    "⚠️ **AVISO LEGAL:** Esta plataforma é uma ferramenta exclusivamente tecnológica e educacional de triagem estatística. "
    "Os filtros são configurados livremente pelo próprio usuário. Nenhuma informação exibida constitui recomendação, "
    "indicação ou consultoria de compra ou venda de valores mobiliários ou criptoativos."
)

st.title("📊 MarketScanner Pro — Rastreador Quantitativo Multi-Ativos")
st.markdown("Configure seus critérios técnicos, fundamentalistas e de volatilidade na barra lateral para filtrar **Ações, ETFs e Criptomoedas**.")

# ==========================================
# BARRA LATERAL: PARÂMETROS DO USUÁRIO
# ==========================================
st.sidebar.header("⚙️ Filtros de Mercado")

ativos_input = st.sidebar.text_area(
    "Ativos para monitorar (separados por vírgula):",
    value="EDP.LS, GALP.LS, PETR4.SA, BBAS3.SA, AAPL, KO, BTC-USD, ETH-USD, SOL-USD",
    help="Use .LS para Lisboa, .SA para Brasil e -USD para Criptomoedas."
)

st.sidebar.subheader("📈 Indicadores Fundamentalistas (Ações)")
dy_minimo = st.sidebar.slider("Dividend Yield Mínimo (%):", min_value=0.0, max_value=15.0, value=4.0, step=0.5)
pl_maximo = st.sidebar.slider("P/L Máximo (Preço/Lucro):", min_value=5.0, max_value=60.0, value=20.0, step=1.0)
roe_minimo = st.sidebar.slider("ROE Mínimo (%):", min_value=0.0, max_value=40.0, value=12.0, step=1.0)

st.sidebar.subheader("📉 Indicadores Técnicos & Proteção")
rsi_maximo = st.sidebar.slider("RSI Máximo (Filtro de Sobrecompra):", min_value=30, max_value=90, value=70, step=5)
queda_alerta = st.sidebar.slider("Alerta de Queda Diária (%):", min_value=-15.0, max_value=-1.0, value=-4.0, step=0.5)
exigir_tendencia_alta = st.sidebar.checkbox("Exigir Preço acima da Média de 200 dias", value=True)

# ==========================================
# MOTOR COM CACHE INTELIGENTE (ESCALABILIDADE)
# ==========================================
# Guarda os dados na memória por 300 segundos (5 min) para suportar centenas de usuários simultâneos
@st.cache_data(ttl=300, show_spinner=False)
def obter_dados_ativo(ticker):
    ativo = yf.Ticker(ticker)
    dados = ativo.history(period="1y", interval="1d")
    info = ativo.info
    return dados, info

def analisar_ativo(ticker, dy_min, pl_max, roe_min, rsi_max, queda_max, exigir_sma200):
    ticker_limpo = ticker.strip().upper()
    try:
        dados, info = obter_dados_ativo(ticker_limpo)
        if len(dados) < 200:
            return None

        # Identifica automaticamente se é Criptomoeda
        is_cripto = ticker_limpo.endswith("-USD") or ticker_limpo.endswith("-EUR") or info.get("quoteType") == "CRYPTOCURRENCY"

        # Cálculos Técnicos
        dados['SMA_200'] = ta.trend.sma_indicator(dados['Close'], window=200)
        dados['RSI'] = ta.momentum.rsi(dados['Close'], window=14)
        dados['ATR'] = ta.volatility.average_true_range(dados['High'], dados['Low'], dados['Close'], window=14)

        ultimo = dados.iloc[-1]
        penultimo = dados.iloc[-2]

        preco = ultimo['Close']
        var_dia = ((preco - penultimo['Close']) / penultimo['Close']) * 100
        sma200 = ultimo['SMA_200']
        rsi = ultimo['RSI']
        atr = ultimo['ATR']

        # Avaliação Técnica e de Volatilidade (Aplica-se a Ações e Cripto)
        criterio_rsi = rsi <= rsi_max
        criterio_tendencia = (preco > sma200) if exigir_sma200 else True
        alerta_volatilidade = var_dia <= queda_max

        if is_cripto:
            # Criptomoedas não têm Dividendos, P/L ou ROE
            dy_texto, pl_texto, roe_texto = "N/A (Cripto)", "N/A", "N/A"
            criterio_fundamental = True
            tipo_ativo = "🪙 Cripto"
        else:
            tipo_ativo = "🏢 Ação/ETF"
            # Extração segura de Dividend Yield
            dy_raw = info.get("dividendYield", 0) or 0
            dy = dy_raw * 100 if dy_raw < 1 else dy_raw

            # Extração segura de P/L (Trailing PE)
            pl = info.get("trailingPE", 0) or 0

            # Extração segura de ROE (Return on Equity)
            roe_raw = info.get("returnOnEquity", 0) or 0
            roe = roe_raw * 100

            dy_texto = f"{dy:.2f}%"
            pl_texto = f"{pl:.1f}x" if pl > 0 else "N/A"
            roe_texto = f"{roe:.1f}%" if roe != 0 else "N/A"

            # Validação dos critérios fundamentalistas
            passou_dy = dy >= dy_min
            passou_pl = (0 < pl <= pl_max) if pl_max > 0 else True
            passou_roe = roe >= roe_min
            criterio_fundamental = passou_dy and passou_pl and passou_roe

        # Veredito Objetivo
        if alerta_volatilidade:
            status = "🚨 Alerta de Queda Brusca"
        elif criterio_fundamental and criterio_rsi and criterio_tendencia:
            status = "✅ Atende aos Critérios"
        else:
            status = "➖ Fora dos Parâmetros"

        return {
            "Ativo": ticker_limpo,
            "Tipo": tipo_ativo,
            "Preço": round(preco, 2),
            "Var. Dia (%)": round(var_dia, 2),
            "Div. Yield": dy_texto,
            "P/L": pl_texto,
            "ROE": roe_texto,
            "RSI (14)": round(rsi, 1),
            "Margem Volat. (2x ATR)": round(preco - (2 * atr), 2),
            "Status": status
        }
    except Exception:
        return None

# ==========================================
# EXECUÇÃO E INTERFACE DO USUÁRIO
# ==========================================
if st.button("🔍 Executar Triagem Completa"):
    lista_tickers = [t for t in ativos_input.split(",") if t.strip()]
    resultados = []

    with st.spinner("Processando indicadores técnicos, fundamentalistas e cripto..."):
        for t in lista_tickers:
            res = analisar_ativo(
                t, dy_minimo, pl_maximo, roe_minimo,
                rsi_maximo, queda_alerta, exigir_tendencia_alta
            )
            if res:
                resultados.append(res)

    if resultados:
        df_resultados = pd.DataFrame(resultados)
        st.dataframe(df_resultados, use_container_width=True, hide_index=True)

        # Métricas rápidas no topo
        total_aprovados = len([r for r in resultados if "✅" in r["Status"]])
        total_alertas = len([r for r in resultados if "🚨" in r["Status"]])
        
        col1, col2, col3 = st.columns(3)
        col1.metric("Ativos Analisados", len(resultados))
        col2.metric("Dentro dos Critérios", total_aprovados)
        col3.metric("Alertas de Queda", total_alertas)

        # Exportação CSV
        csv = df_resultados.to_csv(index=False).encode('utf-8')
        st.download_button(
            label="📥 Exportar Tabela para Excel (CSV)",
            data=csv,
            file_name="relatorio_marketscanner.csv",
            mime="text/csv"
        )
    else:
        st.error("Nenhum ativo válido encontrado. Verifique se os códigos (ticker
