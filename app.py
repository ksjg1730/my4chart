
@st.cache_data(ttl=60)
def get_clean_data():
    all_data = []
    for sym, info in tickers.items():
        try:
            df = yf.download(sym, period='1mo', interval='15m', progress=False)
            if not df.empty:
                # 데이터가 Series인지 DataFrame인지 확인 후 Close 추출
                close = df['Close'].copy()
                if isinstance(close, pd.DataFrame):
                    close = close.iloc[:, 0]
                
                close.index = close.index.tz_convert('Asia/Seoul')
                
                # --- 🕒 주말 및 금요일 14시 이후 데이터 제거 로직 추가 ---
                # 요일(0:월, 4:금, 5:토, 6:일)과 시간 추출
                day_of_week = close.index.weekday
                hour = close.index.hour
                
                # 금요일(4)이면서 14시 이상인 데이터 OR 토요일(5) OR 일요일(6) 데이터 마스킹
                # 이 영역을 NaN으로 만들면 Plotly에서 선이 끊겨서 나옵니다.
                mask = (day_of_week == 4) & (hour >= 14) | (day_of_week == 5) | (day_of_week == 6)
                close.loc[mask] = np.nan
                
                # 주간 수익률 계산 (기존 로직 유지)
                # transform('first')는 NaN을 무시하고 첫 번째 유효한 값을 찾습니다.
                first_price = close.groupby([close.index.year, close.index.isocalendar().week]).transform('first')
                
                weight = 5 if sym == 'DX-Y.NYB' else 1
                ret = ((close - first_price) / first_price * 100) * weight
                ret.name = sym
                all_data.append(ret)
        except Exception as e:
            continue
    
    if not all_data: return None
    
    # 여기서 ffill()을 쓰면 제거한 주말 데이터가 다시 채워질 수 있으므로 
    # concat 후 공통 인덱스만 맞추고 넘깁니다.
    final_df = pd.concat(all_data, axis=1)
    return final_df
