
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
            # interval='15m'은 최근 60일 데이터까지만 가능
            df = yf.download(sym, period='1mo', interval='15m', progress=False)
            if not df.empty:
                # MultiIndex 또는 단일 컬럼 대응
                if isinstance(df.columns, pd.MultiIndex):
                    close = df['Close'][sym].copy()
                else:
                    close = df['Close'].copy()
                
                # 한국 시간 변환
                close.index = close.index.tz_convert('Asia/Seoul')
                
                # --- 🕒 금요일 14시 이후 ~ 일요일 자정 데이터 제거 ---
                day_of_week = close.index.weekday  # 0:월, 4:금, 5:토, 6:일
                hour = close.index.hour
                
                # 금요일 14시 이후거나 토/일요일인 경우 NaN 처리
                mask = ((day_of_week == 4) & (hour >= 14)) | (day_of_week == 5) | (day_of_week == 6)
                close.loc[mask] = np.nan
                
                # 주간 수익률 계산 (NaN을 제외한 해당 주의 첫 번째 가격 기준)
                isoweek = close.index.isocalendar().week
                year = close.index.year
                first_price = close.groupby([year, isoweek]).transform('first')
                
                # 가중치 적용 (달러지수 5배)
                weight = 5 if sym == 'DX-Y.NYB' else 1
                ret = ((close - first_price) / first_price * 100) * weight
                ret.name = sym
                all_data.append(ret)
        except Exception as e:
            continue
    
    if not all_data: return None
    # 주말 빈칸을 유지하기 위해 ffill()을 하지 않고 결합
    return pd.concat(all_data, axis=1)

def run_app():
    st.title("📊 종목별 수익률 및 슈퍼 1등선")
    st.markdown("##### 🔴 빨간 점선: 슈퍼 1등선 (+3%) | 🔵 파란 점선: 주간 리셋 | ⏳ 금요일 14시 이후 휴식")

    df = get_clean_data()
    if df is None:
        st.error("데이터를 불러올 수 없습니다. 인터넷 연결이나 티커명을 확인하세요.")
        return

    # 최신 데이터 (NaN이 아닌 마지막 값)
    latest = df.ffill().iloc[-1]
    
    # 상단 지표 레이아웃
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
                connectgaps=False, # NaN 구간에서 선을 끊음
                hovertemplate=f"<b>{info['name']}</b>: %{{y:.2f}}%<extra></extra>"
            ))

    # 2. 🔥 슈퍼 1등선 (실시간 1등 + 3%)
    # 모든 종목 중 최대값에 3% 더함 (주말 NaN 구간은 자동으로 계산 제외)
    t1_line = df.max(axis=1) + 3.0
    fig.add_trace(go.Scatter(
        x=df.index, 
        y=t1_line, 
        name="🔥 슈퍼 1등선 (+3%)",
        line=dict(color='red', width=2, dash='dot'),
        connectgaps=False,
        hovertemplate="<b>슈퍼 1등선</b>: %{y:.2f}%<extra></extra>"
    ))

    # 3. 🔵 주간 리셋선 (월요일 시작점)
    df['week_check'] = df.index.isocalendar().week
    reset_points = df.index[df['week_check'] != df['week_check'].shift(1)]
    for rp in reset_points:
        if rp != df.index[0]:
            fig.add_vline(x=rp, line_width=1.5, line_color="blue", line_dash="dash", opacity=0.5)

    # 레이아웃 설정
    fig.update_layout(
        hovermode="x unified",
        height=700,
        template="plotly_white",
        xaxis=dict(
            title="시간 (KST)", 
            showgrid=False, 
            tickformat="%m/%d %H:%M",
            # 주말 공백을 차트에서 아예 제거하고 싶다면 아래 주석 해제
            # rangebreaks=[dict(bounds=["sat", "mon"])] 
        ),
        yaxis=dict(title="수익률 (%)", ticksuffix="%", gridcolor="#f0f0f0"),
        legend=dict(orientation="h", y=1.05, x=0.5, xanchor="center")
    )

    st.plotly_chart(fig, use_container_width=True)

    # 급등 알림 (토스트)
    if latest.max() >= 5.0:
        top_asset = tickers[latest.idxmax()]['name']
        st.toast(f"🚀 {top_asset} 수익률 5% 돌파!", icon="🔥")

if __name__ == "__main__":
    run_app()
