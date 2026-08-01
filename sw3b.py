import streamlit as st
import yfinance as yf
import pandas as pd

# --- PAGE CONFIGURATION ---
st.set_page_config(
    page_title="Assets Strength Analyzer",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded"
)

# --- CUSTOM STYLING (Modern UI) ---
st.markdown("""
<style>
    /* Global Styles */
    .main .block-container {
        padding-top: 2rem;
        padding-bottom: 2rem;
    }
    
    /* Header Styling */
    .dashboard-header {
        background: linear-gradient(135deg, #1e293b 0%, #0f172a 100%);
        padding: 1.5rem 2rem;
        border-radius: 12px;
        color: white;
        margin-bottom: 1.5rem;
        border: 1px solid #334155;
    }
    .dashboard-header h1 {
        color: #f8fafc;
        font-size: 1.8rem;
        margin: 0;
        font-weight: 700;
    }
    .dashboard-header p {
        color: #94a3b8;
        margin: 0.3rem 0 0 0;
        font-size: 0.95rem;
    }

    /* Metric Cards */
    div[data-testid="stMetric"] {
        background-color: #f8fafc;
        border: 1px solid #e2e8f0;
        border-radius: 10px;
        padding: 1rem;
        box-shadow: 0 1px 3px rgba(0,0,0,0.05);
    }

    /* Primary Accent Color for Buttons */
    .stButton > button {
        width: 100%;
        border-radius: 8px;
        font-weight: 600;
        background-color: #2563eb;
        color: white;
        border: none;
        padding: 0.5rem 1rem;
        transition: all 0.2s ease;
    }
    .stButton > button:hover {
        background-color: #1d4ed8;
        border: none;
        color: white;
    }
</style>
""", unsafe_allow_html=True)

# --- HEADER SECTION ---
st.markdown("""
<div class="dashboard-header">
    <h1>📊 Assets Strength & Weakness Dashboard</h1>
    <p>Momentum, Directional Bias & Pivot Levels Analysis</p>
</div>
""", unsafe_allow_html=True)

# --- MAPPER TICKER YAHOO FINANCE <-> NAMA STANDAR ---
PAIR_MAP = {
    "XAUUSD": "GC=F",
    "BTCUSD": "BTC-USD",
    "EURUSD": "EURUSD=X",
    "GBPUSD": "GBPUSD=X",
    "AUDUSD": "AUDUSD=X",
    "NZDUSD": "NZDUSD=X",
    "USDJPY": "USDJPY=X",
    "USDCAD": "USDCAD=X",
    "USDCHF": "USDCHF=X",
    "EURGBP": "EURGBP=X",
    "EURAUD": "EURAUD=X",
    "EURNZD": "EURNZD=X",
    "EURJPY": "EURJPY=X",
    "EURCAD": "EURCAD=X",
    "EURCHF": "EURCHF=X",
    "GBPAUD": "GBPAUD=X",
    "GBPNZD": "GBPNZD=X",
    "GBPJPY": "GBPJPY=X",
    "GBPCAD": "GBPCAD=X",
    "GBPCHF": "GBPCHF=X",
    "AUDNZD": "AUDNZD=X",
    "AUDJPY": "AUDJPY=X",
    "AUDCAD": "AUDCAD=X",
    "AUDCHF": "AUDCHF=X",
    "NZDJPY": "NZDJPY=X",
    "NZDCAD": "NZDCAD=X",
    "NZDCHF": "NZDCHF=X",
    "CADJPY": "CADJPY=X",
    "CADCHF": "CADCHF=X",
    "CHFJPY": "CHFJPY=X"
}

ALL_PAIRS = list(PAIR_MAP.keys())

# --- SIDEBAR: SETTINGS ---
st.sidebar.header("⚙️ Setting")

# Opsi dropdown dengan "All" di posisi pertama
pair_options = ["All"] + ALL_PAIRS

selected_selection = st.sidebar.multiselect(
    "Select Trading Pair(s):",
    options=pair_options,
    default=["All"]
)

# LOGIKA SELEKSI "ALL":
# Jika "All" terpilih atau pengguna mengosongkan pilihan, gunakan seluruh daftar pair.
if "All" in selected_selection or not selected_selection:
    selected_display_pairs = ALL_PAIRS
else:
    selected_display_pairs = selected_selection

# FIXED BLOCK WEIGHTS (50% Block 1, 30% Block 2, 20% Block 3)
W_B1_NORM = 0.50
W_B2_NORM = 0.30
W_B3_NORM = 0.20

# --- HELPER FUNCTIONS ---
def calculate_3block_metrics(pair_label):
    """Calculates % performance across 3 distinct 4-hour blocks and Pivot/S&R Levels (S1-S3, R1-R3)."""
    ticker = PAIR_MAP[pair_label]
    try:
        data = yf.download(ticker, period="5d", interval="1h", progress=False)
        
        if len(data) >= 13:
            close = data['Close']
            high = data['High']
            low = data['Low']

            if isinstance(close, pd.DataFrame):
                close = close.iloc[:, 0]
                high = high.iloc[:, 0]
                low = low.iloc[:, 0]

            # --- DATA HARGA ---
            p_now = close.iloc[-1]
            p_4h = close.iloc[-5]
            p_8h = close.iloc[-9]
            p_12h = close.iloc[-13]

            # --- HIGH, LOW, CLOSE (UNTUK PIVOT LEVEL 4 JAM TERAKHIR) ---
            last_4h_high = high.iloc[-5:].max()
            last_4h_low = low.iloc[-5:].min()
            last_4h_close = p_now

            # Perhitungan Pivot, S1-S3, R1-R3 Standard
            pivot = (last_4h_high + last_4h_low + last_4h_close) / 3
            
            r1 = (2 * pivot) - last_4h_low
            s1 = (2 * pivot) - last_4h_high
            
            r2 = pivot + (last_4h_high - last_4h_low)
            s2 = pivot - (last_4h_high - last_4h_low)
            
            r3 = last_4h_high + 2 * (pivot - last_4h_low)
            s3 = last_4h_low - 2 * (last_4h_high - pivot)

            # --- ATURAN PRESISI DESIMAL ---
            if pair_label in ["XAUUSD", "BTCUSD"]:
                digits = 2
            elif "JPY" in pair_label:
                digits = 3
            else:
                digits = 5

            # --- CALCULATE % PERFORMANCE ---
            b1_pct = ((p_now - p_4h) / p_4h) * 100       # Block 1 (0-4h)
            b2_pct = ((p_4h - p_8h) / p_8h) * 100       # Block 2 (4-8h)
            b3_pct = ((p_8h - p_12h) / p_12h) * 100     # Block 3 (8-12h)

            avg_score = (b1_pct * W_B1_NORM) + (b2_pct * W_B2_NORM) + (b3_pct * W_B3_NORM)

            # --- SOUGHT HIERARCHY LOGIC ---
            if b1_pct > 0 and b2_pct > 0 and b3_pct > 0:
                prediction = "🚀 Strong Bullish Trend"
            elif avg_score > 0 and not (b1_pct < 0 and b2_pct > 0 and b3_pct > 0):
                prediction = "📈 Mild Bullish Bias"
            elif b1_pct < 0 and b2_pct > 0 and b3_pct > 0:
                prediction = "⚠️ Bearish Reversal Potential"
            elif b1_pct > 0 and b2_pct < 0 and b3_pct < 0:
                prediction = "🔄 Bullish Reversal Potential"
            elif avg_score <= 0 and not (b1_pct < 0 and b2_pct < 0 and b3_pct < 0):
                prediction = "📉 Mild Bearish Bias"
            elif b1_pct < 0 and b2_pct < 0 and b3_pct < 0:
                prediction = "🔻 Strong Bearish Trend"
            else:
                prediction = "📉 Mild Bearish Bias"

            return {
                "Pair": pair_label,
                "Status / Projection": prediction,
                "Avg Score": round(avg_score, 2),
                "S3": f"{s3:,.{digits}f}",
                "S2": f"{s2:,.{digits}f}",
                "S1": f"{s1:,.{digits}f}",
                "Pivot": f"{pivot:,.{digits}f}",
                "R1": f"{r1:,.{digits}f}",
                "R2": f"{r2:,.{digits}f}",
                "R3": f"{r3:,.{digits}f}",
                "Block 1 (0-4h) %": round(b1_pct, 2),
                "Block 2 (4-8h) %": round(b2_pct, 2),
                "Block 3 (8-12h) %": round(b3_pct, 2)
            }
    except Exception:
        pass

    return {
        "Pair": pair_label,
        "Status / Projection": "N/A Data",
        "Avg Score": 0.0,
        "S3": "-", "S2": "-", "S1": "-", "Pivot": "-", "R1": "-", "R2": "-", "R3": "-",
        "Block 1 (0-4h) %": 0.0, "Block 2 (4-8h) %": 0.0, "Block 3 (8-12h) %": 0.0
    }

# --- MAIN CONTROLLER ---
if st.button("🔄 Refresh Data Real-Time") or "results_df" not in st.session_state:
    with st.spinner("Analyzing 3x H4 Blocks & Pivot Levels across selected pairs..."):
        results = [calculate_3block_metrics(pair_label) for pair_label in selected_display_pairs]
        df_raw = pd.DataFrame(results)
        
        if not df_raw.empty:
            status_order = [
                "🚀 Strong Bullish Trend",
                "📈 Mild Bullish Bias",
                "⚠️ Bearish Reversal Potential",
                "🔄 Bullish Reversal Potential",
                "📉 Mild Bearish Bias",
                "🔻 Strong Bearish Trend",
                "N/A Data"
            ]
            
            df_raw['Status / Projection'] = pd.Categorical(
                df_raw['Status / Projection'], 
                categories=status_order, 
                ordered=True
            )
            
            # Sort by Status hierarchy first, then highest Avg Score
            df_sorted = df_raw.sort_values(
                by=["Status / Projection", "Avg Score"], 
                ascending=[True, False]
            ).reset_index(drop=True)
            
            st.session_state.results_df = df_sorted
        else:
            st.session_state.results_df = df_raw

df = st.session_state.results_df

# --- SUMMARY METRICS SECTION ---
if not df.empty and len(df[df['Status / Projection'] != 'N/A Data']) > 0:
    top_asset = df.iloc[0]
    worst_asset = df.iloc[-1]
    
    bullish_count = len(df[df['Avg Score'] > 0])
    bearish_count = len(df[df['Avg Score'] < 0])

    m1, m2, m3, m4 = st.columns(4)
    with m1:
        st.metric("🏆 Strongest Asset", top_asset['Pair'], f"{top_asset['Avg Score']:+.2f}%")
    with m2:
        st.metric("🔻 Weakest Asset", worst_asset['Pair'], f"{worst_asset['Avg Score']:+.2f}%")
    with m3:
        st.metric("🟢 Bullish Pairs", f"{bullish_count} Pairs", f"{round(bullish_count/len(df)*100)}% of total")
    with m4:
        st.metric("🔴 Bearish Pairs", f"{bearish_count} Pairs", f"{round(bearish_count/len(df)*100)}% of total")

st.markdown("<br>", unsafe_allow_html=True)

# --- DATA TABLE DISPLAY ---
st.subheader("📋 Assets Status & Pivot Levels")

if not df.empty:
    cols_to_display = [
        "Pair", "Status / Projection", 
        "S3", "S2", "S1", "Pivot", "R1", "R2", "R3"
    ]
    df_display = df[cols_to_display].copy()
    df_display.insert(0, "#", range(1, len(df_display) + 1))

    st.dataframe(
        df_display, 
        use_container_width=True, 
        height=680,
        hide_index=True
    )
else:
    st.info("No data to display. Please click 'Refresh Data Real-Time'.")