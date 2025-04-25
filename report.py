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
from docx.oxml.ns import qn


# API 키 입력
api_key = getpass("OpenAI API 키를 입력하세요: ")

os.environ['OPENAI_API_KEY'] = api_key

# 현재 파일의 경로를 기준으로 상대경로 설정
base_dir = os.path.dirname(os.path.abspath(__file__))
result_json_path = os.path.join(base_dir, 'data', 'survey_result.json')
outline_json_path = os.path.join(base_dir, 'data', 'survey_outline.json')
survey_path = os.path.join(base_dir, 'data', 'survey.json')
cross_result_path = os.path.join(base_dir, 'data', 'ESG.test_cross.json')
img_folder = os.path.join(base_dir, 'img', 'test')
cross_img_folder = os.path.join(base_dir, 'img', 'test_cross')

# 1. 데이터 로딩
with open(result_json_path, 'r', encoding='utf-8-sig') as f:
    survey_json = json.load(f)

with open(outline_json_path, "r", encoding="utf-8") as f:
    outline_data = json.load(f)
    
with open(survey_path, "r", encoding="utf-8") as f:
    survey_data = json.load(f)
    
with open(cross_result_path, 'r', encoding='utf-8') as f:
    cross_result_text = f.read()

# 2. 이미지 img_path 리스트로 설정
img_path = [os.path.join(img_folder, fname) 
            for fname in sorted(os.listdir(img_folder)) 
            if fname.endswith(".png")]

# 3. Prompt
## (1) 보고서 목차 생성 템플릿
index_template = '''
너는 설문조사 결과를 바탕으로 한국어 보고서를 작성하는 AI야.

다음은 네가 수행해야 할 작업이야:
1) 입력된 설문 정보에는 보고서 제목과 목적이 포함돼 있어.  
2) 이를 참고해서 해당 보고서 제목과 목적에 맞는 [보고서 목차]를 작성해줘.  
3) 아래 예시처럼 보고서 제목에 맞는 목차를 항목별로 구성해줘.

[입력된 설문 정보]
{survey}

[예시]  
[보고서 제목]  
Digital Predictions 2018  

[보고서 목차]  
- Foreword  
- The digital consumer  
- Smart(er) phones: smarter applications  
- The machines are learning  
- Strap in: connectivity takes off  
- Augmented Reality bites  
- The subscription prescription  
- Rebuilding the supply chain – block by blockchain  
- Endnotes  
- Contacts  
'''

## (2) 목차에 설문 질문 매칭 템플릿
question_template='''
1) 입력된 설문 조사 결과 정보에는 설문 조사 질문 내용이 포함돼 있어. 
2) 입력된 설문 조사 목차에는 보고서의 목차가 있어.
3) 이를 참고해서 각 설문 조사 질문 내용을 잘 설명해주는 목차에 질문 번호를 주의 사항에 맞춰서 배치해줘.
4) 주의 사항 : 질문 번호는 모두 매치되어야 하고, 여러 목차에 중복해서 배치되면 안돼. 질문 유형이 "성별", "학년", "전화번호"와 같은 개인 정보를 담은 질문은 배치에서 제외해줘. 

[입력된 설문 조사 결과 정보]
{survey_json}

[입력된 설문 조사 목차]
{survey_index}
'''

## (3) 단일 질문 분석 템플릿
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

## (4) 교차 분석 질문 쌍 추천 템플릿
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

## (5) 교차 분석 결과 해석 템플릿
cross_analy_prompt_template = '''
아래 교차 분석 결과는 질문 3과 질문 7에 대한 응답을 바탕으로 생성된 것이다. ERG 이론(Existence, Relatedness, Growth)을 바탕으로 질문 3(R)과 질문 7(만족도) 사이의 전반적인 경향만 자연스럽고 간결하게 설명해줘.  
수치 언급은 최소화하고, 전체적인 패턴과 관련성 중심으로 해석해줘.

[교차 분석 질문 및 결과]  
{cross_result_text}
'''
# 4. LLM
model = ChatOpenAI(model='gpt-4o-mini', temperature=0, seed=42)

# 5. 분석 파이프라인
## 5.1 Langcahin 실행
### (1) 보고서 목차 생성
index_prompt = ChatPromptTemplate.from_template(index_template)

def get_index(survey_data):

    chain = (
        {
            "survey": lambda _: survey_data,
        }
        | index_prompt
        | model
        | StrOutputParser()
    )
    return chain.invoke({})

survey_index_content = get_index(survey_data)

start_keyword = "[보고서 목차]"
start_index = survey_index_content.find(start_keyword)
if start_index != -1:
    survey_index = survey_index_content[start_index + len(start_keyword):].strip()
else:
    print("❌ '[보고서 목차]' 항목을 찾을 수 없습니다.")


# 문자열을 적절하게 처리하도록 수정
def parse_survey_index(content):
    parsed_index = []
    lines = content.split("\n")
    
    current_title = ""
    sub_entries = []

    for line in lines:
        if line.strip() == "":  # 빈 줄은 건너뛰기
            continue

        indent_level = (len(line) - len(line.lstrip())) // 4  # 4칸씩 들여쓰기를 기준으로
        line = line.strip()

        if indent_level == 0:
            if current_title:
                parsed_index.append((current_title, sub_entries))  # 이전 항목 추가
            current_title = line
            sub_entries = []
        else:
            sub_entries.append(line)

    if current_title:
        parsed_index.append((current_title, sub_entries))  # 마지막 항목 추가

    return parsed_index

index_content = parse_survey_index(survey_index)

### (2) 목차에 설문 질문들 매칭
question_prompt = ChatPromptTemplate.from_template(question_template)

def get_question(survey_json, survey_index):

    chain = (
        {
            "survey_json": lambda _: survey_json,
            "survey_index": lambda _: survey_index,
        }
        | question_prompt
        | model
        | StrOutputParser()
    )
    return chain.invoke({})

matching_result = get_question(survey_json, survey_index)

### (3) 단일 질문 분석 
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

### (4) 교차 분석 질문 쌍 추천
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

### (5) 교차 분석 결과 해석
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
### (3) 단일 질문 해석
survey_content = []

for idx in range(len(survey_json)):
    try:
        result = get_analysis(idx, survey_json)
        survey_content.append(result)
    except Exception as e:
        survey_content.append(f"해석 실패: {e}")

### (4) 교차 분석 문항 쌍 추천
cross_tab_result = get_cross_tab_questions(survey_json)

### (5) 교차 분석 결과 해석
cross_analy_result = get_cross_analy_questions(cross_result_text)

# 6. Word 보고서 생성
doc = Document()

## 제목
title = "대학생의 SNS 사용동기가 만족도와 사용시간에 미친 영향 연구– Alderfer의 ERG 이론을 중심으로 -"
doc.add_heading(title, level=0)

## 목차
doc.add_page_break()
doc.add_heading("목차", level=1)
doc.add_paragraph("\n")

# sections = ["[1] 설문 주제 및 조사 개요", "[2] 단일 질문 분석", "[3] 교차 분석"]
# print(survey_index)

# for section in survey_index:
#     para = doc.add_paragraph()
#     run = para.add_run(section)
#     run.font.name = '맑은 고딕'
#     run.font.size = Pt(11)

def add_index_entry(text, indent_level=0): 
    para = doc.add_paragraph()
    run = para.add_run("    " * indent_level + text)
    run.font.name = '맑은 고딕'
    run._element.rPr.rFonts.set(qn('w:eastAsia'), '맑은 고딕')
    run.font.size = Pt(11)

# parsed_index에 따라 문서에 항목 추가
for entry in index_content:
    title, subentries = entry
    add_index_entry(title, indent_level=0)
    for subentry in subentries:
        add_index_entry(subentry, indent_level=1)

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

cross_img = os.path.join(cross_img_folder, 'cross_img.png')
doc.add_picture(cross_img, width=Inches(6)) 

para = doc.add_paragraph()
run = para.add_run(cross_analy_result)
run.font.name = '맑은 고딕'
run.font.size = Pt(11)

doc.add_paragraph("\n")

## 저장
output_name = "ERG 이론 설문조사_보고서.docx"
doc.save(output_name)
print(f" Word 저장 완료: {output_name}")
