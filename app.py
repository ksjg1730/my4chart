import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.graph_objects as go
import numpy as np

# 1. 페이지 설정
st.set_page_config(page_title="1등선 이평선 분석", layout="wide")

# 2. 종목 및 고유 컬러 설정
tickers = {
    'CL=F': {'name': 'WTI 원유', 'color': '#FF9900'},
    'SI=F': {'name': '글로벌 은', 'color': '#95A5A6'},
    'DX-Y.NYB': {'name': '달러지수', 'color': '#2C3E50'},
    'SOXX': {'name': '반도체(SOXX)', 'color': '#3498DB'}
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
        except: continue
    if not all_data: return None
    return pd.concat(all_data, axis=1).ffill().dropna()

def run_app():
    st.title("📈 1등선 이동평균 및 매수 분석")
    st.markdown("##### 🟢 초록 실선: 1등선 | 🟣 보라 실선: 1등선의 10MA 이평선 | 🟠 황금 점선: 누적 매수 평단가")

    df = get_clean_data()
    if df is None: return

    # --- 📊 데이터 계산 ---
    
    # 1. 매 순간의 1등선
    top1_line = df.max(axis=1)

    # 2. 1등선의 10MA 이동평균선 (Rolling Mean)
    # 주차별로 끊어서 계산하여 주초에 이전 주의 데이터가 섞이지 않도록 함
    top1_ma10 = top1_line.groupby([top1_line.index.year, top1_line.index.isocalendar().week]).rolling(window=10).mean().reset_index(level=[0,1], drop=True)

    # 3. 누적 매수 평균값 (월요일~금요일 14시)
    def calculate_weekly_avg(series):
        groups = series.groupby([series.index.year, series.index.isocalendar().week])
        avg_series = []
        for _, group in groups:
            mask = ~((group.index.weekday == 4) & (group.index.hour >= 14))
            buy_points = group.copy()
            buy_points[~mask] = np.nan 
            group_avg = buy_points.expanding().mean().ffill()
            avg_series.append(group_avg)
        return pd.concat(avg_series)

    avg_line = calculate_weekly_avg(top1_line)

    # --- 📈 그래프 그리기 ---
    fig = go.Figure()

    # 배경: 개별 종목 (아주 흐리게)
    for sym, info in tickers.items():
        if sym in df.columns:
            fig.add_trace(go.Scatter(x=df.index, y=df[sym], name=info['name'],
                                     line=dict(color=info['color'], width=1), opacity=0.2))

    # 1. 실시간 1등선 (초록)
    fig.add_trace(go.Scatter(x=df.index, y=top1_line, name="🏆 1등선",
                             line=dict(color='#2ECC71', width=1.5, opacity=0.7)))

    # 2. 10MA 이동평균선 (보라 - 새로 추가됨)
    fig.add_trace(go.Scatter(x=df.index, y=top1_ma10, name="💜 1등선 10MA",
                             line=dict(color='#9B59B6', width=2.5)))

    # 3. 누적 매수 평단가 (황금 점선)
    fig.add_trace(go.Scatter(x=df.index, y=avg_line, name="💰 누적 평단가",
                             line=dict(color='#F1C40F', width=3, dash='dot')))

    # 4. 슈퍼 1등선 (+3%)
    fig.add_trace(go.Scatter(x=df.index, y=top1_line + 3.0, name="🔥 슈퍼 1등선",
                             line=dict(color='red', width=1, dash='dash')))

    # 월요일 리셋선
    monday_indices = df.index[df.index.weekday == 0]
    if not monday_indices.empty:
        reset_times = df.loc[monday_indices].groupby([monday_indices.year, monday_indices.isocalendar().week]).idxmin().iloc[:, 0]
        for rt in reset_times:
            fig.add_vline(x=rt, line_width=2, line_color="blue", opacity=0.4)

    fig.update_layout(hovermode="x unified", height=750, template="plotly_white",
                      legend=dict(orientation="h", y=1.05, x=0.5, xanchor="center"),
                      margin=dict(l=10, r=10, t=50, b=10))

    st.plotly_chart(fig, use_container_width=True)

if __name__ == "__main__":
    run_app()
