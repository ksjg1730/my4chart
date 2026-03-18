import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.graph_objects as go
import numpy as np

# 1. 페이지 설정
st.set_page_config(page_title="자산별 수익률 대시보드", layout="wide")

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
            # 데이터 다운로드 (최근 1개월, 15분 단위)
            df = yf.download(sym, period='1mo', interval='15m', progress=False)
            if df.empty: continue
            
            # Multi-index 처리 및 종가 선택
            if isinstance(df.columns, pd.MultiIndex):
                close = df['Close'][sym].copy()
            else:
                close = df['Close'].copy()

            # 타임존 처리 (UTC -> Asia/Seoul)
            if close.index.tz is None:
                close.index = close.index.tz_localize('UTC')
            close.index = close.index.tz_convert('Asia/Seoul')

            # 주간 수익률 계산 (매주 월요일 장초반 가격 기준)
            # ISO week와 Year 기준으로 그룹화하여 첫 번째 가격 추출
            weeks = close.index.isocalendar().week
            years = close.index.year
            first_prices = close.groupby([years, weeks]).transform('first')
            
            # 가중치 적용 (달러지수는 변동폭이 작으므로 5배 가중치)
            weight = 5 if sym == 'DX-Y.NYB' else 1
            ret = ((close - first_prices) / first_prices * 100) * weight
            ret.name = sym
            all_data.append(ret)
        except Exception as e:
            st.warning(f"{sym} 데이터 로드 중 오류: {e}")
            continue
    
    if not all_data: return None
    # 모든 종목 데이터를 하나의 DataFrame으로 병합
    return pd.concat(all_data, axis=1).ffill()

def run_app():
    st.title("📊 종목별 수익률 및 슈퍼 1등선")
    st.markdown("##### 🔴 빨간 실선: 슈퍼 1등선 (+3%) | 🔵 파란 세로선: 주간 리셋 (월요일)")

    df = get_clean_data()
    if df is None or df.empty:
        st.error("데이터를 불러올 수 없습니다. API 연결 상태를 확인하세요.")
        return

    # 최신 데이터 추출
    latest = df.iloc[-1]
    
    # --- 🚨 알림 로직 ---
    top_val = latest.max()
    top_sym = latest.idxmax()
    if top_val >= 5.0:
        st.toast(f"🚀 {tickers[top_sym]['name']} 급등 중! ({top_val:.2f}%)", icon="🔥")

    # 상단 지표 (Metric)
    cols = st.columns(len(tickers))
    for i, (sym, info) in enumerate(tickers.items()):
        if sym in latest:
            cols[i].metric(info['name'], f"{latest[sym]:+.2f}%")

    # --- 📈 그래프 그리기 ---
    fig = go.Figure()

    # 1. 각 종목별 수익률 선
    for sym, info in tickers.items():
        if sym in df.columns:
            fig.add_trace(go.Scatter(
                x=df.index, 
                y=df[sym], 
                name=info['name'],
                line=dict(color=info['color'], width=2),
                hovertemplate=f"<b>{info['name']}</b>: %{{y:.2f}}%<extra></extra>"
            ))

    # 2. 🔥 슈퍼 1등선 (실시간 최고 수익률 + 3%)
    t1_line = df.max(axis=1) + 3.0
    fig.add_trace(go.Scatter(
        x=df.index, 
        y=t1_line, 
        name="🔥 슈퍼 1등선 (+3%)",
        line=dict(color='red', width=3, dash='dot'), # 구분을 위해 점선 스타일 추천
        hovertemplate="<b>슈퍼 1등선</b>: %{y:.2f}%<extra></extra>"
    ))

    # 3. 🔵 월요일 리셋 세로선
    # 날짜가 바뀌면서 월요일인 지점 찾기
    reset_dates = df.index[df.index.weekday == 0]
    if not reset_dates.empty:
        # 각 주차별 첫 번째 데이터 포인트 추출
        reset_times = df.loc[reset_dates].groupby([reset_dates.year, reset_dates.isocalendar().week]).apply(lambda x: x.index[0])
        for rt in reset_times:
            fig.add_vline(x=rt, line_width=1.5, line_color="blue", line_dash="dash", opacity=0.6)

    # 레이아웃 설정
    fig.update_layout(
        hovermode="x unified",
        height=650,
        template="plotly_white",
        margin=dict(t=50, b=50, l=50, r=50),
        xaxis=dict(title="시간 (KST)", showgrid=False, tickformat="%m/%d\n%H:%M"),
        yaxis=dict(title="누적 수익률 (%)", ticksuffix="%", gridcolor="#f0f0f0"),
        legend=dict(orientation="h", y=1.1, x=0.5, xanchor="center")
    )

    st.plotly_chart(fig, use_container_width=True)

if __name__ == "__main__":
    run_app()
