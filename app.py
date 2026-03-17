import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.graph_objects as go
from datetime import datetime
import pytz

# 1. 페이지 설정
st.set_page_config(page_title="주간 수익률 대시보드 (15분봉)", layout="wide")

st.title("📊 자산별 주간 수익률 분석 (15분봉)")
st.markdown("##### 🕒 월요일 첫 거래 기준 리셋 | 🏆 1위 종목 강조 모드")

# 2. 종목 및 설정
tickers = {
    'CL=F': 'WTI 원유 선물',
    'SI=F': '글로벌 은 선물',
    'DX-Y.NYB': 'DXY 달러지수',
    'SOXX': '필라델피아 반도체(SOXX)'
}
# 기본 색상 (1위가 아닐 때 사용)
default_colors = ['#7F8C8D', '#95A5A6', '#BDC3C7', '#D5D8DC'] 

@st.cache_data(ttl=600)
def load_all_data():
    ticker_symbols = list(tickers.keys())
    df = yf.download(tickers=ticker_symbols, period='1mo', interval='15m', progress=False)
    return df

def draw_dashboard():
    df = load_all_data()
    
    if df is None or df.empty:
        st.error("❌ 데이터를 불러올 수 없습니다.")
        return

    # 데이터 전처리 및 수익률 계산 결과를 담을 리스트
    results = []
    is_multi = isinstance(df.columns, pd.MultiIndex)
    all_reset_times = set()

    for symbol, name in tickers.items():
        try:
            if is_multi:
                series = df['Close'][symbol].dropna()
            else:
                series = df['Close'].dropna() if len(tickers) == 1 else df[symbol].dropna()
            
            if series.empty: continue
            series.index = series.index.tz_convert('Asia/Seoul')

            # 가중치 설정
            weight = 5 if symbol == 'DX-Y.NYB' else (2 if symbol == 'SI=F' else 1)
            
            # 주차별 그룹화 및 첫 봉(리셋 지점) 찾기
            groups = series.groupby([series.index.year, series.index.isocalendar().week])
            weekly_first = groups.transform('first')
            reset_times = series.groupby([series.index.year, series.index.isocalendar().week]).idxmin()
            for t in reset_times: all_reset_times.add(t)

            returns = ((series - weekly_first) / weekly_first * 100) * weight
            
            results.append({
                'symbol': symbol,
                'name': name,
                'returns': returns,
                'last_return': returns.iloc[-1],
                'last_price': series.iloc[-1],
                'weight': weight
            })
        except: continue

    if not results: return

    # 3. 수익률 1위 종목 찾기
    results.sort(key=lambda x: x['last_return'], reverse=True)
    best_stock = results[0] # 현재 수익률 가장 높은 종목

    fig = go.Figure()
    cols = st.columns(len(tickers))

    for i, res in enumerate(results):
        is_best = (res['symbol'] == best_stock['symbol'])
        line_color = 'red' if is_best else '#D3D3D3' # 1위는 빨강, 나머지는 연한 회색
        line_width = 4 if is_best else 1.5
        
        display_name = f"{res['name']} ({res['weight']}x)" if res['weight'] > 1 else res['name']
        
        # 상단 Metric 표시 (정렬된 순서대로 표시됨)
        cols[i].metric(label=display_name, value=f"{res['last_price']:,.2f}", delta=f"{res['last_return']:+.2f}%")

        # 차트 선 추가
        fig.add_trace(go.Scatter(
            x=res['returns'].index, y=res['returns'],
            mode='lines', 
            name=f"🏆 {display_name}" if is_best else display_name,
            line=dict(width=line_width, color=line_color),
            hovertemplate='<b>%{fullData.name}</b>
