import streamlit as st
import pandas as pd
from google_play_scraper import Sort, reviews
import matplotlib.pyplot as plt
import matplotlib.font_manager as fm
import seaborn as sns
import platform
from wordcloud import WordCloud
from collections import Counter
import re

# Streamlit Page Configuration
st.set_page_config(page_title="홈택스 가치 제안 대시보드", layout="wide")

# OS별 한글 폰트 설정 (Matplotlib 용)
def set_korean_font():
    os_name = platform.system()
    if os_name == 'Windows':
        # 로컬 Windows 환경일 경우 기존 방식 유지
        plt.rc('font', family='Malgun Gothic')
    else:
        # 리눅스 환경(Streamlit Cloud)에서 명시적 폰트 경로 등록 및 설정
        # 다른 폰트 경로는 배제하고 오직 나눔고딕 절대 경로 단일 지정
        linux_font_path = '/usr/share/fonts/truetype/nanum/NanumGothic.ttf'
        
        # 폰트 매니저에 폰트 경로를 명시적으로 추가
        fm.fontManager.addfont(linux_font_path)
        
        # 띄어쓰기 없이 정확히 NanumGothic 으로 지정
        plt.rc('font', family='NanumGothic')
    
    # 마이너스(-) 기호 깨짐 방지
    plt.rcParams['axes.unicode_minus'] = False

# OS별 한글 폰트 경로 반환 (WordCloud 용)
def get_font_path():
    os_name = platform.system()
    if os_name == 'Windows':
        return 'c:/Windows/Fonts/malgun.ttf'
    else:
        # WordCloud를 위한 리눅스 환경 나눔고딕 절대 경로 반환
        return '/usr/share/fonts/truetype/nanum/NanumGothic.ttf'

# 앱 리뷰 데이터 수집 (캐싱 적용)
@st.cache_data(ttl=3600)
def load_app_reviews(app_id, count=500):
    try:
        result, continuation_token = reviews(
            app_id,
            lang='ko',
            country='kr',
            sort=Sort.NEWEST,
            count=count
        )
        
        extracted_data = []
        for review in result:
            extracted_data.append({
                'userName': review['userName'],
                'score': review['score'],
                'at': review['at'],
                'content': review['content']
            })
            
        df = pd.DataFrame(extracted_data)
        return df
    except Exception as e:
        st.error(f"데이터 수집 중 오류가 발생했습니다: {e}")
        return pd.DataFrame()

# 텍스트 정제 함수 (특수문자 제거 및 영문, 한글만 유지)
def clean_text(text):
    text = re.sub(r'[^가-힣a-zA-Z\s]', '', text)
    return text

# 서비스 개선안 도출 함수 (Pain Point 기반)
def generate_improvement_plan(low_df):
    if low_df.empty:
        return "현재 낮은 별점의 리뷰가 없어 Pain Point를 도출할 수 없습니다."
    
    # 리뷰 텍스트 결합
    all_text = " ".join(low_df['content'].astype(str).tolist())
    
    # 단순 키워드 매칭을 통한 불만 유형 분류
    keywords = {
        '로그인/인증': ['로그인', '인증', '공동인증서', '금융인증서', '비밀번호', '지문', '생체'],
        '오류/버그': ['오류', '에러', '버그', '튕김', '꺼짐', '안됨', '무한로딩'],
        'UI/UX 및 속도': ['UI', 'UX', '화면', '느림', '속도', '복잡', '불편', '가독성', '업데이트']
    }
    
    issue_counts = {category: 0 for category in keywords}
    
    for category, words in keywords.items():
        for word in words:
            issue_counts[category] += all_text.count(word)
            
    # 가장 많이 언급된 이슈 찾기
    top_issue = max(issue_counts, key=issue_counts.get)
    
    # 특수 기호 없이 마크다운 텍스트 구성
    plan_markdown = f"""
### 실무적 서비스 개선 제안 (Service Improvement Plan)
평점 1점 및 2점 데이터의 Pain Point를 분석하여 도출한 가치 제안입니다.

주요 Pain Point 카테고리별 언급 빈도:
- 로그인/인증 이슈: {issue_counts['로그인/인증']}회
- 시스템 오류/버그: {issue_counts['오류/버그']}회
- UI/UX 및 사용성: {issue_counts['UI/UX 및 속도']}회

가장 시급한 개선 영역: {top_issue}

해결 방안 제안:
"""
    
    if top_issue == '로그인/인증':
        plan_markdown += "- 인증 모듈 경량화 및 생체 인증 연동 안정성 확보\n"
        plan_markdown += "- 세션 만료 시간 연장 옵션 제공 또는 간편 비밀번호 체계 개편"
    elif top_issue == '오류/버그':
        plan_markdown += "- 주요 OS 업데이트에 따른 호환성 테스트 강화\n"
        plan_markdown += "- 앱 충돌 로그 분석을 통한 메모리 누수 및 무한 로딩 구간 식별"
    else:
        plan_markdown += "- 주요 세무 신고 메뉴의 진입 단계 최소화 및 직관적인 UI 설계 적용\n"
        plan_markdown += "- 데이터 로딩 시 Skeleton UI 제공으로 체감 속도 개선"
        
    return plan_markdown

def main():
    set_korean_font()
    
    # 제목 및 설명
    st.title("국세청 홈택스 가치 제안(Value Proposition) 대시보드")
    st.markdown("사용자 리뷰(VoC) 데이터를 심층 분석하여 앱의 핵심 Pain Point를 진단하고, 실무적인 서비스 개선 가치를 제안합니다.")
    
    with st.spinner("데이터를 수집하고 있습니다..."):
        app_id = 'kr.go.nts.android'
        raw_df = load_app_reviews(app_id, count=500)
        
    if not raw_df.empty:
        # Sidebar: 별점 필터링 기능
        st.sidebar.header("Data Filter")
        selected_scores = st.sidebar.multiselect(
            "분석할 별점(Score)을 선택하세요:",
            options=[1, 2, 3, 4, 5],
            default=[1, 2, 3, 4, 5]
        )
        
        if not selected_scores:
            st.warning("최소 1개 이상의 별점을 선택해야 합니다.")
            return
            
        df = raw_df[raw_df['score'].isin(selected_scores)]
        
        # 상단 핵심 지표
        col_m1, col_m2, col_m3 = st.columns(3)
        col_m1.metric(label="총 수집 리뷰 수", value=f"{len(raw_df)} 건")
        col_m2.metric(label="필터링된 리뷰 수", value=f"{len(df)} 건")
        col_m3.metric(label="현재 필터 평균 평점", value=f"{df['score'].mean():.2f} 점")
        
        st.divider()
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.subheader("별점 분포 (Score Distribution)")
            fig, ax = plt.subplots(figsize=(6, 4))
            sns.countplot(data=df, x='score', ax=ax, palette='coolwarm', order=sorted(selected_scores))
            ax.set_xlabel("Score")
            ax.set_ylabel("Count")
            
            for p in ax.patches:
                ax.annotate(f'{int(p.get_height())}', 
                            (p.get_x() + p.get_width() / 2., p.get_height()), 
                            ha='center', va='center', 
                            xytext=(0, 5), textcoords='offset points')
            st.pyplot(fig)
            
        with col2:
            st.subheader("리뷰 키워드 (WordCloud)")
            if not df.empty:
                text_data = " ".join(df['content'].astype(str).tolist())
                cleaned_text = clean_text(text_data)
                
                font_path = get_font_path()
                try:
                    wordcloud = WordCloud(
                        font_path=font_path,
                        background_color='white',
                        width=600,
                        height=400,
                        colormap='Set2'
                    ).generate(cleaned_text)
                    
                    fig_wc, ax_wc = plt.subplots(figsize=(6, 4))
                    ax_wc.imshow(wordcloud, interpolation='bilinear')
                    ax_wc.axis('off')
                    st.pyplot(fig_wc)
                except Exception as e:
                    st.error(f"WordCloud 생성 중 오류 발생 (폰트 경로 확인 필요): {e}")
            else:
                st.info("시각화할 텍스트 데이터가 없습니다.")
                
        st.divider()
        
        # 하단: Pain Point 및 개선안 
        st.subheader("서비스 개선 인사이트 (Service Insights)")
        low_rating_df = raw_df[raw_df['score'] <= 2]
        
        insight_plan = generate_improvement_plan(low_rating_df)
        st.markdown(insight_plan)
        
        with st.expander("낮은 별점 리뷰 원본 데이터 확인 (Raw Data)"):
            st.dataframe(low_rating_df[['score', 'at', 'content']].head(20), use_container_width=True)

    else:
        st.error("데이터 수집에 실패했습니다. 네트워크 연결을 확인해주세요.")

if __name__ == '__main__':
    main()