import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.graph_objects as go
import numpy as np

# 1. 페이지 설정
st.set_page_config(page_title="자산별 수익률 대시보드", layout="wide")

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
                
                # 주간 수익률 계산
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
    st.title("📊 종목별 수익률 및 슈퍼 1등선")
    st.markdown("##### 🔴 빨간 실선: 슈퍼 1등선 (+3%) | 🔵 파란 실선: 월요일 리셋")

    df = get_clean_data()
    if df is None:
        st.error("데이터 로드 실패")
        return

    # --- 🚨 알림 로직 ---
    latest = df.iloc[-1]
    top_sym = latest.idxmax()
    if latest.max() >= 5.0:
        st.toast(f"🚀 {tickers[top_sym]['name']} 급등 중!", icon="🔥")

    # 상단 지표
    cols = st.columns(len(tickers))
    for i, (sym, info) in enumerate(tickers.items()):
        if sym in latest:
            cols[i].metric(info['name'], f"{latest[sym]:+.2f}%")

    # --- 📈 그래프 그리기 ---
    fig = go.Figure()

    # 1. 각 종목별 선 (고유 컬러 적용)
    for sym, info in tickers.items():
        if sym in df.columns:
            fig.add_trace(go.Scatter(
                x=df.index, 
                y=df[sym], 
                name=info['name'],
                line=dict(color=info['color'], width=2),
                hovertemplate=f"<b>{info['name']}</b>: %{{y:.2f}}%<extra></extra>"
            ))

    # 2. 🔥 슈퍼 1등선 (실시간 1등 + 3%)
    t1_line = df.max(axis=1) + 3.0
    fig.add_trace(go.Scatter(
        x=df.index, 
        y=t1_line, 
        name="🔥 슈퍼 1등선 (+3%)",
        line=dict(color='red', width=4),
        hovertemplate="<b>슈퍼 1등선</b>: %{y:.2f}%<extra></extra>"
    ))

    # 3. 🔵 월요일 리셋 실선 추가
    monday_indices = df.index[df.index.weekday == 0]
    if not monday_indices.empty:
        # 주별로 가장 빠른 시간대(장 개장 시점) 추출
        reset_times = df.loc[monday_indices].groupby([monday_indices.year, monday_indices.isocalendar().week]).idxmin().iloc[:, 0]
        for rt in reset_times:
            fig.add_vline(x=rt, line_width=2, line_color="blue", opacity=0.8)

    # 레이아웃 설정
    fig.update_layout(
        hovermode="x unified",
        height=700,
        template="plotly_white",
        xaxis=dict(title="시간 (KST)", showgrid=False, tickformat="%m/%d %H:%M"),
        yaxis=dict(title="수익률 (%)", ticksuffix="%", gridcolor="#f0f0f0"),
        legend=dict(orientation="h", y=1.05, x=0.5, xanchor="center")
    )

    st.plotly_chart(fig, use_container_width=True)

if __name__ == "__main__":
    run_app()
