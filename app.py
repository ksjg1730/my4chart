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
    ticker_symbols = list(tickers.keys())
    # 15분봉, 1개월 데이터 호출
    df = yf.download(
        tickers=ticker_symbols,
        period='1mo',
        interval='15m',
        progress=False
    )
    return df

def draw_dashboard():
    df = load_all_data()
    
    if df is None or df.empty:
        st.error("❌ 데이터를 불러올 수 없습니다. 야후 파이낸스 연결을 확인하세요.")
        return

    fig = go.Figure()
    cols = st.columns(len(tickers))

    # 데이터 구조 대응 (MultiIndex 여부 확인)
    is_multi = isinstance(df.columns, pd.MultiIndex)

    for i, (symbol, name) in enumerate(tickers.items()):
        try:
            # 1. 종가(Close) 데이터 추출
            if is_multi:
                series = df['Close'][symbol].dropna()
            else:
                series = df['Close'].dropna() if len(tickers) == 1 else df[symbol].dropna()
            
            if series.empty:
                continue

            # 2. 시간대 변환
            series.index = series.index.tz_convert('Asia/Seoul')

            # 3. 가중치 및 수익률 계산
            weight = 5 if symbol == 'DX-Y.NYB' else (2 if symbol == 'SI=F' else 1)
            weekly_first = series.groupby([series.index.year, series.index.isocalendar().week]).transform('first')
            returns = ((series - weekly_first) / weekly_first * 100) * weight

            # 4. 상단 지표 (Metric)
            curr_price = series.iloc[-1]
            curr_ret = returns.iloc[-1]
            display_name = f"{name} ({weight}x)" if weight > 1 else name
            
            cols[i].metric(label=display_name, value=f"{curr_price:,.2f}", delta=f"{curr_ret:+.2f}%")

            # 5. 차트 추가
            fig.add_trace(go.Scatter(
                x=returns.index, y=returns,
                mode='lines', name=display_name,
                line=dict(width=2, color=colors[i]),
                hovertemplate='%{x|%m/%d %H:%M}<br>수익률: %{y:.2f}%<extra></extra>'
            ))
            
        except Exception as e:
            cols[i].error(f"{name} 계산 오류")
            continue

    fig.update_layout(
        hovermode="x unified",
        height=600,
        template='plotly_white',
        xaxis=dict(title="", tickformat="%m/%d\n%H:%M"),
        yaxis=dict(title="수익률 (%)", ticksuffix="%"),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        margin=dict(l=0, r=0, t=50, b=0)
    )

    st.plotly_chart(fig, use_container_width=True)

if __name__ == "__main__":
    draw_dashboard()
    now_str = datetime.now(pytz.timezone('Asia/Seoul')).strftime('%Y-%m-%d %H:%M:%S')
    st.caption(f"최근 갱신: {now_str} (KST) | 데이터: 15분봉 | 기준: 매주 첫 거래 데이터")
