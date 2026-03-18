import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.graph_objects as go
from datetime import datetime
import numpy as np

# 1. 페이지 설정 (가장 먼저 실행)
st.set_page_config(page_title="역대 1등 추적 대시보드", layout="wide")

# 2. 스타일 설정 및 모바일 대응
st.markdown(
    """
    <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no">
    <style>
        input, select, textarea { font-size: 16px !important; }
        .stMetric { background-color: white; padding: 10px; border-radius: 5px; box-shadow: 0 1px 3px rgba(0,0,0,0.1); }
    </style>
    """,
    unsafe_allow_html=True
)

# 3. 사이드바 - 버전 선택
st.sidebar.header("📊 설정")
version = st.sidebar.selectbox("시각화 모드", ["원본 버전", "역대 1등 vs 2등 격차 버전"])
is_spread_mode = (version == "역대 1등 vs 2등 격차 버전")

st.title("📈 자산별 주간 수익률 및 리더보드")

if is_spread_mode:
    st.markdown("##### 🏆 모드: **역대 1등선 추적 및 2등과의 격차 (녹색 채우기)**")
    st.caption("과거 모든 시점에서 당시 1등이었던 수치를 연결한 선을 '1등선'이라 부릅니다.")
else:
    st.markdown("##### 📋 모드: **기본 주간 수익률**")

# 4. 종목 설정 (DXY 제외 - 스케일 차이가 너무 커서 격차 분석 시 왜곡됨)
# 필요시 다시 추가 가능하지만, 1/2등 격차 분석에는 변동성이 비슷한 자산군이 좋습니다.
tickers_raw = {
    'CL=F': 'WTI 원유 선물',
    'SI=F': '글로벌 은 선물',
    'GC=F': '골드 선물', # 은과 비교를 위해 골드 추가
    'SOXX': '필라델피아 반도체'
}

@st.cache_data(ttl=300)
def load_all_data():
    ticker_symbols = list(tickers_raw.keys())
    # 15분봉 데이터 호출
    df = yf.download(tickers=ticker_symbols, period='1mo', interval='15m', progress=False)
    if df.empty or 'Close' not in df.columns:
        return None
    return df['Close'] # 종가 데이터만 추출

def draw_dashboard():
    df_close = load_all_data()
    
    if df_close is None or df_close.empty:
        st.error("❌ 데이터를 불러올 수 없습니다. yfinance API 상태를 확인하세요.")
        return

    # 시간대 변환
    df_close.index = df_close.index.tz_convert('Asia/Seoul')
    
    # --- [데이터 처리 로직 start] ---
    
    all_returns_list = []
    current_metrics = []

    # 1. 각 종목별 주간 수익률 계산
    for symbol, name in tickers_raw.items():
        if symbol not in df_close.columns: continue
        
        series = df_close[symbol].dropna()
        if series.empty: continue

        # 주간(ISO Week) 기준 transform('first')로 주초 가격 계산
        weekly_first_price = series.groupby([series.index.year, series.index.isocalendar().week]).transform('first')
        
        # 기본 수익률 (%)
        returns = ((series - weekly_first_price) / weekly_first_price * 100)
        
        # 시계열 병합을 위해 이름 변경
        returns.name = symbol
        all_returns_list.append(returns)
        
        # 상단 metric용 데이터 저장
        current_metrics.append({
            'name': name,
            'last_price': series.iloc[-1],
            'last_return': returns.iloc[-1]
        })

    if not all_returns_list:
        st.warning("분석할 데이터가 충분하지 않습니다.")
        return

    # 2. 모든 수익률 데이터를 하나의 DataFrame으로 병합 (시간축 정렬)
    df_returns = pd.concat(all_returns_list, axis=1).ffill() # 결측치는 이전 값으로 채움
    
    # 월요일 리셋 지점 추출 (차트 수직선용)
    monday_indices = df_returns.index[df_returns.index.weekday == 0]
    # 주가 바뀔 때의 첫 번째 인덱스만 추출
    monday_reset_times = df_returns.loc[monday_indices].groupby([monday_indices.year, monday_indices.isocalendar().week]).idxmin().iloc[:, 0].unique()

    # --- [상단 메트릭 표시] ---
    cols = st.columns(len(current_metrics))
    # 현재 수익률 순으로 정렬하여 표시
    current_metrics.sort(key=lambda x: x['last_return'], reverse=True)
    
    for i, met in enumerate(current_metrics):
        # 1등에게 왕관 표시
        label = f"{'🏆 ' if i==0 else ''}{met['name']}"
        cols[i].metric(
            label=label,
            value=f"{met['last_price']:,.2f}",
            delta=f"{met['last_return']:+.2f}%"
        )

    # --- [그리기 로직] ---
    fig = go.Figure()

    if is_spread_mode:
        # --- 🏆 [핵심 로직] 역대 1등선 vs 2등선 격차 시각화 ---
        
        # 행(Row) 단위로 값을 정렬하여 1등, 2등 값을 추출
        # numpy를 사용하는 것이 pandas rank보다 속도가 빠름
        vals = df_returns.values
        if vals.shape[1] < 2:
            st.warning("비교할 자산이 2개 이상 필요합니다.")
            return
            
        sorted_vals = np.sort(vals, axis=1)
        
        # 가장 우측에 있는 값이 1등, 그 왼쪽이 2등 (오름차순 정렬이므로)
        top1_line = pd.Series(sorted_vals[:, -1], index=df_returns.index)
        top2_line = pd.Series(sorted_vals[:, -2], index=df_returns.index)

        # 1. 배경 종목선들 (회색, 흐리게)
        for symbol in df_returns.columns:
            name = tickers_raw[symbol]
            fig.add_trace(go.Scatter(
                x=df_returns.index, y=df_returns[symbol],
                mode='lines', name=name,
                line=dict(color='#E6E6E6', width=1),
                hoverinfo='skip', # 호버 안되게
                showlegend=True
            ))

        # 2. 녹색 격차 채우기 (2등선 위에 1등선과의 차이를 채움)
        fig.add_trace(go.Scatter(
            x=top2_line.index, y=top2_line,
            mode='lines',
            line=dict(width=0), # 선은 안보이게
            showlegend=False,
            hoverinfo='skip'
        ))
        
        fig.add_trace(go.Scatter(
            x=top1_line.index, y=top1_line,
            mode='lines',
            name='1등-2등 격차',
            fill='tonexty', # 바로 이전 trace(2등선)까지 채움
            fillcolor='rgba(0, 200, 100, 0.3)', # 투명한 녹색
            line=dict(width=0), # 선은 안보이게
            hoverinfo='skip'
        ))

        # 3. 최상위 1등선 (굵은 검은색 실선)
        fig.add_trace(go.Scatter(
            x=top1_line.index, y=top1_line,
            mode='lines',
            name='🏆 역대 1등선',
            line=dict(color='#2C3E50', width=2.5),
            hovertemplate='<b>당시 1등 수치</b>: %{y:.2f}%<extra></extra>'
        ))

    else:
        # --- 📋 기본 모드 (기존 코드와 유사) ---
        colors = ['#636EFA', '#EF553B', '#00CC96', '#AB63FA'] # Plotly 기본 컬러셋
        for i, symbol in enumerate(df_returns.columns):
            name = tickers_raw[symbol]
            fig.add_trace(go.Scatter(
                x=df_returns.index, y=df_returns[symbol],
                mode='lines',
                name=name,
                line=dict(width=2, color=colors[i % len(colors)]),
                hovertemplate='<b>' + name + '</b>: %{y:.2f}%<extra></extra>'
            ))

    # --- 공통 레이아웃 설정 ---
    
    # 월요일 리셋 수직선 (파란 점선)
    for rt in monday_reset_times:
        fig.add_vline(x=rt, line_dash="dash", line_color="#5DADE2", line_width=1, opacity=0.7)

    # 0% 기준선
    fig.add_hline(y=0, line_color="#333", line_width=1)

    fig.update_layout(
        hovermode="x unified",
        height=700,
        template='plotly_white',
        xaxis=dict(title="시간 (KST)", tickformat="%m/%d %H:%M", showgrid=False),
        yaxis=dict(title="주간 수익률 (%)", ticksuffix="%", zeroline=False, gridcolor='#F0F0F0'),
        legend=dict(orientation="h", y=1.08, x=0.5, xanchor="center"),
        margin=dict(l=10, r=10, t=20, b=10)
    )

    st.plotly_chart(fig, use_container_width=True)

if __name__ == "__main__":
    draw_dashboard()
    st.caption("🔵 파란 점선: 월요일 주초 리셋 시점 | 데이터 출처: Yahoo Finance")
