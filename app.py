import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.graph_objects as go
import numpy as np

# 1. 페이지 설정
st.set_page_config(page_title="자산별 수익률 대시보드", layout="wide")

# 2. 종목 및 고유 컬러 설정 (채권 -> 구리 'HG=F'로 변경)
tickers = {
    'CL=F': {'name': 'WTI 원유', 'color': '#FF9900'},    # 주황색
    'SI=F': {'name': '글로벌 은', 'color': '#95A5A6'},    # 은색
    'DX-Y.NYB': {'name': '달러지수', 'color': '#2C3E50'}, # 진회색
    'HG=F': {'name': '구리(HG=F)', 'color': '#D35400'}    # 구리색(진한 주황)
}

@st.cache_data(ttl=60)
def get_clean_data():
    all_data = []
    for sym, info in tickers.items():
        try:
            df = yf.download(sym, period='1mo', interval='15m', progress=False)
            if not df.empty:
                # 데이터 구조 대응
                if isinstance(df.columns, pd.MultiIndex):
                    close = df['Close'][sym].copy()
                else:
                    close = df['Close'].copy()
                
                # 한국 시간 변환
                close.index = close.index.tz_convert('Asia/Seoul')
                
                # --- 🕒 금요일 14시 이후 데이터 제거 ---
                day_of_week = close.index.weekday
                hour = close.index.hour
                mask = ((day_of_week == 4) & (hour >= 14)) | (day_of_week == 5) | (day_of_week == 6)
                close.loc[mask] = np.nan
                
                # 주간 수익률 계산
                isoweek = close.index.isocalendar().week
                year = close.index.year
                first_price = close.groupby([year, isoweek]).transform('first')
                
                # --- ⚖️ 가중치 적용 로직 ---
                if sym == 'DX-Y.NYB':
                    weight = 5
                elif sym == 'HG=F':
                    weight = 20  # 구리 수익률 20배 가중치 적용
                else:
                    weight = 1
                
                ret = ((close - first_price) / first_price * 100) * weight
                ret.name = sym
                all_data.append(ret)
        except:
            continue
    
    if not all_data: return None
    return pd.concat(all_data, axis=1)

def run_app():
    st.title("📊 자산별 수익률 및 슈퍼 1등선")
    st.markdown("##### 🔴 빨간 점선: 슈퍼 1등선 (+3%) | 🔵 파란 점선: 주간 리셋 | ⚖️ 가중치: 달러 x5, 구리 x20")

    df = get_clean_data()
    if df is None:
        st.error("데이터를 불러올 수 없습니다.")
        return

    # 마지막 유효 데이터 추출
    latest = df.ffill().iloc[-1]
    
    # 상단 지표
    cols = st.columns(len(tickers))
    for i, (sym, info) in enumerate(tickers.items()):
        if sym in latest:
            cols[i].metric(info['name'], f"{latest[sym]:+.2f}%")

    fig = go.Figure()

    # 1. 종목별 선
    for sym, info in tickers.items():
        if sym in df.columns:
            fig.add_trace(go.Scatter(
                x=df.index, y=df[sym], name=info['name'],
                line=dict(color=info['color'], width=2),
                connectgaps=False,
                hovertemplate=f"<b>{info['name']}</b>: %{{y:.2f}}%<extra></extra>"
            ))

    # 2. 🔥 슈퍼 1등선
    t1_line = df.max(axis=1) + 3.0
    fig.add_trace(go.Scatter(
        x=df.index, y=t1_line, name="🔥 슈퍼 1등선 (+3%)",
        line=dict(color='red', width=2, dash='dot'),
        connectgaps=False
    ))

    # 3. 🔵 주간 리셋선
    df['week_check'] = df.index.isocalendar().week
    reset_points = df.index[df['week_check'] != df['week_check'].shift(1)]
    for rp in reset_points:
        if rp != df.index[0]:
            fig.add_vline(x=rp, line_width=1.5, line_color="blue", line_dash="dash", opacity=0.4)

    fig.update_layout(
        hovermode="x unified",
        height=700,
        template="plotly_white",
        xaxis=dict(title="시간 (KST)", tickformat="%m/%d %H:%M"),
        yaxis=dict(title="수익률 (가중치 적용 %)", ticksuffix="%", gridcolor="#f0f0f0"),
        legend=dict(orientation="h", y=1.05, x=0.5, xanchor="center")
    )

    st.plotly_chart(fig, use_container_width=True)

if __name__ == "__main__":
    run_app()
