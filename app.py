import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.graph_objects as go
from datetime import datetime
import pytz

# 1. 페이지 설정
st.set_page_config(page_title="주간 수익률 대시보드 (15분봉)", layout="wide")

st.title("📊 자산별 주간 수익률 분석 (15분봉)")
st.markdown("##### 🕒 매주 월요일 첫 거래 데이터 기준 리셋 (가중치 반영)")

# 2. 종목 및 설정
tickers = {
    'CL=F': 'WTI 원유 선물',
    'SI=F': '글로벌 은 선물',
    'DX-Y.NYB': 'DXY 달러지수',
    'SOXX': '필라델피아 반도체(SOXX)'
}
colors = ['#333333', '#FFD700', '#FF4B4B', '#00CC96']

@st.cache_data(ttl=600)
def load_all_data():
    """15분봉 데이터를 안전하게 호출"""
    ticker_symbols = list(tickers.keys())
    
    # 15분봉(15m), 기간 1개월(1mo)
    df = yf.download(
        tickers=ticker_symbols,
        period='1mo',
        interval='15m',
        progress=False,
        group_by='ticker' # 종목별로 데이터를 묶어서 가져옴 (가장 안전한 방법)
    )
    
    if df.empty:
        return None
    return df

def process_data(df, symbol, weight):
    """특정 종목의 Close 가격 추출 및 수익률 계산"""
    try:
        # group_by='ticker'로 가져온 경우 처리
        if symbol in df.columns.levels[0]:
            series = df[symbol]['Close'].dropna()
        else:
            return pd.Series()
    except:
        # 단일 종목이거나 구조가 다를 경우 대비
        try:
            series = df['Close'][symbol].dropna()
        except:
            return pd.Series()

    if series.empty:
        return pd.Series()

    # 한국 시간대 변환
    series.index = series.index.tz_convert('Asia/Seoul')

    # 주차별 첫 데이터(기준가) 계산
    weekly_first = series.groupby([series.index.year, series.index.isocalendar().week]).transform('first')
    
    # 수익률 계산 (가중치 적용)
    returns = ((series - weekly_first) / weekly_first * 100) * weight
    return returns

def draw_dashboard():
    df = load_all_data()
    
    if df is None:
        st.error("❌ 데이터를 불러올 수 없습니다. 인터넷 연결이나 야후 파이낸스 상태를 확인하세요.")
        return

    fig = go.Figure()
    cols = st.columns(len(tickers))

    for i, (symbol, name) in enumerate(tickers.items()):
        weight = 5 if symbol == 'DX-Y.NYB' else (2 if symbol == 'SI=F' else 1)
        returns = process_data(df, symbol, weight)
        
        if returns.empty:
            cols[i].warning(f"{name} 데이터 없음")
            continue

        # 현재 수치들
        curr_ret = returns.iloc[-1]
        try:
            # 원 데이터에서 현재가 추출
            if symbol in df.columns.levels[0]:
                curr_price = df[symbol]['Close'].dropna().iloc[-1]
            else:
                curr_price = df['Close'][symbol
