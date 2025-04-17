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
csv_path = r"C:\Users\toozi\OneDrive\문서\GitHub\BizLab\data\survey_data.csv"
json_path = r"C:\Users\toozi\OneDrive\문서\GitHub\BizLab\data\survey_result.json"
ref_path = r"C:\Users\toozi\OneDrive\문서\GitHub\BizLab\data\reference.pdf"
img_folder = r"C:\Users\toozi\OneDrive\문서\GitHub\BizLab\img"


# 1. 데이터 로딩
pd.read_csv(csv_path, encoding='utf-8')  # 필요 시 사용
with open(json_path, 'r', encoding='utf-8-sig') as f:
    survey_json = json.load(f)

# 2. 이미지 img_path 리스트로 설정

img_path = [os.path.join(img_folder, fname) 
            for fname in sorted(os.listdir(img_folder)) 
            if fname.endswith(".png")]

# 3. Prompt
template = '''
너는 설문 조사 결과에 대한 보고서를 한국어로 작성하는 AI야.

아래는 너가 해야할 일이야 :
1) {survey_result}를 바탕으로 해당 질문의 설문 조사 결과를 아래 예시의 형태대로 해석해줘.
ex. SNS 채널 콘텐츠 만족도는 매우 만족 50.8%(827명), 만족 41.6%(677명)으로 92.4% 만족한다.  
'''

prompt = ChatPromptTemplate.from_template(template)

# 4. LLM
model = ChatOpenAI(model='gpt-4o-mini', temperature=0)

# 5. 분석 파이프라인
## 5.1 Langcahin 실행
result_content = []

def get_analysis(img_idx, survey_json):
    """이미지 인덱스를 기반으로 LangChain 분석 실행"""
    
    chain = (
        {
            "survey_result": lambda _: survey_json[img_idx],
            "result_content": lambda _: survey_json[img_idx]
        }
        | prompt
        | model
        | StrOutputParser()
    )
    return chain.invoke({})

## 5.2 해석 결과 받기
for idx in range(len(img_path)):
    print(f"🔍 {idx+1}번 이미지 해석 중...")
    try:
        analysis_result = get_analysis(idx, survey_json)
        result_content.append(analysis_result)
    except Exception as e:
        result_content.append(f"해석 실패: {e}")

print(result_content)

# 6. Word 보고서 생성
doc = Document()
# 제목
doc.add_heading("ERG 이론에 따른 대학생의 SNS 사용 동기와 SNS 사용 만족도간의 관계 연구 설문조사 보고서", level=0)

# 목차
doc.add_page_break()
doc.add_heading("목차", level=1)
sections = ["[1] 설문 주제 및 조사 개요", "[2] Introduction", "[3] 단일 질문 분석", "[4] 교차 분석", "[5] 결론", "[6] 기타"]
for section in sections:
    doc.add_paragraph(section)

# [1] 설문 주제 및 조사 개요
doc.add_page_break()
doc.add_heading("[1] 설문 주제 및 조사 개요", level=1)

# [2] Introduction
doc.add_page_break()
doc.add_heading("[2] Introduction", level=1)

# [3] 단일 질문 분석
doc.add_page_break()
doc.add_heading("[3] 단일 질문 분석", level=1)

for i, img in enumerate(img_path):
    doc.add_heading(f"질문 {i+1}", level=2)

    # 이미지 삽입
    try:
        doc.add_picture(img, width=Inches(6))
    except Exception as e:
        doc.add_paragraph(f"이미지 삽입 오류: {e}")

    # 해석 텍스트 삽입
    try:
        analysis_text = result_content[i] if i < len(result_content) else "해석 없음"
    except Exception as e:
        analysis_text = f"해석 실패: {e}"

    # 문단 생성 후 글꼴 적용
    para = doc.add_paragraph()
    run = para.add_run(analysis_text)
    run.font.name = '맑은 고딕'  # 또는 'Arial', 'NanumGothic' 등 시스템에 설치된 폰트명
    run.font.size = Pt(11)       # 글씨 크기 (11pt 정도가 일반적인 본문용)

    doc.add_paragraph("\n")  # 간격 띄우기

# [4] 교차 분석
doc.add_page_break()
doc.add_heading("[4] 교차 분석", level=1)

# [5] 결론
doc.add_page_break()
doc.add_heading("[5] 결론", level=1)

# [6] 기타
doc.add_page_break()
doc.add_heading("[6] 기타", level=1)

# 저장
output_name = "ERG 이론 설문조사_보고서.docx"
doc.save(output_name)
print(f"✅ Word 저장 완료: {output_name}")
