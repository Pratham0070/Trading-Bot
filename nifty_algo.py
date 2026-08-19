import yfinance as yf
import pandas as pd
import numpy as np
import datetime
import os

def fetch_data():
    end_date = datetime.datetime.now()
    start_date = end_date - datetime.timedelta(days=730)
    
    print("Fetching data from Yahoo Finance...")
    nifty = yf.download('^NSEI', start=start_date, end=end_date, progress=False)
    vix = yf.download('^INDIAVIX', start=start_date, end=end_date, progress=False)
    
    # Handle both single and multi-level columns from yfinance
    if isinstance(nifty.columns, pd.MultiIndex):
        nifty_close = nifty['Close'].iloc[:, 0]
        vix_close = vix['Close'].iloc[:, 0]
    else:
        nifty_close = nifty['Close']
        vix_close = vix['Close']
    
    df = pd.DataFrame({
        'Nifty': nifty_close,
        'VIX': vix_close
    }).dropna()
    
    return df

def calculate_pillars(df):
    df['Returns'] = np.log(df['Nifty'] / df['Nifty'].shift(1))
    
    # Pillar 1: Mean Reversion (Z-Score)
    df['SMA_20'] = df['Nifty'].rolling(window=20).mean()
    df['STD_20'] = df['Nifty'].rolling(window=20).std()
    df['Z_Score'] = (df['Nifty'] - df['SMA_20']) / df['STD_20']
    
    # Pillar 2: Leverage Effect (VIX Change)
    df['VIX_Change'] = df['VIX'].diff()
    
    # Pillar 3: Volatility Clustering
    df['Realized_Vol_20d'] = df['Returns'].rolling(window=20).std() * np.sqrt(252) * 100
    df['Vol_Median_252d'] = df['Realized_Vol_20d'].rolling(window=252).median()
    
    # Pillar 4: Regime Switching (Macro Trend)
    df['SMA_200'] = df['Nifty'].rolling(window=200).mean()
    
    # Pillar 5: Volatility Risk Premium (VRP)
    df['VRP'] = df['VIX'] - df['Realized_Vol_20d']
    df['VRP_SMA_90'] = df['VRP'].rolling(window=90).mean()
    df['VRP_STD_90'] = df['VRP'].rolling(window=90).std()
    
    return df.dropna()

def generate_signal(row):
    is_oversold = float(row['Z_Score']) < -2.0
    fear_spike = float(row['VRP']) > (float(row['VRP_SMA_90']) + float(row['VRP_STD_90']))
    
    safe_regime = float(row['Nifty']) > float(row['SMA_200'])
    vol_contracting = float(row['VIX_Change']) < 0
    calm_cluster = float(row['Realized_Vol_20d']) < float(row['Vol_Median_252d'])
    
    if safe_regime and vol_contracting and calm_cluster:
        if is_oversold or fear_spike:
            return "BUY"
            
    return "HOLD"

def run_bot():
    df = fetch_data()
    df = calculate_pillars(df)
    
    latest_data = df.iloc[-1]
    signal = generate_signal(latest_data)
    
    record = {
        'Date': datetime.datetime.now().strftime("%Y-%m-%d"),
        'Nifty_Close': round(float(latest_data['Nifty']), 2),
        'VIX_Close': round(float(latest_data['VIX']), 2),
        'Signal': signal,
        'Action': "Bought 1 Lakh worth of NIFTYBEES" if signal == "BUY" else "No Action"
    }
    
    print(f"\n--- ALGO REPORT FOR {record['Date']} ---")
    print(f"Nifty: {record['Nifty_Close']} | VIX: {record['VIX_Close']}")
    print(f"SIGNAL: {record['Signal']}")
    
    # Explicitly pass index=[0] to prevent scalar value errors
    log_df = pd.DataFrame(record, index=[0])
    
    file_exists = os.path.isfile('paper_trading_log.csv')
    log_df.to_csv('paper_trading_log.csv', mode='a', header=not file_exists, index=False)
    print("Logged to paper_trading_log.csv")

if __name__ == "__main__":
    run_bot()
