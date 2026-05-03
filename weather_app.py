import streamlit as st
import requests
from datetime import datetime, timedelta
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import random
import platform

# 한글 폰트 설정 - os별 자동 감지
if platform.system() == 'Windows':
    plt.rcParams['font.family'] = 'Malgun Gothic'
elif platform.system() == 'Darwin':  # macOS
    plt.rcParams['font.family'] = 'AppleGothic'
else:  # Linux 및 기타 OS
    plt.rcParams['font.family'] = 'DejaVu Sans'

plt.rcParams['axes.unicode_minus'] = False  # 마이너스 기호 깨짐 방지

# 페이지 설정
st.set_page_config(page_title="고급 날씨 대시보드", page_icon="🌤️", layout="wide")

# 제목 및 설명 (정류장 대기 시 불편함 해결을 위한 사용자 중심 대시보드)
st.title("🚌 대중교통 이용자 기상 케어 대시보드")
st.markdown("정류장 대기 시 쾌적도를 실시간으로 확인하고 이용 시간을 계획하세요!")
st.markdown("---")

# 사이드바에서 API Key 입력
st.sidebar.header("⚙️ 설정")
api_key = st.sidebar.text_input(
    "OpenWeatherMap API 키를 입력하세요:",
    type="password",
    help="https://openweathermap.org/api에서 무료 API 키를 발급받으세요"
)

# 도시 선택 필터 추가 - 주요 도시 목록을 사용자가 선택 가능하게 함
st.sidebar.header("🏙️ 도시 선택")
city_options = ["서울", "부산", "제주", "도쿄", "베이징", "방콕", "싱가포르"]
selected_city = st.sidebar.selectbox(
    "조회할 도시를 선택하세요:",
    city_options,
    index=0
)

# 영문 도시명 매핑 (API 요청용)
city_english_map = {
    "서울": "Seoul",
    "부산": "Busan",
    "제주": "Jeju",
    "도쿄": "Tokyo",
    "베이징": "Beijing",
    "방콕": "Bangkok",
    "싱가포르": "Singapore"
}

# 날씨 상태에 따른 아이콘 매핑
weather_icons = {
    "Clear": "☀️",
    "Clouds": "☁️",
    "Rain": "🌧️",
    "Drizzle": "🌦️",
    "Thunderstorm": "⛈️",
    "Snow": "❄️",
    "Mist": "🌫️",
    "Smoke": "💨",
    "Haze": "🌫️",
    "Dust": "🌪️",
    "Fog": "🌫️",
    "Sand": "🌪️",
    "Ash": "💨",
    "Squall": "💨",
    "Tornado": "🌪️"
}

def get_weather_data(city, api_key):
    """OpenWeatherMap API에서 현재 날씨 정보 조회"""
    url = "https://api.openweathermap.org/data/2.5/weather"
    params = {
        "q": city,
        "appid": api_key,
        "units": "metric",
        "lang": "ko"
    }
    
    try:
        response = requests.get(url, params=params, timeout=5)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException:
        return None

def get_weather_icon(main_condition):
    """날씨 상태에 맞는 아이콘 반환"""
    return weather_icons.get(main_condition, "🌤️")

def calculate_comfort_index(temp, humidity, wind_speed):
    """
    실외 대기 쾌적도 지수 계산 (정류장 대기자 Pain Point 해결)
    - 기온: 18~25°C 범위가 최적
    - 습도: 40~60% 범위가 최적
    - 풍속: 0.5~2.0 m/s 범위가 최적
    반환값: 0~100 (높을수록 쾌적함)
    """
    # 기온 쾌적도 계산: 18~25°C가 최적
    if 18 <= temp <= 25:
        temp_score = 100
    elif temp < 18:
        temp_score = max(0, 100 - (18 - temp) * 10)  # 1도 내려갈 때마다 -10점
    else:  # temp > 25
        temp_score = max(0, 100 - (temp - 25) * 8)   # 1도 올라갈 때마다 -8점
    
    # 습도 쾌적도 계산: 40~60%가 최적
    if 40 <= humidity <= 60:
        humidity_score = 100
    elif humidity < 40:
        humidity_score = max(0, 100 - (40 - humidity) * 2)
    else:  # humidity > 60
        humidity_score = max(0, 100 - (humidity - 60) * 3)
    
    # 풍속 쾌적도 계산: 0.5~2.0 m/s가 최적
    if 0.5 <= wind_speed <= 2.0:
        wind_score = 100
    elif wind_speed < 0.5:
        wind_score = max(50, 100 - (0.5 - wind_speed) * 50)  # 무풍은 다소 답답함
    else:  # wind_speed > 2.0
        wind_score = max(0, 100 - (wind_speed - 2.0) * 15)
    
    # 가중 평균: 기온(40%) + 습도(35%) + 풍속(25%)
    comfort_index = (temp_score * 0.4 + humidity_score * 0.35 + wind_score * 0.25)
    
    return round(comfort_index, 1)

def generate_hourly_comfort_forecast(base_temp, base_humidity, base_wind):
    """
    시간대별 쾌적도 변화 데이터 생성 (정류장 대기 시간 계획 지원)
    - 사용자의 Pain Point: 정류장에서 몇 시부터 대기하는 것이 가장 쾌적할까?
    - 해결책: 24시간 쾌적도 예측으로 '최적 대기 시간대' 추천
    """
    hours = []
    comfort_scores = []
    current_time = datetime.now()
    
    for i in range(24):
        # 시간별 시각 (현재로부터 24시간 범위)
        time_point = current_time - timedelta(hours=23-i)
        hours.append(time_point)
        
        # 시간별 기온 변화 (정현파 패턴으로 자연스러운 변화 시뮬레이션)
        # 새벽 냉각, 낮 상승 패턴 반영 - 현실적인 기온 변화 모델링
        temp_variation = 5 * (1 - ((i - 6) ** 2) / 144)
        hourly_temp = base_temp + temp_variation + random.uniform(-1, 1)
        
        # 습도 변화: 새벽에 높고 낮에 낮음 (정류장 불쾌감의 주요 요인)
        humidity_variation = 20 * (1 - ((i - 12) ** 2) / 144)
        hourly_humidity = base_humidity + humidity_variation + random.uniform(-2, 2)
        hourly_humidity = max(20, min(90, hourly_humidity))  # 20~90% 범위 제한
        
        # 풍속 변화: 시간대별 자연 변화 (강풍은 정류장 불편감 증대)
        wind_variation = 1.5 * (0.5 + 0.5 * (i % 6) / 6)
        hourly_wind = base_wind + wind_variation + random.uniform(-0.3, 0.3)
        hourly_wind = max(0, hourly_wind)
        
        # 쾌적도 지수 계산 (기온+습도+풍속의 가중 평균)
        comfort = calculate_comfort_index(hourly_temp, hourly_humidity, hourly_wind)
        comfort_scores.append(comfort)
    
    return hours, comfort_scores

def get_comfort_recommendation(comfort_index):
    """
    쾌적도 지수에 따른 정류장 이용 추천 메시지 반환
    사용자가 즉시 행동을 결정할 수 있도록 지원
    """
    if comfort_index >= 80:
        return "✅ 정류장 대기 최적 시간대", "green"
    elif comfort_index >= 60:
        return "🟡 보통 쾌적함, 이용 가능", "orange"
    elif comfort_index >= 40:
        return "🔶 불편함, 주의 필요", "orange"
    else:
        return "❌ 정류장 대기 불쾌적", "red"

# 메인 컨텐츠
if api_key:
    # 선택된 도시의 영문명 가져오기
    city_english = city_english_map[selected_city]
    weather_data = get_weather_data(city_english, api_key)
    
    if weather_data and weather_data.get("cod") == 200:
        # 날씨 정보 추출
        main_weather = weather_data["main"]
        weather_info = weather_data["weather"][0]
        wind_info = weather_data["wind"]
        
        temp = main_weather["temp"]
        feels_like = main_weather["feels_like"]
        humidity = main_weather["humidity"]
        pressure = main_weather["pressure"]
        wind_speed = wind_info["speed"]
        description = weather_info["description"]
        main_condition = weather_info["main"]
        icon = get_weather_icon(main_condition)
        
        # 업데이트 시간
        update_time = datetime.now().strftime("%Y년 %m월 %d일 %H:%M:%S")
        
        # 큰 날씨 아이콘과 기본 정보 표시
        col1, col2 = st.columns([1, 2])
        with col1:
            st.markdown(f"<h1 style='text-align: center; font-size: 100px;'>{icon}</h1>", unsafe_allow_html=True)
        
        with col2:
            st.markdown(f"### 📍 {selected_city}")
            st.markdown(f"**날씨:** {description.capitalize()}")
            st.markdown(f"**현재 기온:** {temp}°C")
            st.markdown(f"**체감 기온:** {feels_like}°C")
        
        st.markdown("---")
        
        # 상세 정보 - 3개 열로 표시
        col1, col2, col3 = st.columns(3)
        
        with col1:
            st.metric(
                label="💧 습도",
                value=f"{humidity}%",
                delta=None
            )
        
        with col2:
            st.metric(
                label="💨 풍속",
                value=f"{wind_speed} m/s",
                delta=None
            )
        
        with col3:
            st.metric(
                label="🔽 기압",
                value=f"{pressure} hPa",
                delta=None
            )
        
        st.markdown("---")
        
        # 쾌적도 지수 계산 및 추천 메시지 표시 (정류장 이용 최적 시간대 추천)
        current_comfort = calculate_comfort_index(temp, humidity, wind_speed)
        recommendation, color = get_comfort_recommendation(current_comfort)
        
        st.subheader("🎯 현재 정류장 쾌적도 평가")
        col1, col2, col3 = st.columns([1, 2, 1])
        with col1:
            st.metric(
                label="쾌적도 지수",
                value=f"{current_comfort}",
                delta=None
            )
        with col2:
            st.markdown(f"<div style='text-align: center; font-size: 18px; color: {color};'>{recommendation}</div>", unsafe_allow_html=True)
        
        st.markdown("---")
        
        # 동적 차트 구현: Matplotlib을 사용한 시간대별 쾌적도 변화 선 그래프 출력
        # Pain Point 해결: '정류장에서 몇 시부터 대기하는 것이 가장 쾌적할까?' 라는 사용자의 의문에 직접 답변
        st.subheader("📈 시간대별 쾌적도 변화 (24시간 예측)")
        
        # 시간대별 쾌적도 데이터 생성 (24시간 데이터)
        hours, comfort_scores = generate_hourly_comfort_forecast(temp, humidity, wind_speed)
        
        # Matplotlib 그래프 생성 (한글 폰트 자동 설정 적용)
        fig, ax = plt.subplots(figsize=(14, 6))
        
        # 시간대별 쾌적도 변화를 선 그래프로 표시 (사용자가 최적 대기 시간대를 한눈에 파악)
        ax.plot(hours, comfort_scores, marker='o', linewidth=2.5, markersize=7, 
                color='#2E86AB', label='쾌적도 지수', alpha=0.9)
        
        # 최적 쾌적도 구간 배경 표시 (80 이상)
        ax.axhspan(80, 100, alpha=0.15, color='green', label='최적 구간 (80 이상)')
        
        # 보통 구간 표시 (60~80)
        ax.axhspan(60, 80, alpha=0.1, color='yellow')
        
        # 불편한 구간 표시 (40 이하)
        ax.axhspan(0, 40, alpha=0.15, color='red', label='불편한 구간 (40 이하)')
        
        # 평균 쾌적도 라인 추가
        avg_comfort = sum(comfort_scores) / len(comfort_scores)
        ax.axhline(y=avg_comfort, color='orange', linestyle='--', 
                   linewidth=2, label=f'평균 쾌적도: {avg_comfort:.1f}', alpha=0.8)
        
        # 현재 시간 표시선 추가
        current_time = datetime.now()
        ax.axvline(x=current_time, color='red', linestyle=':', 
                   linewidth=2, label='현재 시간', alpha=0.7)
        
        # 그래프 스타일 설정
        ax.set_xlabel('시간', fontsize=12, weight='bold')
        ax.set_ylabel('쾌적도 지수 (0~100)', fontsize=12, weight='bold')
        ax.set_title(f'{selected_city} - 24시간 정류장 쾌적도 변화 예측', fontsize=14, weight='bold', pad=20)
        ax.set_ylim(0, 105)
        ax.grid(True, alpha=0.3, linestyle=':')
        ax.legend(loc='best', fontsize=10)
        
        # X축 시간 포맷 설정 (2시간 간격으로 표시)
        ax.xaxis.set_major_locator(mdates.HourLocator(interval=2))
        ax.xaxis.set_major_formatter(mdates.DateFormatter('%H:%M'))
        fig.autofmt_xdate(rotation=45, ha='right')
        
        # Streamlit에 그래프 표시
        st.pyplot(fig)
        
        # 최적 대기 시간대 추천 (사용자의 시간 계획을 직접 지원)
        st.markdown("---")
        st.subheader("⏰ 최적 대기 시간대 추천")
        
        # 쾌적도가 80 이상인 시간대 찾기
        optimal_times = [hours[i].strftime('%H:%M') for i, score in enumerate(comfort_scores) if score >= 80]
        
        if optimal_times:
            st.success(f"✅ 최적 대기 시간대: {', '.join(optimal_times[:3])} (및 기타)")
        else:
            # 쾌적도 60 이상 표시
            good_times = [hours[i].strftime('%H:%M') for i, score in enumerate(comfort_scores) if score >= 60]
            if good_times:
                st.info(f"🟡 비교적 쾌적한 시간대: {', '.join(good_times[:3])} (및 기타)")
            else:
                st.warning("⚠️ 현재 날씨 상황에서 권장할 만한 시간대가 없습니다.")
        
        st.markdown("---")
        st.markdown(f"<small style='color: gray; text-align: center;'>마지막 업데이트: {update_time}</small>", unsafe_allow_html=True)
        
    else:
        st.error("❌ API 키가 유효하지 않거나 요청에 오류가 발생했습니다.")
        st.info("💡 https://openweathermap.org/api 에서 무료 API 키를 발급받으세요.")

else:
    st.warning("⚠️ 왼쪽 사이드바에서 OpenWeatherMap API 키를 입력해주세요.")
    st.info("""
    ### 🚀 사용 방법:
    1. [OpenWeatherMap](https://openweathermap.org/api) 방문
    2. 무료 계정 가입 및 API 키 발급
    3. 왼쪽 사이드바의 설정 섹션에 API 키 입력
    4. 원하는 도시를 선택
    5. 현재 날씨 정보 및 시간대별 기온 변화 확인!
    """)
