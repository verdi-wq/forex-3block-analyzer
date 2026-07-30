import streamlit as st
import yfinance as yf
import pandas as pd

# --- CONFIGURATION PAGE ---
st.set_page_config(
    page_title="3-Block H4 Strength Analyzer",
    page_icon="📊",
    layout="wide"
)

st.title("📊 Rolling 3-Block H4 Strength & Weakness Dashboard")
st.caption("Analisis Momentum 12 Jam Terakhir yang Dibagi Menjadi 3 Blok H4 (0-4h, 4-8h, 8-12h)")

# --- SIDEBAR: SETTINGS ---
st.sidebar.header("⚙️ Pengaturan Asset & Bobot Blok")

TRADING_30_PAIRS = [
    "GC=F", "BTC-USD",
    "EURUSD=X", "GBPUSD=X", "AUDUSD=X", "NZDUSD=X", "USDJPY=X", "USDCAD=X", "USDCHF=X",
    "EURGBP=X", "EURAUD=X", "EURNZD=X", "EURJPY=X", "EURCAD=X", "EURCHF=X",
    "GBPAUD=X", "GBPNZD=X", "GBPJPY=X", "GBPCAD=X", "GBPCHF=X",
    "AUDNZD=X", "AUDJPY=X", "AUDCAD=X", "AUDCHF=X",
    "NZDJPY=X", "NZDCAD=X", "NZDCHF=X",
    "CADJPY=X", "CADCHF=X", "CHFJPY=X"
]

selected_tickers = st.sidebar.multiselect(
    "Pilih Trading Pair(s):",
    options=TRADING_30_PAIRS,
    default=TRADING_30_PAIRS
)

st.sidebar.subheader("⚖️ Bobot Masing-Masing Blok")
w_b1 = st.sidebar.slider("Blok 1 (0-4j lalu - Terbaru) (%)", 0, 100, 50) / 100
w_b2 = st.sidebar.slider("Blok 2 (4-8j lalu) (%)", 0, 100, 30) / 100
w_b3 = st.sidebar.slider("Blok 3 (8-12j lalu) (%)", 0, 100, 20) / 100

# --- HELPER FUNCTIONS ---
def clean_pair_name(ticker):
    if ticker == "GC=F":
        return "XAUUSD (GOLD)"
    elif ticker == "BTC-USD":
        return "BTCUSD"
    return ticker.replace("=X", "")

def calculate_3block_metrics(ticker):
    """Menghitung pergerakan % di 3 blok 4-jam secara terpisah dan mengambil rata-ratanya."""
    try:
        # Unduh data 1H selama 5 hari terakhir
        data = yf.download(ticker, period="5d", interval="1h", progress=False)
        
        if len(data) >= 13:
            # Ambil seri Close
            close = data['Close']
            if isinstance(close, pd.DataFrame):
                close = close.iloc[:, 0]

            # Titik-titik harga penutupan (0 = sekarang, -4 = 4j lalu, dst)
            p_now = close.iloc[-1]
            p_4h = close.iloc[-5]
            p_8h = close.iloc[-9]
            p_12h = close.iloc[-13]

            # Hitung % Change per blok 4 jam
            b1_pct = ((p_now - p_4h) / p_4h) * 100       # Blok 1 (0-4h)
            b2_pct = ((p_4h - p_8h) / p_8h) * 100       # Blok 2 (4-8h)
            b3_pct = ((p_8h - p_12h) / p_12h) * 100     # Blok 3 (8-12h)

            # Rata-rata terbobot (Weighted Average Score)
            avg_score = (b1_pct * w_b1) + (b2_pct * w_b2) + (b3_pct * w_b3)

            # Logika Tren Prediktif Sederhana
            if b1_pct > 0 and b2_pct > 0 and b3_pct > 0:
                prediction = "🚀 Strong Bullish Trend (Konsisten 12j)"
            elif b1_pct < 0 and b2_pct < 0 and b3_pct < 0:
                prediction = "🔻 Strong Bearish Trend (Konsisten 12j)"
            elif b1_pct > 0 and b2_pct < 0 and b3_pct < 0:
                prediction = "🔄 Bullish Reversal Potential"
            elif b1_pct < 0 and b2_pct > 0 and b3_pct > 0:
                prediction = "⚠️ Bearish Reversal Potential"
            elif avg_score > 0:
                prediction = "📈 Mild Bullish Bias"
            else:
                prediction = "📉 Mild Bearish Bias"

            return {
                "Pair": clean_pair_name(ticker),
                "Avg Score": round(avg_score, 2),
                "Blok 1 (0-4h) %": round(b1_pct, 2),
                "Blok 2 (4-8h) %": round(b2_pct, 2),
                "Blok 3 (8-12h) %": round(b3_pct, 2),
                "Proyeksi/Status": prediction
            }
    except Exception:
        pass

    return {
        "Pair": clean_pair_name(ticker),
        "Avg Score": 0.0,
        "Blok 1 (0-4h) %": 0.0,
        "Blok 2 (4-8h) %": 0.0,
        "Blok 3 (8-12h) %": 0.0,
        "Proyeksi/Status": "N/A Data"
    }

# --- MAIN CONTROLLER ---
if st.button("🔄 Refresh Data Real-Time") or "results_df" not in st.session_state:
    with st.spinner("Menganalisis 3 Blok H4 untuk 30 Trading Pairs..."):
        results = [calculate_3block_metrics(ticker) for ticker in selected_tickers]
        df_raw = pd.DataFrame(results)
        
        if not df_raw.empty:
            # 1. Tentukan urutan hirarki status sesuai keinginanmu
            status_order = [
                "🚀 Strong Bullish Trend (Konsisten 12j)",
                "📈 Mild Bullish Bias",
                "🔄 Bullish Reversal Potential",
                "⚠️ Bearish Reversal Potential",
                "📉 Mild Bearish Bias",
                "🔻 Strong Bearish Trend (Konsisten 12j)",
                "N/A Data"
            ]
            
            # 2. Ubah kolom Proyeksi/Status menjadi tipe Categorical dengan urutan spesifik
            df_raw['Proyeksi/Status'] = pd.Categorical(
                df_raw['Proyeksi/Status'], 
                categories=status_order, 
                ordered=True
            )
            
            # 3. Urutkan berdasarkan Status (sesuai urutan hirarki) lalu Avg Score (tertinggi ke terendah)
            df_sorted = df_raw.sort_values(
                by=["Proyeksi/Status", "Avg Score"], 
                ascending=[True, False]
            ).reset_index(drop=True)
            
            st.session_state.results_df = df_sorted
        else:
            st.session_state.results_df = df_raw

df = st.session_state.results_df

# --- DISPLAY METRICS & TABLE ---
st.subheader("📌 Ringkasan Top & Lowest Avg Score (12 Hours Window)")

if not df.empty:
    top_asset = df.iloc[0]
    worst_asset = df.iloc[-1]
    
    col1, col2 = st.columns(2)
    with col1:
        st.metric("🏆 Skor Rata-Rata Terkuat", top_asset['Pair'], f"{top_asset['Avg Score']} pts")
    with col2:
        st.metric("🔻 Skor Rata-Rata Terlemah", worst_asset['Pair'], f"{worst_asset['Avg Score']} pts")

st.markdown("---")

def color_surfaces(val):
    if isinstance(val, (int, float)):
        color = '#d4edda' if val > 0 else '#f8d7da' if val < 0 else '#ffffff'
        text_color = '#155724' if val > 0 else '#721c24' if val < 0 else '#000000'
        return f'background-color: {color}; color: {text_color}'
    return ''

st.subheader("📋 Matriks 3 Blok H4 (0-4j, 4-8j, 8-12j)")

if hasattr(df.style, "map"):
    styled_df = df.style.map(color_surfaces, subset=["Avg Score", "Blok 1 (0-4h) %", "Blok 2 (4-8h) %", "Blok 3 (8-12h) %"])
else:
    styled_df = df.style.applymap(color_surfaces, subset=["Avg Score", "Blok 1 (0-4h) %", "Blok 2 (4-8h) %", "Blok 3 (8-12h) %"])

st.dataframe(styled_df, use_container_width=True, height=650)

st.subheader("📊 Ranking Skor Rata-Rata Terbobot (Prediction Score)")
st.bar_chart(df.set_index("Pair")["Avg Score"])