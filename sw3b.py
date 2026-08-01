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

pivot_type = st.sidebar.selectbox(
    "Pivot Level Mode:",
    options=["Standard Pivot Level", "Fibonacci Level"],
    index=0
)

# DEFAULT EXECUTION: SELALU PROSES SELURUH PAIR
selected_display_pairs = ALL_PAIRS

# FIXED BLOCK WEIGHTS (50% Block 1, 30% Block 2, 20% Block 3)
W_B1_NORM = 0.50
W_B2_NORM = 0.30
W_B3_NORM = 0.20

# --- HELPER FUNCTIONS ---
def calculate_3block_metrics(pair_label, mode="Standard Pivot Level"):
    """Calculates % performance across 3 distinct 4-hour blocks and Pivot / Fibonacci Levels."""
    ticker = PAIR_MAP[pair_label]
    try:
        # Download data 1h untuk performance block
        data_1h = yf.download(ticker, period="5d", interval="1h", progress=False)
        
        if len(data_1h) >= 13:
            close_1h = data_1h['Close']
            high_1h = data_1h['High']
            low_1h = data_1h['Low']

            if isinstance(close_1h, pd.DataFrame):
                close_1h = close_1h.iloc[:, 0]
                high_1h = high_1h.iloc[:, 0]
                low_1h = low_1h.iloc[:, 0]

            # --- DATA HARGA PERFORMANCE ---
            p_now = close_1h.iloc[-1]
            p_4h = close_1h.iloc[-5]
            p_8h = close_1h.iloc[-9]
            p_12h = close_1h.iloc[-13]

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

            # --- PROJECTION LOGIC ---
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

            res_dict = {
                "Pair": pair_label,
                "Status / Projection": prediction,
                "Avg Score": round(avg_score, 2),
                "Block 1 (0-4h) %": round(b1_pct, 2),
                "Block 2 (4-8h) %": round(b2_pct, 2),
                "Block 3 (8-12h) %": round(b3_pct, 2)
            }

            if mode == "Standard Pivot Level":
                # High, Low, Close (4H)
                last_4h_high = high_1h.iloc[-5:].max()
                last_4h_low = low_1h.iloc[-5:].min()
                last_4h_close = p_now

                pivot = (last_4h_high + last_4h_low + last_4h_close) / 3
                r1 = (2 * pivot) - last_4h_low
                s1 = (2 * pivot) - last_4h_high
                r2 = pivot + (last_4h_high - last_4h_low)
                s2 = pivot - (last_4h_high - last_4h_low)
                r3 = last_4h_high + 2 * (pivot - last_4h_low)
                s3 = last_4h_low - 2 * (last_4h_high - pivot)

                res_dict.update({
                    "S3": f"{s3:,.{digits}f}",
                    "S2": f"{s2:,.{digits}f}",
                    "S1": f"{s1:,.{digits}f}",
                    "Pivot": f"{pivot:,.{digits}f}",
                    "R1": f"{r1:,.{digits}f}",
                    "R2": f"{r2:,.{digits}f}",
                    "R3": f"{r3:,.{digits}f}"
                })
            else:
                # Mode Fibonacci Level pada TF 15m
                data_15m = yf.download(ticker, period="3d", interval="15m", progress=False)
                if not data_15m.empty and len(data_15m) >= 96:
                    high_15m = data_15m['High']
                    low_15m = data_15m['Low']
                    if isinstance(high_15m, pd.DataFrame):
                        high_15m = high_15m.iloc[:, 0]
                        low_15m = low_15m.iloc[:, 0]
                    
                    # Swing High & Low 15m (96 bar = 24 Jam terakhir TF 15m)
                    fib_high = high_15m.iloc[-96:].max()
                    fib_low = low_15m.iloc[-96:].min()
                    diff = fib_high - fib_low

                    f_0 = fib_low
                    f_236 = fib_low + (diff * 0.236)
                    f_382 = fib_low + (diff * 0.382)
                    f_500 = fib_low + (diff * 0.500)
                    f_618 = fib_low + (diff * 0.618)
                    f_786 = fib_low + (diff * 0.786)
                    f_100 = fib_high

                    res_dict.update({
                        "0%": f"{f_0:,.{digits}f}",
                        "23.6%": f"{f_236:,.{digits}f}",
                        "38.2%": f"{f_382:,.{digits}f}",
                        "50%": f"{f_500:,.{digits}f}",
                        "61.8%": f"{f_618:,.{digits}f}",
                        "78.6%": f"{f_786:,.{digits}f}",
                        "100%": f"{f_100:,.{digits}f}"
                    })
                else:
                    for k in ["0%", "23.6%", "38.2%", "50%", "61.8%", "78.6%", "100%"]:
                        res_dict[k] = "-"

            return res_dict
    except Exception:
        pass

    fallback_dict = {
        "Pair": pair_label,
        "Status / Projection": "N/A Data",
        "Avg Score": 0.0,
        "Block 1 (0-4h) %": 0.0, "Block 2 (4-8h) %": 0.0, "Block 3 (8-12h) %": 0.0
    }
    if mode == "Standard Pivot Level":
        fallback_dict.update({"S3": "-", "S2": "-", "S1": "-", "Pivot": "-", "R1": "-", "R2": "-", "R3": "-"})
    else:
        fallback_dict.update({"0%": "-", "23.6%": "-", "38.2%": "-", "50%": "-", "61.8%": "-", "78.6%": "-", "100%": "-"})

    return fallback_dict

# --- MAIN CONTROLLER ---
if st.button("🔄 Refresh Data Real-Time") or "results_df" not in st.session_state or st.session_state.get("current_pivot_type") != pivot_type:
    st.session_state.current_pivot_type = pivot_type
    with st.spinner("Analyzing Strenght, Weakness & Pivot Levels across assets..."):
        results = [calculate_3block_metrics(pair_label, pivot_type) for pair_label in selected_display_pairs]
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
table_title = "📋 Assets Status & Pivot Levels" if pivot_type == "Standard Pivot Level" else "📋 Assets Status & Fibonacci Levels"
st.subheader(table_title)

if not df.empty:
    if pivot_type == "Standard Pivot Level":
        cols_to_display = ["Pair", "Status / Projection", "S3", "S2", "S1", "Pivot", "R1", "R2", "R3"]
    else:
        cols_to_display = ["Pair", "Status / Projection", "0%", "23.6%", "38.2%", "50%", "61.8%", "78.6%", "100%"]

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