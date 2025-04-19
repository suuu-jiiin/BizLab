import os
import pandas as pd
from getpass import getpass
from fpdf import FPDF
from fpdf.enums import XPos, YPos
import fitz
import json
import re
from PIL import Image
from langchain_community.document_loaders import PyMuPDFLoader
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from docx import Document
from docx.shared import Inches, Pt 


# API 키 입력
api_key = getpass("OpenAI API 키를 입력하세요: ")

os.environ['OPENAI_API_KEY'] = api_key

# 파일 경로 설정
#csv_path = r"C:\Users\toozi\OneDrive\문서\GitHub\BizLab\data\survey_data.csv"
outline_json_path = r"C:\Users\toozi\OneDrive\문서\GitHub\BizLab\data\survey_outline.json"
result_json_path = r"C:\Users\toozi\OneDrive\문서\GitHub\BizLab\data\survey_result.json"
img_folder = r"C:\Users\toozi\OneDrive\문서\GitHub\BizLab\img\test"

# 1. 데이터 로딩
#survey_csv = pd.read_csv(csv_path, encoding='utf-8')  
with open(result_json_path, 'r', encoding='utf-8-sig') as f:
    survey_json = json.load(f)

with open(outline_json_path, "r", encoding="utf-8") as f:
    outline_data = json.load(f)
    
cross_result_text = '''
3:{"질문 내용": "삶의 행복에 사회적 관계망(SNS)은 도움이 된다고 생각한다.",
        "질문 유형": "객관식 질문"
        "카테고리": 1,2,3,4,5}
7:{ "질문 내용": "나는 사회적 관계망(SNS)의 사용에 만족도가 높다.",
        "질문 유형": "객관식 질문"
        "카테고리": 1,2,3,4,5}
교차분석 결과: {3번 1을 고른 사람 중: {7번에 1을 고른 사람의 비율이 19%,
                 7번에 2을 고른 사람의 비율이 31%,
                 7번에 3을 고른 사람의 비율이 31%,
                 7번에 4을 고른 사람의 비율이 12%,
                 7번에 5을 고른 사람의 비율이 6% },

                3번 2을 고른 사람 중: {7번에 1을 고른 사람의 비욜이 0%,
                 7번에 2을 고른 사람의 비율이 33%,
                 7번에 3을 고른 사람의 비율이 50%,
                 7번에 4을 고른 사람의 비율이 17%,
                 7번에 5을 고른 사람의 비율이 0%},

                3번 3을 고른 사람 중:{7번에 1을 고른 사람의 비욜이 0%,
                 7번에 2을 고른 사람의 비율이 5%,
                 7번에 3을 고른 사람의 비율이 31%,
                 7번에 4을 고른 사람의 비율이 60%,
                 7번에 5을 고른 사람의 비율이 5%},

                3번 4을 고른 사람 중 :{ 7번에 1을 고른 사람의 비욜이 2%,
                 7번에 2을 고른 사람의 비율이 2%,
                 7번에 3을 고른 사람의 비율이 29%,
                 7번에 4을 고른 사람의 비율이 51%,
                 7번에 5을 고른 사람의 비율이 16%},

               3번 5을 고른 사람 중 { 7번에 1을 고른 사람의 비욜이 6%,
                 7번에 2을 고른 사람의 비율이 0%,
                 7번에 3을 고른 사람의 비율이 11%,
                 7번에 4을 고른 사람의 비율이 39%,
                 7번에 5을 고른 사람의 비율이 44%}}

'''

# 2. 이미지 img_path 리스트로 설정

img_path = [os.path.join(img_folder, fname) 
            for fname in sorted(os.listdir(img_folder)) 
            if fname.endswith(".png")]

# 3. Prompt
## (1) 단일 질문 분석 템플릿
template = '''
너는 설문 조사 결과에 대한 보고서를 한국어로 작성하는 AI야.

아래는 너가 해야 할 일이야:
1) {survey_result}를 바탕으로 해당 질문의 설문 조사 결과를 아래 예시의 형태처럼 간결하게 해석해줘.
불필요한 도입 문장은 생략하고, 핵심 수치만 중심으로 정리해줘.
추가로 설문 조사 결과를 질문 내용과 비교해서 인사이트가 도출되면 한 줄 정도로 작성해줘.

예시:  
SNS 채널 콘텐츠 만족도는 매우 만족 50.8%(827명), 만족 41.6%(677명)으로 92.4%가 만족한다고 응답했다.
이는 콘텐츠 기획이나 운영 방향이 단순한 ‘호감’ 수준을 넘어서 사용자 니즈에 정밀하게 부합하고 있을 가능성을 시사합니다.
'''

## (2) 교차 분석 문항 쌍 추천 템플릿
cross_prompt_template = '''
너는 ERG 이론에 따른 대학생의 SNS 사용 동기와 SNS 사용 만족도간의 관계를 분석하고자 하는 AI야.

아래는 설문조사 질문 리스트야:
{all_questions}

이 중에서 두 문항을 선택해서 교차 분석을 할 거야.  
**ERG 이론에 따른 SNS 사용 동기와 SNS 사용 만족도 간의 관계**를 가장 잘 보여줄 수 있는 문항의 쌍을 골라줘.
단, 교차 분석 가능한 문항 유형은 객관식-객관식, 객관식-성별, 객관식-학년이야. 
형식은 아래처럼 작성해줘:

[추천 문항 쌍]  
(0,2)
'''

## (3) 교차 분석 결과 해석 템플릿
cross_analy_prompt_template = '''
아래 교차 분석 결과를 보고, ERG 이론(Existence, Relatedness, Growth)을 바탕으로 SNS 사용 동기와 SNS 사용 만족도 간의 관계를 불필요한 도입 문장은 생략하고, 간단하고 명확하게 해석해줘.  
구체적인 수치나 비율보다는 전반적인 경향과 관련성 중심으로, 자연스러운 문장으로 정리해줘.

[교차 분석 질문 및 결과]  
{cross_result_text}
'''
# 4. LLM
model = ChatOpenAI(model='gpt-4o-mini', temperature=0)

# 5. 분석 파이프라인
## 5.1 Langcahin 실행
### (1) 단일 질문 분석 
prompt = ChatPromptTemplate.from_template(template)

def get_analysis(img_idx, survey_json):
    """이미지 인덱스를 기반으로 LangChain 분석 실행"""
    
    chain = (
        {
            "survey_result": lambda _: survey_json[img_idx],
        }
        | prompt
        | model
        | StrOutputParser()
    )
    return chain.invoke({})

### (2) 교차 분석 문항 쌍 추천
cross_prompt = ChatPromptTemplate.from_template(cross_prompt_template)

def get_cross_tab_questions(survey_json):
    # 질문 내용만 모아서 문자열로 연결
    question_texts = "\n".join(
        [f"Q{q['질문 번호']}. {q['질문 내용']}" for q in survey_json if '질문 내용' in q]
    )
    
    chain = (
        {
            "all_questions": lambda _: question_texts
        }
        | cross_prompt
        | model
        | StrOutputParser()
    )
    return chain.invoke({})

### (3) 교차 분석 결과 해석
cross_analy_prompt = ChatPromptTemplate.from_template(cross_analy_prompt_template)

def get_cross_analy_questions(cross_result_text):
    chain = (
        {
            "cross_result_text": lambda _: cross_result_text
        }
        | cross_analy_prompt
        | model
        | StrOutputParser()
    )
    return chain.invoke({})


## 5.2 해석 결과 받기
### (1) 단일 문항 해석
survey_content = []

for idx in range(len(survey_json)):
    try:
        result = get_analysis(idx, survey_json)
        survey_content.append(result)
    except Exception as e:
        survey_content.append(f"해석 실패: {e}")

### (2) 교차 분석 문항 쌍 추천
cross_tab_result = get_cross_tab_questions(survey_json)

### (3) 교차 분석 결과 해석
cross_analy_result = get_cross_analy_questions(cross_result_text)

# 6. Word 보고서 생성
doc = Document()

## 제목
doc.add_heading("ERG 이론에 따른 대학생의 SNS 사용 동기와 SNS 사용 만족도간의 관계 연구 설문조사 보고서", level=0)

## 목차
doc.add_page_break()
doc.add_heading("목차", level=1)
doc.add_paragraph("\n")

sections = ["[1] 설문 주제 및 조사 개요", "[2] 단일 질문 분석", "[3] 교차 분석"]

for section in sections:
    para = doc.add_paragraph()
    run = para.add_run(section)
    run.font.name = '맑은 고딕'
    run.font.size = Pt(11)

## [1] 설문 주제 및 조사 개요
doc.add_page_break()
doc.add_heading("[1] 설문 주제 및 조사 개요", level=1)
doc.add_heading("1. 조사목적", level=2)
para1 = doc.add_paragraph()
run1 = para1.add_run(f"• {outline_data['조사목적']}")
run1.font.name = '맑은 고딕'
run1.font.size = Pt(11)

doc.add_heading("2. 조사설계 및 방법", level=2)
outline_contents = ["조사대상", "조사기간", "조사방법", "조사내용", "참여인원"]

for content in outline_contents:
    value = outline_data.get(content, "정보 없음")
    para = doc.add_paragraph()
    run = para.add_run(f"• {content} : {value}")
    run.font.name = '맑은 고딕'
    run.font.size = Pt(11)

## [2] 단일 질문 분석
doc.add_page_break()
doc.add_heading("[2] 단일 질문 분석", level=1)

for i, img in enumerate(img_path):
    doc.add_heading(f"질문 {i+1}", level=2)

    # 이미지 삽입
    try:
        doc.add_picture(img, width=Inches(5))
    except Exception as e:
        doc.add_paragraph(f"이미지 삽입 오류: {e}")

    # 해석 텍스트 삽입
    try:
        analysis_text = survey_content[i] if i < len(survey_content) else "해석 없음"
    except Exception as e:
        analysis_text = f"해석 실패: {e}"

     # 문장 단위로 줄바꿈 처리
    sentences = re.split(r'(?<=[.!?])\s+', analysis_text.strip())  # 마침표, 느낌표, 물음표 뒤 기준
    for sentence in sentences:
        para = doc.add_paragraph()
        run = para.add_run(sentence.strip())
        run.font.name = '맑은 고딕'
        run.font.size = Pt(11)

    doc.add_paragraph("\n")  # 간격 띄우기
    
    # # 문단 생성 후 글꼴 적용
    # para = doc.add_paragraph()
    # run = para.add_run(analysis_text)
    # run.font.name = '맑은 고딕'  
    # run.font.size = Pt(11)       

    doc.add_paragraph("\n")  # 간격 띄우기

## [3] 교차 분석
doc.add_page_break()
doc.add_heading("[3] 교차 분석", level=1)

cross_img = r"C:\Users\toozi\OneDrive\문서\GitHub\BizLab\img\test_cross\cross_img.png"
doc.add_picture(cross_img, width=Inches(6)) 

para = doc.add_paragraph()
run = para.add_run(cross_analy_result)
run.font.name = '맑은 고딕'
run.font.size = Pt(11)

doc.add_paragraph("\n")

## 저장
output_name = "ERG 이론 설문조사_보고서.docx"
doc.save(output_name)
print(f"✅ Word 저장 완료: {output_name}")
