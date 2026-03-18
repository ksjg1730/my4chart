import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.graph_objects as go
import numpy as np

# 1. 페이지 설정
st.set_page_config(page_title="삼성전자-글로벌 지표 분석기", layout="wide")

# 2. 종목 및 기본 설정
tickers = {
    '005930.KS': {'name': '삼성전자', 'color': '#0057D8', 'width': 6}, # 가장 두껍게
    'CL=F': {'name': 'WTI 원유', 'color': '#E67E22', 'width': 2},
    'DX-Y.NYB': {'name': '달러지수(x5)', 'color': '#34495E', 'width': 2},
    'SI=F': {'name': '글로벌 은', 'color': '#BDC3C7', 'width': 2}
}

@st.cache_data(ttl=60)
def get_clean_data():
    all_data = []
    for sym, info in tickers.items():
        try:
            # 15분 단위 데이터 로드
            df = yf.download(sym, period='1mo', interval='15m', progress=False)
            if df.empty: continue
            
            close = df['Close'][sym] if isinstance(df.columns, pd.MultiIndex) else df['Close']
            close = close.copy()
            
            # 시간대 KST 변환
            if close.index.tz is None:
                close.index = close.index.tz_localize('UTC').tz_convert('Asia/Seoul')
            else:
                close.index = close.index.tz_convert('Asia/Seoul')

            # 주간 수익률 계산 (매주 월요일 첫 데이터 기준 0%)
            year_week = close.index.strftime('%Y-%U')
            first_prices = close.groupby(year_week).transform(lambda x: x.dropna().iloc[0] if not x.dropna().empty else np.nan)
            ret = ((close - first_prices) / first_prices * 100)
            
            # 달러지수 변동성 보정 (x5)
            if sym == 'DX-Y.NYB': ret *= 5
            
            ret.name = sym
            all_data.append(ret)
        except: continue
    
    return pd.concat(all_data, axis=1) if all_data else None

def run_app():
    st.title("📊 삼성전자 vs 글로벌 지표 (Y축 ±20% 고정)")
    
    df = get_clean_data()
    if df is None:
        st.error("데이터를 불러오지 못했습니다.")
        return

    fig = go.Figure()

    # 1. 그래프 그리기 (삼성전자를 가장 마지막에 추가하여 레이어 최상단 배치)
    plot_order = ['CL=F', 'DX-Y.NYB', 'SI=F', '005930.KS']
    
    for sym in plot_order:
        if sym in df.columns:
            info = tickers[sym]
            fig.add_trace(go.Scatter(
                x=df.index, y=df[sym],
                name=info['name'],
                line=dict(color=info['color'], width=info['width']),
                connectgaps=True, # 밤 시간대 빈 곳을 직선으로 연결
                hovertemplate=f"<b>{info['name']}</b>: %{{y:.2f}}%<extra></extra>"
            ))

    # 2. 월요일 개장 실선 추가 (09:00 KST)
    monday_starts = df.index[(df.index.weekday == 0) & (df.index.hour == 9) & (df.index.minute == 0)]
    for m_start in monday_starts:
        fig.add_vline(x=m_start, line_width=2, line_dash="solid", line_color="#333333")
        fig.add_annotation(x=m_start, y=1, yref="paper", text="월요일 개장", showarrow=False, font=dict(size=10))

    # 3. 레이아웃 및 X/Y축 최적화
    fig.update_layout(
        hovermode="x unified",
        height=850,
        template="plotly_white",
        xaxis=dict(
            title="날짜/시간 (KST)",
            tickformat="%m/%d %H:%M",
            rangebreaks=[
                dict(bounds=["sat", "mon"]),           # 주말 삭제
                dict(bounds=[15.5, 9], pattern="hour"), # 밤 시간(15:30~09:00) 삭제하여 선 연결
            ]
        ),
        yaxis=dict(
            title="수익률 (%)",
            ticksuffix="%",
            range=[-20, 20],   # 사용자의 요청대로 ±20% 고정
            zeroline=True, 
            zerolinewidth=2, 
            zerolinecolor='black',
            gridcolor='lightgray'
        ),
        legend=dict(orientation="h", y=1.05, x=0.5, xanchor="center"),
        margin=dict(l=10, r=10, t=50, b=10)
    )

    st.plotly_chart(fig, use_container_width=True)

if __name__ == "__main__":
    run_app()
