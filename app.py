import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.graph_objects as go
import numpy as np

# 1. 페이지 설정
st.set_page_config(page_title="자산별 수익률 대시보드", layout="wide")

# 2. 종목 및 고유 컬러 설정
tickers = {
    'CL=F': {'name': 'WTI 원유', 'color': '#FF9900'},
    'SI=F': {'name': '글로벌 은', 'color': '#95A5A6'},
    'DX-Y.NYB': {'name': '달러지수', 'color': '#2C3E50'},
    'SOXX': {'name': '반도체(SOXX)', 'color': '#3498DB'}
}

@st.cache_data(ttl=60)
def get_clean_data():
    all_data = []
    for sym, info in tickers.items():
        try:
            df = yf.download(sym, period='1mo', interval='15m', progress=False)
            if df.empty: continue
            
            # Multi-index 및 단일 index 대응
            close = df['Close'][sym] if isinstance(df.columns, pd.MultiIndex) else df['Close']
            
            if close.index.tz is None:
                close = close.tz_localize('UTC')
            close = close.tz_convert('Asia/Seoul')

            # 주간 수익률 (월요일 기준 리셋)
            first_price = close.groupby([close.index.year, close.index.isocalendar().week]).transform('first')
            weight = 5 if sym == 'DX-Y.NYB' else 1
            ret = ((close - first_price) / first_price * 100) * weight
            ret.name = sym
            all_data.append(ret)
        except: continue
    
    if not all_data: return None
    return pd.concat(all_data, axis=1).ffill().dropna()

def run_app():
    st.title("📊 종목별 수익률 및 주도주 교체 알림")
    st.markdown("##### ➕ **십자가 표식**: 1등 종목 교체 지점 | 🔴 **빨간선**: 슈퍼 1등선")

    df = get_clean_data()
    if df is None: return

    latest = df.iloc[-1]
    
    # --- 📈 그래프 구성 ---
    fig = go.Figure()

    # 1. 각 종목별 선
    for sym, info in tickers.items():
        if sym in df.columns:
            fig.add_trace(go.Scatter(
                x=df.index, y=df[sym], name=info['name'],
                line=dict(color=info['color'], width=2),
                hovertemplate=f"<b>{info['name']}</b>: %{{y:.2f}}%<extra></extra>"
            ))

    # 2. 🔥 슈퍼 1등선 (+3%)
    t1_line = df.max(axis=1) + 3.0
    fig.add_trace(go.Scatter(
        x=df.index, y=t1_line, name="🔥 슈퍼 1등선",
        line=dict(color='red', width=2, dash='dash'),
        opacity=0.5
    ))

    # 3. ➕ 주도주 교체(1등 변경) 지점 찾기 및 표시
    # 매 시점별 1등 종목의 심볼 찾기
    leader_series = df.idxmax(axis=1)
    # 이전 시점과 1등이 달라지는 지점 (True/False)
    change_mask = leader_series != leader_series.shift(1)
    # 첫 번째 행은 제외 (비교 대상 없음)
    change_mask.iloc[0] = False
    
    # 교차 지점 데이터 추출
    cross_points = df[change_mask]
    
    for timestamp, row in cross_points.iterrows():
        new_leader_sym = leader_series[timestamp]
        current_val = row[new_leader_sym]
        
        fig.add_trace(go.Scatter(
            x=[timestamp],
            y=[current_val],
            mode='markers',
            marker=dict(
                symbol='cross',
                size=12,
                color='black', # 혹은 특정 강조 컬러
                line=dict(width=2, color='white')
            ),
            name=f"교체: {tickers[new_leader_sym]['name']}",
            showlegend=False,
            hovertemplate=f"<b>주도주 교체!</b><br>새로운 1등: {tickers[new_leader_sym]['name']}<br>수익률: {current_val:.2f}%<extra></extra>"
        ))

    # 4. 세로 리셋선 (월요일)
    reset_times = df.index[df.index.weekday == 0]
    if not reset_times.empty:
        weeks = df.loc[reset_times].index.to_series().dt.isocalendar().week
        unique_weeks = df.loc[reset_times].groupby([df.loc[reset_times].index.year, weeks]).apply(lambda x: x.index[0])
        for rt in unique_weeks:
            fig.add_vline(x=rt, line_width=1, line_color="blue", opacity=0.3)

    fig.update_layout(
        hovermode="x unified", height=700, template="plotly_white",
        xaxis=dict(tickformat="%m/%d %H:%M"),
        yaxis=dict(ticksuffix="%"),
        legend=dict(orientation="h", y=1.05, x=0.5, xanchor="center")
    )

    st.plotly_chart(fig, use_container_width=True)
    
    # 하단 알림창
    if change_mask.any():
        last_change_time = cross_points.index[-1]
        last_leader = tickers[leader_series[last_change_time]]['name']
        st.info(f"💡 최근 주도주 교체: **{last_leader}** ({last_change_time.strftime('%m/%d %H:%M')})")

if __name__ == "__main__":
    run_app()
