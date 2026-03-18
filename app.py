import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.graph_objects as go
import numpy as np

# 1. 페이지 설정
st.set_page_config(page_title="삼성전자 vs 글로벌 지표", layout="wide")

# 2. 종목 및 기본 설정
tickers = {
    '005930.KS': {'name': '삼성전자', 'color': '#0057D8', 'width': 5}, # 삼성전자 강조
    'CL=F': {'name': 'WTI 원유', 'color': '#E67E22', 'width': 1.5},
    'DX-Y.NYB': {'name': '달러지수', 'color': '#34495E', 'width': 1.5},
    'SI=F': {'name': '글로벌 은', 'color': '#BDC3C7', 'width': 1.5}
}

@st.cache_data(ttl=60)
def get_clean_data():
    all_data = []
    for sym, info in tickers.items():
        try:
            # 데이터 로드 (최근 1개월, 15분봉)
            df = yf.download(sym, period='1mo', interval='15m', progress=False)
            if df.empty: continue
            
            # Close 데이터 추출 (MultiIndex 대응)
            close = df['Close'][sym] if isinstance(df.columns, pd.MultiIndex) else df['Close']
            close = close.copy()
            
            # 시간대 변환 (KST)
            if close.index.tz is None:
                close.index = close.index.tz_localize('UTC').tz_convert('Asia/Seoul')
            else:
                close.index = close.index.tz_convert('Asia/Seoul')

            # --- 🕒 시간 필터링 ---
            day_of_week = close.index.weekday
            hour = close.index.hour
            
            if sym == '005930.KS':
                # 삼성전자: 장중 시간만 남김 (09:00 ~ 15:30)
                minute = close.index.minute
                t_min = hour * 60 + minute
                mask = (t_min < 540) | (t_min > 930) | (day_of_week >= 5)
                close.loc[mask] = np.nan
            else:
                # 해외자산: 주말만 제거
                mask = ((day_of_week == 4) & (hour >= 15)) | (day_of_week >= 5)
                close.loc[mask] = np.nan

            # --- 📈 주간 수익률 계산 (월요일 시점 기준) ---
            year_week = close.index.strftime('%Y-%U')
            # 해당 주의 첫 번째 유효한 가격 찾기
            first_prices = close.groupby(year_week).transform(lambda x: x.dropna().iloc[0] if not x.dropna().empty else np.nan)
            ret = ((close - first_prices) / first_prices * 100)
            
            # 달러지수 가중치 (변동성 보정)
            if sym == 'DX-Y.NYB': ret *= 5
            
            ret.name = sym
            all_data.append(ret)
        except: continue
    
    return pd.concat(all_data, axis=1) if all_data else None

def run_app():
    st.title("📊 삼성전자 & 글로벌 지표 주간 비교")
    st.markdown("##### 🟦 삼성전자 두껍게 | 📏 월요일 개장 실선 | ✂️ 주말 공백 제거")

    df = get_clean_data()
    if df is None or df.empty:
        st.error("데이터를 가져오지 못했습니다.")
        return

    fig = go.Figure()

    # 1. 그래프 그리기 (삼성전자를 가장 마지막에 그려서 위로 올림)
    plot_order = ['CL=F', 'DX-Y.NYB', 'SI=F', '005930.KS']
    
    for sym in plot_order:
        if sym in df.columns:
            info = tickers[sym]
            fig.add_trace(go.Scatter(
                x=df.index, y=df[sym],
                name=info['name'],
                line=dict(color=info['color'], width=info['width']),
                connectgaps=False,
                hovertemplate=f"<b>{info['name']}</b>: %{{y:.2f}}%<extra></extra>"
            ))

    # 2. 월요일 개장 실선 추가 (Vertical Lines)
    # 데이터셋에서 월요일의 첫 번째 인덱스들을 추출
    monday_starts = df.index[
        (df.index.weekday == 0) & 
        (df.index.hour == 9) & 
        (df.index.minute == 0)
    ]
    
    for m_start in monday_starts:
        fig.add_vline(x=m_start, line_width=1.5, line_dash="solid", line_color="black")
        fig.add_annotation(x=m_start, y=1.02, yref="paper", text="월요일 개장", showarrow=False)

    # 3. 레이아웃 설정
    fig.update_layout(
        hovermode="x unified",
        height=750,
        template="plotly_white",
        xaxis=dict(
            title="시간 (KST)",
            tickformat="%m/%d %H:%M",
            rangebreaks=[
                dict(bounds=["sat", "mon"]), # 주말 제거
                dict(bounds=[16, 9], pattern="hour"), # 야간 시간 제거 (삼성전자 기준 가독성)
            ]
        ),
        yaxis=dict(
            title="수익률 (%)",
            ticksuffix="%",
            zeroline=True, zerolinewidth=2, zerolinecolor='gray'
        ),
        legend=dict(orientation="h", y=1.08, x=0.5, xanchor="center")
    )

    st.plotly_chart(fig, use_container_width=True)

if __name__ == "__main__":
    run_app()
