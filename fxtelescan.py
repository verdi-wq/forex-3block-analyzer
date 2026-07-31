import time
import requests
import pandas as pd
import numpy as np
import yfinance as yf
from scipy.signal import find_peaks

# ==========================================================
# KONFIGURASI TELEGRAM BOT (Ganti dengan Token & Chat ID Anda)
# ==========================================================
TELEGRAM_BOT_TOKEN = "8491294576:AAELX9hgRF9Vkta8mXHX9MlyDdvuqo6mslg"
TELEGRAM_CHAT_ID = "281122469"

def send_telegram_message(message):
    """Mengirim notifikasi teks ke Telegram"""
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": TELEGRAM_CHAT_ID,
        "text": message,
        "parse_mode": "Markdown"
    }
    try:
        requests.post(url, json=payload, timeout=10)
    except Exception as e:
        print(f"[-] Gagal mengirim pesan ke Telegram: {e}")

# ==========================================================
# DAFTAR ASSET (28 Forex Pairs + Crypto + Gold)
# ==========================================================
ASSETS = {
    "XAUUSD": "GC=F",     "BTCUSD": "BTC-USD",   "ETHUSD": "ETH-USD",
    "EURUSD": "EURUSD=X", "GBPUSD": "GBPUSD=X", "AUDUSD": "AUDUSD=X",
    "NZDUSD": "NZDUSD=X", "USDJPY": "JPY=X",    "USDCAD": "USDCAD=X",
    "USDCHF": "USDCHF=X", "EURGBP": "EURGBP=X", "EURJPY": "EURJPY=X",
    "EURCAD": "EURCAD=X", "EURAUD": "EURAUD=X", "EURNZD": "EURNZD=X",
    "EURCHF": "EURCHF=X", "GBPJPY": "GBPJPY=X", "GBPCAD": "GBPCAD=X",
    "GBPAUD": "GBPAUD=X", "GBPNZD": "GBPNZD=X", "GBPCHF": "GBPCHF=X",
    "AUDJPY": "AUDJPY=X", "AUDCAD": "AUDCAD=X", "AUDNZD": "AUDNZD=X",
    "AUDCHF": "AUDCHF=X", "NZDJPY": "NZDJPY=X", "NZDCAD": "NZDCAD=X",
    "NZDCHF": "NZDCHF=X", "CADJPY": "CADJPY=X", "CADCHF": "CADCHF=X",
    "CHFJPY": "CHFJPY=X"
}

# Menyimpan history sinyal agar tidak mengirim notifikasi ganda untuk candle yang sama
sent_signals_cache = set()

# ==========================================================
# FUNGSI INDIKATOR TEKNIKAL
# ==========================================================
def calculate_rsi(series, period=14):
    delta = series.diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
    rs = gain / loss
    return 100 - (100 / (1 + rs))

def calculate_macd(series, fast=12, slow=26, signal=9):
    ema_fast = series.ewm(span=fast, adjust=False).mean()
    ema_slow = series.ewm(span=slow, adjust=False).mean()
    macd_line = ema_fast - ema_slow
    signal_line = macd_line.ewm(span=signal, adjust=False).mean()
    return macd_line, signal_line

# ==========================================================
# FUNGSI PEMINDAIAN SINGLE ASSET
# ==========================================================
def scan_asset(pair_name, symbol):
    try:
        df_30m = yf.download(symbol, period="1mo", interval="30m", progress=False)
        df_15m = yf.download(symbol, period="5d",  interval="15m", progress=False)
        df_5m  = yf.download(symbol, period="2d",  interval="5m",  progress=False)

        if df_30m.empty or df_15m.empty or df_5m.empty:
            return None

        for df in [df_30m, df_15m, df_5m]:
            if isinstance(df.columns, pd.MultiIndex):
                df.columns = df.columns.get_level_values(0)

        # 1. TF 30m Trend
        df_30m['EMA_20'] = df_30m['Close'].ewm(span=20, adjust=False).mean()
        df_30m['EMA_50'] = df_30m['Close'].ewm(span=50, adjust=False).mean()
        close_30m = float(df_30m['Close'].iloc[-1])
        ema20_30m = float(df_30m['EMA_20'].iloc[-1])
        ema50_30m = float(df_30m['EMA_50'].iloc[-1])

        macro_trend = "NEUTRAL"
        if close_30m > ema20_30m and ema20_30m > ema50_30m:
            macro_trend = "BULLISH"
        elif close_30m < ema20_30m and ema20_30m < ema50_30m:
            macro_trend = "BEARISH"

        if macro_trend == "NEUTRAL":
            return None

        # 2. TF 15m Fibo
        distance = 12
        highs, _ = find_peaks(df_15m['High'].values, distance=distance)
        lows, _  = find_peaks(-df_15m['Low'].values, distance=distance)

        if len(highs) == 0 or len(lows) == 0:
            return None

        swing_high = float(df_15m['High'].iloc[highs[-1]])
        swing_low  = float(df_15m['Low'].iloc[lows[-1]])
        diff = swing_high - swing_low

        if df_15m.index[lows[-1]] < df_15m.index[highs[-1]]:
            fibo_trend = "UPTREND"
            fibo_50  = swing_high - 0.500 * diff
            fibo_618 = swing_high - 0.618 * diff
        else:
            fibo_trend = "DOWNTREND"
            fibo_50  = swing_low + 0.500 * diff
            fibo_618 = swing_low + 0.618 * diff

        gz_min = min(fibo_50, fibo_618)
        gz_max = max(fibo_50, fibo_618)

        # 3. TF 5m MACD & RSI
        df_5m['RSI_14'] = calculate_rsi(df_5m['Close'], period=14)
        df_5m['MACD'], df_5m['Signal'] = calculate_macd(df_5m['Close'], fast=12, slow=26, signal=9)

        price_5m   = float(df_5m['Close'].iloc[-1])
        rsi_5m     = float(df_5m['RSI_14'].iloc[-1])
        last_time  = str(df_5m.index[-1])
        
        macd_curr = df_5m['MACD'].iloc[-1]
        macd_prev = df_5m['MACD'].iloc[-2]
        sig_curr  = df_5m['Signal'].iloc[-1]
        sig_prev  = df_5m['Signal'].iloc[-2]

        bullish_cross = (macd_prev < sig_prev) and (macd_curr > sig_curr)
        bearish_cross = (macd_prev > sig_prev) and (macd_curr < sig_curr)
        in_golden_zone = (gz_min <= price_5m <= gz_max)

        signal_id = f"{pair_name}_{last_time}"

        # Evaluasi Sinyal
        if macro_trend == "BULLISH" and fibo_trend == "UPTREND" and in_golden_zone:
            if bullish_cross and rsi_5m < 50 and signal_id not in sent_signals_cache:
                stop_loss = swing_low
                risk = price_5m - stop_loss
                take_profit = price_5m + (risk * 2)
                
                sent_signals_cache.add(signal_id)
                return {
                    "pair": pair_name, "direction": "🟢 BUY",
                    "entry": round(price_5m, 5), "sl": round(stop_loss, 5), "tp": round(take_profit, 5)
                }

        elif macro_trend == "BEARISH" and fibo_trend == "DOWNTREND" and in_golden_zone:
            if bearish_cross and rsi_5m > 50 and signal_id not in sent_signals_cache:
                stop_loss = swing_high
                risk = stop_loss - price_5m
                take_profit = price_5m - (risk * 2)
                
                sent_signals_cache.add(signal_id)
                return {
                    "pair": pair_name, "direction": "🔴 SELL",
                    "entry": round(price_5m, 5), "sl": round(stop_loss, 5), "tp": round(take_profit, 5)
                }

    except Exception:
        pass

    return None

# ==========================================================
# LOOP SCANNER (Berjalan Otomatis Setiap 5 Menit)
# ==========================================================
def run_loop():
    print("[+] Trading Bot Service Aktif. Memindai pasar...")
    send_telegram_message("🚀 *Trading Bot Active!* Memindai 31 aset setiap 5 menit...")

    while True:
        for pair_name, symbol in ASSETS.items():
            sig = scan_asset(pair_name, symbol)
            if sig:
                # Format Pesan Notifikasi Telegram
                msg = (
                    f"🚨 *CONFLUENCE SIGNAL DETECTED!*\n\n"
                    f"📌 *Pair:* {sig['pair']}\n"
                    f"📈 *Direction:* {sig['direction']}\n"
                    f"💵 *Entry Price:* `{sig['entry']}`\n"
                    f"🛑 *Stop Loss:* `{sig['sl']}`\n"
                    f"🎯 *Take Profit (1:2):* `{sig['tp']}`\n\n"
                    f"⚙️ _Filtered by Multi-TF EMA + Fibo + MACD + RSI_"
                )
                send_telegram_message(msg)
                print(f"[!] Sinyal terkirim ke Telegram: {sig['pair']} {sig['direction']}")
        
        # Tunda 5 menit (300 detik) sesuai interval candle terkecil
        time.sleep(300)

if __name__ == "__main__":
    run_loop()