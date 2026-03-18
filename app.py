import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.graph_objects as go
import numpy as np

# 1. 페이지 설정
st.set_page_config(page_title="삼성전자 주간 분석기", layout="wide")

# 2. 종목 및 기본 설정
tickers = {
    'CL=F': {'name': 'WTI 원유', 'color': '#E67E22'},
    'DX-Y.NYB': {'name': '달러지수', 'color': '#34495E'},
    '005930.KS': {'name': '삼성전자', 'color': '#0057D8'}, # 구리 대신 삼성전자 추가 (파란색)
    'SI=F': {'name': '글로벌 은', 'color': '#BDC3C7'}
}

@st.cache_data(ttl=60)
def get_clean_data():
    all_data = []
    # 데이터 확보를 위해 period를 '2mo'로 변경
    for sym, info in tickers.items():
        try:
            # 삼성전자는 국내 주식이므로 장중 데이터 로드 방식이 다를 수 있음
            # 일단 15분 단위 데이터 로드 (최근 1개월)
            df = yf.download(sym, period='1mo', interval='15m', progress=False)
            if not df.empty:
                close = df['Close'][sym] if isinstance(df.columns, pd.MultiIndex) else df['Close']
                close = close.copy()
                
                # 시간대 변환
                if sym == '005930.KS':
                    # 삼성전자는 이미 KST (Asia/Seoul)
                    if close.index.tz is None:
                        close.index = close.index.tz_localize('Asia/Seoul')
                else:
                    # 해외 지수는 UTC -> KST
                    if close.index.tz is None:
                        close.index = close.index.tz_localize('UTC').tz_convert('Asia/Seoul')
                    else:
                        close.index = close.index.tz_convert('Asia/Seoul')
                
                # --- 🕒 데이터 필터링: 국내 장외 시간 삭제 ---
                if sym == '005930.KS':
                     # 삼성전자는 국내 주식 거래 시간(09:00 ~ 15:30) 외에는 NaN 처리
                     # (주말은 pattern='sat', 'mon'으로 처리됨)
                     day_of_week = close.index.weekday
                     hour = close.index.hour
                     minute = close.index.minute
                     time_in_minutes = hour * 60 + minute
                     # 9시(540분) 이전 또는 15시 30분(930분) 이후 제외
                     mask = (time_in_minutes < 540) | (time_in_minutes > 930)
                     close.loc[mask] = np.nan
                else:
                    # 해외 지수는 금요일 14:00 이후 ~ 월요일 개장 전 삭제 유지
                    day_of_week = close.index.weekday
                    hour = close.index.hour
                    # 금요일(4) 14시 이후 OR 토요일(5) OR 일요일(6) 데이터 제외
                    mask = ((day_of_week == 4) & (hour >= 14)) | (day_of_week >= 5)
                    close.loc[mask] = np.nan
                
                # 주간 수익률 계산
                year, week = close.index.year, close.index.isocalendar().week
                first_price = close.groupby([year, week]).transform('first')
                # 첫 가격이 NaN인 경우 (주말) 바로 다음 유효한 가격을 찾음
                first_price = first_price.fillna(method='bfill')
                
                ret = ((close - first_price) / first_price * 100)
                
                # 가중치 적용 (달러 x5)
                if sym == 'DX-Y.NYB': ret *= 5
                
                ret.name = sym
                all_data.append(ret)
        except: continue
    
    return pd.concat(all_data, axis=1) if all_data else None

def run_app():
    st.title("📊 삼성전자 주간 수익률 분석기")
    st.markdown("##### ✨ 삼성전자 강조 | 🌫 배경지표(원유/달러/은) 투명화 | ✂️ 주말 및 장외 타임라인 삭제")

    df = get_clean_data()
    if df is None:
        st.error("데이터를 불러오는 데 실패했습니다.")
        return

    # --- 🔍 데이터 필터링 (-1% 미만 수치 제거 로직은 삼성전자 단독 차트이므로 제외) ---
    df_filtered = df.copy()

    fig = go.Figure()

    # 1. 🌫 배경: 타 자산 (투명하지 않게 색상 적용)
    background_tickers = ['CL=F', 'DX-Y.NYB', 'SI=F']
    for sym in background_tickers:
        if sym in df_filtered.columns:
            info = tickers[sym]
            fig.add_trace(go.Scatter(
                x=df_filtered.index, y=df_filtered[sym], 
                name=f"{info['name']} (참고)",
                opacity=1.0, line=dict(color=info['color'], width=1), # opacity 1.0으로 변경
                connectgaps=False, hoverinfo='skip'
            ))

    # 2. 🚀 주인공: 삼성전자 (굵고 선명하게)
    samsung_ticker = '005930.KS'
    if samsung_ticker in df_filtered.columns:
        info = tickers[samsung_ticker]
        fig.add_trace(go.Scatter(
            x=df_filtered.index, y=df_filtered[samsung_ticker], 
            name=info['name'],
            line=dict(color=info['color'], width=4), 
            connectgaps=False,
            hovertemplate=f"<b>{info['name']}</b>: %{{y:.2f}}%<extra></extra>"
        ))

    # --- 🌫 1등선 & 3등선 로직은 삼성전자 단독 차트이므로 제외 ---

    # 4. 레이아웃 및 X축 타임라인 압축
    fig.update_layout(
        hovermode="x unified",
        height=800,
        template="plotly_white",
        xaxis=dict(
            title="시간 (KST)", 
            tickformat="%m/%d %H:%M",
            # --- ✂️ 주말 공백 삭제 설정 ---
            rangebreaks=[
                # 해외 지수 기준 주말
                dict(bounds=[14, 24], pattern="hour"), # 금요일 14시 ~ 24시 삭제
                dict(bounds=["sat", "mon"]),           # 토요일 ~ 월요일 아침 삭제
                # 삼성전자 기준 장외 시간 (추가)
                # KST 15:30 ~ 익일 09:00 삭제
                dict(bounds=[15.5, 9], pattern="hour")
            ]
        ),
        yaxis=dict(
            title="주간 수익률 (%)", 
            ticksuffix="%", 
            zeroline=True, zerolinewidth=1, zerolinecolor='black' # 0선 추가
        ),
        legend=dict(orientation="h", y=1.05, x=0.5, xanchor="center")
    )

    st.plotly_chart(fig, use_container_width=True)

if __name__ == "__main__":
    run_app()
