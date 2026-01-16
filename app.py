import streamlit as st
import pandas as pd
import requests
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import seaborn as sns
from datetime import datetime

# 1. 페이지 설정
st.set_page_config(page_title="Fixed Layout Exchange", layout="wide")

# 2. CSS 완전 고정 (줌 조절 시에도 요소 크기 비율 유지 및 최소 너비 강제)
st.markdown(
    """
    <style>
    /* 전체 페이지에 가로 스크롤 허용 및 줌 영향 최소화 */
    html, body, [data-testid="stAppViewContainer"] {
        min-width: 1200px !important;
        overflow-x: auto !important;
    }

    /* 메인 컨테이너를 1100px로 물리적 박제 */
    .main .block-container {
        width: 1100px !important;
        max-width: 1100px !important;
        min-width: 1100px !important;
        margin: 0 auto !important;
        padding: 2rem 0 !important;
        /* 브라우저 줌 조절 시에도 내부 요소의 상대적 크기 유지 노력 */
        transform-origin: top left;
    }

    /* 타이틀 및 텍스트 크기 고정 시도 (px 단위 강제) */
    h1 { font-size: 40px !important; }
    h3 { font-size: 24px !important; }
    
    /* 컬럼 너비 절대값 고정 */
    [data-testid="column"] {
        width: 300px !important;
        flex: none !important;
    }

    /* 메트릭 카드 고정 */
    [data-testid="stMetric"] {
        width: 200px !important;
        min-width: 200px !important;
    }
    </style>
    """,
    unsafe_allow_html=True
)

st.title("💰 글로벌 환율 변동 분석 대시보드")
st.caption("화면을 확대/축소해도 레이아웃 구조와 요소의 최소 크기가 고정됩니다.")

# 전체 통화 리스트
all_currencies = ["USD", "EUR", "KRW", "JPY", "GBP", "CAD", "CNY", "HKD"]

# --- 상단 옵션 배치 ---
st.write("---")
col1, col2, col3 = st.columns([1, 2, 1])

with col1:
    base_currency = st.selectbox("기준 통화 (1단위)", all_currencies, index=0)

with col2:
    filtered_currencies = [c for c in all_currencies if c != base_currency]
    target_currencies = st.multiselect(
        "비교할 통화들",
        options=filtered_currencies,
        default=["KRW"]
    )

with col3:
    current_year = datetime.now().year
    year_range = st.slider("조회 연도 범위", 1999, current_year, (2015, current_year))

st.write("---")

# --- 데이터 로드 함수 ---
@st.cache_data(ttl=3600)
def get_exchange_data(base, targets, start_y, end_y):
    if not targets: return None
    start_date = f"{start_y}-01-04"
    today = datetime.now().strftime('%Y-%m-%d')
    end_date = f"{end_y}-12-31" if end_y < current_year else today
    
    url = f"https://api.frankfurter.app/{start_date}..{end_date}?from={base}&to={','.join(targets)}"
    try:
        response = requests.get(url)
        data = response.json()
        df = pd.DataFrame(data['rates']).T
        df.index = pd.to_datetime(df.index)
        return df
    except:
        return None

# --- 결과 출력 섹션 ---
if target_currencies:
    df_rates = get_exchange_data(base_currency, target_currencies, year_range[0], year_range[1])

    if df_rates is not None and not df_rates.empty:
        # 1. 상단 증감 현황
        st.subheader("🔔 전날 대비 실시간 환율 증감 현황")
        m_cols = st.columns(len(target_currencies))
        
        for i, target in enumerate(target_currencies):
            series = df_rates[target].dropna()
            current_val = series.iloc[-1]
            prev_val = series.iloc[-2] if len(series) > 1 else current_val
            delta = current_val - prev_val
            val_format = ".4f" if base_currency == "KRW" or current_val < 1 else ".2f"
            
            with m_cols[i]:
                st.metric(label=f"1 {base_currency} ➔ {target}", value=f"{current_val:{val_format}}", delta=f"{delta:{val_format}}")
        
        st.write("---")

        # 2. 연도별 환율 변동 추이 (Matplotlib 크기 고정)
        st.subheader(f"📈 {year_range[0]}년~{year_range[1]}년 환율 추이")
        
        sns.set_theme(style="whitegrid")
        # dpi를 고정하여 브라우저 확대 시에도 이미지 해상도와 크기 비율 유지
        fig, ax = plt.subplots(figsize=(10, 4), dpi=100)
        
        for target in target_currencies:
            sns.lineplot(data=df_rates, x=df_rates.index, y=target, ax=ax, label=target, linewidth=2)

        ax.xaxis.set_major_locator(mdates.YearLocator())
        ax.xaxis.set_major_formatter(mdates.DateFormatter('%Y'))
        
        plt.xticks(rotation=0)
        ax.set_xlabel("연도 (Year)")
        ax.set_ylabel(f"환율")
        ax.legend(loc='upper left', bbox_to_anchor=(1, 1))
        
        plt.tight_layout()
        
        # use_container_width=False로 설정하여 차트가 창 크기에 따라 늘어나지 않게 고정
        st.pyplot(fig, use_container_width=False)
        
    else:
        st.error("데이터를 불러오지 못했습니다.")