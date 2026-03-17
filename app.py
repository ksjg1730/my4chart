import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.graph_objects as go
from datetime import datetime
import pytz

# 1. 페이지 설정
st.set_page_config(page_title="주간 수익률 대시보드 (10분봉)", layout="wide")

st.title("📊 자산별 주간 수익률 분석 (10분봉)")
st.markdown("##### 🕒 매주 월요일 첫 거래 데이터 기준 리셋 (가중치 반영)")

# 2. 종목 및 설정
# 티커: 이름 (가중치는 로직 내에서 별도 처리)
tickers = {
    'CL=F': 'WTI 원유 선물',
    'SI=F': '글로벌 은 선물',
    'DX-Y.NYB': 'DXY 달러지수',
    'SOXX': '필라델피아 반도체(SOXX)'
}
colors = ['#333333', '#FFD700', '#FF4B4B', '#00CC96']

@st.cache_data(ttl=300) # 5분마다 캐시 갱신
def load_all_data(ticker_dict):
    """모든 티커의 데이터를 한 번에 가져와서 Close 가격만 반환"""
    ticker_list = list(ticker_dict.keys())
    # 10분봉(10m)은 최근 30일 데이터까지만 조회 가능합니다.
    df = yf.download(ticker_list, period='1mo', interval='10m', progress=False)
    
    # 데이터가 비어있을 경우 대응
    if df.empty:
        return pd.DataFrame()

    # 최신 yfinance는 기본적으로 MultiIndex를 반환하므로 'Close' 레벨만 추출
    if isinstance(df.columns, pd.MultiIndex):
        df = df['Close']
    else:
        # 단일 종목일 경우 컬럼명을 티커로 변경
        df = df[['Close']]
        df.columns = ticker_list
        
    # 한국 시간대(KST)로 변환
    df.index = df.index.tz_convert('Asia/Seoul')
    return df

def get_weekly_returns(df, symbol, weight):
    """종목별 주간 리셋 수익률 계산"""
    series = df[symbol].dropna()
    if series.empty:
        return pd.Series(), None

    # 주차별(Year, Week)로 그룹화하여 해당 주의 첫 번째 데이터(기준가) 추출
    # 월요일 09:00 데이터가 없더라도 그 주에 처음 발생한 데이터를 기준으로 잡습니다.
    weekly_first_prices = series.groupby([series.index.year, series.index.isocalendar().week]).transform('first')
    
    # 수익률 계산 및 가중치 적용
    returns = ((series - weekly_first_prices) / weekly_first_prices * 100) * weight
    
    # 리셋 지점(각 주의 첫 데이터 인덱스) 추출
    reset_indices = series.groupby([series.index.year, series.index.isocalendar().week]).idxmin()
    
    return returns, reset_indices

def draw_dashboard():
    all_data = load_all_data(tickers)
    
    if all_data.empty:
        st.error("데이터를 불러오지 못했습니다. 티커를 확인하거나 잠시 후 다시 시도해주세요.")
        return

    fig = go.Figure()
    cols = st.columns(len(tickers))
    all_reset_points = set()

    for i, (symbol, name) in enumerate(tickers.items()):
        # 가중치 설정: 달러지수 5배, 은 2배, 나머지는 1배
        weight = 5 if symbol == 'DX-Y.NYB' else (2 if symbol == 'SI=F' else 1)
        
        returns, reset_points = get_weekly_returns(all_data, symbol, weight)
        
        if returns.empty:
            cols[i].error(f"{name} 데이터 누락")
            continue

        # 상단 지표 표시
        curr_price = all_data[symbol].dropna().iloc[-1]
        curr_ret = returns.iloc[-1]
        display_name = f"{name} ({weight}x)" if weight > 1 else name
        
        cols[i].metric(
            label=display_name, 
            value=f"{curr_price:,.2f}", 
            delta=f"{curr_ret:+.2f}%"
        )

        # 차트 선 추가
        fig.add_trace(go.Scatter(
            x=returns.index, 
            y=returns,
            mode='lines', 
            name=display_name,
            line=dict(width=2, color=colors[i]),
            hovertemplate='<b>' + display_name + '</b><br>%{x|%m/%d %H:%M}<br>수익률: %{y:.2f}%<extra></extra>'
        ))
        
        if reset_points is not None:
            all_reset_points.update(reset_points.tolist())

    # 리셋 라인 (월요일 시작점 표시)
    for rp in all_reset_points:
        fig.add_vline(x=rp, line_dash="dot", line_color="red", opacity=0.2)

    # 0% 기준선
    fig.add_hline(y=0, line_color="black", line_width=1)

    fig.update_layout(
        hovermode="x unified",
        height=600,
        template='plotly_white',
        xaxis=dict(title="", tickformat="%m/%d\n%H:%M"),
        yaxis=dict(title="수익률 (%)", ticksuffix="%"),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        margin=dict(l=0, r=0, t=50, b=0)
    )

    st.plotly_chart(fig, use_container_width=True)

# 메인 실행부
if __name__ == "__main__":
    draw_dashboard()
    
    now_kst = datetime.now(pytz.timezone('Asia/Seoul')).strftime('%Y-%m-%d %H:%M:%S')
    st.divider()
    st.caption(f"🚀 실시간 업데이트 중: {now_kst} (KST) | 데이터 소스: Yahoo Finance (10분봉)")
    st.caption("참고: 수익률은 매주 첫 거래 시점 가격을 0%로 잡고 계산하며, 설정된 가중치가 곱해진 결과입니다.")
