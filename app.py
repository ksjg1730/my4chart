import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.graph_objects as go

# 1. 페이지 설정
st.set_page_config(page_title="30분봉 주도주 평균 대시보드", layout="wide")

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
    success_list = []
    
    for sym, info in tickers.items():
        try:
            # 30분봉(30m)으로 데이터 로드
            df = yf.download(sym, period='1mo', interval='30m', progress=False)
            if df.empty or len(df) < 10: continue
            
            # 컬럼 추출 (Multi-index 대응)
            close = df['Close'][sym] if isinstance(df.columns, pd.MultiIndex) else df['Close']
            
            # 타임존 설정 및 변환
            if close.index.tz is None: close = close.tz_localize('UTC')
            close = close.index.tz_convert('Asia/Seoul')

            # 주간 수익률 리셋 (월요일 장초 기준)
            years = close.index.year
            weeks = close.index.isocalendar().week
            first_price = close.groupby([years, weeks]).transform('first')
            
            # 수익률 계산 및 가중치
            weight = 5 if sym == 'DX-Y.NYB' else 1
            ret = ((close - first_price) / first_price * 100) * weight
            ret.name = sym
            all_data.append(ret)
            success_list.append(sym)
        except Exception as e:
            continue
    
    if not all_data: return None, []
    
    # 데이터 병합 및 결측치 처리 (중요: ffill 후 dropna로 계산 가능하게 만듦)
    combined = pd.concat(all_data, axis=1).sort_index().ffill().dropna()
    return combined, success_list

def run_app():
    st.title("📊 주도주(1-2위) 평균선 감지 (30분봉)")
    st.markdown("##### ⚫ **검정 실선**: 상위 1, 2등 종목의 평균 수익률 | ❌ **적색 십자가**: 1등 교체")

    df, success_list = get_clean_data()
    
    if df is None or len(success_list) < 2:
        st.error("데이터 로드 실패. 종목이 부족하거나 인터넷 연결을 확인하세요.")
        return

    # --- 🧮 상위 1-2등 평균 계산 (NaN 방지를 위해 row별 계산) ---
    # 각 시점마다 살아있는 데이터 중 상위 2개를 뽑아 평균
    df['주도주평균'] = df[success_list].apply(lambda x: x.nlargest(2).mean(), axis=1)

    fig = go.Figure()

    # 1. 개별 종목 선 (평균선 아래에 깔리도록 먼저 그림)
    for sym in success_list:
        info = tickers[sym]
        fig.add_trace(go.Scatter(
            x=df.index, y=df[sym], 
            name=info['name'],
            line=dict(color=info['color'], width=1.5),
            opacity=0.35, # 투명하게 처리
            hovertemplate=f"{info['name']}: %{{y:.2f}}%<extra></extra>"
        ))

    # 2. ⚫ 주도주 평균 실선 (가장 마지막에 그려서 맨 위로 올림)
    fig.add_trace(go.Scatter(
        x=df.index, y=df['주도주평균'], 
        name="<b>[투톱 평균선]</b>",
        line=dict(color='black', width=4), # 굵고 진하게
        hovertemplate="<b>평균(1+2위)</b>: %{y:.2f}%<extra></extra>"
    ))

    # 3. ❌ 주도주 교체 지점
    leader_series = df[success_list].idxmax(axis=1)
    change_mask = (leader_series != leader_series.shift(1)) & (leader_series.notnull())
    change_mask.iloc[0] = False
    cross_points = df[change_mask]
    
    if not cross_points.empty:
        fig.add_trace(go.Scatter(
            x=cross_points.index,
            y=[df.loc[t, leader_series[t]] for t in cross_points.index],
            mode='markers',
            marker=dict(symbol='x', size=18, color='red', line=dict(width=2, color='white')),
            name="주도주 교체"
        ))

    # 레이아웃 설정
    fig.update_layout(
        hovermode="x unified", height=750, template="plotly_white",
        xaxis=dict(tickformat="%m/%d %H:%M", showgrid=False),
        yaxis=dict(title="수익률 (%)", ticksuffix="%", gridcolor="#f0f0f0"),
        legend=dict(orientation="h", y=1.05, x=0.5, xanchor="center")
    )

    st.plotly_chart(fig, use_container_width=True)

    # --- 📋 데이터 검증용 하단 바 ---
    curr_avg = df['주도주평균'].iloc[-1]
    st.info(f"💡 현재 시각: {df.index[-1].strftime('%Y-%m-%d %H:%M')} | 현재 투톱 평균: **{curr_avg:+.2f}%**")

if __name__ == "__main__":
    run_app()
