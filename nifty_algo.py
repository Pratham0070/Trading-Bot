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
    
    # Fail-safe if Yahoo blocks the GitHub Cloud IP
    if nifty.empty or vix.empty:
        print("ERROR: Yahoo Finance returned no data. Exiting safely.")
        return None

    # Safely extract columns without risking the "scalar" bug
    nifty_close = nifty['Close'].iloc[:, 0] if isinstance(nifty.columns, pd.MultiIndex) else nifty['Close']
    vix_close = vix['Close'].iloc[:, 0] if isinstance(vix.columns, pd.MultiIndex) else vix['Close']
    
    # Safely combine the columns using pd.concat
    df = pd.concat([nifty_close, vix_close], axis=1)
    df.columns = ['Nifty', 'VIX']
    
    return df.dropna()

def calculate_pillars(df):
    df['Returns'] = np.log(df['Nifty'] / df['Nifty'].shift(1))
    
    df['SMA_20'] = df['Nifty'].rolling(window=20).mean()
    df['STD_20'] = df['Nifty'].rolling(window=20).std()
    df['Z_Score'] = (df['Nifty'] - df['SMA_20']) / df['STD_20']
    
    df['VIX_Change'] = df['VIX'].diff()
    
    df['Realized_Vol_20d'] = df['Returns'].rolling(window=20).std() * np.sqrt(252) * 100
    df['Vol_Median_252d'] = df['Realized_Vol_20d'].rolling(window=252).median()
    
    df['SMA_200'] = df['Nifty'].rolling(window=200).mean()
    
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
    
    # Stop the script gracefully if data fails to download
    if df is None or df.empty:
        return
        
    df = calculate_pillars(df)
    
    # Stop if we don't have enough days to calculate the 200-day moving average
    if df.empty:
        print("Not enough historical data to calculate pillars.")
        return
        
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
    
    log_df = pd.DataFrame([record])
    
    file_exists = os.path.isfile('paper_trading_log.csv')
    log_df.to_csv('paper_trading_log.csv', mode='a', header=not file_exists, index=False)
    print("Logged to paper_trading_log.csv")

if __name__ == "__main__":
    run_bot()
