import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.graph_objects as go
import numpy as np

# 1. 페이지 설정
st.set_page_config(page_title="역대 1등 추적 대시보드", layout="wide")

# 2. 스타일 및 모바일 대응
st.markdown(
    """
    <style>
        input, select, textarea { font-size: 16px !important; }
        .stMetric { border: 1px solid #f0f2f6; padding: 10px; border-radius: 10px; }
    </style>
    """,
    unsafe_allow_html=True
)

# 3. 사이드바 설정
st.sidebar.header("📊 시각화 설정")
version = st.sidebar.selectbox("모드 선택", ["원본 버전", "역대 1등-2등 격차 채우기"])
is_spread_mode = (version == "역대 1등-2등 격차 채우기")

st.title("🛢️ 자산별 주간 수익률 분석")
if is_spread_mode:
    st.markdown("##### 🏆 **1등선 vs 2등선 격차 분석** (녹색 영역 = 선두 그룹의 여유 폭)")

# 4. 종목 설정 (골드 대신 원유 'CL=F' 포함)
tickers_raw = {
    'CL=F': 'WTI 원유 선물',
    'SI=F': '글로벌 은 선물',
    'DX-Y.NYB': 'DXY 달러지수',
    'SOXX': '필라델피아 반도체'
}

@st.cache_data(ttl=300)
def load_all_data():
    ticker_symbols = list(tickers_raw.keys())
    df = yf.download(tickers=ticker_symbols, period='1mo', interval='15m', progress=False)
    if df.empty: return None
    return df['Close']

def draw_dashboard():
    df_close = load_all_data()
    if df_close is None:
        st.error("데이터를 불러오지 못했습니다.")
        return

    df_close.index = df_close.index.tz_convert('Asia/Seoul')
    
    # --- [데이터 처리] ---
    all_returns = []
    
    for symbol, name in tickers_raw.items():
        if symbol not in df_close.columns: continue
        series = df_close[symbol].dropna()
        
        # 주간 수익률 계산 (월요일 리셋 기준)
        weekly_first = series.groupby([series.index.year, series.index.isocalendar().week]).transform('first')
        # DXY는 변동성이 작으므로 가중치 5배 유지 (필요 없으면 1로 수정 가능)
        weight = 5 if symbol == 'DX-Y.NYB' else 1
        returns = ((series - weekly_first) / weekly_first * 100) * weight
        returns.name = symbol
        all_returns.append(returns)

    df_returns = pd.concat(all_returns, axis=1).ffill()
    
    # 상단 지표 (현재 수익률 순)
    current_res = [{"name": tickers_raw[s], "val": df_returns[s].iloc[-1], "price": df_close[s].iloc[-1]} for s in df_returns.columns]
    current_res.sort(key=lambda x: x['val'], reverse=True)
    
    cols = st.columns(len(current_res))
    for i, res in enumerate(current_res):
        cols[i].metric(label=f"{'👑 ' if i==0 else ''}{res['name']}", 
                       value=f"{res['price']:,.2f}", 
                       delta=f"{res['val']:+.2f}%")

    # --- [그래프 그리기] ---
    fig = go.Figure()

    if is_spread_mode:
        # 매 순간의 1등값과 2등값 계산
        vals = df_returns.values
        sorted_vals = np.sort(vals, axis=1)
        top1_line = sorted_vals[:, -1]
        top2_line = sorted_vals[:, -2]

        # 1. 배경이 되는 개별 종목 선 (연한 회색)
        for symbol in df_returns.columns:
            fig.add_trace(go.Scatter(
                x=df_returns.index, y=df_returns[symbol],
                line=dict(color='rgba(200, 200, 200, 0.4)', width=1),
                name=tickers_raw[symbol], showlegend=True
            ))

        # 2. 2등선 (채우기의 기준선 역할을 위해 먼저 그림)
        fig.add_trace(go.Scatter(
            x=df_returns.index, y=top2_line,
            line=dict(width=0),
            showlegend=False,
            hoverinfo='skip',
            name='2등선'
        ))

        # 3. 1등선 + 채우기 (2등선으로부터 1등선까지 녹색 채우기)
        fig.add_trace(go.Scatter(
            x=df_returns.index, y=top1_line,
            line=dict(color='#2ECC71', width=3), # 1등선은 선명한 녹색 실선
            fill='tonexty', # 직전 trace(2등선)까지 채움
            fillcolor='rgba(46, 204, 113, 0.25)', # 연한 녹색
            name='🏆 역대 1등선 (Spread)',
            hovertemplate='최고 수익률: %{y:.2f}%<extra></extra>'
        ))

    else:
        # 기본 모드
        for symbol in df_returns.columns:
            fig.add_trace(go.Scatter(x=df_returns.index, y=df_returns[symbol], name=tickers_raw[symbol]))

    # 레이아웃 설정
    fig.update_layout(
        hovermode="x unified", height=750, template='plotly_white',
        xaxis=dict(showgrid=False, tickformat="%m/%d %H:%M"),
        yaxis=dict(ticksuffix="%", gridcolor='#f0f0f0'),
        legend=dict(orientation="h", y=1.05, x=0.5, xanchor="center")
    )
    
    # 월요일 리셋선
    monday_indices = df_returns.index[df_returns.index.weekday == 0]
    if not monday_indices.empty:
        reset_days = df_returns.loc[monday_indices].groupby([monday_indices.year, monday_indices.isocalendar().week]).idxmin().iloc[:, 0]
        for rd in reset_days:
            fig.add_vline(x=rd, line_dash="dot", line_color="blue", opacity=0.3)

    st.plotly_chart(fig, use_container_width=True)

if __name__ == "__main__":
    draw_dashboard()
