import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.graph_objects as go
from datetime import datetime
import pytz

# 1. 페이지 설정
st.set_page_config(page_title="주간 수익률 대시보드", layout="wide")

st.title("📊 자산별 주간 수익률 분석")
st.markdown("##### 🔵 월요일 리셋 지표 (굵은 실선) | 🏆 실시간 수익률 1위 동적 추적")

# 2. 종목 설정
tickers = {
    'CL=F': 'WTI 원유 선물',
    'SI=F': '글로벌 은 선물',
    'DX-Y.NYB': 'DXY 달러지수',
    'SOXX': '필라델피아 반도체(SOXX)'
}

@st.cache_data(ttl=300)
def load_all_data():
    ticker_symbols = list(tickers.keys())
    # 15분봉 데이터 호출
    df = yf.download(tickers=ticker_symbols, period='1mo', interval='15m', progress=False)
    return df

def draw_dashboard():
    df = load_all_data()
    
    if df is None or df.empty:
        st.error("❌ 데이터를 불러올 수 없습니다.")
        return

    results = []
    monday_reset_times = set()
    is_multi = isinstance(df.columns, pd.MultiIndex)

    # 데이터 가공 및 수익률 계산
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
            
            # 주차별 리셋 지점 (월요일 첫 봉) 계산
            # 월요일(weekday=0) 데이터만 필터링하여 그 중 각 주별 첫 시간대 추출
            monday_data = series[series.index.weekday == 0]
            if not monday_data.empty:
                resets = monday_data.groupby([monday_data.index.year, monday_data.index.isocalendar().week]).idxmin()
                for t in resets: monday_reset_times.add(t)

            # 수익률 계산용 기준가 (매주 첫 거래 데이터)
            weekly_first = series.groupby([series.index.year, series.index.isocalendar().week]).transform('first')
            returns = ((series - weekly_first) / weekly_first * 100) * weight
            
            results.append({
                'symbol': symbol, 'name': name, 'returns': returns,
                'last_return': returns.iloc[-1], 'last_price': series.iloc[-1], 'weight': weight
            })
        except: continue

    if not results:
        return

    # 실시간 수익률 기준 내림차순 정렬 (1위 종목 추출)
    results.sort(key=lambda x: x['last_return'], reverse=True)
    best_res = results[0] 

    fig = go.Figure()
    cols = st.columns(len(tickers))

    for i, res in enumerate(results):
        is_best = (res['symbol'] == best_res['symbol'])
        line_color = 'red' if is_best else '#D3D3D3'
        line_width = 4.5 if is_best else 1.5
        
        display_name = f"{res['name']} ({res['weight']}x)" if res['weight'] > 1 else res['name']
        
        # 상단 Metric
        cols[i].metric(label=display_name, value=f"{res['last_price']:,.2f}", delta=f"{res['last_return']:+.2f}%")

        # 메인 수익률 선
        fig.add_trace(go.Scatter(
            x=res['returns'].index, 
            y=res['returns'],
            mode='lines', 
            name=display_name,
            line=dict(width=line_width, color=line_color),
            hovertemplate='<b>' + display_name + '</b><br>수익률: %{y:.2f}%<extra></extra>'
        ))

        # 🏆 [동적 표시] 현재 1위 종목의 현재가 상단 3% 지점에 특별 마커
        if is_best:
            target_y = res['last_return'] + 3
            fig.add_trace(go.Scatter(
                x=[res['returns'].index[-1]], 
                y=[target_y],
                mode='markers+text',
                marker=dict(size=15, color='red', symbol='star'),
                text=[f"🏆 최고상승: {res['name']}<br>{res['last_return']:+.2f}%"],
                textposition="top center",
                textfont=dict(color="red", size=13, family="Arial Black"),
                showlegend=False
            ))

    # 월요일 리셋 수직선 (블루 굵은 실선) - 다른 선은 제거됨
    for rt in monday_reset_times:
        fig.add_vline(x=rt, line_dash="solid", line_color="blue", line_width=3, opacity=0.7)

    # 기준선 0%
    fig.add_hline(y=0, line_color="black", line_width=1.5)

    fig.update_layout(
        hovermode="x unified", height=750, template='plotly_white',
        xaxis=dict(tickformat="%m/%d\n%H:%M", showgrid=False),
        yaxis=dict(title="가중 수익률 (%)", ticksuffix="%", zeroline=False),
        legend=dict(orientation="h", y=1.05, x=0.5, xanchor="center"),
        margin=dict(l=10, r=10, t=80, b=10)
    )

    st.plotly_chart(fig, use_container_width=True)

if __name__ == "__main__":
    draw_dashboard()
    st.caption(f"기준: 매주 월요일 첫 거래 | 강조: 실시간 수익률 1위 종목 (RED) | 수직선: 월요일 개장 시점 (BLUE)")
