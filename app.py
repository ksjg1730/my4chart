import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.graph_objects as go
from datetime import datetime, timedelta

# 1. 페이지 설정
st.set_page_config(page_title="주간/월간 수익률 대시보드", layout="wide")

st.title("📊 자산별 수익률 분석 (주간 & 월간 리셋)")

# 2. 종목 설정
tickers = {
    'CL=F': 'WTI 원유 선물',
    'SI=F': '글로벌 은 선물 (2x)',
    'DX-Y.NYB': 'DXY 달러지수 (5x)',
    '233740.KS': 'KODEX 코스닥150레버리지'
}

# 데이터 수집 함수 (캐싱)
@st.cache_data(ttl=600)
def load_data(symbol):
    # 월간 데이터를 위해 2개월치 로드
    df = yf.download(symbol, period='2mo', interval='30m', progress=False)
    if not df.empty:
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.get_level_values(0)
        df.index = df.index.tz_convert('Asia/Seoul')
    return df

# 차트 생성 함수
def create_chart(mode='weekly'):
    fig = go.Figure()
    # 고유 ID 생성을 위한 prefix
    prefix = "week" if mode == 'weekly' else "month"
    
    # 지표를 표시할 컬럼 생성
    cols = st.columns(len(tickers))
    colors = ['#333333', '#FFD700', '#FF4B4B', '#00CC96']
    all_indices = []

    for i, (symbol, name) in enumerate(tickers.items()):
        df = load_data(symbol).copy() # 데이터 복사본 사용
        if df.empty: continue
        
        # --- 기준가 계산 로직 ---
        if mode == 'weekly':
            # 매주 월요일 09:00 기준
            bases = df[(df.index.weekday == 0) & (df.index.hour == 9) & (df.index.minute == 0)]
        else:
            # 매월 초 개장 시점 기준
            df['month_val'] = df.index.month
            # 월이 바뀌는 첫 번째 행들 추출
            bases = df[df['month_val'] != df['month_val'].shift(1)]

        def get_base_price(ts):
            past_bases = bases[bases.index <= ts]
            return float(past_bases['Close'].iloc[-1]) if not past_bases.empty else float(df['Close'].iloc[0])

        df['Base_Price'] = [get_base_price(ts) for ts in df.index]
        raw_return = ((df['Close'] - df['Base_Price']) / df['Base_Price'] * 100)
        
        # 가중치 적용
        if symbol == 'DX-Y.NYB': df['Return'] = raw_return * 5
        elif symbol == 'SI=F': df['Return'] = raw_return * 2
        else: df['Return'] = raw_return
            
        current_return = float(df['Return'].iloc[-1])
        
        # 상단 지표 (metric에 고유 라벨 부여)
        display_name = f"{name} (5x)" if symbol == 'DX-Y.NYB' else (f"{name} (2x)" if symbol == 'SI=F' else name)
        cols[i].metric(label=display_name, value=f"{current_return:+.2f}%")

        fig.add_trace(go.Scatter(
            x=df.index, y=df['Return'],
            mode='lines', name=display_name,
            line=dict(width=2, color=colors[i])
        ))
        all_indices.append(df.index)

    # 리셋 수직선 추가
    if all_indices:
        start_date, end_date = all_indices[0].min(), all_indices[0].max()
        if mode == 'weekly':
            curr = start_date.replace(hour=9, minute=0, second=0)
            while curr <= end_date:
                if curr.weekday() == 0:
                    fig.add_vline(x=curr.timestamp()*1000, line_dash="solid", line_color="rgba(200,0,0,0.2)", 
                                  annotation_text=curr.strftime('%m%d'))
                curr += timedelta(days=1)
        else:
            for b_ts in bases.index:
                if b_ts >= start_date:
                    fig.add_vline(x=b_ts.timestamp()*1000, line_dash="solid", line_color="rgba(0,0,200,0.2)",
                                  annotation_text=b_ts.strftime('%m월'))

    fig.add_hline(y=0, line_color="black", opacity=0.5)
    fig.update_layout(hovermode="x unified", height=600, template='plotly_white',
                      xaxis=dict(tickformat="%m%d\n%H:%M", dtick=86400000.0),
                      legend=dict(orientation="h", y=1.02, x=1))
    
    # [핵심] 차트에 고유한 key를 부여하여 중복 ID 에러 방지
    st.plotly_chart(fig, use_container_width=True, key=f"chart_{mode}")

# 3. 탭 구성
tab1, tab2 = st.tabs(["📅 주간 기준 (월요일 09:00)", "📆 월간 기준 (월초 개장)"])

with tab1:
    st.subheader("이번 주 성적")
    create_chart(mode='weekly')

with tab2:
    st.subheader("이번 달 성적")
    create_chart(mode='monthly')

st.caption(f"최근 갱신: {datetime.now().strftime('%m%d %H:%M:%S')} | 데이터: yfinance 30분봉")
