import yfinance as yf
import pandas as pd
import numpy as np
import datetime
import os

def fetch_data():
    # Fetch Nifty 50 and India VIX data for the last 2 years
    end_date = datetime.datetime.now()
    start_date = end_date - datetime.timedelta(days=730)
    
    print("Fetching data from Yahoo Finance...")
    nifty = yf.download('^NSEI', start=start_date, end=end_date, progress=False)
    vix = yf.download('^INDIAVIX', start=start_date, end=end_date, progress=False)
    
    # Combine closing prices
    df = pd.DataFrame({
        'Nifty': nifty['Close'],
        'VIX': vix['Close']
    }).dropna()
    
    return df

def calculate_pillars(df):
    # Daily Returns
    df['Returns'] = np.log(df['Nifty'] / df['Nifty'].shift(1))
    
    # Pillar 1: Mean Reversion (Z-Score)
    df['SMA_20'] = df['Nifty'].rolling(window=20).mean()
    df['STD_20'] = df['Nifty'].rolling(window=20).std()
    df['Z_Score'] = (df['Nifty'] - df['SMA_20']) / df['STD_20']
    
    # Pillar 2: Leverage Effect (VIX Change)
    df['VIX_Change'] = df['VIX'].diff()
    
    # Pillar 3: Volatility Clustering (Is current vol below historical median?)
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
    # Triggers (GAS PEDAL)
    is_oversold = row['Z_Score'] < -2.0
    fear_spike = row['VRP'] > (row['VRP_SMA_90'] + row['VRP_STD_90'])
    
    # Filters (BRAKES)
    safe_regime = row['Nifty'] > row['SMA_200'] # Must be in a Bull Regime
    vol_contracting = row['VIX_Change'] < 0     # VIX must be dropping today
    calm_cluster = row['Realized_Vol_20d'] < row['Vol_Median_252d']
    
    # Logic: If it is safe, and a trigger hits, BUY.
    if safe_regime and vol_contracting and calm_cluster:
        if is_oversold or fear_spike:
            return "BUY"
            
    return "HOLD"

def run_bot():
    df = fetch_data()
    df = calculate_pillars(df)
    
    # Apply logic to the most recent day
    latest_data = df.iloc[-1]
    signal = generate_signal(latest_data)
    
    # Prepare paper trading record
    record = {
        'Date': datetime.datetime.now().strftime("%Y-%m-%d"),
        'Nifty_Close': round(latest_data['Nifty'], 2),
        'VIX_Close': round(latest_data['VIX'], 2),
        'Signal': signal,
        'Action': "Bought 1 Lakh worth of NIFTYBEES" if signal == "BUY" else "No Action"
    }
    
    print(f"\n--- ALGO REPORT FOR {record['Date']} ---")
    print(f"Nifty: {record['Nifty_Close']} | VIX: {record['VIX_Close']}")
    print(f"Pillar Check: Regime Safe? {latest_data['Nifty'] > latest_data['SMA_200']}")
    print(f"SIGNAL: {record['Signal']}")
    
    # Save to CSV log
    file_exists = os.path.isfile('paper_trading_log.csv')
    log_df = pd.DataFrame([record])
    log_df.to_csv('paper_trading_log.csv', mode='a', header=not file_exists, index=False)
    print("Logged to paper_trading_log.csv")

if __name__ == "__main__":
    run_bot()