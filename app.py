import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.graph_objects as go
from datetime import datetime
import pytz

# 1. 페이지 설정
st.set_page_config(page_title="주간 수익률 대시보드 (15분봉)", layout="wide")

st.title("📊 자산별 주간 수익률 분석 (15분봉)")
st.markdown("##### 🕒 월요일 첫 거래 기준 리셋 | 🏆 1위 종목 RED 강조")

# 2. 종목 설정
tickers = {
    'CL=F': 'WTI 원유 선물',
    'SI=F': '글로벌 은 선물',
    'DX-Y.NYB': 'DXY 달러지수',
    'SOXX': '필라델피아 반도체(SOXX)'
}

@st.cache_data(ttl=600)
def load_all_data():
    ticker_symbols = list(tickers.keys())
    # 15분봉, 1개월 데이터 호출
    df = yf.download(tickers=ticker_symbols, period='1mo', interval='15m', progress=False)
    return df

def draw_dashboard():
    df = load_all_data()
    
    if df is None or df.empty:
        st.error("❌ 데이터를 불러올 수 없습니다.")
        return

    results = []
    all_reset_times = set()
    is_multi = isinstance(df.columns, pd.MultiIndex)

    # 데이터 가공 및 수익률 계산
    for symbol, name in tickers.items():
        try:
            if is_multi:
                series = df['Close'][symbol].dropna()
            else:
                series = df['Close'].dropna() if len(tickers) == 1 else df[symbol].dropna()
            
            if series.empty: continue
            series.index = series.index.tz_convert('Asia/Seoul')

            # 가중치 설정
            weight = 5 if symbol == 'DX-Y.NYB' else (2 if symbol == 'SI=F' else 1)
            
            # 주차별 리셋 지점(첫 봉) 및 수익률 계산
            groups = series.groupby([series.index.year, series.index.isocalendar().week])
            weekly_first = groups.transform('first')
            
            # 리셋 시간 추출 (수직선용)
            reset_times = series.groupby([series.index.year, series.index.isocalendar().week]).idxmin()
            for t in reset_times: all_reset_times.add(t)

            returns = ((series - weekly_first) / weekly_first * 100) * weight
            
            results.append({
                'symbol': symbol, 'name': name, 'returns': returns,
                'last_return': returns.iloc[-1], 'last_price': series.iloc[-1], 'weight': weight
            })
        except: continue

    if not results:
        st.warning("분석 가능한 데이터가 없습니다.")
        return

    # 수익률 순 정렬 (1위 찾기 및 상단 지표 순서용)
    results.sort(key=lambda x: x['last_return'], reverse=True)
    best_symbol = results[0]['symbol']

    fig = go.Figure()
    cols = st.columns(len(tickers))

    for i, res in enumerate(results):
        # 1위 종목은 RED, 나머지는 연한 회색
        is_best = (res['symbol'] == best_symbol)
        line_color = 'red' if is_best else '#D3D3D3'
        line_width = 3.5 if is_best else 1.5
        
        display_name = f"{res['name']} ({res['weight']}x)" if res['weight'] > 1 else res['name']
        
        # 상단 지표 (Metric)
        cols[i].metric(label=display_name, value=f"{res['last_price']:,.2f}", delta=f"{res['last_return']:+.2f}%")

        # 차트 선 추가 (SyntaxError 방지를 위해 한 줄로 작성)
        fig.add_trace(go.Scatter(
            x=res['returns'].index, 
            y=res['returns'],
            mode='lines', 
            name=display_name,
            line=dict(width=line_width, color=line_color),
            hovertemplate='<b>' + display_name + '</b><br>수익률: %{y:.2f}%<extra></extra>'
        ))

        # 1위 종목 상단 3% 지점에 표식 추가
        if is_best:
            target_y = res['last_return'] + 3
            fig.add_trace(go.Scatter(
                x=[res['returns'].index[-1]], y=[target_y],
                mode='markers+text',
                marker=dict(size=10, color='red', symbol='star'),
                text=[f"Top+3%: {target_y:.2f}%"],
                textposition="top center",
                showlegend=False
            ))

    # 월요일 첫 봉 리셋 수직선 추가
    for rt in all_reset_times:
        fig.add_vline(x=rt, line_dash="dash", line_color="#808080", opacity=0.4)

    # 0% 기준선
    fig.add_hline(y=0, line_color="black", line_width=1)

    fig.update_layout(
        hovermode="x unified", height=700, template='plotly_white',
        xaxis=dict(tickformat="%m/%d\n%H:%M"),
        yaxis=dict(title="가중 수익률 (%)", ticksuffix="%"),
        legend=dict(orientation="h", y=1.05, x=0.5, xanchor="center"),
        margin=dict(l=10, r=10, t=50, b=10)
    )

    st.plotly_chart(fig, use_container_width=True)

if __name__ == "__main__":
    draw_dashboard()
    now_str = datetime.now(pytz.timezone('Asia/Seoul')).strftime('%Y-%m-%d %H:%M:%S')
    st.caption(f"최근 갱신: {now_str} (KST) | 레드 라인: 현재 수익률 1위 | 점선: 주간 리셋(월요일)")
