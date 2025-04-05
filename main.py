
import time
import requests
import pandas as pd
import ccxt
import os

BOT_TOKEN = os.environ['BOT_TOKEN']
CHAT_ID = os.environ['CHAT_ID']

symbols = ["BTC/USDT", "ETH/USDT"]
rsi_period = 14
stoch_period = 14
stoch_signal = 3
timeframes = {"4h": "진입", "1d": "추매"}
exchange = ccxt.binance()

def fetch_ohlcv(symbol, tf):
    ohlcv = exchange.fetch_ohlcv(symbol, tf, limit=100)
    df = pd.DataFrame(ohlcv, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
    df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
    return df

def calculate_indicators(df):
    df['low14'] = df['low'].rolling(stoch_period).min()
    df['high14'] = df['high'].rolling(stoch_period).max()
    df['%K'] = 100 * (df['close'] - df['low14']) / (df['high14'] - df['low14'])
    df['%D'] = df['%K'].rolling(stoch_signal).mean()
    delta = df['close'].diff()
    gain = delta.where(delta > 0, 0)
    loss = -delta.where(delta < 0, 0)
    avg_gain = gain.rolling(rsi_period).mean()
    avg_loss = loss.rolling(rsi_period).mean()
    rs = avg_gain / avg_loss
    df['RSI'] = 100 - (100 / (1 + rs))
    return df

def send_telegram(message):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    params = {"chat_id": CHAT_ID, "text": message}
    requests.get(url, params=params)

def check_signals():
    for symbol in symbols:
        base = symbol.replace("/USDT", "")
        for tf, signal_type in timeframes.items():
            try:
                df = fetch_ohlcv(symbol, tf)
                df = calculate_indicators(df)
                latest = df.iloc[-1]
                if latest['%K'] <= 10 and latest['RSI'] <= 10:
                    msg = f"""📥 [{base}] {signal_type} 시그널 (롱)
🕒 {tf} 기준: {latest['timestamp']}
%K: {latest['%K']:.2f}, RSI: {latest['RSI']:.2f}"""
                    send_telegram(msg)
                elif latest['%K'] >= 90 and latest['RSI'] >= 80:
                    msg = f"""📤 [{base}] {signal_type} 시그널 (숏)
🕒 {tf} 기준: {latest['timestamp']}
%K: {latest['%K']:.2f}, RSI: {latest['RSI']:.2f}"""
                    send_telegram(msg)
            except Exception as e:
                print(f"[{symbol} - {tf}] 오류 발생:", e)

if __name__ == "__main__":
    while True:
        check_signals()
        time.sleep(60 * 60 * 4)
