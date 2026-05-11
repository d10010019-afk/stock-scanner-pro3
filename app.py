import streamlit as st
from FinMind.data import DataLoader
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from datetime import datetime, timedelta

# 1. 頁面基本設定 (讓手機顯示更美觀)
st.set_page_config(page_title="五星共振系統-專業版", layout="wide")
st.title("🌟 五星共振量化選股系統")

# 2. 填入您的 FinMind 通行鑰匙
FINMIND_TOKEN = "EyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9.eyJ1c2VyX2lkIjoiTWlrZSAiLCJlbWFpbCI6ImQxMDAxMDAxOUBnbWFpbC5jb20iLCJ0b2tlbl92ZXJzaW9uIjowfQ.ll0lBmiltd6LZWSR36rp-llozQ0EXvacpA57F0vmBqc"

# 3. 股票代碼輸入框 (直接放在主畫面，不需點側邊欄)
symbol = st.text_input("🔍 請輸入台股代碼 (例: 2330, 3481, 0050)", "2330")

@st.cache_data(ttl=1800) # 緩存30分鐘，避免頻繁存取
def get_finmind_data(ticker):
    dl = DataLoader()
    dl.login(token=FINMIND_TOKEN)
    
    # 抓取最近 180 天的資料
    start_date = (datetime.now() - timedelta(days=180)).strftime('%Y-%m-%d')
    df = dl.taiwan_stock_daily(stock_id=ticker, start_date=start_date)
    
    # 資料欄位清洗，對應 FinMind 格式
    df = df.rename(columns={
        'date': 'Date', 'open': 'Open', 'high': 'High', 
        'low': 'Low', 'close': 'Close', 'trading_volume': 'Volume'
    })
    df.set_index('Date', inplace=True)
    
    # --- 量化指標計算 ---
    # 5日均線
    df['MA5'] = df['Close'].rolling(window=5).mean()
    
    # RSI 計算
    delta = df['Close'].diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
    rs = gain / loss
    df['RSI'] = 100 - (100 / (1 + rs))
    
    # MACD 計算
    exp1 = df['Close'].ewm(span=12, adjust=False).mean()
    exp2 = df['Close'].ewm(span=26, adjust=False).mean()
    df['DIF'] = exp1 - exp2
    df['MACD_Line'] = df['DIF'].ewm(span=9, adjust=False).mean()
    df['MACD_Hist'] = df['DIF'] - df['MACD_Line']
    
    return df

try:
    # 讀取數據
    df = get_finmind_data(symbol)
    last = df.iloc[-1]   # 最新一筆資料
    prev = df.iloc[-2]   # 前一筆資料
    
    # --- 五星共振評分邏輯 ---
    score = 0
    results = []
    
    if last['Close'] > last['MA5']:
        score += 1
        results.append("✅ 5日線上")
    if last['MACD_Hist'] > 0 and last['MACD_Hist'] > prev['MACD_Hist']:
        score += 1
        results.append("✅ MACD轉強")
    if 40 < last['RSI'] < 75:
        score += 1
        results.append(f"✅ RSI強勢區 ({last['RSI']:.1f})")
    if last['Close'] > last['Open']:
        score += 1
        results.append("✅ 收紅K線")
    if last['Volume'] > df['Volume'].tail(5).mean():
        score += 1
        results.append("✅ 量能爆發")

    # --- 顯示介面設計 ---
    st.markdown(f"### 📊 當前量化評分：{score} / 5")
    
    # 用彩色方塊顯示亮起的星標
    cols = st.columns(len(results) if results else 1)
    for i, res in enumerate(results):
        with cols[i]:
            st.info(res)
            
    # 給出行動建議
    if score >= 4:
        st.success("🚀 多頭訊號強烈，建議依據智慧條件單布局！")
    elif score <= 1:
        st.warning("⚠️ 趨勢轉弱，建議觀望或執行移動停損。")

    # --- 繪製 K 線與指標圖表 ---
    fig = make_subplots(rows=2, cols=1, shared_xaxes=True, 
                        vertical_spacing=0.05, row_heights=[0.7, 0.3])
    
    # 主圖：K線與5日線
    fig.add_trace(go.Candlestick(x=df.index, open=df['Open'], high=df['High'], 
                                 low=df['Low'], close=df['Close'], name='K線'), row=1, col=1)
    fig.add_trace(go.Scatter(x=df.index, y=df['MA5'], line=dict(color='orange', width=2), name='5日均線'), row=1, col=1)
    
    # 副圖：MACD 紅綠柱
    fig.add_trace(go.Bar(x=df.index, y=df['MACD_Hist'], name='MACD動能'), row=2, col=1)
    
    fig.update_layout(height=600, template='plotly_dark', xaxis_rangeslider_visible=False,
                      margin=dict(l=10, r=10, t=10, b=10))
    st.plotly_chart(fig, use_container_width=True)

except Exception as e:
    st.error("⚠️ 無法獲取資料。請確認代碼（如 2330）是否正確，或稍後再試。")
    st.info("💡 提示：FinMind 版本不需輸入 .TW 字樣。")
