import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.graph_objects as go
from datetime import datetime
import pytz

# 1. 페이지 설정
st.set_page_config(page_title="주간 수익률 대시보드", layout="wide")

st.title("📊 자산별 주간 수익률 분석")
st.markdown("##### 🔵 월요일 리셋 | 🏆 실시간 1위 종목 그래프 2배 가중 시각화")

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

    # 1차 가공: 일반 수익률 계산
    for symbol, name in tickers.items():
        try:
            if is_multi:
                series = df['Close'][symbol].dropna()
            else:
                series = df['Close'].dropna() if len(tickers) == 1 else df[symbol].dropna()
            
            if series.empty: continue
            series.index = series.index.tz_convert('Asia/Seoul')

            # 기본 가중치 적용 (DXY: 5x, Silver: 2x, etc.)
            base_w = 5 if symbol == 'DX-Y.NYB' else (2 if symbol == 'SI=F' else 1)
            
            # 월요일 리셋 지점 추출
            monday_data = series[series.index.weekday == 0]
            if not monday_data.empty:
                resets = monday_data.groupby([monday_data.index.year, monday_data.index.isocalendar().week]).idxmin()
                for t in resets: monday_reset_times.add(t)

            # 주간 수익률 계산
            weekly_first = series.groupby([series.index.year, series.index.isocalendar().week]).transform('first')
            returns = ((series - weekly_first) / weekly_first * 100) * base_w
            
            results.append({
                'symbol': symbol, 'name': name, 'returns': returns,
                'last_val': returns.iloc[-1], 'last_price': series.iloc[-1], 'weight': base_w
            })
        except: continue

    if not results: return

    # 🚀 실시간 1위 종목 찾기
    results.sort(key=lambda x: x['last_val'], reverse=True)
    best_symbol = results[0]['symbol']

    fig = go.Figure()
    cols = st.columns(len(tickers))

    for i, res in enumerate(results):
        is_best = (res['symbol'] == best_symbol)
        
        # 🏆 [핵심 수정] 1위 종목인 경우 그래프 데이터를 2배로 증폭
        plot_returns = res['returns'] * 2 if is_best else res['returns']
        
        line_color = 'red' if is_best else '#D3D3D3'
        line_width = 5.0 if is_best else 1.5
        
        display_name = f"{res['name']} ({res['weight']}x)"
        if is_best: display_name += " [2x BOOST]"
        
        # 상단 지표 (수치는 실제값 표시, Delta에만 부스트 표시 가능)
        cols[i].metric(label=display_name, value=f"{res['last_price']:,.2f}", 
                       delta=f"{res['last_val']:+.2f}%" + (" (x2)" if is_best else ""))

        # 차트 선 그리기
        fig.add_trace(go.Scatter(
            x=plot_returns.index, 
            y=plot_returns,
            mode='lines', 
            name=display_name,
            line=dict(width=line_width, color=line_color),
            hovertemplate='<b>' + res['name'] + '</b><br>표시수익률(x2): %{y:.2f}%<extra></extra>' if is_best else '<b>' + res['name'] + '</b><br>수익률: %{y:.2f}%<extra></extra>'
        ))

        # 1위 종목 현재가 위치에 HIGH 마커 추가
        if is_best:
            fig.add_trace(go.Scatter(
                x=[plot_returns.index[-1]], 
                y=[plot_returns.iloc[-1]],
                mode='markers+text',
                marker=dict(size=15, color='red', symbol='star'),
                text=[f"🏆 HIGH BOOST<br>{plot_returns.iloc[-1]:+.2f}%"],
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
        yaxis=dict(title="수익률 (1위는 2배 증폭됨)", ticksuffix="%", zeroline=False),
        legend=dict(orientation="h", y=1.05, x=0.5, xanchor="center"),
        margin=dict(l=10, r=10, t=100, b=10)
    )

    st.plotly_chart(fig, use_container_width=True)

if __name__ == "__main__":
    draw_dashboard()
    st.info("💡 현재 수익률이 가장 높은 종목은 차트상에서 가독성을 위해 **실제 수익률의 2배** 높이로 그려집니다.")
