import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.graph_objects as go
from datetime import datetime
import pytz

# 1. 페이지 설정
st.set_page_config(page_title="10분봉 주간 수익률", layout="wide")

st.title("📊 자산별 주간 수익률 분석 (10분봉)")

# 2. 종목 설정
tickers = {
    'CL=F': 'WTI 원유 선물',
    'SI=F': '글로벌 은 선물',
    'DX-Y.NYB': 'DXY 달러지수',
    'SOXX': '필라델피아 반도체(SOXX)'
}

@st.cache_data(ttl=300)
def load_data_10m():
    # interval='10m'을 사용할 때는 period를 1mo(한달) 이내로 설정하는 것이 가장 안정적입니다.
    # 만약 데이터가 안 불러와지면 period='7d'로 줄여보세요.
    ticker_list = list(tickers.keys())
    df = yf.download(ticker_list, period='1mo', interval='10m', progress=False)
    
    if df.empty:
        return None

    # yfinance 버전별로 MultiIndex 구조가 다를 수 있어 안전하게 처리
    # 'Close' 컬럼만 선택
    if isinstance(df.columns, pd.MultiIndex):
        close_df = df.xs('Close', axis=1, level=0)
    else:
        close_df = df[['Close']]
        close_df.columns = ticker_list

    # 한국 시간으로 변환
    close_df.index = close_df.index.tz_convert('Asia/Seoul')
    return close_df

def draw_dashboard():
    data = load_data_10m()
    
    if data is None or data.empty:
        st.error("❌ 10분봉 데이터를 불러오지 못했습니다. 야후 파이낸스 서버 제한이거나 장 폐쇄 시간일 수 있습니다. '7d'로 기간을 줄여보세요.")
        return

    fig = go.Figure()
    cols = st.columns(len(tickers))
    colors = ['#333333', '#FFD700', '#FF4B4B', '#00CC96']

    for i, (symbol, name) in enumerate(tickers.items()):
        if symbol not in data.columns:
            continue
            
        series = data[symbol].dropna()
        if series.empty:
            continue

        # 가중치 설정
        weight = 5 if symbol == 'DX-Y.NYB' else (2 if symbol == 'SI=F' else 1)
        
        # 주간 리셋 로직: 매주 첫 데이터 찾기
        weekly_groups = series.groupby([series.index.year, series.index.isocalendar().week])
        base_prices = weekly_groups.transform('first')
        returns = ((series - base_prices) / base_prices * 100) * weight
        
        curr_ret = returns.iloc[-1]
        display_name = f"{name} ({weight}x)" if weight > 1 else name

        # 상단 지표
        cols[i].metric(label=display_name, value=f"{series.iloc[-1]:,.2f}", delta=f"{curr_ret:+.2f}%")

        # 차트 선
        fig.add_trace(go.Scatter(
            x=returns.index, y=returns,
            mode='lines', name=display_name,
            line=dict(width=2, color=colors[i]),
            hovertemplate='%{x|%m/%d %H:%M} 수익률: %{y:.2f}%<extra></extra>'
        ))

    fig.update_layout(
        hovermode="x unified", height=600, template='plotly_white',
        margin=dict(l=0, r=0, t=50, b=0),
        legend=dict(orientation="h", y=1.05, x=0.5, xanchor="center")
    )
    
    st.plotly_chart(fig, use_container_width=True)

draw_dashboard()
