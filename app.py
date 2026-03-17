import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.graph_objects as go
from datetime import datetime
import pytz

# 1. 페이지 설정
st.set_page_config(page_title="주간 수익률 대시보드", layout="wide")

st.title("📊 자산별 주간 수익률 분석")
st.markdown("##### 🔵 월요일 리셋 (굵은 실선) | 🏆 실시간 1위 종목 2배 증폭 그래프")

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

    # 1. 모든 종목의 기본 수익률 계산
    for symbol, name in tickers.items():
        try:
            if is_multi:
                series = df['Close'][symbol].dropna()
            else:
                series = df['Close'].dropna() if len(tickers) == 1 else df[symbol].dropna()
            
            if series.empty: continue
            series.index = series.index.tz_convert('Asia/Seoul')

            # 기본 가중치 적용
            base_w = 5 if symbol == 'DX-Y.NYB' else (2 if symbol == 'SI=F' else 1)
            
            # 월요일 리셋 지점 추출 (블루 실선용)
            monday_data = series[series.index.weekday == 0]
            if not monday_data.empty:
                resets = monday_data.groupby([monday_data.index.year, monday_data.index.isocalendar().week]).idxmin()
                for t in resets: monday_reset_times.add(t)

            # 주간 수익률 계산 (기본값)
            weekly_first = series.groupby([series.index.year, series.index.isocalendar().week]).transform('first')
            raw_returns = ((series - weekly_first) / weekly_first * 100) * base_w
            
            results.append({
                'symbol': symbol, 'name': name, 'returns': raw_returns,
                'last_val': raw_returns.iloc[-1], 'last_price': series.iloc[-1]
            })
        except: continue

    if not results: return

    # 2. 🚀 실시간 모든 종목 중 가장 높은 수치(1위) 찾기
    results.sort(key=lambda x: x['last_val'], reverse=True)
    best_symbol = results[0]['symbol']

    fig = go.Figure()
    cols = st.columns(len(tickers))

    # 3. 그래프 그리기 (1위 종목만 2배 가중치 적용)
    for i, res in enumerate(results):
        is_best = (res['symbol'] == best_symbol)
        
        # 🏆 1위 종목은 그래프 데이터를 2배로 뻥튀기하여 표시
        plot_data = res['returns'] * 2 if is_best else res['returns']
        
        line_color = 'red' if is_best else '#D3D3D3'
        line_width = 5.0 if is_best else 1.5
        
        display_name = res['name']
        if is_best: display_name += " (x2 BOOST)"
        
        # 상단 지표 (수치는 실제 가격 표시)
        cols[i].metric(label=display_name, value=f"{res['last_price']:,.2f}", 
                       delta=f"{res['last_val']:+.2f}%" + (" (x2)" if is_best else ""))

        # 선 추가
        fig.add_trace(go.Scatter(
            x=plot_data.index, y=plot_data,
            mode='lines', name=display_name,
            line=dict(width=line_width, color=line_color),
            hovertemplate='<b>' + res['name'] + '</b><br>차트수치: %{y:.2f}%<extra></extra>'
        ))

        # 1위 종목 최고점에 HIGH 라벨 표시
        if is_best:
            fig.add_trace(go.Scatter(
                x=[plot_data.index[-1]], y=[plot_data.iloc[-1]],
                mode='markers+text',
                marker=dict(size=12, color='red', symbol='star'),
                text=[f"🏆 HIGH: {res['last_val']:+.2f}% x 2"],
                textposition="top center",
                textfont=dict(color="red", size=14, family="Arial Black"),
                showlegend=False
            ))

    # 월요일 리셋 수직선 (블루 굵은 실선)
    for rt in monday_reset_times:
        fig.add_vline(x=rt, line_dash="solid", line_color="blue", line_width=3, opacity=0.7)

    fig.add_hline(y=0, line_color="black", line_width=1.5)

    fig.update_layout(
        hovermode="x unified", height=800, template='plotly_white',
        xaxis=dict(tickformat="%m/%d\n%H:%M", showgrid=False),
        yaxis=dict(title="수익률 가중치 그래프", ticksuffix="%", zeroline=False),
        legend=dict(orientation="h", y=1.05, x=0.5, xanchor="center"),
        margin=dict(l=10, r=10, t=80, b=10)
    )

    st.plotly_chart(fig, use_container_width=True)

if __name__ == "__main__":
    draw_dashboard()
    st.caption("🔵 블루 실선: 월요일 리셋 | 🔴 레드 라인: 현재 주간 수익률 1위 (시각화 가중치 2배 적용)")
