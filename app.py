import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.graph_objects as go
from datetime import datetime
import pytz

# 1. 페이지 설정 (가장 먼저 실행되어야 함)
st.set_page_config(page_title="주간 수익률 대시보드", layout="wide")

# 2. 모바일 확대 방지 및 스타일 설정
st.markdown(
    """
    <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no">
    <style>
        input, select, textarea { font-size: 16px !important; }
        .main { background-color: #f8f9fa; }
    </style>
    """,
    unsafe_allow_html=True
)

# 3. 사이드바 설정
version = st.sidebar.selectbox("🚀 모드 선택", ["원본 버전", "2배 가중치 버전"])
is_weighted_mode = (version == "2배 가중치 버전")

st.title("📊 자산별 주간 수익률 분석")
st.markdown(f"##### 현재 모드: `{'🔥 2배 가중치' if is_weighted_mode else '📋 원본'}`")
st.markdown("##### 🔵 월요일 리셋 (굵은 실선) | 🏆 실시간 1위 종목 강조")

# 4. 종목 설정
tickers = {
    'CL=F': 'WTI 원유 선물',
    'SI=F': '글로벌 은 선물',
    'DX-Y.NYB': 'DXY 달러지수',
    'SOXX': '필라델피아 반도체(SOXX)'
}

@st.cache_data(ttl=300)
def load_all_data():
    ticker_symbols = list(tickers.keys())
    # 데이터 안정성을 위해 종가(Close) 위주로 가져옴
    df = yf.download(tickers=ticker_symbols, period='1mo', interval='15m', progress=False)
    return df

def draw_dashboard():
    df = load_all_data()
    
    if df is None or df.empty:
        st.error("❌ 데이터를 불러올 수 없습니다.")
        return

    results = []
    monday_reset_times = set()

    # 데이터 구조 파악 (MultiIndex 대응)
    for symbol, name in tickers.items():
        try:
            if isinstance(df.columns, pd.MultiIndex):
                series = df['Close'][symbol].dropna()
            else:
                series = df['Close'].dropna() if len(tickers) == 1 else df[symbol].dropna()
            
            if series.empty: continue
            
            # 시간대 변환
            series.index = series.index.tz_convert('Asia/Seoul')

            # 기본 가중치 적용 (DXY 등 변동성 보정)
            base_w = 5 if symbol == 'DX-Y.NYB' else (2 if symbol == 'SI=F' else 1)
            
            # 월요일 리셋 지점 추출
            monday_data = series[series.index.weekday == 0]
            if not monday_data.empty:
                resets = monday_data.groupby([monday_data.index.year, monday_data.index.isocalendar().week]).idxmin()
                for t in resets: monday_reset_times.add(t)

            # 주간 수익률 계산
            weekly_first = series.groupby([series.index.year, series.index.isocalendar().week]).transform('first')
            raw_returns = ((series - weekly_first) / weekly_first * 100) * base_w
            
            results.append({
                'symbol': symbol, 'name': name, 'returns': raw_returns,
                'last_val': raw_returns.iloc[-1], 'last_price': series.iloc[-1]
            })
        except Exception as e:
            continue

    if not results:
        st.warning("분석할 데이터가 부족합니다.")
        return

    # 1위 종목 찾기
    results.sort(key=lambda x: x['last_val'], reverse=True)
    best_symbol = results[0]['symbol']

    fig = go.Figure()
    cols = st.columns(len(results))

    for i, res in enumerate(results):
        is_best = (res['symbol'] == best_symbol)
        
        # 가중치 모드일 경우 1위 종목만 2배 뻥튀기
        plot_weight = 2.0 if (is_best and is_weighted_mode) else 1.0
        plot_data = res['returns'] * plot_weight
        
        line_color = '#EF553B' if is_best else '#BDC3C7'
        line_width = 4 if is_best else 1.5
        
        display_name = res['name']
        if is_best and is_weighted_mode: display_name += " (x2 BOOST)"
        
        # 상단 지표 출력
        cols[i].metric(
            label=display_name, 
            value=f"{res['last_price']:,.2f}", 
            delta=f"{res['last_val']:+.2f}%" + (" (x2)" if is_best and is_weighted_mode else "")
        )

        # 차트 선 추가
        fig.add_trace(go.Scatter(
            x=plot_data.index, y=plot_data,
            mode='lines', name=display_name,
            line=dict(width=line_width, color=line_color),
            hovertemplate='<b>%{text}</b><br>수익률: %{y:.2f}%<extra></extra>',
            text=[res['name']] * len(plot_data)
        ))

        # 1위 종목 하이라이트 마커
        if is_best:
            fig.add_trace(go.Scatter(
                x=[plot_data.index[-1]], y=[plot_data.iloc[-1]],
                mode='markers+text',
                marker=dict(size=10, color=line_color),
                text=[f"🏆 {res['last_val']:+.2f}%"],
                textposition="top right",
                showlegend=False
            ))

    # 기준선 및 레이아웃 설정
    for rt in monday_reset_times:
        fig.add_vline(x=rt, line_dash="dash", line_color="blue", line_width=1, opacity=0.5)

    fig.add_hline(y=0, line_color="black", line_width=1)

    fig.update_layout(
        hovermode="x unified", height=600, template='plotly_white',
        xaxis=dict(tickformat="%m/%d\n%H:%M", showgrid=False),
        yaxis=dict(title="수익률 (%)", ticksuffix="%", zeroline=False),
        legend=dict(orientation="h", y=1.1, x=0.5, xanchor="center"),
        margin=dict(l=10, r=10, t=50, b=10)
    )

    st.plotly_chart(fig, use_container_width=True)

if __name__ == "__main__":
    draw_dashboard()
    st.caption("ℹ️ 가중치 안내: DXY(x5), 은(x2) 기본 적용 | 선택 모드에 따라 1위 종목 추가 배수 적용")
