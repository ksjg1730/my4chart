import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.graph_objects as go

# 1. 페이지 설정
st.set_page_config(page_title="주도주 교체 대시보드 (1시간봉)", layout="wide")

# 2. 종목 및 고유 컬러 설정
tickers = {
    'CL=F': {'name': 'WTI 원유', 'color': '#FF9900'},
    'SI=F': {'name': '글로벌 은', 'color': '#95A5A6'},
    'DX-Y.NYB': {'name': '달러지수', 'color': '#2C3E50'},
    'SOXX': {'name': '반도체(SOXX)', 'color': '#3498DB'}
}

@st.cache_data(ttl=300) # 1시간봉이므로 캐시 시간을 5분으로 늘림
def get_clean_data():
    all_data = []
    for sym, info in tickers.items():
        try:
            # 1시간봉(1h)으로 변경, 데이터 범위는 2개월로 확대
            df = yf.download(sym, period='2mo', interval='1h', progress=False)
            if df.empty: continue
            
            # Multi-index 대응
            close = df['Close'][sym] if isinstance(df.columns, pd.MultiIndex) else df['Close']
            
            if close.index.tz is None:
                close = close.tz_localize('UTC')
            close = close.tz_convert('Asia/Seoul')

            # 주간 수익률 리셋 로직
            years = close.index.year
            weeks = close.index.isocalendar().week
            first_price = close.groupby([years, weeks]).transform('first')
            
            weight = 5 if sym == 'DX-Y.NYB' else 1
            ret = ((close - first_price) / first_price * 100) * weight
            ret.name = sym
            all_data.append(ret)
        except: continue
    
    if not all_data: return None
    return pd.concat(all_data, axis=1).ffill().dropna()

def run_app():
    st.title("📈 주도주 교체 감지 (1시간봉 모드)")
    st.markdown("##### ❌ **대형 적색 십자가**: 1등 종목 교차 지점 | 🔵 **파란 점선**: 주간 리셋")

    df = get_clean_data()
    if df is None:
        st.error("데이터를 가져오지 못했습니다.")
        return

    # --- 📈 그래프 구성 ---
    fig = go.Figure()

    # 1. 각 종목별 수익률 선
    for sym, info in tickers.items():
        if sym in df.columns:
            fig.add_trace(go.Scatter(
                x=df.index, y=df[sym], name=info['name'],
                line=dict(color=info['color'], width=2.5),
                hovertemplate=f"<b>{info['name']}</b>: %{{y:.2f}}%<extra></extra>"
            ))

    # 2. 주도주(1등) 교체 지점 로직
    leader_series = df.idxmax(axis=1)
    change_mask = leader_series != leader_series.shift(1)
    change_mask.iloc[0] = False # 첫 지점 제외
    
    cross_points = df[change_mask]
    
    # 3. ❌ 크고 붉은 십자가 추가
    if not cross_points.empty:
        fig.add_trace(go.Scatter(
            x=cross_points.index,
            y=[df.loc[t, leader_series[t]] for t in cross_points.index],
            mode='markers',
            marker=dict(
                symbol='x',          # 십자가 모양
                size=18,             # 크기 확대
                color='red',         # 붉은색
                line=dict(width=2, color='white') # 테두리 추가로 가독성 확보
            ),
            name="주도주 교체",
            hovertemplate="<b>주도주 교체 지점</b><br>일시: %{x}<br>수익률: %{y:.2f}%<extra></extra>"
        ))

    # 4. 🔥 슈퍼 1등선 (+3%)
    t1_line = df.max(axis=1) + 3.0
    fig.add_trace(go.Scatter(
        x=df.index, y=t1_line, name="슈퍼 1등선(+3%)",
        line=dict(color='rgba(255,0,0,0.3)', width=1.5, dash='dash'),
        hoverinfo='skip'
    ))

    # 5. 주간 구분선
    reset_times = df.index[df.index.weekday == 0]
    if not reset_times.empty:
        unique_weeks = df.loc[reset_times].groupby([reset_times.year, reset_times.isocalendar().week]).apply(lambda x: x.index[0])
        for rt in unique_weeks:
            fig.add_vline(x=rt, line_width=1, line_color="blue", line_dash="dot", opacity=0.4)

    fig.update_layout(
        hovermode="x unified", height=750, template="plotly_white",
        xaxis=dict(title="날짜 및 시간", tickformat="%m/%d %H시"),
        yaxis=dict(title="수익률 (%)", ticksuffix="%"),
        legend=dict(orientation="h", y=1.05, x=0.5, xanchor="center")
    )

    st.plotly_chart(fig, use_container_width=True)

    # 최근 교체 이력 테이블
    if not cross_points.empty:
        st.subheader("🔔 최근 주도주 교체 이력")
        history = []
        # 최근 5개 교체 지점 추출
        recent_idx = cross_points.index[-5:] if len(cross_points) > 5 else cross_points.index
        for t in reversed(recent_idx):
            new_leader = leader_series[t]
            prev_leader = leader_series[:t].iloc[-2] # 교체 직전 1등
            history.append({
                "시간": t.strftime('%Y-%m-%d %H:%M'),
                "이전 주도주": tickers[prev_leader]['name'],
                "현재 주도주": tickers[new_leader]['name'],
                "수익률": f"{df.loc[t, new_leader]:+.2f}%"
            })
        st.table(pd.DataFrame(history))

if __name__ == "__main__":
    run_app()
