import time
import numpy as np
import pandas as pd
import plotly.graph_objects as go
from scipy.signal import argrelextrema
import streamlit as st
import yfinance as yf

# ==========================================
# 1. LIST 30 PAIR (28 FOREX + XAUUSD + BTCUSD)
# ==========================================
SYMBOL_MAP = {
    'EURUSD': 'EURUSD=X',
    'GBPUSD': 'GBPUSD=X',
    'USDJPY': 'USDJPY=X',
    'AUDUSD': 'AUDUSD=X',
    'USDCAD': 'USDCAD=X',
    'USDCHF': 'USDCHF=X',
    'NZDUSD': 'NZDUSD=X',
    'EURGBP': 'EURGBP=X',
    'EURJPY': 'EURJPY=X',
    'GBPJPY': 'GBPJPY=X',
    'AUDJPY': 'AUDJPY=X',
    'EURAUD': 'EURAUD=X',
    'EURCAD': 'EURCAD=X',
    'EURCHF': 'EURCHF=X',
    'EURNZD': 'EURNZD=X',
    'GBPAUD': 'GBPAUD=X',
    'GBPCAD': 'GBPCAD=X',
    'GBPCHF': 'GBPCHF=X',
    'GBPNZD': 'GBPNZD=X',
    'AUDCAD': 'AUDCAD=X',
    'AUDCHF': 'AUDCHF=X',
    'AUDNZD': 'AUDNZD=X',
    'CADJPY': 'CADJPY=X',
    'CADCHF': 'CADCHF=X',
    'CHFJPY': 'CHFJPY=X',
    'NZDCAD': 'NZDCAD=X',
    'NZDCHF': 'NZDCHF=X',
    'NZDJPY': 'NZDJPY=X',
    'XAUUSD': 'GC=F',
    'BTCUSD': 'BTC-USD',
}

st.set_page_config(
    page_title='SMC Day Trading Scanner',
    layout='wide',
    page_icon='📊',
)

if 'active_signals' not in st.session_state:
    st.session_state['active_signals'] = {}


# ==========================================
# 2. FETCH DATA ENGINE
# ==========================================
@st.cache_data(ttl=300)
def fetch_pair_data(yf_ticker):
    try:
        ticker = yf.Ticker(yf_ticker)
        df_m30 = ticker.history(period='5d', interval='30m').tail(100)
        df_m15 = ticker.history(period='5d', interval='15m').tail(120)
        df_m5 = ticker.history(period='5d', interval='5m').tail(200)

        cleaned_dfs = []
        for df in [df_m30, df_m15, df_m5]:
            if df is None or df.empty:
                return None, None, None
            
            # Hapus duplikat index jika timestamp Yahoo Finance terduplikasi
            df = df[~df.index.duplicated(keep='first')].copy()
            df.reset_index(inplace=True)
            
            if 'Datetime' in df.columns:
                df.rename(columns={'Datetime': 'Date'}, inplace=True)
                
            cleaned_dfs.append(df)

        return cleaned_dfs[0], cleaned_dfs[1], cleaned_dfs[2]
    except Exception:
        return None, None, None


# ==========================================
# 3. STRUCTURE ENGINE (BOS/CHoCH)
# ==========================================
def analyze_structure(df: pd.DataFrame, order: int = 3):
    if df is None or len(df) < (order * 2 + 1):
        return df, None, None, None, None, None

    # Pastikan index selalu unik dan berupa integer 0, 1, 2...
    df = df.copy().reset_index(drop=True)

    high_idx = argrelextrema(
        df['High'].values, np.greater_equal, order=order
    )[0]
    low_idx = argrelextrema(df['Low'].values, np.less_equal, order=order)[0]

    swing_highs = df.iloc[high_idx][['High']].rename(columns={'High': 'Price'})
    swing_highs['Type'] = 'High'
    swing_lows = df.iloc[low_idx][['Low']].rename(columns={'Low': 'Price'})
    swing_lows['Type'] = 'Low'

    swings = pd.concat([swing_highs, swing_lows]).sort_index()
    
    # Buang duplikat index di tabel swings jika ada candle yang jadi high & low sekaligus
    swings = swings[~swings.index.duplicated(keep='first')]
    
    swings['Swing_Label'] = ''
    prev_high, prev_low = None, None

    for idx, row in swings.iterrows():
        p = float(row['Price'])
        if row['Type'] == 'High':
            if prev_high is not None:
                swings.loc[idx, 'Swing_Label'] = 'HH' if p > prev_high else 'LH'
            else:
                swings.loc[idx, 'Swing_Label'] = 'High'
            prev_high = p
        elif row['Type'] == 'Low':
            if prev_low is not None:
                swings.loc[idx, 'Swing_Label'] = 'HL' if p > prev_low else 'LL'
            else:
                swings.loc[idx, 'Swing_Label'] = 'Low'
            prev_low = p

    df['Swing_Label'] = swings['Swing_Label']
    df['Event'] = None

    current_trend = None
    last_hh, last_hl, last_lh, last_ll = None, None, None, None

    for i in range(len(df)):
        close_p = float(df.loc[i, 'Close'])
        label = df.loc[i, 'Swing_Label']

        if pd.notna(label):
            if label == 'HH':
                last_hh = float(df.loc[i, 'High'])
            elif label == 'HL':
                last_hl = float(df.loc[i, 'Low'])
            elif label == 'LH':
                last_lh = float(df.loc[i, 'High'])
            elif label == 'LL':
                last_ll = float(df.loc[i, 'Low'])

        if current_trend == 'UPTREND':
            if last_hh and close_p > last_hh:
                df.loc[i, 'Event'] = 'BOS (Bullish)'
                last_hh = close_p
            elif last_hl and close_p < last_hl:
                df.loc[i, 'Event'] = 'CHoCH (Bearish)'
                current_trend = 'DOWNTREND'

        elif current_trend == 'DOWNTREND':
            if last_ll and close_p < last_ll:
                df.loc[i, 'Event'] = 'BOS (Bearish)'
                last_ll = close_p
            elif last_lh and close_p > last_lh:
                df.loc[i, 'Event'] = 'CHoCH (Bullish)'
                current_trend = 'UPTREND'

        else:
            if label == 'HH':
                current_trend = 'UPTREND'
            elif label == 'LL':
                current_trend = 'DOWNTREND'

    return df, current_trend, last_hl, last_lh, last_hh, last_ll


# ==========================================
# 4. SIGNAL SCANNER & POSITION LOCKING
# ==========================================
def scan_pair_signal(display_name, yf_ticker):
    df_m30, df_m15, df_m5 = fetch_pair_data(yf_ticker)
    if df_m30 is None or df_m5 is None or df_m5.empty:
        return None

    current_price = float(df_m5.iloc[-1]['Close'])
    current_high = float(df_m5.iloc[-1]['High'])
    current_low = float(df_m5.iloc[-1]['Low'])

    # A. Unlock Check
    if display_name in st.session_state['active_signals']:
        active_sig = st.session_state['active_signals'][display_name]
        direction = active_sig['Direction']

        hit_tp, hit_sl = False, False
        if direction == 'LONG':
            if current_high >= active_sig['TP']:
                hit_tp = True
            elif current_low <= active_sig['SL']:
                hit_sl = True
        elif direction == 'SHORT':
            if current_low <= active_sig['TP']:
                hit_tp = True
            elif current_high >= active_sig['SL']:
                hit_sl = True

        if hit_tp or hit_sl:
            del st.session_state['active_signals'][display_name]
        else:
            active_sig['Current_Price'] = current_price
            active_sig['df_m30'] = df_m30
            return active_sig

    # B. Scan New Signal
    m30_df, m30_trend, _, _, _, _ = analyze_structure(df_m30, order=4)
    m15_df, _, _, _, _, _ = analyze_structure(df_m15, order=3)
    m5_df, _, m5_hl, m5_lh, m5_hh, m5_ll = analyze_structure(df_m5, order=3)

    if m5_df is None:
        return None

    m15_events = (
        m15_df.dropna(subset=['Event'])
        if m15_df is not None
        else pd.DataFrame()
    )
    m5_events = (
        m5_df.dropna(subset=['Event']) if m5_df is not None else pd.DataFrame()
    )

    last_m15_event = (
        m15_events.iloc[-1]['Event'] if len(m15_events) > 0 else None
    )
    last_m5_event = m5_events.iloc[-1]['Event'] if len(m5_events) > 0 else None

    last_m15_idx = m15_events.index[-1] if len(m15_events) > 0 else 0
    last_m5_idx = m5_events.index[-1] if len(m5_events) > 0 else 0

    m15_recent = (
        (len(m15_df) - 1 - last_m15_idx) <= 8 if m15_df is not None else False
    )
    m5_recent = (len(m5_df) - 1 - last_m5_idx) <= 5

    direction, order_type = None, None
    entry, sl, tp = None, None, None
    risk = 0

    # Bullish Logic
    if m30_trend == 'UPTREND' or (
        m15_recent and last_m15_event == 'CHoCH (Bullish)'
    ):
        if m5_recent and last_m5_event in [
            'BOS (Bullish)',
            'CHoCH (Bullish)',
        ]:
            direction = 'LONG'
            sl = (
                float(m5_hl)
                if (m5_hl is not None and float(m5_hl) < current_price)
                else current_price * 0.998
            )
            target_level = float(m5_hh) if m5_hh is not None else current_price
            diff_pct = abs(current_price - target_level) / current_price

            if diff_pct <= 0.0005:
                order_type = 'Market Order (Buy)'
                entry = current_price
            elif current_price > target_level:
                order_type = 'Limit Order (Limit Buy)'
                entry = target_level
            else:
                order_type = 'Stop Order (Stop Buy)'
                entry = target_level

            risk = entry - sl
            tp = entry + (risk * 1.5)

    # Bearish Logic
    elif m30_trend == 'DOWNTREND' or (
        m15_recent and last_m15_event == 'CHoCH (Bearish)'
    ):
        if m5_recent and last_m5_event in [
            'BOS (Bearish)',
            'CHoCH (Bearish)',
        ]:
            direction = 'SHORT'
            sl = (
                float(m5_lh)
                if (m5_lh is not None and float(m5_lh) > current_price)
                else current_price * 1.002
            )
            target_level = float(m5_ll) if m5_ll is not None else current_price
            diff_pct = abs(current_price - target_level) / current_price

            if diff_pct <= 0.0005:
                order_type = 'Market Order (Sell)'
                entry = current_price
            elif current_price < target_level:
                order_type = 'Limit Order (Limit Sell)'
                entry = target_level
            else:
                order_type = 'Stop Order (Stop Sell)'
                entry = target_level

            risk = sl - entry
            tp = entry - (risk * 1.5)

    if direction and entry and sl and tp and (risk > 0):
        sig_data = {
            'Symbol': display_name,
            'Direction': direction,
            'Order_Type': order_type,
            'Current_Price': current_price,
            'Entry': entry,
            'SL': sl,
            'TP': tp,
            'RR': '1 : 1.5',
            'df_m30': df_m30,
        }
        st.session_state['active_signals'][display_name] = sig_data
        return sig_data

    return None


# ==========================================
# 5. CHART RENDERER
# ==========================================
def render_m30_chart(sig_data):
    df_m30 = sig_data['df_m30'].copy()
    fig = go.Figure()

    fig.add_trace(
        go.Candlestick(
            x=df_m30['Date'],
            open=df_m30['Open'],
            high=df_m30['High'],
            low=df_m30['Low'],
            close=df_m30['Close'],
            name=f"{sig_data['Symbol']} M30",
        )
    )

    if 'Swing_Label' in df_m30.columns:
        swings = df_m30.dropna(subset=['Swing_Label'])
        for _, row in swings.iterrows():
            color = (
                '#00E676' if 'H' in str(row['Swing_Label']) else '#FF5252'
            )
            fig.add_annotation(
                x=row['Date'],
                y=row['High'] if 'H' in str(row['Type']) else row['Low'],
                text=f"<b>{row['Swing_Label']}</b>",
                showarrow=True,
                arrowhead=2,
                arrowcolor=color,
                font=dict(size=10, color=color),
                ax=0,
                ay=-20 if 'H' in str(row['Type']) else 20,
            )

    fig.add_hline(
        y=sig_data['Entry'],
        line_dash='dash',
        line_color='yellow',
        annotation_text=f"ENTRY: {sig_data['Entry']}",
    )
    fig.add_hline(
        y=sig_data['SL'],
        line_dash='dot',
        line_color='red',
        annotation_text=f"SL: {sig_data['SL']}",
    )
    fig.add_hline(
        y=sig_data['TP'],
        line_dash='dot',
        line_color='green',
        annotation_text=f"TP: {sig_data['TP']}",
    )

    fig.update_layout(
        title=f"Chart M30 - {sig_data['Symbol']} ({sig_data['Direction']})",
        yaxis_title='Price',
        template='plotly_dark',
        xaxis_rangeslider_visible=False,
        height=520,
    )
    st.plotly_chart(fig, use_container_width=True)


# ==========================================
# 6. FRONTEND INTERFACE
# ==========================================
st.title('⚡ SMC Day Trading Scanner')
st.caption('28 Pair Forex + XAUUSD + BTCUSD | Yahoo Finance Data | RR 1 : 1.5')

col_top1, col_top2 = st.columns([4, 1])
with col_top1:
    st.info(
        'Memindai 30 Pair... (Pair tanpa sinyal disembunyikan. Sinyal aktif dikunci sampai Hit TP/SL)'
    )
with col_top2:
    if st.button('🔄 Scan Sekarang'):
        st.cache_data.clear()
        st.rerun()

found_signals = []
progress = st.progress(0)

for idx, (display_name, yf_ticker) in enumerate(SYMBOL_MAP.items()):
    sig = scan_pair_signal(display_name, yf_ticker)
    if sig:
        found_signals.append(sig)
    progress.progress((idx + 1) / len(SYMBOL_MAP))

progress.empty()

if len(found_signals) > 0:
    st.subheader(f'📌 Sinyal Day Trading Aktif ({len(found_signals)} Pair)')

    table_data = []
    for s in found_signals:
        fmt_spec = (
            ',.2f'
            if s['Symbol'] in ['XAUUSD', 'BTCUSD'] or 'JPY' in s['Symbol']
            else ',.5f'
        )

        table_data.append({
            'Pair': s['Symbol'],
            'Direction': s['Direction'],
            'Execution Order': s['Order_Type'],
            'Current Price': format(s['Current_Price'], fmt_spec),
            'Entry Price': format(s['Entry'], fmt_spec),
            'Stop Loss (SL)': format(s['SL'], fmt_spec),
            'Take Profit (TP)': format(s['TP'], fmt_spec),
            'R : R': s['RR'],
        })

    df_display = pd.DataFrame(table_data)
    st.dataframe(df_display, use_container_width=True)

    st.markdown('---')
    st.subheader('🔍 Tampilkan Chart M30 (On-Demand)')

    selected_pair = st.selectbox(
        'Pilih Pair untuk Melihat Chart:',
        options=['-- Pilih Pair --'] + [s['Symbol'] for s in found_signals],
    )

    if selected_pair != '-- Pilih Pair --':
        target_sig = next(
            s for s in found_signals if s['Symbol'] == selected_pair
        )
        render_m30_chart(target_sig)

else:
    st.warning('Tidak ada sinyal aktif saat ini (Semua pair status Wait & See).')

st.caption('Aplikasi diperbarui otomatis setiap 30 menit.')