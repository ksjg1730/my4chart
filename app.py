import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.graph_objects as go
import numpy as np

# 1. 페이지 설정
st.set_page_config(page_title="1등선 누적 매수 분석", layout="wide")

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
                first_price = close.groupby([close.index.year, close.index.isocalendar().week]).transform('first')
                weight = 5 if sym == 'DX-Y.NYB' else 1
                ret = ((close - first_price) / first_price * 100) * weight
                ret.name = sym
                all_data.append(ret)
        except: continue
    if not all_data: return None
    return pd.concat(all_data, axis=1).ffill().dropna()

def run_app():
    st.title("🏆 1등선 가상 종목 매수 시뮬레이션")
    st.markdown("##### 🟢 초록 실선: 매 순간 1등선 | 🟠 황금 점선: 1등선 누적 매수 평균값 (월~금 14시)")

    df = get_clean_data()
    if df is None: return

    # --- 📊 데이터 계산 로직 ---
    
    # 1. 매 순간의 1등선 (가상 종목)
    top1_line = df.max(axis=1)

    # 2. 누적 매수 평균값 계산 (Expanding Mean per Week)
    # 월요일부터 금요일 14시까지만 데이터를 필터링하여 누적 평균 계산
    def calculate_weekly_avg(series):
        # 주차별 그룹화
        groups = series.groupby([series.index.year, series.index.isocalendar().week])
        avg_series = []
        
        for _, group in groups:
            # 금요일 오후 2시(14:00) 이전 데이터만 매수 대상으로 간주
            # (그 이후는 매수 중단 상태로 마지막 평균값 유지)
            mask = ~((group.index.weekday == 4) & (group.index.hour >= 14))
            buy_points = group.copy()
            # 매수 중단 이후 데이터는 NaN 처리 후 ffill로 평균값 고정 효과
            buy_points[~mask] = np.nan 
            
            # 누적 평균(Expanding Mean) 계산
            group_avg = buy_points.expanding().mean().ffill()
            avg_series.append(group_avg)
            
        return pd.concat(avg_series)

    avg_line = calculate_weekly_avg(top1_line)

    # --- 📈 그래프 그리기 ---
    fig = go.Figure()

    # 배경: 개별 종목 (흐리게)
    for sym, info in tickers.items():
        if sym in df.columns:
            fig.add_trace(go.Scatter(x=df.index, y=df[sym], name=info['name'],
                                     line=dict(color=info['color'], width=1), opacity=0.3))

    # 핵심 1: 1등선 (이전 모드의 일등선)
    fig.add_trace(go.Scatter(x=df.index, y=top1_line, name="🏆 실시간 1등선",
                             line=dict(color='#2ECC71', width=2.5)))

    # 핵심 2: 누적 매수 평균값 선
    fig.add_trace(go.Scatter(x=df.index, y=avg_line, name="💰 누적 매수 평균",
                             line=dict(color='#F1C40F', width=3, dash='dot')))

    # 슈퍼 1등선 (요청하신 빨간색 +3%도 유지)
    fig.add_trace(go.Scatter(x=df.index, y=top1_line + 3.0, name="🔥 슈퍼 1등선 (+3%)",
                             line=dict(color='red', width=1.5, dash='dash')))

    # 월요일 리셋선 (파란색)
    monday_indices = df.index[df.index.weekday == 0]
    if not monday_indices.empty:
        reset_times = df.loc[monday_indices].groupby([monday_indices.year, monday_indices.isocalendar().week]).idxmin().iloc[:, 0]
        for rt in reset_times:
            fig.add_vline(x=rt, line_width=2, line_color="blue", opacity=0.5)

    fig.update_layout(hovermode="x unified", height=750, template="plotly_white",
                      legend=dict(orientation="h", y=1.05, x=0.5, xanchor="center"))

    st.plotly_chart(fig, use_container_width=True)

if __name__ == "__main__":
    run_app()
