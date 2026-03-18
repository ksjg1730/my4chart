import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.graph_objects as go
import numpy as np

# 1. 페이지 설정
st.set_page_config(page_title="자산별 수익률 및 스프레드 대시보드", layout="wide")

# 2. 종목 및 고유 컬러 설정
tickers = {
    'CL=F': {'name': 'WTI 원유', 'color': '#FF9900'},    # 주황색
    'SI=F': {'name': '글로벌 은', 'color': '#95A5A6'},    # 은색
    'DX-Y.NYB': {'name': '달러지수', 'color': '#2C3E50'}, # 진회색
    'HG=F': {'name': '구리(HG=F)', 'color': '#D35400'}    # 구리색
}

@st.cache_data(ttl=60)
def get_clean_data():
    all_data = []
    for sym, info in tickers.items():
        try:
            df = yf.download(sym, period='1mo', interval='15m', progress=False)
            if not df.empty:
                if isinstance(df.columns, pd.MultiIndex):
                    close = df['Close'][sym].copy()
                else:
                    close = df['Close'].copy()
                
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
                
                # 가중치 적용
                if sym == 'DX-Y.NYB':
                    weight = 5
                elif sym == 'HG=F':
                    weight = 2
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
    st.title("📊 자산 수익률 및 [은-구리] 스프레드")
    st.markdown("##### 🔴 빨간 점선: 슈퍼 1등선 (+3%) | 🖤 검정 실선: 은 - 구리 스프레드 | ⏳ 금요일 14시 이후 휴식")

    df = get_clean_data()
    if df is None:
        st.error("데이터 로드 실패")
        return

    # --- 📈 스프레드 계산 (은 - 구리) ---
    if 'SI=F' in df.columns and 'HG=F' in df.columns:
        df['Spread_SI_HG'] = df['SI=F'] - df['HG=F']

    latest = df.ffill().iloc[-1]
    
    # 상단 지표
    cols = st.columns(len(tickers) + 1)
    for i, (sym, info) in enumerate(tickers.items()):
        if sym in latest:
            cols[i].metric(info['name'], f"{latest[sym]:+.2f}%")
    
    # 스프레드 지표 추가
    if 'Spread_SI_HG' in latest:
        cols[-1].metric("은-구리 차이", f"{latest['Spread_SI_HG']:+.2f}%", delta_color="off")

    fig = go.Figure()

    # 1. 종목별 선
    for sym, info in tickers.items():
        if sym in df.columns:
            fig.add_trace(go.Scatter(
                x=df.index, y=df[sym], name=info['name'],
                line=dict(color=info['color'], width=1.5, opacity=0.6), # 기존선은 약간 연하게
                connectgaps=False
            ))

    # 2. 🖤 은 - 구리 스프레드 선 (강조)
    if 'Spread_SI_HG' in df.columns:
        fig.add_trace(go.Scatter(
            x=df.index, y=df['Spread_SI_HG'], 
            name="📊 은 - 구리 스프레드",
            line=dict(color='black', width=3), # 두꺼운 검정 실선
            connectgaps=False,
            hovertemplate="<b>은-구리 스프레드</b>: %{y:.2f}%<extra></extra>"
        ))

    # 3. 🔥 슈퍼 1등선
    # 스프레드 선을 제외한 종목들 중 최대값 + 3%
    stock_cols = [c for c in df.columns if c in tickers]
    t1_line = df[stock_cols].max(axis=1) + 3.0
    fig.add_trace(go.Scatter(
        x=df.index, y=t1_line, name="🔥 슈퍼 1등선 (+3%)",
        line=dict(color='red', width=2, dash='dot'),
        connectgaps=False
    ))

    # 4. 🔵 주간 리셋선
    df['week_check'] = df.index.isocalendar().week
    reset_points = df.index[df['week_check'] != df['week_check'].shift(1)]
    for rp in reset_points:
        if rp != df.index[0]:
            fig.add_vline(x=rp, line_width=1.5, line_color="blue", line_dash="dash", opacity=0.3)

    fig.update_layout(
        hovermode="x unified",
        height=750,
        template="plotly_white",
        xaxis=dict(title="시간 (KST)", tickformat="%m/%d %H:%M"),
        yaxis=dict(title="수익률 및 스프레드 (%)", ticksuffix="%", gridcolor="#f0f0f0"),
        legend=dict(orientation="h", y=1.05, x=0.5, xanchor="center")
    )

    st.plotly_chart(fig, use_container_width=True)

if __name__ == "__main__":
    run_app()
