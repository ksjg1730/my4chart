import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.graph_objects as go
import numpy as np

# 1. 페이지 설정
st.set_page_config(page_title="누적 슈퍼 1등선 대시보드", layout="wide")

# 2. 종목 및 고유 컬러 설정
tickers = {
    'CL=F': {'name': 'WTI 원유', 'color': '#FF9900'},    # 주황색
    'SI=F': {'name': '글로벌 은', 'color': '#95A5A6'},    # 은색
    'DX-Y.NYB': {'name': '달러지수', 'color': '#2C3E50'}, # 진회색
    'SOXX': {'name': '반도체(SOXX)', 'color': '#3498DB'}  # 파란색
}

@st.cache_data(ttl=60)
def get_clean_data():
    all_data = []
    for sym, info in tickers.items():
        try:
            df = yf.download(sym, period='1mo', interval='15m', progress=False)
            if not df.empty:
                close = df['Close'].copy()
                close.index = close.index.tz_convert('Asia/Seoul')
                
                # 주간 수익률 계산 (월요일 리셋)
                first_price = close.groupby([close.index.year, close.index.isocalendar().week]).transform('first')
                weight = 5 if sym == 'DX-Y.NYB' else 1
                ret = ((close - first_price) / first_price * 100) * weight
                ret.name = sym
                all_data.append(ret)
        except:
            continue
    
    if not all_data: return None
    return pd.concat(all_data, axis=1).ffill().dropna()

def run_app():
    st.title("📈 누적 상승 1등선 & 자산 분석")
    st.markdown("##### 🔴 빨간 계단선: 누적 슈퍼 1등선 (역대 최고점 + 3%) | 🔵 파란 실선: 월요일 리셋")

    df = get_clean_data()
    if df is None:
        st.error("데이터 로드 실패")
        return

    # --- 📈 그래프 로직 ---
    fig = go.Figure()

    # 1. 각 종목별 선 (고유 컬러)
    for sym, info in tickers.items():
        if sym in df.columns:
            fig.add_trace(go.Scatter(
                x=df.index, y=df[sym], 
                name=info['name'],
                line=dict(color=info['color'], width=2),
                opacity=0.8
            ))

    # 2. 🏆 [핵심] 누적 상승 1등선 계산
    # 매 시점의 1등 수치를 뽑은 후, 그 수치들의 '누적 최대값(cummax)'을 구함
    current_best = df.max(axis=1) 
    cumulative_best = current_best.cummax() # 아래로 꺾이지 않고 고점 유지
    super_cumulative_line = cumulative_best + 3.0 # 거기에 3% 더함

    fig.add_trace(go.Scatter(
        x=df.index, 
        y=super_cumulative_line, 
        name="🔥 누적 슈퍼 1등선 (+3%)",
        line=dict(color='red', width=4, shape='hv'), # 'hv' 옵션으로 계단식 강조
        hovertemplate="<b>누적 최고 목표</b>: %{y:.2f}%<extra></extra>"
    ))

    # 3. 🔵 월요일 리셋 실선
    monday_indices = df.index[df.index.weekday == 0]
    if not monday_indices.empty:
        reset_times = df.loc[monday_indices].groupby([monday_indices.year, monday_indices.isocalendar().week]).idxmin().iloc[:, 0]
        for rt in reset_times:
            fig.add_vline(x=rt, line_width=2, line_color="blue", opacity=0.6)

    # 4. 상단 지표 (현재가 기준)
    latest = df.iloc[-1]
    cols = st.columns(len(tickers))
    for i, (sym, info) in enumerate(tickers.items()):
        if sym in latest:
            cols[i].metric(info['name'], f"{latest[sym]:+.2f}%")

    fig.update_layout(
        hovermode="x unified",
        height=750,
        template="plotly_white",
        xaxis=dict(showgrid=False),
        yaxis=dict(title="수익률 (%)", ticksuffix="%", gridcolor="#f0f0f0"),
        legend=dict(orientation="h", y=1.05, x=0.5, xanchor="center")
    )

    st.plotly_chart(fig, use_container_width=True)

if __name__ == "__main__":
    run_app()
