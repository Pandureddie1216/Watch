# Pandu AI Trading Agent — Groww Free API Edition

## Features
- Connects to your Groww account with a Trading API access token.
- Retrieves official Groww holdings and cash positions using `/v1/holdings/user` and `/v1/positions/user`.
- Stores the access token in Windows Credential Manager via `keyring`.
- Shows portfolio holdings, average price, quantities and position details.
- Adds unofficial Yahoo Finance indicative prices/P&L where available.
- Includes a technical stock scanner and Indian market news.
- No Groww order placement or auto-trading.

## Critical free-plan limitation
Groww Free Trial includes portfolio APIs (holdings/positions) but excludes live market-data APIs (LTP, quote, OHLC), option chain/Greeks and historical candles/backtesting. This application does not bypass those restrictions. Scanner and indicative market prices come from Yahoo Finance via yfinance and may be delayed or unavailable.

## Install
1. Install Python 3.11 or 3.12 (64-bit).
2. Extract ZIP.
3. Double-click `run.bat`.
4. Dashboard opens at `http://127.0.0.1:8502`.
5. Paste your Groww Trading API Access Token in the sidebar and click Save token.
6. Open My Groww Portfolio and click Refresh Groww portfolio.

Do not paste API secrets, TOTP secrets, passwords or browser-session JWTs. If a credential has been exposed, revoke/regenerate it.


## New Holding Advisor tab
After fetching Groww holdings in the Portfolio tab, open **Holding Advisor**. For each holding it calculates:
- Invested value = quantity × Groww average purchase price
- Indicative market value = quantity × latest available Yahoo daily close
- Indicative unrealised P&L = market value − invested value
- ATR / recent-support-based stop reference and two staged upside target references
- Trend/momentum score, RSI and rule-based HOLD / REVIEW / PARTIAL PROFIT guidance
- Downloadable CSV with the calculated rows

The bullish score is not a probability of profit. The price feed is unofficial and may be delayed; it is not a Groww live quote. Levels are analytical references, not guaranteed orders or financial advice. Check the live price in Groww and consider your own risk tolerance before selling.


## New-listing support in Holding Advisor
The advisor now accepts at least 5 daily candles instead of requiring 25. It tries the NSE Yahoo symbol first and BSE symbol as a fallback. When fewer than 50 sessions exist, it labels the analysis as limited history and does not claim a reliable 50-day EMA. Newly listed shares still carry higher uncertainty; verify live prices in Groww.


## Gemini AI analyst
Enter your Gemini API key in the sidebar and click Save Gemini key. The key is stored in Windows Credential Manager. Then open the Gemini AI Analyst tab and click Run Gemini portfolio analysis. The app sends Groww holdings/positions plus available daily price/indicator data to Gemini 3.8 Flash for a written review. Gemini is the reasoning layer, not a live market feed; its API quota and billing depend on your Google AI Studio project.

## Real-time data limitation
This build still uses Yahoo Finance through yfinance for market prices. This is unofficial and may be delayed or unavailable. Gemini cannot make those prices real-time. For exchange-grade live NSE/BSE quotes, connect an authorised live market-data feed such as Groww's paid LTP/quote/OHLC API or another licensed provider.


## Gemini 503 resilience
Gemini AI Analyst now retries transient 5xx capacity errors with short waits and then falls back across supported stable Flash models: 3.8, 3.7, 3.6, 3.5 and 3.5 Flash-Lite. It does not treat 503 as an invalid API key. HTTP 429 is reported as a quota/rate-limit issue and 400/401/403 are reported separately.


## Access Pandu AI from other PCs on the same LAN
1. Keep the host Windows PC and other PCs on the same trusted Wi-Fi/LAN.
2. On the host PC, right-click `ALLOW_LAN_FIREWALL.bat` and choose **Run as administrator**. This opens TCP 8502 only for the Windows Private network profile.
3. Run `run.bat` on the host PC. It binds Streamlit to `0.0.0.0:8502`.
4. On the host PC, run `ipconfig` and note the active Wi-Fi/Ethernet **IPv4 Address**, e.g. `192.168.1.25`.
5. On another PC, open `http://192.168.1.25:8502` (replace with the host's actual IPv4 address).
6. Keep the host PC powered on, connected to the LAN, and keep the run.bat window open.

Security:
- This is LAN access only; do not configure router port forwarding or expose port 8502 to the public internet.
- Anyone on the same allowed network who can reach this app may be able to view or trigger portfolio analysis. Use only a trusted private network. Do not use public Wi-Fi.
- The Groww and Gemini keys remain stored on the host PC in Windows Credential Manager; never share them.
- If Windows marks the network Public, do not change it to Private on an untrusted network. Only use a trusted home/office LAN.
- If the host PC's IP changes, run `ipconfig` again and use the new address.
"# Watch" 
