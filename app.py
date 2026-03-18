import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.graph_objects as go
import numpy as np

# 1. 페이지 설정
st.set_page_config(page_title="슈퍼 1등선 대시보드", layout="wide")

# 2. 사이드바 설정
st.sidebar.header("⚙️ 설정")
alert_val = st.sidebar.number_input("알림 기준 수익률 (%)", value=5.0, step=0.5)

# 3. 데이터 로딩 (종목별 개별 호출로 구조적 오류 방지)
tickers = {'CL=F': '원유', 'SI=F': '은', 'DX-Y.NYB': '달러지수', 'SOXX': '반도체'}

@st.cache_data(ttl=60)
def get_clean_data():
    all_data = []
    for sym, name in tickers.items():
        try:
            # 개별 종목씩 가져와서 구조 오류 차단
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
    # 모든 종목을 시간축 기준으로 합치고 빈칸은 앞의 값으로 채움
    final_df = pd.concat(all_data, axis=1).ffill().dropna()
    return final_df

def run_app():
    st.title("🚀 실시간 자산분석 & 슈퍼 1등선")
    
    df = get_clean_data()
    
    if df is None or df.empty:
        st.error("데이터를 가져오지 못했습니다. 인터넷 연결이나 종목 코드를 확인하세요.")
        return

    # --- 🚨 알림 및 메트릭 ---
    latest = df.iloc[-1]
    top_sym = latest.idxmax()
    top_val = latest.max()

    if top_val >= alert_val:
        st.toast(f"🔥 {tickers[top_sym]} 기준치 돌파!", icon="⚠️")
        st.error(f"🚨 알림: {tickers[top_sym]} 현재 {top_val:.2f}% (기준 {alert_val}% 초과)")

    cols = st.columns(len(tickers))
    for i, (sym, name) in enumerate(tickers.items()):
        if sym in latest:
            cols[i].metric(name, f"{latest[sym]:+.2f}%")

    # --- 📈 그래프 그리기 ---
    fig = go.Figure()

    # 데이터 정렬 (1등, 2등 추출)
    vals = df.values
    sorted_vals = np.sort(vals, axis=1)
    t1 = sorted_vals[:, -1] # 1등선
    t2 = sorted_vals[:, -2] # 2등선
    super_line = t1 + 3.0   # 슈퍼 1등선 (+3%)

    # 1. 배경선 (모든 종목)
    for sym in df.columns:
        fig.add_trace(go.Scatter(x=df.index, y=df[sym], name=tickers[sym], 
                                 line=dict(color='rgba(150,150,150,0.3)', width=1)))

    # 2. 채우기 (2등선 -> 1등선)
    fig.add_trace(go.Scatter(x=df.index, y=t2, line=dict(width=0), showlegend=False, hoverinfo='skip'))
    fig.add_trace(go.Scatter(x=df.index, y=t1, name="현재 1등선", 
                             fill='tonexty', fillcolor='rgba(0,255,100,0.1)',
                             line=dict(color='#2ECC71', width=2)))

    # 3. 🔥 슈퍼 1등선 (빨간색 강조)
    fig.add_trace(go.Scatter(x=df.index, y=super_line, name="🔥 슈퍼 1등선 (+3%)",
                             line=dict(color='red', width=4)))

    fig.update_layout(
        hovermode="x unified",
        height=650,
        template="plotly_white",
        xaxis=dict(showgrid=False),
        yaxis=dict(ticksuffix="%", gridcolor="#eee")
    )

    st.plotly_chart(fig, use_container_width=True)

if __name__ == "__main__":
    run_app()
