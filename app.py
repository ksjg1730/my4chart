import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.graph_objects as go
from datetime import datetime, timedelta

# 1. 페이지 설정
st.set_page_config(page_title="달러 인덱스 vs 국내 ETF 비교", layout="wide")

st.title("📊 글로벌 달러 인덱스 vs 국내 ETF 수익률 비교")

# 2. 종목 설정 (글로벌 은 선물 -> 달러 인덱스로 변경)
tickers = {
    'DX=F': '달러 인덱스 선물 (ICE)',  # 글로벌 달러 인덱스
   'SI=F': '글로벌 은 선물 (COMEX)',
    '261250.KS': 'KODEX 달러레버리지',
    '233740.KS': 'KODEX 코스닥150레버리지'
}

def get_reference_time():
    """최근 금요일 12:00 (KST) 계산"""
    today = datetime.now()
    days_since_friday = (today.weekday() - 4) % 7
    last_friday = today - timedelta(days=days_since_friday)
    if today.weekday() < 4 or (today.weekday() == 4 and today.hour < 12):
        last_friday -= timedelta(days=7)
    return pd.Timestamp(last_friday.replace(hour=12, minute=0, second=0)).tz_localize('Asia/Seoul')

ref_time = get_reference_time()

# 3. 차트 그리기
@st.fragment(run_every=60)
def draw_chart():
    fig = go.Figure()
    cols = st.columns(4)
    # 달러 인덱스를 강조하기 위해 첫 번째 색상을 감청색으로 변경
    colors = ['#1F77B4', '#EF553B', '#00CC96', '#636EFA']

    all_data_indices = []

    for i, (symbol, name) in enumerate(tickers.items()):
        # 데이터 수집 (최근 1개월, 30분봉)
        df = yf.download(symbol, period='1mo', interval='30m', progress=False)
        if df.empty: continue
        
        # 멀티인덱스 컬럼 문제 해결
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.get_level_values(0)
        
        # 시간대 변환 (KST)
        df.index = df.index.tz_convert('Asia/Seoul')
        all_data_indices.append(df.index)
        
        # 수익률 계산 (기준점: 금요일 12:00)
        base_df = df[df.index <= ref_time]
        base_price = float(base_df['Close'].iloc[-1]) if not base_df.empty else float(df['Close'].iloc[0])
        
        df['Return'] = ((df['Close'] - base_price) / base_price
