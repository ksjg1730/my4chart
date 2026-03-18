import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.graph_objects as go
import numpy as np

# 1. 페이지 설정
st.set_page_config(page_title="삼성전자-글로벌 지표 최적화", layout="wide")

# 2. 종목 및 기본 설정
tickers = {
    '005930.KS': {'name': '삼성전자', 'color': '#0057D8', 'width': 5},
    'CL=F': {'name': 'WTI 원유', 'color': '#E67E22', 'width': 2},
    'DX-Y.NYB': {'name': '달러지수', 'color': '#34495E', 'width': 2},
    'SI=F': {'name': '글로벌 은', 'color': '#BDC3C7', 'width': 2}
}

@st.cache_data(ttl=60)
def get_clean_data():
    all_data = []
    for sym, info in tickers.items():
        try:
            df = yf.download(sym, period='1mo', interval='15m', progress=False)
            if df.empty: continue
            
            close = df['Close'][sym] if isinstance(df.columns, pd.MultiIndex) else df['Close']
            close = close.copy()
            
            # 시간대 KST 변환
            if close.index.tz is None:
                close.index = close.index.tz_localize('UTC').tz_convert('Asia/Seoul')
            else:
                close.index = close.index.tz_convert('Asia/Seoul')

            # 주간 수익률 계산 (월요일 첫 데이터 기준 0%)
            year_week = close.index.strftime('%Y-%U')
            first_prices = close.groupby(year_week).transform(lambda x: x.dropna().iloc[0] if not x.dropna().empty else np.nan)
            ret = ((close - first_prices) / first_prices * 100)
            
            if sym == 'DX-Y.NYB': ret *= 5 # 달러 가중치
            
            ret.name = sym
            all_data.append(ret)
        except: continue
    
    return pd.concat(all_data, axis=1) if all_data else None

def run_app():
    st.title("📊 삼성전자 중심 글로벌 지표 분석 (밤 시간 압축)")
    
    df = get_clean_data()
    if df is None: return

    fig = go.Figure()

    # 1. 배경 지표 (해외 자산)
    for sym in ['CL=F', 'DX-Y.NYB', 'SI=F']:
        if sym in df.columns:
            info = tickers[sym]
            fig.add_trace(go.Scatter(
                x=df.index, y=df[sym],
                name=info['name'],
                line=dict(color=info['color'], width=info['width']),
                connectgaps=True # 비는 구간 연결
            ))

    # 2. 주인공 (삼성전자) - 가장 위에 그림
    if '005930.KS' in df.columns:
        info = tickers['005930.KS']
        fig.add_trace(go.Scatter(
            x=df.index, y=df['005930.KS'],
            name=info['name'],
            line=dict(color=info['color'], width=info['width']),
            connectgaps=True # 밤 시간대를 직선으로 연결
        ))

    # 3. 월요일 개장 실선 (09:00 기준)
    monday_starts = df.index[(df.index.weekday == 0) & (df.index.hour == 9) & (df.index.minute == 0)]
    for m_start in monday_starts:
        fig.add_vline(x=m_start, line_width=2, line_dash="solid", line_color="black")

    # 4. 레이아웃: 밤 시간(15:30 ~ 익일 09:00) 삭제
    fig.update_layout(
        hovermode="x unified",
        height=800,
        xaxis=dict(
            rangebreaks=[
                dict(bounds=["sat", "mon"]), # 주말 삭제
                dict(bounds=[15.5, 9], pattern="hour"), # 15:30부터 09:00까지 삭제 (핵심)
            ]
        ),
        yaxis=dict(title="수익률 (%)", zeroline=True, zerolinewidth=2),
        legend=dict(orientation="h", y=1.05, x=0.5, xanchor="center")
    )

    st.plotly_chart(fig, use_container_width=True)

if __name__ == "__main__":
    run_app()
