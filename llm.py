import os
import json
from getpass import getpass
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser


# API 키 입력
api_key = getpass("OpenAI API 키를 입력하세요: ")

os.environ['OPENAI_API_KEY'] = api_key

# 1. Prompt
## (1) 단일 질문 분석 템플릿
single_template = '''
너는 설문 조사 결과에 대한 보고서를 한국어로 작성하는 AI야.

아래는 너가 해야 할 일이야:
1) {survey_result}를 바탕으로 해당 질문의 설문 조사 결과를 아래 예시의 형태처럼 간결하게 해석해줘.
불필요한 도입 문장은 생략하고, 핵심 수치만 중심으로 정리해줘.
추가로 설문 조사 결과를 질문 내용과 비교해서 인사이트가 도출되면 한 줄 정도로 작성해줘.

예시:  
SNS 채널 콘텐츠 만족도는 매우 만족 50.8%(827명), 만족 41.6%(677명)으로 92.4%가 만족한다고 응답했다.
이는 콘텐츠 기획이나 운영 방향이 단순한 ‘호감’ 수준을 넘어서 사용자 니즈에 정밀하게 부합하고 있을 가능성을 시사합니다.
'''

## (2) 교차 분석 질문 쌍 추천 템플릿
cross_prompt_template = '''
너는 설문 조사 목적에 맞게 교차 분석하기 좋은 질문 쌍을 파악하는 AI야.
[설문조사 목적]을 읽고 [설문조사 질문 리스트] 중 [설문조사 목적]을 가장 잘 보여줄 수 있는 질문의 쌍을 3개 이하로 골라줘.
단, 교차 분석 가능한 문항 유형은 아래와 같아:
- 객관식 vs 객관식
- 객관식 vs 성별
- 객관식 vs 학년

[설문조사 목적]
{survey_purpose}

[설문조사 질문 리스트]
{all_questions}

다른 설명 없이 결과 형식은 아래처럼 작성해줘:

[추천 문항 쌍]  
(0,2)
'''

## (3) 교차 분석 결과 해석 템플릿
cross_analy_prompt_template = '''
[교차 분석 질문 및 결과]의 key는 질문 쌍이 나와있고 value에는 해당 질문 쌍에 대한 해석이 있어.
아래 [기준]들을 모두 종합해서, [교차 분석 질문 및 결과]의 모든 질문 쌍에 대한 분석을 하나씩 실행해줘.

[기준]
- [설문조사 목적]을 바탕으로 두 질문 사이의 전반적인 경향을 자연스럽고 간결하게 요약해줘.
- 수치나 비율은 언급하지 말고, 전반적인 경향, 차이점, 일관성 등의 패턴을 중심으로 요약해.
- 결과 간의 뚜렷한 차이, 특정 응답 유형의 집중 등 눈에 띄는 경향이 있다면 언급해.
- 단정하지 말고, '~해석될 수 있다', '~경향이 보인다'처럼 유연한 표현을 사용해.
- 보고서에 들어갈 분석 파트처럼, 간결하고 객관적인 어조로 작성해줘.

[설문조사 목적]
{survey_purpose}

[교차 분석 질문 및 결과]
{cross_result_text}

결과 형식은 아래처럼 작성해줘:

[a번 질문, b번 질문]  
해석 결과
'''

# 2. LLM
model = ChatOpenAI(model='gpt-4o-mini', temperature=0, seed=42)

# 3. Langcahin 실행
## (1) 단일 질문 분석 
single_prompt = ChatPromptTemplate.from_template(single_template)

def get_analysis(img_idx, survey_json):
    
    chain = (
        {
            "survey_result": lambda _: survey_json[img_idx],
        }
        | single_prompt
        | model
        | StrOutputParser()
    )
    return chain.invoke({})

## (2) 교차 분석 질문 쌍 추천
cross_prompt = ChatPromptTemplate.from_template(cross_prompt_template)

def get_cross_tab_questions(survey_outline,survey_json):
    survey_purpose = survey_outline['조사목적']
    # 질문 내용만 모아서 문자열로 연결
    question_texts = "\n".join(
        [f"Q{q['질문 번호']}. {q['질문 내용']}" for q in survey_json if '질문 내용' in q]
    )
    
    chain = (
        {
            "survey_purpose": lambda _: survey_purpose,
            "all_questions": lambda _: question_texts
        }
        | cross_prompt
        | model
        | StrOutputParser()
    )
    return chain.invoke({})

## (3) 교차 분석 결과 해석
cross_analy_prompt = ChatPromptTemplate.from_template(cross_analy_prompt_template)

def get_cross_analy_questions(survey_outline, cross_result_text):
    survey_purpose = survey_outline['조사목적']
    chain = (
        {
            "survey_purpose": lambda _: survey_purpose,
            "cross_result_text": lambda _: cross_result_text
        }
        | cross_analy_prompt
        | model
        | StrOutputParser()
    )
    return chain.invoke({})
