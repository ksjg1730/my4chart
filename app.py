import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.graph_objects as go

# 1. 페이지 설정
st.set_page_config(page_title="자산 통합 수익률 대시보드", layout="wide")

# 2. 종목 설정
tickers = {
    'CL=F': {'name': 'WTI 원유', 'color': '#FF9900'},
    'SI=F': {'name': '글로벌 은', 'color': '#95A5A6'},
    'DX-Y.NYB': {'name': '달러지수(x5)', 'color': '#2C3E50'},
    'SOXX': {'name': '반도체(SOXX)', 'color': '#3498DB'}
}

@st.cache_data(ttl=300)
def get_clean_data():
    all_data = []
    for sym, info in tickers.items():
        try:
            df = yf.download(sym, period='2mo', interval='1h', progress=False)
            if df.empty: continue
            close = df['Close'][sym] if isinstance(df.columns, pd.MultiIndex) else df['Close']
            if close.index.tz is None: close = close.tz_localize('UTC')
            close = close.index.tz_convert('Asia/Seoul')

            # 주간 리셋 수익률 계산
            first_price = close.groupby([close.index.year, close.index.isocalendar().week]).transform('first')
            weight = 5 if sym == 'DX-Y.NYB' else 1
            ret = ((close - first_price) / first_price * 100) * weight
            ret.name = sym
            all_data.append(ret)
        except: continue
    
    if not all_data: return None
    return pd.concat(all_data, axis=1).ffill().dropna()

def run_app():
    st.title("📉 자산별 수익률 및 통합 지수 (1시간봉)")
    
    df = get_clean_data()
    if df is None: return

    # --- 🧮 통합 수익률 계산 ---
    # 4개 자산의 평균값을 '통합' 수익률로 정의
    df['통합'] = df.mean(axis=1)

    fig = go.Figure()

    # 1. 🖤 통합 수익선 (가장 강조)
    fig.add_trace(go.Scatter(
        x=df.index, y=df['통합'], name="✅ 통합 수익률 (AVG)",
        line=dict(color='black', width=4),
        hovertemplate="<b>[통합]</b>: %{y:.2f}%<extra></extra>"
    ))

    # 2. 각 개별 종목 선
    for sym, info in tickers.items():
        if sym in df.columns and sym != '통합':
            fig.add_trace(go.Scatter(
                x=df.index, y=df[sym], name=info['name'],
                line=dict(color=info['color'], width=1.5), # 개별선은 조금 얇게
                opacity=0.7,
                hovertemplate=f"{info['name']}: %{{y:.2f}}%<extra></extra>"
            ))

    # 3. ❌ 주도주 교체 지점 (대형 적색 십자가)
    leader_series = df.drop(columns=['통합']).idxmax(axis=1) # 통합 제외하고 1등 판별
    change_mask = leader_series != leader_series.shift(1)
    change_mask.iloc[0] = False
    cross_points = df[change_mask]
    
    if not cross_points.empty:
        fig.add_trace(go.Scatter(
            x=cross_points.index,
            y=[df.loc[t, leader_series[t]] for t in cross_points.index],
            mode='markers',
            marker=dict(symbol='x', size=18, color='red', line=dict(width=2, color='white')),
            name="주도주 교체",
            showlegend=True
        ))

    # 4. 🔥 슈퍼 1등선 (+3%)
    t1_line = df.drop(columns=['통합']).max(axis=1) + 3.0
    fig.add_trace(go.Scatter(
        x=df.index, y=t1_line, name="슈퍼 1등선",
        line=dict(color='rgba(255,0,0,0.2)', width=1, dash='dot'),
        hoverinfo='skip'
    ))

    # 레이아웃
    fig.update_layout(
        hovermode="x unified", height=750, template="plotly_white",
        xaxis=dict(tickformat="%m/%d %H시"),
        yaxis=dict(ticksuffix="%"),
        legend=dict(orientation="h", y=1.05, x=0.5, xanchor="center")
    )

    st.plotly_chart(fig, use_container_width=True)

    # 통합 수익률 기반 성과 요약
    curr_total = df['통합'].iloc[-1]
    st.metric("현재 통합 수익률", f"{curr_total:+.2f}%", 
              delta=f"{curr_total - df['통합'].iloc[-2]:+.2f}% (직전 대비)")

if __name__ == "__main__":
    run_app()
