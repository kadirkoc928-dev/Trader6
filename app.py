import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from datetime import datetime
import ta
from concurrent.futures import ThreadPoolExecutor, as_completed
import time
import warnings
warnings.filterwarnings('ignore')

st.set_page_config(page_title="TradeScanner Pro", page_icon="📊", layout="wide")

st.markdown("""
<style>
    .stButton > button {
        width: 100%; background-color: #00ff88; color: black;
        font-weight: bold; border: none; padding: 15px; border-radius: 10px; font-size: 18px;
    }
    .stButton > button:hover { background-color: #00cc6a; }
</style>
""", unsafe_allow_html=True)

# SIDEBAR
st.sidebar.title("📊 TradeScanner Pro")
st.sidebar.markdown("---")

mode = st.sidebar.radio("Modus:", ["📈 Einzelanalyse", "🔎 Market Scanner"], index=1)

if mode == "📈 Einzelanalyse":
    ticker_input = st.sidebar.text_input("Ticker:", value="AAPL").upper()
    period = st.sidebar.selectbox("Zeitraum:", ["1mo", "3mo", "6mo", "1y"], index=1)
else:
    st.sidebar.subheader("🎯 Scanner-Typ")
    scanner_type = st.sidebar.radio(
        "Wähle Modus:",
        ["⚡ Quick Scan (Top 100)", "📊 Standard Scan (ALLE)", "💾 Watchlist Scan"],
        index=0
    )
    
    if scanner_type == "💾 Watchlist Scan":
        if 'user_watchlist' not in st.session_state or len(st.session_state.user_watchlist) == 0:
            st.sidebar.warning("⚠️ Watchlist ist leer!")
    
    st.sidebar.markdown("---")
    st.sidebar.subheader("🎯 Filter-Preset")
    
    filter_preset = st.sidebar.selectbox(
        "Wähle Preset:",
        ["📊 Moderat (60+)", "✅ Gut (70+)", "🏆 Exzellent (80+)", "🔧 Eigene Einstellungen"],
        index=0
    )
    
    if filter_preset == "📊 Moderat (60+)":
        min_swing_score = 60
        min_volume = 1000000
        rsi_min = 30
        rsi_max = 75
        adx_min = 15
        volume_surge_min = 0.8
        require_sma_above = False
        require_macd_bullish = False
    elif filter_preset == "✅ Gut (70+)":
        min_swing_score = 70
        min_volume = 5000000
        rsi_min = 40
        rsi_max = 65
        adx_min = 25
        volume_surge_min = 1.2
        require_sma_above = True
        require_macd_bullish = True
    elif filter_preset == "🏆 Exzellent (80+)":
        min_swing_score = 80
        min_volume = 10000000
        rsi_min = 45
        rsi_max = 60
        adx_min = 30
        volume_surge_min = 1.5
        require_sma_above = True
        require_macd_bullish = True
    else:
        min_swing_score = st.sidebar.slider("Min. Swing-Score:", 0, 100, 50)
        min_volume = st.sidebar.number_input("Min. Volumen ($):", 0, 1000000000, 1000000, 500000)
        rsi_min = st.sidebar.slider("RSI Min:", 0, 100, 30)
        rsi_max = st.sidebar.slider("RSI Max:", 0, 100, 75)
        adx_min = st.sidebar.slider("ADX Min:", 0, 100, 15)
        volume_surge_min = st.sidebar.slider("Vol Ratio:", 0.5, 5.0, 0.8)
        require_sma_above = st.sidebar.checkbox("Kurs > SMA20", value=False)
        require_macd_bullish = st.sidebar.checkbox("MACD bullisch", value=False)
    
    max_price = 10000.0
    
    # Watchlist
    st.sidebar.markdown("---")
    st.sidebar.subheader("💾 Watchlist")
    if 'user_watchlist' not in st.session_state:
        st.session_state.user_watchlist = []
    
    new_ticker = st.sidebar.text_input("Ticker hinzufügen:", key="wl_input").upper()
    if st.sidebar.button("➕ Hinzufügen"):
        if new_ticker and new_ticker not in st.session_state.user_watchlist:
            st.session_state.user_watchlist.append(new_ticker)
            st.sidebar.success("✅ " + str(new_ticker))
    
    if st.session_state.user_watchlist:
        st.sidebar.markdown("**" + str(len(st.session_state.user_watchlist)) + " Ticker**")
        if st.sidebar.button("🗑️ Leeren"):
            st.session_state.user_watchlist = []
            st.rerun()
    
    if st.sidebar.button("🗑️ Cache leeren"):
        st.cache_data.clear()
        st.success("✅ Cache geleert!")
        time.sleep(1)
        st.rerun()

st.sidebar.markdown("---")
st.sidebar.caption("⚠️ Keine Finanzberatung!")
st.sidebar.caption("📊 Yahoo Finance (verzögert)")# =============================================
# ALLE TICKER (S&P 500 + NASDAQ 100 + Russell 2000 + DAX 40)
# =============================================
@st.cache_data(ttl=86400)
def get_all_tickers():
    SP500 = ["A","AAL","AAPL","ABBV","ABNB","ABT","ACGL","ACN","ADBE","ADI","ADM","ADP","ADSK","AEE","AEP","AES","AFL","AIG","AIZ","AJG","AKAM","ALB","ALGN","ALK","ALL","ALLE","AMAT","AMCR","AMD","AME","AMGN","AMP","AMT","AMZN","ANET","ANSS","AON","AOS","APA","APD","APH","APTV","ARE","ATO","AVB","AVGO","AVY","AWK","AXP","AZO","BA","BAC","BALL","BAX","BBWI","BBY","BDX","BEN","BF.B","BG","BIIB","BIO","BK","BKNG","BKR","BLDR","BLK","BMY","BR","BRK.B","BRO","BSX","BWA","BXP","C","CAG","CAH","CARR","CAT","CB","CBOE","CBRE","CCI","CCL","CDNS","CDW","CE","CEG","CF","CFG","CHD","CHRW","CHTR","CI","CINF","CL","CLX","CMA","CMCSA","CME","CMG","CMI","CMS","CNC","CNP","COF","COO","COP","COR","COST","CPAY","CPB","CPRT","CPT","CRL","CRM","CSCO","CSGP","CSX","CTAS","CTLT","CTRA","CTSH","CTVA","CVS","CVX","CZR","D","DAL","DD","DE","DFS","DG","DGX","DHI","DHR","DIS","DLR","DLTR","DOV","DOW","DPZ","DRI","DTE","DUK","DVA","DVN","DXCM","EA","EBAY","ECL","ED","EFX","EIX","EL","ELV","EMN","EMR","ENPH","EOG","EPAM","EQIX","EQR","EQT","ES","ESS","ETN","ETR","ETSY","EVRG","EW","EXC","EXPD","EXPE","EXR","F","FANG","FAST","FCX","FDS","FDX","FE","FFIV","FICO","FIS","FITB","FMC","FOX","FOXA","FRT","FSLR","FTNT","FTV","GD","GE","GEHC","GEN","GILD","GIS","GL","GLW","GM","GNRC","GOOG","GOOGL","GPC","GPN","GRMN","GS","GWW","HAL","HAS","HBAN","HCA","HD","HES","HIG","HII","HLT","HOLX","HON","HPE","HPQ","HRL","HSIC","HST","HSY","HUBB","HUM","HWM","IBM","ICE","IDXX","IEX","IFF","ILMN","INCY","INTC","INTU","INVH","IP","IPG","IQV","IR","IRM","ISRG","IT","ITW","IVZ","J","JBHT","JBL","JCI","JKHY","JNJ","JNPR","JPM","K","KDP","KEY","KEYS","KHC","KIM","KLAC","KMB","KMI","KMX","KO","KR","KVUE","L","LDOS","LEN","LH","LHX","LIN","LKQ","LLY","LMT","LNC","LNT","LOW","LRCX","LULU","LUV","LVS","LW","LYB","LYV","MA","MAA","MAR","MAS","MCD","MCHP","MCK","MCO","MDLZ","MDT","MET","META","MGM","MHK","MKC","MLM","MMC","MMM","MNST","MO","MOH","MOS","MPC","MPWR","MRK","MRNA","MRO","MS","MSCI","MSFT","MSI","MTB","MTCH","MTD","MU","NCLH","NDAQ","NDSN","NEE","NEM","NFLX","NI","NKE","NOC","NOW","NRG","NSC","NTAP","NTRS","NUE","NVDA","NVR","NWL","NWS","NWSA","NXPI","O","ODFL","OKE","OMC","ON","ORCL","ORLY","OTIS","OXY","PANW","PARA","PAYC","PAYX","PCAR","PCG","PEG","PEP","PFE","PFG","PG","PGR","PH","PHM","PKG","PLD","PM","PNC","PNR","PNW","PODD","POOL","PPG","PPL","PRU","PSA","PSX","PTC","PWR","PYPL","QCOM","QRVO","RCL","REG","REGN","RF","RHI","RJF","RL","RMD","ROK","ROL","ROP","ROST","RSG","RTX","RVTY","SBAC","SBUX","SCHW","SHW","SJM","SLB","SMCI","SNA","SNPS","SO","SPG","SPGI","SRE","STE","STLD","STT","STX","STZ","SWK","SWKS","SYF","SYK","SYY","T","TAP","TDG","TDY","TECH","TEL","TER","TFC","TFX","TGT","TJX","TMO","TMUS","TPR","TRGP","TRMB","TROW","TRV","TSCO","TSLA","TSN","TT","TTWO","TXN","TXT","TYL","UA","UAL","UBER","UDR","UHS","ULTA","UNH","UNP","UPS","URI","USB","V","VFC","VICI","VLO","VLTO","VMC","VRSK","VRSN","VRTX","VTR","VTRS","VZ","WAB","WAT","WBA","WBD","WDC","WEC","WELL","WFC","WHR","WM","WMB","WMT","WRB","WST","WTW","WY","WYNN","XEL","XOM","XRAY","XYL","YUM","ZBH","ZBRA","ZION","ZTS"]
    NASDAQ100 = ["AAPL","ABNB","ADBE","ADI","ADP","ADSK","AEP","AMAT","AMD","AMGN","AMZN","ANSS","ASML","AVGO","AZN","BIIB","BKNG","BKR","CDNS","CDW","CEG","CHTR","CMCSA","COST","CPRT","CRWD","CSCO","CSGP","CSX","CTAS","CTSH","DASH","DDOG","DLTR","DXCM","EA","EBAY","EXC","FANG","FAST","FTNT","GEHC","GFS","GILD","GOOG","GOOGL","HON","IDXX","ILMN","INTC","INTU","ISRG","JD","KDP","KHC","KLAC","LRCX","LULU","MAR","MCHP","MDB","MDLZ","MELI","META","MNST","MRNA","MRVL","MSFT","MU","NFLX","NVDA","NXPI","ODFL","ON","ORLY","PANW","PAYX","PCAR","PDD","PEP","PYPL","QCOM","REGN","ROP","ROST","SBUX","SGEN","SIRI","SNPS","SPLK","SWKS","TEAM","TMUS","TSLA","TXN","VRSK","VRTX","WBA","WBD","WDAY","XEL","ZS"]
    RUSSELL = ["AAON","AAN","AAWW","ABCB","ABG","ABM","ABR","ACAD","ACCD","ACCO","ACEL","ACHC","ACIW","ACLS","ACMR","ACRE","ACT","ACVA","ADMA","ADNT","ADUS","AEIS","AEO","AGIO","AGM","AGNC","AGX","AHCO","AHH","AIRS","AIT","AIZ","AJRD","AKR","AL","ALEX","ALG","ALGT","ALHC","ALIT","ALK","ALKS","ALLO","ALPN","ALRM","ALSN","ALTR","AM","AMBA","AMBC","AMCX","AMED","AMK","AMKR","AMN","AMPH","AMPY","AMR","AMRC","AMRX","AMSC","AMSF","AMSWA","AMTB","AMWD","AN","ANAB","ANDE","ANF","ANGO","ANIP","ANNX","AORT","AOSL","APAM","APG","APLE","APLS","APO","APOG","APPF","APPN","APPS","AR","ARAY","ARCB","ARCH","ARCO","ARDX","ARI","ARIS","ARLO","AROC","ARR","ARRY","ARTNA","ARVN","ARW","ARWR","ASAN","ASB","ASGN","ASH","ASIX","ASLE","ASO","ASPN","ASTE","ATEC","ATEN","ATEX","ATGE","ATKR","ATR","ATRC","ATRI","ATRO","ATSG","ATUS","AUB","AUPH","AUR","AVA","AVAV","AVD","AVDX","AVNS","AVNT","AVNW","AVO","AVT","AVXL","AWR","AX","AXGN","AXL","AXNX","AXON","AXSM","AZEK","AZTA","AZZ","B","BANC","BAND","BANF","BANR","BARK","BASE","BBSI","BC","BCC","BCO","BCPC","BDC","BE","BEAM","BECN","BERY","BFH","BFS","BGCP","BGS","BGSF","BH","BHB","BHE","BHF","BHLB","BIG","BIGC","BILL","BIO","BIPC","BIVI","BJRI","BKD","BKE","BKH","BKU","BL","BLBD","BLDR","BLFS","BLKB","BLMN","BLNK","BMBL","BMEA","BMI","BMRC","BMRN","BMY","BNL","BOC","BOH","BOOM","BOOT","BORR","BOX","BPOP","BRBR","BRC","BRCC","BRKL","BRP","BRSP","BRT","BRX","BRY","BSIG","BSRR","BSVN","BTBT","BTU","BUSE","BV","BWA","BWXT","BXMT","BXP","BY","BYD","BYON","BZH","CABA","CAC","CADE","CAKE","CAL","CALM","CALX","CAMP","CAPL","CARA","CARG","CARR","CARS","CASH","CASS","CATC","CATO","CATY","CBAN","CBB","CBRE","CBT","CBU","CBZ","CC","CCBG","CCCS","CCF","CCNE","CCO","CCOI","CCRN","CCS","CD","CDE","CDLX","CDNA","CDP","CDRE","CDXS","CE","CECO","CEIX","CENT","CENTA","CENX","CEPU","CERE","CERT","CFB","CFFN","CFR","CG","CGEM","CGTX","CHCO","CHCT","CHE","CHEF","CHGG","CHH","CHMG","CHRD","CHRS","CHRW","CHTR","CHUY","CHWY","CHX","CIEN","CIM","CINF","CIR","CIVI","CIX","CLAR","CLB","CLBK","CLDT","CLDX","CLF","CLFD","CLH","CLNE","CLOV","CLPR","CLR","CLS","CLSK","CLVT","CLW","CM","CMA","CMBM","CMC","CMCO","CME","CMP","CMPR","CMRE","CMRX","CMS","CNA","CNC","CNDT","CNK","CNM","CNMD","CNNE","CNO","CNOB","CNS","CNSL","CNTY","CNX","CNXC","CNXN","COCO","CODI","COFS","COGT","COHN","COHU","COKE","COLB","COLD","COLL","COMM","COMP","COOK","COOP","CORT","COUR","CPE","CPF","CPK","CPRX","CPSI","CPSS","CR","CRAI","CRBG","CRBK","CRC","CRDO","CRGE","CRGY","CRI","CRK","CRL","CRM","CRMT","CRNC","CRNX","CRS","CRSP","CRSR","CRVL","CRWD","CS","CSGS","CSR","CSTL","CSTM","CSV","CSWC","CTBI","CTGO","CTKB","CTLP","CTLT","CTO","CTOS","CTRA","CTRE","CTRN","CTS","CTSH","CUBI","CUE","CUZ","CVBF","CVCO","CVE","CVGI","CVGW","CVI","CVLG","CVLT","CVNA","CVRX","CVT","CW","CWAN","CWH","CWK","CWST","CXM","CXW","CYBR","CYH","CYT","CYTH","CYTK","CZFS","CZNC","CZR","D","DAKT","DAL","DAN","DAR","DAVA","DBD","DBI","DBRG","DCBO","DCGO","DCO","DCOM","DDD","DEA","DEI","DEN","DENN","DFH","DFIN","DFS","DGICA","DGII","DHC","DHIL","DIN","DIOD","DISH","DK","DKS","DLB","DLHC","DLR","DLTH","DLX","DM","DMRC","DNB","DNLI","DNOW","DNUT","DOC","DOCN","DOCS","DOLE","DOMO","DOOR","DORM","DOUG","DOV","DOX","DRH","DRI","DRQ","DRVN","DSGN","DSGR","DSKE","DSP","DT","DTE","DTM","DUK","DUNE","DUOL","DV","DVA","DVAX","DVN","DX","DXC","DXCM","DXPE","DY","DYN","EAF","EAT","EB","EBC","EBF","EBS","ECPG","ECVT","EDIT","EE","EEFT","EEX","EFC","EFSC","EGAN","EGBN","EGHT","EGLE","EGP","EGRX","EGY","EHAB","EHC","EIG","EJH","ELAN","ELF","ELVN","EMBC","EME","EML","EMN","ENFN","ENOV","ENR","ENS","ENSG","ENTA","ENTG","ENV","ENVA","ENVB","ENZ","EOLS","EP","EPAC","EPC","EPM","EPR","EPRT","EQBK","EQC","EQH","EQT","ERAS","ERII","ERJ","ERM","ESAB","ESCA","ESE","ESGR","ESI","ESNT","ESPR","ESQ","ESRT","ESS","ESTA","ESTC","ESTE","ET","ETD","ETNB","ETRN","ETSY","ETWO","EURN","EVA","EVC","EVCM","EVER","EVEX","EVGO","EVH","EVLV","EVO","EVOP","EVRI","EVTC","EW","EWBC","EWCZ","EWTX","EXAS","EXC","EXEL","EXFY","EXK","EXLS","EXPD","EXPE","EXPI","EXPO","EXR","EXTR","EYE","EYEN","EYPT","F","FA","FARO","FAST","FATE","FBK","FBMS","FBNC","FBP","FBRT","FC","FCBC","FCEL","FCF","FCFS","FCN","FCX","FDP","FDUS","FE","FELE","FENC","FER","FF","FFBC","FFIC","FFIN","FFIV","FFWM","FG","FGBI","FHB","FHI","FHL","FHTX","FI","FIBK","FICO","FIGS","FINW","FIP","FIS","FISI","FITB","FIVE","FIVN","FIX","FIZZ","FL","FLGT","FLIC","FLL","FLNC","FLNG","FLR","FLS","FLT","FLWS","FLYW","FMAO","FMBH","FMC","FMNB","FMS","FMTX","FN","FNA","FNB","FND","FNF","FNKO","FNLC","FNV","FNWB","FOCS","FOLD","FOR","FORA","FORD","FORM","FORR","FOSL","FOUR","FOX","FOXA","FOXF","FPI","FR","FRA","FRAF","FRBA","FRBK","FRC","FREE","FREQ","FRG","FRGE","FRGI","FRHC","FROG","FRPH","FRPT","FRSH","FRST","FRSX","FRT","FSBC","FSBW","FSEA","FSFG","FSK","FSLR","FSM","FSP","FSS","FSTR","FT","FTAI","FTC","FTCI","FTDR","FTEK","FTFT","FTHM","FTK","FTNT","FTRE","FTS","FTV","FUBO","FUL","FULT","FUN","FUNC","FUSN","FUTU","FVCB","FVRR","FWONA","FWRD","FWRG","FXNC"]
    DAX40 = ["ADS.DE","AIR.DE","ALV.DE","BAS.DE","BAYN.DE","BMW.DE","BNR.DE","CBK.DE","CON.DE","DTE.DE","DBK.DE","DB1.DE","DPW.DE","DRW3.DE","EOAN.DE","FRE.DE","FME.DE","HEI.DE","HEN3.DE","IFX.DE","LIN.DE","MBG.DE","MRK.DE","MTX.DE","MUV2.DE","PAH3.DE","PUM.DE","QIA.DE","RWE.DE","SAP.DE","SIE.DE","SRT3.DE","VOW3.DE","VNA.DE","ZAL.DE","SY1.DE","HFG.DE","SHL.DE","BOSS.DE","EVT.DE"]
    
    all_tickers = SP500.copy()
    for t in NASDAQ100:
        if t not in all_tickers: all_tickers.append(t)
    for t in RUSSELL:
        if t not in all_tickers: all_tickers.append(t)
    for t in DAX40:
        if t not in all_tickers: all_tickers.append(t)
    return all_tickers

# INDIKATOREN
def calc_indicators(df):
    if len(df) < 20: return None
    try:
        df['SMA_20'] = ta.trend.sma_indicator(df['Close'], window=20)
        df['SMA_50'] = ta.trend.sma_indicator(df['Close'], window=50)
        df['ADX'] = ta.trend.adx(df['High'], df['Low'], df['Close'], window=14)
        df['ATR'] = ta.volatility.average_true_range(df['High'], df['Low'], df['Close'], window=14)
        df['RSI'] = ta.momentum.rsi(df['Close'], window=14)
        df['MACD'] = ta.trend.macd(df['Close'])
        df['MACD_signal'] = ta.trend.macd_signal(df['Close'])
        df['MACD_hist'] = ta.trend.macd_diff(df['Close'])
        df['Volume_SMA'] = df['Volume'].rolling(window=20).mean()
        df['Volume_Ratio'] = df['Volume'] / df['Volume_SMA']
        return df
    except:
        return None

def swing_score(df):
    if df is None or len(df) < 20: return 0
    try:
        latest = df.iloc[-1]
        score = 0
        if pd.notna(latest.get('SMA_20')) and pd.notna(latest.get('SMA_50')):
            if latest['SMA_20'] > latest['SMA_50']: score += 15
            if latest['Close'] > latest['SMA_20']: score += 10
            if latest['Close'] > latest['SMA_50']: score += 5
        if pd.notna(latest.get('ADX')):
            adx = latest['ADX']
            if adx > 40: score += 25
            elif adx > 30: score += 20
            elif adx > 25: score += 15
            elif adx > 20: score += 10
            elif adx > 15: score += 5
            else: score += 2
        if pd.notna(latest.get('RSI')):
            rsi = latest['RSI']
            if 45 <= rsi <= 60: score += 20
            elif 40 <= rsi <= 70: score += 15
            elif 30 <= rsi <= 75: score += 10
            else: score += 5
        if pd.notna(latest.get('Volume_Ratio')):
            vr = latest['Volume_Ratio']
            if 1.2 <= vr <= 2.5: score += 15
            elif 1.0 <= vr <= 3.0: score += 10
            elif vr > 0.7: score += 5
            else: score += 2
        if pd.notna(latest.get('MACD')) and pd.notna(latest.get('MACD_signal')):
            if latest['MACD'] > latest['MACD_signal']: score += 7
            if latest['MACD'] > 0: score += 3
        return min(100, score)
    except:
        return 0

def tv_link(ticker):
    u = ticker.upper()
    if '.DE' in u: e, c = "XETR", u.replace('.DE','')
    else: e, c = "NASDAQ", u
    return "https://www.tradingview.com/chart/?symbol=" + e + "%3A" + c + "&interval=D"

def scan_one(ticker):
    try:
        s = yf.Ticker(ticker)
        df = s.history(period="3mo", interval="1d")
        if df.empty or len(df) < 20: return None
        avg_v = df['Volume'].tail(20).mean()
        price = df['Close'].iloc[-1]
        dv = avg_v * price
        if dv < 500000: return None
        df = calc_indicators(df)
        if df is None: return None
        score = swing_score(df)
        latest = df.iloc[-1]
        try:
            name = s.info.get('shortName', ticker)
            if name is None: name = ticker
        except:
            name = ticker
        rsi_v = latest.get('RSI', 50)
        if pd.isna(rsi_v): rsi_v = 50
        adx_v = latest.get('ADX', 20)
        if pd.isna(adx_v): adx_v = 20
        vr_v = latest.get('Volume_Ratio', 1.0)
        if pd.isna(vr_v): vr_v = 1.0
        atr_v = latest.get('ATR', 0)
        if pd.isna(atr_v) or price == 0: atr_p = 2.0
        else: atr_p = (atr_v / price) * 100
        sma_v = latest.get('SMA_20')
        if pd.isna(sma_v): sma_s = 'N/A'
        else: sma_s = 'Above' if price > sma_v else 'Below'
        macd = latest.get('MACD')
        macd_s = latest.get('MACD_signal')
        if pd.isna(macd) or pd.isna(macd_s): macd_st = 'N/A'
        else: macd_st = 'Bullish' if macd > macd_s else 'Bearish'
        return {
            'Ticker': ticker, 'Name': str(name)[:50], 'Preis': round(price, 2),
            'Swing-Score': score, 'RSI': round(rsi_v, 1), 'ADX': round(adx_v, 1),
            'Vol Ratio': round(vr_v, 2), 'ATR%': round(atr_p, 2),
            'SMA20': sma_s, 'MACD': macd_st,
            'Volumen': round(dv, 0),
'Chart': tv_link(ticker)
        }
    except:
        return None

def run_scan(tickers, max_workers=10):
    results = []
    progress_bar = st.progress(0)
    status_text = st.empty()
    total = len(tickers)
    completed = 0
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = {executor.submit(scan_one, t): t for t in tickers}
        for future in as_completed(futures):
            completed += 1
            result = future.result()
            if result is not None: results.append(result)
            progress_bar.progress(completed / total)
            status_text.text("Scanne " + str(completed) + "/" + str(total) + " | " + str(len(results)) + " Treffer")
    progress_bar.empty()
    status_text.empty()
    return pd.DataFrame(results) if results else pd.DataFrame()# MAIN
if mode == "📈 Einzelanalyse":
    st.title("📈 " + ticker_input + " - Analyse")
    try:
        with st.spinner("Lade Daten..."):
            s = yf.Ticker(ticker_input)
            df = s.history(period=period, interval="1d")
        if df.empty:
            st.error("Keine Daten")
        else:
            df = calc_indicators(df)
            if df is not None:
                latest = df.iloc[-1]
                score = swing_score(df)
                st.markdown("[📈 TradingView Chart](" + tv_link(ticker_input) + ")")
                c1, c2, c3, c4, c5 = st.columns(5)
                with c1: st.metric("Score", str(score) + "/100")
                with c2: st.metric("Preis", "$" + str(round(latest['Close'], 2)))
                with c3: st.metric("RSI", str(round(latest.get('RSI', 50), 1)))
                with c4: st.metric("ADX", str(round(latest.get('ADX', 20), 1)))
                with c5: st.metric("ATR%", str(round((latest.get('ATR',0)/latest['Close']*100), 2)) + "%")
                fig = go.Figure()
                fig.add_trace(go.Candlestick(x=df.index, open=df['Open'], high=df['High'], low=df['Low'], close=df['Close'], name="Kurs", increasing_line_color='#00ff88', decreasing_line_color='#ff4444'))
                if pd.notna(latest.get('SMA_20')): fig.add_trace(go.Scatter(x=df.index, y=df['SMA_20'], name='SMA20', line=dict(color='blue', width=1.5)))
                if pd.notna(latest.get('SMA_50')): fig.add_trace(go.Scatter(x=df.index, y=df['SMA_50'], name='SMA50', line=dict(color='orange', width=1.5)))
                fig.update_layout(height=500, template='plotly_dark', margin=dict(l=0,r=0,t=20,b=0), xaxis_rangeslider_visible=False)
                st.plotly_chart(fig, use_container_width=True)
    except Exception as e:
        st.error("Fehler: " + str(e))

else:
    st.title("🔎 Market Scanner")
    
    if scanner_type == "⚡ Quick Scan (Top 100)":
        st.markdown("### ⚡ Quick Scan - Top 100 Aktien")
    elif scanner_type == "💾 Watchlist Scan":
        st.markdown("### 💾 Watchlist Scan - " + str(len(st.session_state.get('user_watchlist', []))) + " Aktien")
    else:
        st.markdown("### 📊 Standard Scan - ALLE S&P 500 + NASDAQ 100 + Russell 2000 + DAX 40")
    
    if st.button("🚀 SCAN STARTEN", type="primary", use_container_width=True):
        if scanner_type == "💾 Watchlist Scan":
            if len(st.session_state.get('user_watchlist', [])) == 0:
                st.error("Watchlist leer!")
                st.stop()
            tickers = st.session_state.user_watchlist
        else:
            tickers = get_all_tickers()
            if scanner_type == "⚡ Quick Scan (Top 100)":
                tickers = tickers[:100]
        
        st.markdown("Scanne " + str(len(tickers)) + " Aktien...")
        start_time = time.time()
        
        if scanner_type == "📊 Standard Scan (ALLE)":
            df_results = run_scan(tickers)
            end_time = time.time()
        scan_time = round(end_time - start_time, 2)

        if df_results.empty:
            st.warning("❌ Keine Treffer gefunden!")
        else:

            # FILTER
            df_results = df_results[
                (df_results['Swing-Score'] >= min_swing_score) &
                (df_results['RSI'] >= rsi_min) &
                (df_results['RSI'] <= rsi_max) &
                (df_results['ADX'] >= adx_min) &
                (df_results['Vol Ratio'] >= volume_surge_min)
            ]

            if require_sma_above:
                df_results = df_results[
                    df_results['SMA20'] == 'Above'
                ]

            if require_macd_bullish:
                df_results = df_results[
                    df_results['MACD'] == 'Bullish'
                ]

            # SORTIEREN
            df_results = df_results.sort_values(
                by='Swing-Score',
                ascending=False
            )

            # INFO
            st.success(
                f"✅ {len(df_results)} Treffer gefunden | Zeit: {scan_time}s"
            )

            # TABELLE
            st.dataframe(
    df_results,
    column_config={
        "Chart": st.column_config.LinkColumn(
            "Chart",
            display_text="📈 Öffnen"
        )
    },
    use_container_width=True,
    height=650
)

            # CSV DOWNLOAD
            csv = df_results.to_csv(index=False).encode('utf-8')

            st.download_button(
                "📥 Ergebnisse herunterladen",
                csv,
                "scanner_results.csv",
                "text/csv"
            )
