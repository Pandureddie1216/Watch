import streamlit as st
import requests, keyring, yfinance as yf, pandas as pd, numpy as np, feedparser, time
from datetime import datetime, time as dtime
from zoneinfo import ZoneInfo
import json

IST = ZoneInfo("Asia/Kolkata")
GROWW_BASE = "https://api.groww.in/v1"
KEYRING_SERVICE = "PanduAITradingAgent"
KEYRING_USER = "groww_access_token"

st.set_page_config(page_title="Pandu AI Trading Agent", page_icon="📈", layout="wide")
st.title("📈 Pandu AI Trading Agent")
st.caption("Groww Free API portfolio connection + alternative market data • Manual trading only")

def groww_headers(token):
    return {"Authorization": f"Bearer {token}", "Accept": "application/json", "X-API-VERSION": "1.0"}

def groww_get(path, token, params=None):
    r = requests.get(GROWW_BASE + path, headers=groww_headers(token), params=params, timeout=20)
    try:
        data = r.json()
    except Exception:
        data = {"raw": r.text[:500]}
    if r.status_code == 401:
        raise RuntimeError("Groww returned 401 Unauthorized. Your access token may be expired or invalid. Generate a fresh Trading API access token.")
    if r.status_code == 403:
        raise RuntimeError("Groww returned 403 Forbidden. Confirm the Free Trial is active and that this endpoint is included in your plan. Holdings/positions are included in Groww's free trial; live-data endpoints are not.")
    if not r.ok:
        raise RuntimeError(f"Groww API HTTP {r.status_code}: {data}")
    if isinstance(data, dict) and data.get("status") == "FAILURE":
        err = data.get("error", {})
        raise RuntimeError(f"Groww API failure: {err.get('message', data)}")
    return data

def extract_payload(data):
    return data.get("payload", data) if isinstance(data, dict) else {}

with st.sidebar:
    st.header("Groww account connection")
    saved_token = keyring.get_password(KEYRING_SERVICE, KEYRING_USER)
    token_input = st.text_input("Groww Trading API Access Token", value="", type="password",
        placeholder="Paste access token here", help="Token is saved in Windows Credential Manager. Never paste your API secret or TOTP secret.")
    c1, c2 = st.columns(2)
    save_clicked = c1.button("Save token", use_container_width=True)
    clear_clicked = c2.button("Clear", use_container_width=True)
    if save_clicked:
        if token_input.strip():
            keyring.set_password(KEYRING_SERVICE, KEYRING_USER, token_input.strip())
            st.success("Token saved in Windows Credential Manager.")
            st.rerun()
        else:
            st.warning("Paste an access token first.")
    if clear_clicked:
        try:
            keyring.delete_password(KEYRING_SERVICE, KEYRING_USER)
        except keyring.errors.PasswordDeleteError:
            pass
        st.success("Saved token cleared.")
        st.rerun()
    st.caption("Token is stored locally on this Windows PC. Groww access tokens expire; replace it when expired.")
    st.divider()
    st.header("Scanner settings")
    capital = st.number_input("Trading capital (₹)", min_value=1000, max_value=10000000, value=9000, step=500)
    risk_pct = st.slider("Risk per trade (%)", 0.25, 2.0, 1.0, 0.25)
    refresh_minutes = st.selectbox("Dashboard refresh (minutes)", [5,10,15,30], index=2)
    default_symbols = "RELIANCE.NS, HDFCBANK.NS, ICICIBANK.NS, SBIN.NS, INFY.NS, TCS.NS, LT.NS, ITC.NS, BHARTIARTL.NS, TATAMOTORS.NS, BEL.NS, TRENT.NS"
    symbols_text = st.text_area("NSE symbols", default_symbols, height=100)
    st.caption("Scanner prices are from Yahoo Finance (unofficial, potentially delayed).")

# Streamlit built-in rerun timer
try:
    from streamlit_autorefresh import st_autorefresh
    st_autorefresh(interval=refresh_minutes * 60 * 1000, key="pandu_auto_refresh")
except Exception:
    pass

token = keyring.get_password(KEYRING_SERVICE, KEYRING_USER)
if token:
    st.sidebar.success("Access token saved")
else:
    st.sidebar.warning("Groww account not connected")

st.sidebar.divider()
st.sidebar.header("Gemini AI connection")
saved_gemini_key = keyring.get_password("PanduAITradingAgent", "gemini_api_key")
gemini_key_input = st.sidebar.text_input("Gemini API key", value="", type="password", placeholder="Paste Gemini API key")
g1, g2 = st.sidebar.columns(2)
if g1.button("Save Gemini key", use_container_width=True):
    if gemini_key_input.strip():
        keyring.set_password("PanduAITradingAgent", "gemini_api_key", gemini_key_input.strip())
        st.sidebar.success("Gemini key saved securely.")
        st.rerun()
    else:
        st.sidebar.warning("Paste your Gemini API key first.")
if g2.button("Clear Gemini key", use_container_width=True):
    try:
        keyring.delete_password("PanduAITradingAgent", "gemini_api_key")
    except keyring.errors.PasswordDeleteError:
        pass
    st.rerun()
if saved_gemini_key:
    st.sidebar.success("Gemini AI connected")
else:
    st.sidebar.warning("Gemini key not configured")

tab_portfolio, tab_advisor, tab_gemini, tab_scanner, tab_news, tab_help = st.tabs(["💼 My Groww Portfolio", "🧭 Holding Advisor", "🤖 Gemini AI Analyst", "🔎 Stock Scanner", "📰 Market News", "ℹ️ Setup & Limits"])

with tab_portfolio:
    st.subheader("Your Groww holdings and positions")
    st.caption("This reads your portfolio from Groww's official portfolio endpoints. No order is placed.")
    if not token:
        st.info("Paste your Groww Trading API Access Token in the sidebar and click Save token.")
    else:
        col_a, col_b = st.columns(2)
        fetch_portfolio = st.button("Refresh Groww portfolio", type="primary")
        if "groww_holdings" not in st.session_state or fetch_portfolio:
            try:
                with st.spinner("Fetching holdings from Groww..."):
                    hdata = groww_get("/holdings/user", token)
                    pdata = groww_get("/positions/user", token, params={"segment":"CASH"})
                    hp = extract_payload(hdata)
                    pp = extract_payload(pdata)
                    st.session_state.groww_holdings = hp.get("holdings", [])
                    st.session_state.groww_positions = pp.get("positions", [])
                    st.session_state.groww_fetch_error = None
                    st.session_state.groww_fetch_time = datetime.now(IST).strftime("%d-%b-%Y %I:%M:%S %p IST")
            except Exception as e:
                st.session_state.groww_fetch_error = str(e)
        if st.session_state.get("groww_fetch_error"):
            st.error(st.session_state.groww_fetch_error)
        elif "groww_holdings" in st.session_state:
            holdings = st.session_state.groww_holdings
            positions = st.session_state.groww_positions
            st.caption(f"Last fetched: {st.session_state.get('groww_fetch_time','')}")
            hdf = pd.DataFrame(holdings)
            if hdf.empty:
                st.info("Groww's Demat holdings endpoint returned no settled equity holdings.")
                # CNC delivery positions can appear in positions before they are reflected
                # in the Demat holdings endpoint. Keep them separate and label clearly.
                cnc_positions = [x for x in positions if str(x.get("product", "")).upper() == "CNC" and float(x.get("quantity") or 0) != 0]
                if cnc_positions:
                    st.warning("However, Groww returned CNC delivery positions below. These are positions, not confirmed Demat holdings yet. They may be awaiting settlement or transfer into the Demat holdings view.")
                    cnc_df = pd.DataFrame(cnc_positions)
                    cnc_cols = [c for c in ["trading_symbol","exchange","product","quantity","net_price","net_carry_forward_quantity","net_carry_forward_price","realised_pnl","symbol_isin"] if c in cnc_df.columns]
                    cnc_view = cnc_df[cnc_cols].rename(columns={
                        "trading_symbol":"Symbol","exchange":"Exchange","product":"Product",
                        "quantity":"Net qty","net_price":"Net average price (₹)",
                        "net_carry_forward_quantity":"Carry-forward qty",
                        "net_carry_forward_price":"Carry-forward avg (₹)",
                        "realised_pnl":"Realised P&L (₹)","symbol_isin":"ISIN"
                    })
                    st.dataframe(cnc_view, use_container_width=True, hide_index=True)
                    st.caption("Check Groww app's Holdings and Orders/Positions tabs. If the purchase was made recently, wait for settlement and refresh. Do not treat this row as a confirmed demat holding.")
                else:
                    st.info("No CNC delivery positions were returned either.")
            else:
                # Preserve all returned holding fields; add unofficial estimate from Yahoo where available.
                show_cols = [c for c in ["trading_symbol","quantity","average_price","pledge_quantity","t1_quantity","demat_free_quantity","isin"] if c in hdf.columns]
                hview = hdf[show_cols].copy()
                hview.rename(columns={"trading_symbol":"Symbol","quantity":"Quantity","average_price":"Avg. buy price (₹)","pledge_quantity":"Pledged","t1_quantity":"T1 qty","demat_free_quantity":"Free qty","isin":"ISIN"}, inplace=True)
                hview["Yahoo indicative LTP (₹)"] = np.nan
                hview["Indicative P&L (₹)"] = np.nan
                for idx, row in hdf.iterrows():
                    sym = str(row.get("trading_symbol","")).strip()
                    if not sym:
                        continue
                    try:
                        hist = yf.Ticker(sym + ".NS").history(period="5d", interval="1d")
                        if not hist.empty:
                            ltp = float(hist["Close"].dropna().iloc[-1])
                            avg = float(row.get("average_price") or 0)
                            qty = float(row.get("quantity") or 0)
                            hview.loc[idx, "Yahoo indicative LTP (₹)"] = ltp
                            hview.loc[idx, "Indicative P&L (₹)"] = (ltp-avg)*qty
                    except Exception:
                        pass
                st.dataframe(hview, use_container_width=True, hide_index=True)
                st.caption("Yahoo indicative LTP/P&L is not a Groww live quote. It may be delayed or unavailable. Groww holdings quantity and average price are returned by Groww.")
                invested = sum(float(x.get("quantity") or 0)*float(x.get("average_price") or 0) for x in holdings)
                indicative_pnl = pd.to_numeric(hview.get("Indicative P&L (₹)", pd.Series(dtype=float)), errors="coerce").sum()
                m1,m2,m3 = st.columns(3)
                m1.metric("Holdings", len(holdings))
                m2.metric("Cost value", f"₹{invested:,.2f}")
                m3.metric("Indicative P&L", f"₹{indicative_pnl:,.2f}" if pd.notna(indicative_pnl) else "Unavailable")
            st.markdown("#### Current positions")
            posdf = pd.DataFrame(positions)
            if posdf.empty:
                st.info("No current cash positions returned.")
            else:
                pcols = [c for c in ["trading_symbol","exchange","product","quantity","net_price","realised_pnl","net_carry_forward_quantity"] if c in posdf.columns]
                posview = posdf[pcols].rename(columns={"trading_symbol":"Symbol","exchange":"Exchange","product":"Product","quantity":"Net qty","net_price":"Net price (₹)","realised_pnl":"Realised P&L (₹)","net_carry_forward_quantity":"Carry-forward qty"})
                st.dataframe(posview, use_container_width=True, hide_index=True)


with tab_advisor:
    st.subheader("Holding-by-holding sell, stop-loss & target advisor")
    st.caption("Uses Groww holdings quantity/average cost and Yahoo Finance daily prices. Yahoo prices may be delayed; verify the live price in Groww before acting.")
    st.warning("The 'Bullish setup score' is a rule-based technical score, NOT a probability that the stock will rise. No model can guarantee the next price move.")
    holdings_for_advisor = list(st.session_state.get("groww_holdings", []))
    # Include CNC positions absent from the Demat holdings endpoint so recent delivery
    # positions are still analysed; never duplicate symbols already in holdings.
    existing_symbols = {str(x.get("trading_symbol","")).upper() for x in holdings_for_advisor}
    for position in st.session_state.get("groww_positions", []):
        psym = str(position.get("trading_symbol","")).upper()
        if str(position.get("product","")).upper() == "CNC" and float(position.get("quantity") or 0) > 0 and psym and psym not in existing_symbols:
            holdings_for_advisor.append({
                "trading_symbol": psym,
                "quantity": position.get("quantity", 0),
                "average_price": position.get("net_price", 0),
                "isin": position.get("symbol_isin", ""),
                "_source": "CNC position (not yet in Demat holdings)"
            })
            existing_symbols.add(psym)
    if not token:
        st.info("Connect your Groww token in the sidebar, then refresh your portfolio.")
    elif not holdings_for_advisor:
        st.info("First open My Groww Portfolio and click Refresh Groww portfolio. Then return here.")
    else:
        advisor_rows = []
        with st.spinner("Calculating ATR, trend, stop-loss and targets for each holding..."):
            for holding in holdings_for_advisor:
                symbol = str(holding.get("trading_symbol") or holding.get("symbol") or "").strip().upper()
                qty = float(holding.get("quantity") or 0)
                avg = float(holding.get("average_price") or holding.get("avg_price") or 0)
                if not symbol or qty <= 0:
                    continue
                yf_symbol = symbol if symbol.endswith(".NS") or symbol.endswith(".BO") else symbol + ".NS"
                try:
                    # Newly listed stocks may not have 25 sessions yet. Try NSE first,
                    # then BSE ticker as a fallback; analyse short history cautiously.
                    hist = yf.Ticker(yf_symbol).history(period="1y", interval="1d", auto_adjust=False)
                    hist = hist.dropna(subset=["Close"]) if hist is not None else pd.DataFrame()
                    if hist.empty and symbol and not symbol.endswith(".BO"):
                        hist = yf.Ticker(symbol + ".BO").history(period="1y", interval="1d", auto_adjust=False)
                        hist = hist.dropna(subset=["Close"]) if hist is not None else pd.DataFrame()
                    if len(hist) < 5:
                        advisor_rows.append({"Symbol":symbol,"Qty":qty,"Avg Cost":avg,"Status":f"Insufficient price history ({len(hist)} daily candles; need at least 5)"})
                        continue
                    close = hist["Close"].astype(float)
                    current = float(close.iloc[-1])
                    ema_period = min(20, len(close))
                    ema20 = float(close.ewm(span=ema_period,adjust=False).mean().iloc[-1])
                    ema50 = float(close.ewm(span=50,adjust=False).mean().iloc[-1]) if len(close) >= 50 else float("nan")
                    limited_history = len(hist) < 50
                    delta = close.diff()
                    gain = delta.clip(lower=0).ewm(alpha=1/14,adjust=False).mean()
                    loss = (-delta.clip(upper=0)).ewm(alpha=1/14,adjust=False).mean()
                    rs = gain / loss.replace(0,np.nan)
                    rsi_value = float((100-(100/(1+rs))).iloc[-1])
                    tr = pd.concat([
                        hist["High"]-hist["Low"],
                        (hist["High"]-hist["Close"].shift()).abs(),
                        (hist["Low"]-hist["Close"].shift()).abs()
                    ],axis=1).max(axis=1)
                    atr_period = min(14, len(hist))
                    atr = float(tr.rolling(atr_period, min_periods=1).mean().iloc[-1])
                    if not np.isfinite(atr) or atr <= 0:
                        atr = current * 0.02
                    support20 = float(hist["Low"].tail(20).min())
                    resistance20 = float(hist["High"].tail(20).max())
                    # Long-only risk levels: volatility/support-based protective stop and staged upside references.
                    stop = max(support20 - 0.35*atr, current - 1.5*atr)
                    stop = min(stop, current*0.995)
                    risk_per_share = max(current-stop, current*0.005)
                    target1 = current + 1.5*risk_per_share
                    target2 = current + 2.5*risk_per_share
                    if resistance20 > current:
                        target1 = min(target1, resistance20)
                        target2 = max(target2, resistance20 + 0.5*atr)
                    invested = qty*avg
                    market_value = qty*current
                    pnl = market_value-invested
                    pnl_pct = ((current/avg)-1)*100 if avg > 0 else 0
                    score = 0
                    reasons=[]
                    if np.isfinite(ema50):
                        if current > ema20 > ema50:
                            score += 40; reasons.append("Price above EMA20/EMA50 trend")
                        elif current > ema20:
                            score += 20; reasons.append("Price above EMA20")
                        else:
                            reasons.append("Price below EMA20")
                    else:
                        if current > ema20:
                            score += 20; reasons.append("Price above short-history EMA")
                        else:
                            reasons.append("Price below short-history EMA")
                        reasons.append(f"Limited listing history: {len(hist)} sessions; 50-day EMA unavailable")
                    if 50 <= rsi_value <= 68:
                        score += 25; reasons.append("RSI supports momentum")
                    elif 40 <= rsi_value < 50:
                        score += 10; reasons.append("RSI is weak-neutral")
                    elif rsi_value > 68:
                        score += 10; reasons.append("Momentum strong but extended")
                    else:
                        reasons.append("RSI weak")
                    if current > float(close.iloc[-2]):
                        score += 15; reasons.append("Latest daily close positive")
                    if current >= support20 + 0.5*atr:
                        score += 10; reasons.append("Above recent 20-day support")
                    if current >= avg:
                        score += 10; reasons.append("Above your average cost")
                    if current <= stop:
                        action="SELL / REVIEW NOW"
                        timing="Stop reference breached; review immediately during market hours"
                    elif current < ema20 and current < ema50:
                        action="REDUCE / REVIEW"
                        timing="Weak trend; reassess on next trading session, don't wait blindly"
                    elif current >= target1:
                        action="BOOK PARTIAL PROFIT"
                        timing="Consider booking 25–50% near Target 1; trail stop on balance"
                    elif score >= 70:
                        action="HOLD WITH TRAILING STOP"
                        timing="Review daily; trail stop upward if price rises"
                    elif score >= 45:
                        action="HOLD / WATCH"
                        timing="Recheck after 1–3 sessions or at stop/target"
                    else:
                        action="REDUCE / REVIEW"
                        timing="Weak setup; reassess within 1–2 sessions"
                    advisor_rows.append({
                        "Symbol":symbol,"Qty":qty,"Avg Cost (₹)":avg,"Indicative LTP (₹)":current,
                        "Invested (₹)":invested,"Value (₹)":market_value,"P&L (₹)":pnl,"P&L %":pnl_pct,
                        "Stop Loss (₹)":stop,"Target 1 (₹)":target1,"Target 2 (₹)":target2,
                        "Bullish Score /100":score,"RSI":rsi_value,"Action":action,
                        "Sell timing guidance":timing,"Analysis":", ".join(reasons),
                        "Data date":str(hist.index[-1].date()),
                        "History sessions":len(hist),
                        "Data quality":("Limited history - newly listed" if limited_history else "Sufficient daily history"),
                        "Groww source":holding.get("_source", "Demat holdings")
                    })
                except Exception as exc:
                    advisor_rows.append({"Symbol":symbol,"Qty":qty,"Avg Cost (₹)":avg,"Status":f"Price data unavailable: {str(exc)[:90]}"})
                time.sleep(0.08)

        advisor_df = pd.DataFrame(advisor_rows)
        if advisor_df.empty:
            st.warning("No valid holdings were returned by Groww.")
        else:
            good = advisor_df[advisor_df["Indicative LTP (₹)"].notna()].copy() if "Indicative LTP (₹)" in advisor_df.columns else pd.DataFrame()
            if not good.empty:
                total_invested = good["Invested (₹)"].sum()
                total_value = good["Value (₹)"].sum()
                total_pnl = good["P&L (₹)"].sum()
                total_pct = (total_pnl/total_invested*100) if total_invested else 0
                k1,k2,k3,k4=st.columns(4)
                k1.metric("Analysed holdings",len(good))
                k2.metric("Invested value",f"₹{total_invested:,.2f}")
                k3.metric("Indicative market value",f"₹{total_value:,.2f}")
                k4.metric("Indicative unrealised P&L",f"₹{total_pnl:,.2f}",f"{total_pct:.2f}%")
                st.markdown("#### Complete holding calculations")
                show=good[["Symbol","Qty","Avg Cost (₹)","Indicative LTP (₹)","Invested (₹)","Value (₹)","P&L (₹)","P&L %","Stop Loss (₹)","Target 1 (₹)","Target 2 (₹)","Bullish Score /100","RSI","Action","History sessions","Data quality","Groww source"]].copy()
                st.dataframe(show.round(2),use_container_width=True,hide_index=True)
                st.markdown("#### Individual recommendations")
                for _,r in good.iterrows():
                    with st.expander(f"{r['Symbol']} — {r['Action']} | P&L {r['P&L %']:.2f}% | score {int(r['Bullish Score /100'])}/100"):
                        a,b,c,d=st.columns(4)
                        a.metric("Indicative LTP",f"₹{r['Indicative LTP (₹)']:.2f}")
                        b.metric("Stop-loss reference",f"₹{r['Stop Loss (₹)']:.2f}")
                        c.metric("Target 1",f"₹{r['Target 1 (₹)']:.2f}")
                        d.metric("Target 2",f"₹{r['Target 2 (₹)']:.2f}")
                        st.write(f"**Your holding:** {int(r['Qty']) if float(r['Qty']).is_integer() else r['Qty']} shares at average ₹{r['Avg Cost (₹)']:.2f}")
                        st.write(f"**P&L calculation:** (₹{r['Indicative LTP (₹)']:.2f} − ₹{r['Avg Cost (₹)']:.2f}) × {r['Qty']} = ₹{r['P&L (₹)']:.2f}")
                        st.write(f"**Action:** {r['Action']}")
                        st.write(f"**When to review/sell:** {r['Sell timing guidance']}")
                        st.write(f"**Technical reasons:** {r['Analysis']}")
                        st.caption(f"Daily data date: {r['Data date']}. Levels are calculated from ATR and recent support/resistance; they are references, not guaranteed execution prices.")
                csv=good.to_csv(index=False).encode("utf-8")
                st.download_button("Download full holding analysis (CSV)",csv,"pandu_holdings_analysis.csv","text/csv")
            bad=advisor_df[advisor_df.get("Indicative LTP (₹)",pd.Series(index=advisor_df.index,dtype=float)).isna()] if "Indicative LTP (₹)" in advisor_df.columns else advisor_df
            if not bad.empty:
                st.markdown("#### Holdings needing price-data attention")
                st.dataframe(bad,use_container_width=True,hide_index=True)
    st.caption("Sell timing is a rule-based review guide, not an instruction to trade at a specific time. Market gaps, liquidity, taxes, charges and personal circumstances can change outcomes.")



with tab_gemini:
    st.subheader("Gemini AI portfolio analyst")
    st.caption("Gemini interprets Groww holdings and available technical data. It is not a market-data feed.")
    st.warning("AI analysis is decision support, not a guarantee or a calibrated probability of profit. Verify live prices in Groww.")
    gemini_key = keyring.get_password("PanduAITradingAgent", "gemini_api_key")
    if not gemini_key:
        st.info("Add your Gemini API key in the left sidebar and click Save Gemini key.")
    elif not token:
        st.info("Connect Groww first so Gemini can analyse your actual holdings.")
    else:
        if st.button("Run Gemini portfolio analysis", type="primary"):
            raw_holdings = list(st.session_state.get("groww_holdings", []))
            raw_positions = list(st.session_state.get("groww_positions", []))
            seen = {str(x.get("trading_symbol","")).upper() for x in raw_holdings}
            for pos in raw_positions:
                sym = str(pos.get("trading_symbol","")).upper()
                if str(pos.get("product","")).upper() == "CNC" and float(pos.get("quantity") or 0) > 0 and sym and sym not in seen:
                    raw_holdings.append({"trading_symbol":sym,"quantity":pos.get("quantity",0),
                                         "average_price":pos.get("net_price",0),
                                         "_source":"CNC position (not yet in Demat holdings)"})
                    seen.add(sym)
            if not raw_holdings:
                st.error("No Groww holdings or CNC positions loaded. Refresh Groww portfolio first.")
            else:
                snapshot=[]
                with st.spinner("Collecting available daily price history..."):
                    for h in raw_holdings:
                        sym=str(h.get("trading_symbol") or "").upper()
                        if not sym: continue
                        qty=float(h.get("quantity") or 0)
                        avg=float(h.get("average_price") or 0)
                        ticker=sym if sym.endswith(".NS") or sym.endswith(".BO") else sym+".NS"
                        row={"symbol":sym,"quantity":qty,"average_buy_price":avg,
                             "portfolio_source":h.get("_source","Groww Demat holdings"),
                             "price_source":"Yahoo Finance/yfinance; unofficial, may be delayed"}
                        try:
                            hist=yf.Ticker(ticker).history(period="6mo",interval="1d",auto_adjust=False)
                            if hist is None or hist.empty:
                                hist=yf.Ticker(sym+".BO").history(period="6mo",interval="1d",auto_adjust=False)
                            hist=hist.dropna(subset=["Close"]) if hist is not None else pd.DataFrame()
                            if len(hist)>=2:
                                close=hist["Close"].astype(float)
                                last=float(close.iloc[-1])
                                ema20=float(close.ewm(span=min(20,len(close)),adjust=False).mean().iloc[-1])
                                delta=close.diff()
                                gain=delta.clip(lower=0).ewm(alpha=1/14,adjust=False).mean()
                                loss=(-delta.clip(upper=0)).ewm(alpha=1/14,adjust=False).mean()
                                rs=gain/loss.replace(0,np.nan)
                                rsi_val=float((100-100/(1+rs)).iloc[-1]) if pd.notna((100-100/(1+rs)).iloc[-1]) else None
                                tr=pd.concat([hist["High"]-hist["Low"],(hist["High"]-hist["Close"].shift()).abs(),(hist["Low"]-hist["Close"].shift()).abs()],axis=1).max(axis=1)
                                atr=float(tr.rolling(min(14,len(hist)),min_periods=1).mean().iloc[-1])
                                row.update({"latest_available_close":round(last,2),"last_candle_date":str(hist.index[-1].date()),
                                            "daily_candles":len(hist),"ema20":round(ema20,2),
                                            "rsi14_approx":round(rsi_val,2) if rsi_val is not None else None,
                                            "atr14_approx":round(atr,2),
                                            "estimated_market_value":round(qty*last,2),
                                            "estimated_unrealised_pnl":round((last-avg)*qty,2) if avg else None})
                            else:
                                row["price_status"]="Insufficient daily history"
                        except Exception as e:
                            row["price_status"]=str(e)[:120]
                        snapshot.append(row)
                        time.sleep(.05)

                prompt=f"""
You are a careful Indian equity portfolio analyst. Analyse this user's Groww holdings using the supplied JSON data.
Portfolio and available market snapshot:
{json.dumps(snapshot,ensure_ascii=False,default=str)}

Produce:
- Portfolio invested value, estimated market value and estimated unrealised P&L, with formulas and caveats.
- A table for every holding: quantity, average cost, latest available close and date, P&L, trend, risk, action category.
- Stop-loss reference and two staged target references only when enough data exists. Explain ATR/support method and label under 20 candles LOW CONFIDENCE.
- Action categories: HOLD, REVIEW, CONSIDER PARTIAL PROFIT, EXIT REVIEW. Never give unconditional sell orders.
- Review timing based on observable conditions. Do not invent exact sell times.
- Do not provide numeric probability of profit unless a calibrated backtest was supplied. Use qualitative confidence and explain limitations.
- Do not invent prices, news, corporate actions, citations, or missing metrics.
- State clearly that Yahoo prices are unofficial, may be delayed, and are NOT live Groww quotes.
"""
                body={"contents":[{"parts":[{"text":prompt}]}],
                      "generationConfig":{"temperature":0.2,"maxOutputTokens":6000}}
                # Stable-model fallback: a 503 means temporary serving capacity exhaustion,
                # not a bad key. Retry briefly, then move to another supported stable Flash model.
                model_chain = ["gemini-3.8-flash", "gemini-3.7-flash",
                               "gemini-3.6-flash", "gemini-3.5-flash",
                               "gemini-3.5-flash-lite"]
                try:
                    successful_payload = None
                    successful_model = None
                    failures = []
                    with st.spinner("Gemini is analysing your holdings (automatic retry and model fallback enabled)..."):
                        for model_name in model_chain:
                            model_succeeded = False
                            for attempt, wait_seconds in enumerate([0, 3, 7], start=1):
                                if wait_seconds:
                                    time.sleep(wait_seconds)
                                url = f"https://generativelanguage.googleapis.com/v1beta/models/{model_name}:generateContent"
                                try:
                                    resp=requests.post(url,params={"key":gemini_key},
                                                       headers={"Content-Type":"application/json"},
                                                       json=body,timeout=90)
                                except requests.RequestException as request_error:
                                    failures.append(f"{model_name} attempt {attempt}: {request_error}")
                                    continue
                                if resp.ok:
                                    successful_payload=resp.json()
                                    successful_model=model_name
                                    model_succeeded=True
                                    break
                                try:
                                    detail=resp.json()
                                except Exception:
                                    detail=resp.text[:1000]
                                failures.append(f"{model_name} attempt {attempt}: HTTP {resp.status_code} {detail}")
                                # Only capacity errors are automatically retried/fallen back.
                                if resp.status_code not in (500, 502, 503, 504):
                                    if resp.status_code == 429:
                                        st.error("Gemini API quota/rate limit (HTTP 429). Check Google AI Studio > Usage & limits. Switching models may not fix a project-wide quota limit.")
                                    elif resp.status_code in (400, 401, 403):
                                        st.error(f"Gemini request or API-key permission error (HTTP {resp.status_code}): {detail}")
                                    else:
                                        st.error(f"Gemini API error HTTP {resp.status_code}: {detail}")
                                    break
                            if model_succeeded:
                                break
                            # If error was non-retryable, stop rather than cycling through models.
                            if failures and not any(f.startswith(model_name) for f in failures[-1:]):
                                break
                            if failures and ("HTTP 429" in failures[-1] or "HTTP 400" in failures[-1] or "HTTP 401" in failures[-1] or "HTTP 403" in failures[-1]):
                                break

                    if successful_payload is not None:
                        parts=successful_payload.get("candidates",[{}])[0].get("content",{}).get("parts",[])
                        report="\\n".join(x.get("text","") for x in parts if x.get("text"))
                        if report:
                            st.session_state.gemini_report=report
                            st.session_state.gemini_report_time=datetime.now(IST).strftime("%d-%b-%Y %I:%M:%S %p IST")
                            st.session_state.gemini_snapshot=snapshot
                            st.session_state.gemini_model_used=successful_model
                            st.success(f"Analysis completed using {successful_model}.")
                        else:
                            st.error(f"{successful_model} returned no text: {successful_payload}")
                    else:
                        st.error("All configured Gemini Flash models were temporarily unavailable or the request could not complete. Wait a few minutes and retry. Last errors:")
                        for message in failures[-8:]:
                            st.caption(message[:700])
                except Exception as e:
                    st.error(f"Gemini analysis failed: {e}")

        if st.session_state.get("gemini_report"):
            st.caption(f"Analysis generated: {st.session_state.get('gemini_report_time','')} • Model: {st.session_state.get('gemini_model_used','unknown')}")
            st.markdown(st.session_state.gemini_report)
            with st.expander("Inspect data sent to Gemini"):
                st.json(st.session_state.get("gemini_snapshot",[]))


with tab_scanner:
    st.subheader("NSE stock scanner")
    st.caption("Rule-based setup score only. It is NOT a calibrated probability of profit.")
    symbols = []
    for raw in symbols_text.replace("\n",",").split(","):
        s=raw.strip().upper()
        if s:
            if not s.endswith(".NS") and not s.endswith(".BO"):
                s += ".NS"
            symbols.append(s)
    symbols=list(dict.fromkeys(symbols))[:50]

    def calc_rsi(s, n=14):
        d=s.diff()
        up=d.clip(lower=0).ewm(alpha=1/n, adjust=False).mean()
        dn=(-d.clip(upper=0)).ewm(alpha=1/n, adjust=False).mean()
        rs=up/dn.replace(0,np.nan)
        return 100-100/(1+rs)

    if st.button("Scan stocks now", type="primary") or "scan_table" not in st.session_state:
        out=[]
        with st.spinner("Scanning symbols using alternative market data..."):
            for sym in symbols:
                try:
                    d=yf.Ticker(sym).history(period="3mo", interval="1d")
                    if d.empty or len(d)<25: continue
                    c=d["Close"].dropna()
                    last=float(c.iloc[-1])
                    ema20=float(c.ewm(span=20,adjust=False).mean().iloc[-1])
                    ema50=float(c.ewm(span=50,adjust=False).mean().iloc[-1])
                    rsi=float(calc_rsi(c).iloc[-1])
                    v=d["Volume"].fillna(0)
                    vr=float(v.iloc[-1]/v.iloc[-21:-1].mean()) if len(v)>21 and v.iloc[-21:-1].mean()>0 else 0
                    score=0; reasons=[]
                    if last>ema20>ema50: score+=35; reasons.append("Daily trend bullish")
                    if 50<=rsi<=68: score+=25; reasons.append("RSI momentum zone")
                    elif 68<rsi<75: score+=10; reasons.append("RSI elevated")
                    if vr>=1.5: score+=25; reasons.append("Volume expansion")
                    elif vr>=1.1: score+=12; reasons.append("Above-average volume")
                    if c.iloc[-1]>c.iloc[-2]: score+=15; reasons.append("Positive daily candle")
                    tr=pd.concat([d["High"]-d["Low"],(d["High"]-d["Close"].shift()).abs(),(d["Low"]-d["Close"].shift()).abs()],axis=1).max(axis=1)
                    atr=float(tr.rolling(14).mean().iloc[-1])
                    if not np.isfinite(atr) or atr<=0: atr=last*.015
                    stop=last-atr; target=last+1.5*atr
                    qty=min(int((capital*risk_pct/100)/max(last-stop,.01)),int(capital/last))
                    out.append({"Symbol":sym.replace(".NS","").replace(".BO",""),"Score":score,"Setup":"WATCH BUY" if score>=70 else ("WAIT" if score>=45 else "AVOID"),"Last close (₹)":last,"RSI":rsi,"Volume x":vr,"Indicative entry (₹)":last,"Stop (₹)":stop,"Target (₹)":target,"Qty*":qty,"Reasons":"; ".join(reasons)})
                except Exception:
                    pass
                time.sleep(.05)
        st.session_state.scan_table=pd.DataFrame(out).sort_values("Score",ascending=False) if out else pd.DataFrame()
    result=st.session_state.get("scan_table",pd.DataFrame())
    if result.empty:
        st.warning("No scan results yet. Check internet access or ticker symbols.")
    else:
        st.dataframe(result.drop(columns=["Reasons"]),use_container_width=True,hide_index=True)
        for _,r in result[result["Setup"]=="WATCH BUY"].head(5).iterrows():
            with st.expander(f"{r['Symbol']} — score {r['Score']}/100"):
                st.write(r["Reasons"])
                st.write(f"Indicative entry ₹{r['Indicative entry (₹)']:.2f} | Stop ₹{r['Stop (₹)']:.2f} | Target ₹{r['Target (₹)']:.2f} | Qty {r['Qty*']}")
    st.caption("Prices are based on Yahoo Finance daily closes, not live Groww quotes. Confirm current prices in Groww before any manual order.")

with tab_news:
    st.subheader("Indian stock market news")
    try:
        feed=feedparser.parse("https://news.google.com/rss/search?q=Indian+stock+market+NSE+stocks+earnings+when:1d&hl=en-IN&gl=IN&ceid=IN:en")
        for e in feed.entries[:15]:
            st.markdown(f"- [{e.title}]({e.link})")
        if not feed.entries: st.info("No news items returned.")
    except Exception as e:
        st.warning(str(e))

with tab_help:
    st.subheader("Connect your Groww Free API")
    st.markdown("""
1. In Groww, open **Profile / Trading APIs** and generate a **Trading API Access Token** under your active Free Trial.
2. Paste only that access token into the sidebar field and click **Save token**.
3. Open **My Groww Portfolio** and click **Refresh Groww portfolio**.
4. Token is stored locally using Windows Credential Manager through Python `keyring`.

**Never paste your API secret, TOTP secret, password, or browser JWT into this app or a chat.** If any credential was shared publicly, revoke/regenerate it.

### Free-plan limits
- Groww Free Trial portfolio endpoints include holdings and positions.
- Groww Free Trial does not include live LTP, quote, OHLC, option-chain, Greeks or historical candle APIs.
- The scanner and indicative holding valuation use Yahoo Finance via yfinance. It is unofficial and can be delayed or stale.
- No automatic order placement is implemented. Use Groww app manually.
""")
    st.markdown("[Groww Portfolio API docs](https://groww.in/trade-api/docs/curl/portfolio) · [Groww Live Data docs](https://groww.in/trade-api/docs/curl/live-data)")
