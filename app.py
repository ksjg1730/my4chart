import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.graph_objects as go
import numpy as np

# 1. 페이지 설정
st.set_page_config(page_title="슈퍼 1등선 대시보드", layout="wide")

# 2. 스타일 설정
st.markdown(
    """
    <style>
        .stMetric { border: 1px solid #f0f2f6; padding: 10px; border-radius: 10px; background-color: #ffffff; }
    </style>
    """,
    unsafe_allow_html=True
)

# 3. 사이드바 설정
st.sidebar.header("📊 시각화 설정")
version = st.sidebar.selectbox("모드 선택", ["원본 버전", "슈퍼 1등선 격차 버전"])
is_super_mode = (version == "슈퍼 1등선 격차 버전")

st.title("🔥 자산별 주간 수익률 분석")
if is_super_mode:
    st.markdown("##### 🚀 **슈퍼 1등선 모드**: 매 시점 1등 수치보다 3% 더 높은 붉은 선 표시")

# 4. 종목 설정
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
        weekly_first = series.groupby([series.index.year, series.index.isocalendar().week]).transform('first')
        
        # 기본 가중치 (DXY 보정)
        weight = 5 if symbol == 'DX-Y.NYB' else 1
        returns = ((series - weekly_first) / weekly_first * 100) * weight
        returns.name = symbol
        all_returns.append(returns)

    df_returns = pd.concat(all_returns, axis=1).ffill()
    
    # 상단 지표
    current_res = [{"name": tickers_raw[s], "val": df_returns[s].iloc[-1], "price": df_close[s].iloc[-1]} for s in df_returns.columns]
    current_res.sort(key=lambda x: x['val'], reverse=True)
    
    cols = st.columns(len(current_res))
    for i, res in enumerate(current_res):
        cols[i].metric(label=f"{'🏆' if i==0 else ''} {res['name']}", 
                       value=f"{res['price']:,.2f}", 
                       delta=f"{res['val']:+.2f}%")

    # --- [그래프 그리기] ---
    fig = go.Figure()

    if is_super_mode:
        vals = df_returns.values
        sorted_vals = np.sort(vals, axis=1)
        top1_line = sorted_vals[:, -1]
        top2_line = sorted_vals[:, -2]
        
        # 🎯 1등선보다 3% 더 높은 "슈퍼 붉은 선"
        super_top_line = top1_line + 3.0

        # 1. 배경 개별 종목 (연한 회색)
        for symbol in df_returns.columns:
            fig.add_trace(go.Scatter(
                x=df_returns.index, y=df_returns[symbol],
                line=dict(color='rgba(200, 200, 200, 0.3)', width=1),
                name=tickers_raw[symbol]
            ))

        # 2. 2등선 (채우기용 바닥)
        fig.add_trace(go.Scatter(
            x=df_returns.index, y=top2_line,
            line=dict(width=0), showlegend=False, hoverinfo='skip'
        ))

        # 3. 1등선 + 녹색 채우기 (1등과 2등 사이)
        fig.add_trace(go.Scatter(
            x=df_returns.index, y=top1_line,
            line=dict(color='#2ECC71', width=2),
            fill='tonexty',
            fillcolor='rgba(46, 204, 113, 0.2)',
            name='🏆 현재 1등선'
        ))

        # 4. 🚀 슈퍼 1등선 (붉은색 + 3% 상향)
        fig.add_trace(go.Scatter(
            x=df_returns.index, y=super_top_line,
            line=dict(color='#E74C3C', width=4, dash='solid'),
            name='🔥 슈퍼 1등선 (+3%)',
            hovertemplate='슈퍼 타겟: %{y:.2f}%<extra></extra>'
        ))

    else:
        for symbol in df_returns.columns:
            fig.add_trace(go.Scatter(x=df_returns.index, y=df_returns[symbol], name=tickers_raw[symbol]))

    fig.update_layout(
        hovermode="x unified", height=800, template='plotly_white',
        xaxis=dict(showgrid=False, tickformat="%m/%d %H:%M"),
        yaxis=dict(title="수익률 가중치 (%)", ticksuffix="%", gridcolor='#f0f0f0'),
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
