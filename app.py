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

# 데이터 수집 함수 (캐싱 활용하여 속도 향상)
@st.cache_data(ttl=600)
def load_data(symbol):
    df = yf.download(symbol, period='2mo', interval='30m', progress=False)
    if not df.empty:
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.get_level_values(0)
        df.index = df.index.tz_convert('Asia/Seoul')
    return df

# 3. 메인 화면 구성
tab1, tab2 = st.tabs(["📅 주간 기준 (월요일 09:00)", "📆 월간 기준 (월초 개장)"])

def create_chart(mode='weekly'):
    fig = go.Figure()
    cols = st.columns(len(tickers))
    colors = ['#333333', '#FFD700', '#FF4B4B', '#00CC96']
    all_indices = []

    for i, (symbol, name) in enumerate(tickers.items()):
        df = load_data(symbol)
        if df.empty: continue
        
        # --- 기준가 계산 로직 ---
        if mode == 'weekly':
            # 매주 월요일 09:00 가격 찾기
            bases = df[(df.index.weekday == 0) & (df.index.hour == 9) & (df.index.minute == 0)]
            reset_label = "Mon 09:00"
        else:
            # 매월 1일(또는 월초 첫 거래일) 09:00 가격 찾기
            # 일(day)이 이전 행보다 작아지는 지점이 월이 바뀌는 지점
            df['day'] = df.index.day
            bases = df[df['day'] != df['day'].shift(1)].resample('MS').first() # 월초 데이터 샘플링
            # 실제 데이터 내 월초 첫 9시 가격 추출
            bases = df[df.index.isin(df.index.to_series().resample('MS').first())] 
            reset_label = "Month Start"

        def get_base_price(ts):
            past_bases = bases[bases.index <= ts]
            return float(past_bases['Close'].iloc[-1]) if not past_bases.empty else float(df['Close'].iloc[0])

        # 기준가 적용 및 수익률 계산
        df['Base_Price'] = [get_base_price(ts) for ts in df.index]
        raw_return = ((df['Close'] - df['Base_Price']) / df['Base_Price'] * 100)
        
        # 가중치 적용
        if symbol == 'DX-Y.NYB': df['Return'] = raw_return * 5
        elif symbol == 'SI=F': df['Return'] = raw_return * 2
        else: df['Return'] = raw_return
            
        current_return = float(df['Return'].iloc[-1])
        cols[i].metric(label=name, value=f"{current_return:+.2f}%")

        fig.add_trace(go.Scatter(
            x=df.index, y=df['Return'],
            mode='lines', name=name,
            line=dict(width=2, color=colors[i])
        ))
        all_indices.append(df.index)

    # 수직선 추가 (리셋 지점)
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
            # 월초 지점 실선 표시
            for b_ts in bases.index:
                if b_ts >= start_date:
                    fig.add_vline(x=b_ts.timestamp()*1000, line_dash="solid", line_color="rgba(0,0,200,0.2)",
                                  annotation_text=b_ts.strftime('%m월'))

    fig.add_hline(y=0, line_color="black", opacity=0.5)
    fig.update_layout(hovermode="x unified", height=600, template='plotly_white',
                      xaxis=dict(tickformat="%m%d\n%H:%M", dtick=86400000.0),
                      legend=dict(orientation="h", y=1.02, x=1))
    st.plotly_chart(fig, use_container_width=True)

# 탭별 출력
with tab1:
    st.subheader("이번 주 성적 (매주 월요일 09:00 리셋)")
    create_chart(mode='weekly')

with tab2:
    st.subheader("이번 달 성적 (매월 초 개장 시점 리셋)")
    create_chart(mode='monthly')

st.caption(f"최근 갱신: {datetime.now().strftime('%m%d %H:%M:%S')} | 데이터: yfinance 30분봉")
