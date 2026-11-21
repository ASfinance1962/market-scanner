import streamlit as st
import yfinance as yf
import pandas as pd
import ta
import requests

# Configuração da página
st.set_page_config(
    page_title="MarketScanner Pro",
    page_icon="📊",
    layout="wide"
)

# Ocultar o botão "Gerenciar aplicativo" e o rodapé padrão do Streamlit
st.markdown(
    """
    <style>
    [data-testid="manage-app-button"],
    [data-testid="stAppDeployButton"],
    .stAppDeployButton,
    footer,
    #MainMenu {
        display: none !important;
        visibility: hidden !important;
    }
    </style>
    """,
    unsafe_allow_html=True
)

# Aviso Legal (Compliance e Transparência - CMVM / ESMA)
st.warning(
    "⚠️ **AVISO LEGAL:** Esta plataforma é uma ferramenta exclusivamente tecnológica e educacional de triagem estatística. "
    "Os filtros são configurados livremente pelo próprio usuário. Nenhuma informação exibida constitui recomendação, "
    "indicação ou consultoria de compra ou venda de valores mobiliários ou criptoativos."
)

st.title("📊 MarketScanner Pro — Rastreador Quantitativo Multi-Ativos")
st.markdown("Analise rapidamente ações globais e criptomoedas com base em indicadores técnicos objetivos (dados diários para fins exclusivamente educacionais).")

# Barra Lateral (Configurações do Usuário)
st.sidebar.header("⚙️ Configurações da Triagem")

mercados = {
     "Euronext Lisboa (PSI)": ["EDP.LS", "GALP.LS", "JMT.LS", "BCP.LS", "NOS.LS", "SON.LS", "RENE.LS", "ALTR.LS", "NVG.LS", "COR.LS"],
    "EUA (Tech & Blue Chips)": ["AAPL", "MSFT", "NVDA", "GOOGL", "AMZN", "META", "TSLA", "JPM", "V", "KO"],
    "Brasil (B3)": ["PETR4.SA", "VALE3.SA", "ITUB4.SA", "BBDC4.SA", "BBAS3.SA", "WEGE3.SA", "RENT3.SA", "ABEV3.SA"],
    "Criptomoedas": ["BTC-USD", "ETH-USD", "SOL-USD", "BNB-USD", "XRP-USD", "ADA-USD", "LINK-USD", "AVAX-USD"],
    "ETFs Globais": ["SPY", "QQQ", "IWM", "EEM", "VWCE.DE", "IWDA.AS"],
    "Matérias-Primas": ["GC=F", "SI=F", "CL=F", "NG=F", "HG=F"],
    "Lista Personalizada": []
}

mercado_escolhido = st.sidebar.selectbox("Selecione o Mercado:", list(mercados.keys()))

if mercado_escolhido == "Lista Personalizada":
    ativos_texto = st.sidebar.text_area(
        "Digite os códigos (tickers) separados por vírgula:",
        value="EDP.LS, AAPL, PETR4.SA, BTC-USD"
    )
    lista_ativos = [x.strip().upper() for x in ativos_texto.split(",") if x.strip()]
else:
    lista_ativos = mercados[mercado_escolhido]

st.sidebar.subheader("📐 Parâmetros Técnicos")
rsi_sobrevenda = st.sidebar.slider("Limite RSI Sobre-venda:", 15, 45, 35)
rsi_sobrecompra = st.sidebar.slider("Limite RSI Sobre-compra:", 55, 85, 70)

perfil_risco = st.sidebar.selectbox(
    "Multiplicador ATR (Gestão de Risco):",
    ["Conservador (Stop 1.5x | Alvo 2.0x)", "Moderado (Stop 2.0x | Alvo 3.0x)", "Agressivo (Stop 2.5x | Alvo 4.5x)"]
)

if "Conservador" in perfil_risco:
    mult_stop, mult_alvo = 1.5, 2.0
elif "Moderado" in perfil_risco:
    mult_stop, mult_alvo = 2.0, 3.0
else:
    mult_stop, mult_alvo = 2.5, 4.5

# Função de análise técnica
def analisar_ativos(tickers):
    resultados = []
    barra_progresso = st.progress(0)
    total = len(tickers)

    for i, ticker in enumerate(tickers):
        try:
            df = yf.download(ticker, period="1y", interval="1d", progress=False)
            if df.empty or len(df) < 200:
                barra_progresso.progress((i + 1) / total)
                continue

            if isinstance(df.columns, pd.MultiIndex):
                df.columns = df.columns.get_level_values(0)

            close = df["Close"].squeeze()
            high = df["High"].squeeze()
            low = df["Low"].squeeze()

            # Indicadores Técnicos
            rsi = ta.momentum.RSIIndicator(close=close, window=14).rsi().iloc[-1]
            mme20 = ta.trend.EMAIndicator(close=close, window=20).ema_indicator().iloc[-1]
            mme50 = ta.trend.EMAIndicator(close=close, window=50).ema_indicator().iloc[-1]
            atr = ta.volatility.AverageTrueRange(high=high, low=low, close=close, window=14).average_true_range().iloc[-1]

            preco_atual = float(close.iloc[-1])
            preco_anterior = float(close.iloc[-2])
            variacao_pct = ((preco_atual - preco_anterior) / preco_anterior) * 100
            mme200 = ta.trend.EMAIndicator(close=close, window=200).ema_indicator().iloc[-1]
            macd_val = ta.trend.MACD(close=close).macd_diff().iloc[-1]
            macd_str = "Positivo" if macd_val > 0 else "Negativo"
            bb = ta.volatility.BollingerBands(close=close, window=20, window_dev=2)
            bb_sup = bb.bollinger_hband().iloc[-1]
            bb_inf = bb.bollinger_lband().iloc[-1]
            bb_str = "Banda Sup." if preco_atual >= bb_sup else ("Banda Inf." if preco_atual <= bb_inf else "Centro")

            # Classificação estatística neutra
            if rsi <= rsi_sobrevenda and preco_atual > mme50:
                status = "🟢 Confluência Alta (Pullback)"
                stop = preco_atual - (atr * mult_stop)
                alvo = preco_atual + (atr * mult_alvo)
            elif rsi <= rsi_sobrevenda:
                status = "🟡 RSI em Sobre-venda"
                stop = preco_atual - (atr * mult_stop)
                alvo = preco_atual + (atr * mult_alvo)
            elif rsi >= rsi_sobrecompra:
                status = "🔴 RSI em Sobre-compra"
                stop = preco_atual + (atr * mult_stop)
                alvo = preco_atual - (atr * mult_alvo)
            elif preco_atual > mme20 and mme20 > mme50:
                status = "🔵 Tendência de Alta Ativa"
                stop = preco_atual - (atr * mult_stop)
                alvo = preco_atual + (atr * mult_alvo)
            else:
                status = "⚪ Neutro / Consolidação"
                stop = preco_atual - (atr * mult_stop)
                alvo = preco_atual + (atr * mult_alvo)

            resultados.append({
                "Ativo": ticker,
                "Preço Ref.": round(preco_atual, 2),
                "Var. (%)": round(variacao_pct, 2),
                "RSI (14)": round(float(rsi), 1),
                "MME 20": round(float(mme20), 2),
                "MME 50": round(float(mme50), 2),
                "MME 200": round(float(mme200), 2),
                "MACD (Hist.)": macd_str,
                "Bollinger": bb_str,
                "Leitura Estatística": status,
                "Ref. Stop (ATR)": round(float(stop), 2),
                "Ref. Alvo (ATR)": round(float(alvo), 2)
            })
        except Exception:
            pass

        barra_progresso.progress((i + 1) / total)

    barra_progresso.empty()
    return pd.DataFrame(resultados)

# Guardar estado na sessão para manter tabela ao trocar o gráfico
if "df_resultados" not in st.session_state:
    st.session_state["df_resultados"] = pd.DataFrame()

if st.button("🔍 Executar Triagem Completa", type="primary"):
    if not lista_ativos:
        st.warning("Adicione pelo menos um código de ativo na barra lateral.")
    else:
        with st.spinner("A processar dados e indicadores técnicos..."):
            st.session_state["df_resultados"] = analisar_ativos(lista_ativos)

df_res = st.session_state["df_resultados"]

if not df_res.empty:
    st.subheader(f"📋 Resultados da Triagem — {mercado_escolhido}")

    # Cartões de Resumo (KPIs)
    col1, col2, col3 = st.columns(3)
    col1.metric("Total Analisado", f"{len(df_res)} ativos")
    em_alta = len(df_res[df_res["Leitura Estatística"].str.contains("Alta|Confluência")])
    col2.metric("Em Alta / Confluência", f"{em_alta} ativos")
    em_sobrevenda = len(df_res[df_res["Leitura Estatística"].str.contains("Sobre-venda")])
    col3.metric("Em Sobre-venda (RSI)", f"{em_sobrevenda} ativos")

    st.dataframe(df_res, width="stretch", hide_index=True)

    # Botão para descarregar CSV
    csv = df_res.to_csv(index=False).encode("utf-8")
    st.download_button(
        label="📥 Descarregar Tabela (CSV / Excel)",
        data=csv,
        file_name=f"triagem_{mercado_escolhido.split()[0].lower()}.csv",
        mime="text/csv"
    )
    # Gráfico de Barras de Variação Diária
    st.markdown("---")
    st.subheader("📊 Comparação de Variação Diária (%)")
    st.bar_chart(df_res.set_index("Ativo")["Var. (%)"])

    
      # Secção de Gráfico Visual
    st.markdown("---")
    st.subheader("📈 Visualização Gráfica do Ativo (1 Ano)")

    ativo_escolhido = st.selectbox(
        "Selecione um ativo da tabela acima para visualizar o preço e as médias móveis:",
        df_res["Ativo"].tolist()
    )

    if ativo_escolhido:
        dados_grafico = yf.download(ativo_escolhido, period="1y", interval="1d", progress=False)
        if not dados_grafico.empty:
            if isinstance(dados_grafico.columns, pd.MultiIndex):
                dados_grafico.columns = dados_grafico.columns.get_level_values(0)

            dados_grafico["Preço Fecho"] = dados_grafico["Close"]
            dados_grafico["MME 20"] = dados_grafico["Close"].ewm(span=20, adjust=False).mean()
            dados_grafico["MME 50"] = dados_grafico["Close"].ewm(span=50, adjust=False).mean()
            dados_grafico["MME 200"] = dados_grafico["Close"].ewm(span=200, adjust=False).mean()

            st.line_chart(
                dados_grafico[["Preço Fecho", "MME 20", "MME 50", "MME 200"]],
                color=["#00FFAA", "#FFA500", "#FF4B4B", "#3399FF"]
            )
else:
    st.info("Clique em **Executar Triagem Completa** acima para carregar os dados do mercado selecionado.")

# Área de Feedback para Testadores
st.markdown("---")
with st.expander("💬 Enviar Opinião ou Sugestão (Versão Beta)"):
    st.write("A sua opinião ajuda a melhorar esta ferramenta:")
    with st.form("form_feedback_beta_v2"):
        preco_justo = st.selectbox(
            "Quanto consideraria justo pagar por mês por um software de triagem destes com dados em tempo real licenciados?",
            ["Prefiro não responder", "Até 9€ / mês", "Entre 10€ e 19€ / mês", "Entre 20€ e 39€ / mês", "Mais de 40€ / mês"],
            key="fb_preco_justo"
        )
        sugestao = st.text_area(
            "O que achou da clareza dos indicadores ou que ativo gostaria de ver incluído?",
            key="fb_sugestao_texto"
        )
        email_testador = st.text_input(
            "O seu e-mail (opcional, caso queira receber novidades ou acesso antecipado):",
            key="fb_email_contacto"
        )
        
        btn_enviar = st.form_submit_button("Enviar Feedback", type="primary")
        
        if btn_enviar:
            if sugestao.strip() or preco_justo != "Prefiro não responder":
                try:
                    resposta = requests.post(
                      "https://formspree.io/f/mppddkkw",
                        data={
                            "Preco_Considerado_Justo": preco_justo,
                            "Opiniao_Sugestao": sugestao,
                            "Email_Testador": email_testador
                        },
                        headers={"Accept": "application/json"}
                    )
                    if resposta.status_code == 200:
                        st.success("✅ Obrigado! A sua resposta foi enviada com sucesso.")
                    else:
                        st.error(f"❌ Erro {resposta.status_code}: {resposta.text}")
                except Exception:
                    st.error("❌ Erro de ligação ao enviar o formulário.")
            else:
                st.warning("⚠️ Por favor, selecione um valor ou escreva uma sugestão antes de enviar.")      
