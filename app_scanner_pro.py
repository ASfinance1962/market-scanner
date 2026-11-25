import streamlit as st
import pandas as pd
import ta
import requests
import time
from datetime import datetime, timezone
from supabase import create_client

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
# --- CONFIGURAÇÃO SUPABASE (7 DIAS GRÁTIS POR UTILIZADOR) ---
SUPABASE_URL = "https://arviymkprercxnlpauax.supabase.co"
SUPABASE_KEY = "sb_publishable_8oB1oixZbqZnW7fPobAVwA_XcadD2Cy"
LINK_PAGAMENTO_STRIPE = "https://stripe.com"

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

if "utilizador" not in st.session_state:
    st.session_state["utilizador"] = None

if not st.session_state["utilizador"]:
    st.sidebar.header("🔐 Acesso à Plataforma")
    aba = st.sidebar.radio("Escolha uma opção:", ["Criar Conta (7 Dias Grátis)", "Entrar"])
    email = st.sidebar.text_input("E-mail:")
    password = st.sidebar.text_input("Palavra-passe (mín. 6 caracteres):", type="password")

    if aba == "Criar Conta (7 Dias Grátis)":
        if st.sidebar.button("Começar Teste Gratuito de 7 Dias", type="primary"):
            try:
                res = supabase.auth.sign_up({"email": email, "password": password})
                if res.user:
                    supabase.table("perfis").insert({"id": res.user.id, "email": email}).execute()
                    st.session_state["utilizador"] = res.user
                    st.rerun()
            except Exception as e:
                st.sidebar.error(f"Erro ao criar conta: {e}")
    else:
        if st.sidebar.button("Entrar", type="primary"):
            try:
                res = supabase.auth.sign_in_with_password({"email": email, "password": password})
                if res.user:
                    st.session_state["utilizador"] = res.user
                    st.rerun()
            except Exception:
                st.sidebar.error("E-mail ou palavra-passe incorretos.")

    st.info("👋 **Bem-vindo ao MarketScanner Pro!** Crie a sua conta gratuita na barra lateral (à esquerda) para desbloquear **7 dias de acesso livre**.")
    st.stop()

user_id = st.session_state["utilizador"].id
dados_perfil = supabase.table("perfis").select("*").eq("id", user_id).execute()

if dados_perfil.data:
    perfil = dados_perfil.data[0]
    data_criacao = datetime.fromisoformat(perfil["criado_em"].replace("Z", "+00:00"))
    dias_passados = (datetime.now(timezone.utc) - data_criacao).days
    dias_restantes = max(0, 7 - dias_passados)
    e_assinante = perfil["assinante"]
    st.sidebar.success(f"👤 {perfil['email']}")
    if st.sidebar.button("Terminar Sessão"):
        st.session_state["utilizador"] = None
        st.rerun()

    if not e_assinante and dias_passados >= 7:
        st.error("🔒 **O seu período experimental gratuito de 7 dias terminou.**")
        st.markdown(f"Para continuar a utilizar o **MarketScanner Pro** sem limites, ative a sua assinatura mensal aqui:\n\n👉 **[Subscrever Plano Mensal]({LINK_PAGAMENTO_STRIPE})**")
        st.stop()
    elif not e_assinante:
        st.info(f"⏳ **Período Experimental:** Restam **{dias_restantes} dia(s)** de acesso gratuito.")

st.sidebar.markdown("---")
st.sidebar.header("🔑 Dados de Mercado (Chave Gratuita)")
api_key = st.sidebar.text_input("Sua API Key (Twelve Data):", type="password")
st.sidebar.caption("Obtenha a sua chave gratuita em [twelvedata.com](https://twelvedata.com) (800 pedidos grátis/dia).")

if not api_key:
    st.warning("🔑 Cole a sua **API Key gratuita da Twelve Data** na barra lateral para carregar os dados de mercado.")
    st.stop()
# Barra Lateral (Configurações do Usuário)
st.sidebar.header("⚙️ Configurações da Triagem")

mercados = {
    "Euronext Lisboa (PSI)": ["EDP:ELI", "GALP:ELI", "JMT:ELI", "BCP:ELI", "NOS:ELI", "SON:ELI", "RENE:ELI", "ALTR:ELI"],
    "EUA (NYSE Blue Chips)": ["JPM", "V", "MA", "JNJ", "WMT", "PG", "DIS", "KO"],
    "EUA (NASDAQ Tech)": ["AAPL", "MSFT", "NVDA", "GOOGL", "AMZN", "META", "TSLA", "AMD"],
    "Londres (FTSE 100)": ["SHEL:LSE", "AZN:LSE", "HSBA:LSE", "ULVR:LSE", "BP:LSE", "RIO:LSE"],
    "Paris (CAC 40)": ["MC:EPA", "OR:EPA", "TTE:EPA", "AIR:EPA", "SAN:EPA", "BNP:EPA"],
    "Madrid (IBEX 35)": ["SAN:BME", "ITX:BME", "IBE:BME", "BBVA:BME", "TEF:BME", "REP:BME"],
    "Frankfurt (DAX 40)": ["SAP:XETR", "SIE:XETR", "ALV:XETR", "DTE:XETR", "MBG:XETR", "BMW:XETR"],
    "Brasil (B3)": ["PETR4:BVMF", "VALE3:BVMF", "ITUB4:BVMF", "BBDC4:BVMF", "BBAS3:BVMF", "WEGE3:BVMF"],
    "Criptomoedas": ["BTC/USD", "ETH/USD", "SOL/USD", "BNB/USD", "XRP/USD", "ADA/USD"],
    "ETFs & Índices EUA": ["SPY", "QQQ", "DIA", "IWM", "EEM", "GLD"],
    "Lista Personalizada": []
}

def obter_dados_twelvedata(ticker, chave_api):
    url = "https://api.twelvedata.com" + f"/time_series?symbol={ticker}&interval=1day&outputsize=220&apikey={chave_api}"
    resp = requests.get(url).json()
    if "values" not in resp:
        return pd.DataFrame()
    df = pd.DataFrame(resp["values"])
    df = df.iloc[::-1].reset_index(drop=True)
    for col in ["open", "high", "low", "close"]:
        df[col] = df[col].astype(float)
    df.rename(columns={"open": "Open", "high": "High", "low": "Low", "close": "Close", "datetime": "Date"}, inplace=True)
    df.set_index("Date", inplace=True)
    time.sleep(8)
    return df

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
            df = obter_dados_twelvedata(ticker, api_key)
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
        dados_grafico = obter_dados_twelvedata(ativo_escolhido, api_key)
        if not dados_grafico.empty:
            dados_grafico["Preço Fecho"] = dados_grafico["Close"]
            dados_grafico["MME 20"] = dados_grafico["Close"].ewm(span=20, adjust=False).mean()
            dados_grafico["MME 50"] = dados_grafico["Close"].ewm(span=50, adjust=False).mean()
            dados_grafico["MME 200"] = dados_grafico["Close"].ewm(span=200, adjust=False).mean()

            dados_grafico["MME 200"] = dados_grafico["Close"].ewm(span=200, adjust=False).mean()
            bb_graf = ta.volatility.BollingerBands(close=dados_grafico["Close"], window=20, window_dev=2)
            dados_grafico["Bollinger Sup."] = bb_graf.bollinger_hband()
            dados_grafico["Bollinger Inf."] = bb_graf.bollinger_lband()

            st.line_chart(
                dados_grafico[["Preço Fecho", "MME 20", "MME 50", "MME 200", "Bollinger Sup.", "Bollinger Inf."]],
                color=["#00FFAA", "#FFA500", "#FF4B4B", "#3399FF", "#888888", "#888888"],
                height=550
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
