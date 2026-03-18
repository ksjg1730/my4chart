import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.graph_objects as go
import numpy as np

# 1. 페이지 설정
st.set_page_config(page_title="슈퍼 1등선 & 알림 대시보드", layout="wide")

# 2. 스타일 설정
st.markdown("""
    <style>
        .stMetric { border: 1px solid #f0f2f6; padding: 10px; border-radius: 10px; background-color: #ffffff; }
    </style>
""", unsafe_allow_html=True)

# 3. 사이드바 및 알림 설정
st.sidebar.header("📊 설정")
version = st.sidebar.selectbox("모드 선택", ["원본 버전", "슈퍼 1등선 모드"])
alert_threshold = st.sidebar.slider("알림 임계치 (수익률 %)", 0.0, 10.0, 5.0) # 특정 수익률 넘으면 알림
is_super_mode = (version == "슈퍼 1등선 모드")

st.title("🔥 자산 분석 및 실시간 알림")

# 4. 종목 설정
tickers_raw = {'CL=F': '원유', 'SI=F': '은', 'DX-Y.NYB': '달러지수', 'SOXX': '반도체'}

@st.cache_data(ttl=60) # 알림을 위해 캐시 시간을 1분으로 단축
def load_all_data():
    ticker_symbols = list(tickers_raw.keys())
    df = yf.download(tickers=ticker_symbols, period='1mo', interval='15m', progress=False)
    return df['Close'] if not df.empty else None

def draw_dashboard():
    df_close = load_all_data()
    if df_close is None:
        st.error("데이터 로드 실패")
        return

    df_close.index = df_close.index.tz_convert('Asia/Seoul')
    
    # --- 데이터 처리 ---
    all_returns = []
    for symbol, name in tickers_raw.items():
        if symbol not in df_close.columns: continue
        series = df_close[symbol].dropna()
        weekly_first = series.groupby([series.index.year, series.index.isocalendar().week]).transform('first')
        weight = 5 if symbol == 'DX-Y.NYB' else 1
        ret = ((series - weekly_first) / weekly_first * 100) * weight
        ret.name = symbol
        all_returns.append(ret)

    df_returns = pd.concat(all_returns, axis=1).ffill().dropna() # 결측치 완벽 제거로 그래프 끊김 방지
    
    # --- 🚨 알림 로직 (가장 최근 데이터 기준) ---
    latest_row = df_returns.iloc[-1]
    top_asset = latest_row.idxmax()
    top_value = latest_row.max()

    if top_value >= alert_threshold:
        st.toast(f"🚀 {tickers_raw[top_asset]} 급등! ({top_value:.2f}%)", icon="🔥")
        st.error(f"⚠️ 알림: {tickers_raw[top_asset]} 수익률이 설정치({alert_threshold}%)를 초과했습니다!")

    # 상단 지표
    current_res = [{"name": tickers_raw[s], "val": df_returns[s].iloc[-1], "price": df_close[s].iloc[-1]} for s in df_returns.columns]
    current_res.sort(key=lambda x: x['val'], reverse=True)
    cols = st.columns(len(current_res))
    for i, res in enumerate(current_res):
        cols[i].metric(label=res['name'], value=f"{res['price']:,.2f}", delta=f"{res['val']:+.2f}%")

    # --- 그래프 ---
    fig = go.Figure()

    if is_super_mode:
        vals = df_returns.values
        sorted_vals = np.sort(vals, axis=1)
        top1 = sorted_vals[:, -1]
        top2 = sorted_vals[:, -2]
        super_line = top1 + 3.0 # 3% 상향

        # 1. 배경 (회색)
        for s in df_returns.columns:
            fig.add_trace(go.Scatter(x=df_returns.index, y=df_returns[s], line=dict(color='lightgrey', width=1), name=tickers_raw[s]))

        # 2. 채우기 레이어 (2등선 -> 1등선)
        fig.add_trace(go.Scatter(x=df_returns.index, y=top2, line=dict(width=0), showlegend=False, hoverinfo='skip'))
        fig.add_trace(go.Scatter(x=df_returns.index, y=top1, fill='tonexty', fillcolor='rgba(0, 255, 100, 0.2)', line=dict(color='green', width=2), name='1등선'))

        # 3. 슈퍼 1등선 (붉은색)
        fig.add_trace(go.Scatter(x=df_returns.index, y=super_line, line=dict(color='red', width=4), name='🔥 슈퍼 1등선 (+3%)'))
    else:
        for s in df_returns.columns:
            fig.add_trace(go.Scatter(x=df_returns.index, y=df_returns[s], name=tickers_raw[s]))

    fig.update_layout(hovermode="x unified", height=600, template='plotly_white')
    st.plotly_chart(fig, use_container_width=True)

if __name__ == "__main__":
    draw_dashboard()
