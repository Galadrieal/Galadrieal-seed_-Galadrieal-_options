import yfinance as yf
import pandas as pd
import datetime
import time

def get_basis(cash_ticker, fut_ticker):
    # Calculates the live premium/discount between the Index and the Futures contract
    try:
        cash_price = yf.Ticker(cash_ticker).history(period="1d")['Close'].iloc[-1]
        fut_price = yf.Ticker(fut_ticker).history(period="1d")['Close'].iloc[-1]
        basis = fut_price - cash_price
        return basis
    except Exception as e:
        print(f"Error calculating basis for {cash_ticker}: {e}")
        return 0

def process_instrument(cash_ticker, fut_ticker, prefix):
    print(f"\n--- Scanning {cash_ticker} for {fut_ticker} Levels ---")
    ticker = yf.Ticker(cash_ticker)
    expirations = ticker.options
    
    if not expirations:
        print(f"No options data found for {cash_ticker}.")
        return

    best_expiry = None
    max_volume = -1
    best_chain = None

    for exp in expirations[:15]:
        try:
            opt = ticker.option_chain(exp)
            calls, puts = opt.calls, opt.puts
            calls['volume'], puts['volume'] = calls['volume'].fillna(0), puts['volume'].fillna(0)
            
            total_vol = calls['volume'].sum() + puts['volume'].sum()
            
            if total_vol > max_volume:
                max_volume = total_vol
                best_expiry = exp
                best_chain = pd.concat([calls, puts])
        except Exception:
            pass
        time.sleep(0.5) # Prevents Yahoo Finance rate limits

    if best_chain is None: return

    print(f"Winner: {best_expiry} with {max_volume} volume.")

    # Group by Strike and get Top 10 by Open Interest
    best_chain['openInterest'] = best_chain['openInterest'].fillna(0)
    strike_oi = best_chain.groupby('strike')['openInterest'].sum().reset_index()
    top_10 = strike_oi.sort_values(by='openInterest', ascending=False).head(10)['strike'].tolist()

    # Apply Auto-Basis so levels match ES/NQ exactly
    basis = get_basis(cash_ticker, fut_ticker)
    print(f"Calculated Basis offset: {basis:.2f} points.")
    
    today_str = datetime.datetime.now().strftime("%Y-%m-%d")
    for i, strike in enumerate(top_10):
        adjusted_strike = round(strike + basis, 2)
        filename = f"{prefix}_RANK_{i+1}.csv"
        with open(filename, "w") as f:
            f.write(f"{today_str},{adjusted_strike},{adjusted_strike},{adjusted_strike},{adjusted_strike},0\n")

if __name__ == "__main__":
    process_instrument("^SPX", "ES=F", "ES")
    process_instrument("^NDX", "NQ=F", "NQ")
