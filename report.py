import os
import pandas as pd
from getpass import getpass
from fpdf import FPDF
from fpdf.enums import XPos, YPos
import fitz
import json
import re
import textwrap
from PIL import Image
from langchain_community.document_loaders import PyMuPDFLoader
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.runnables import RunnableMap, RunnablePassthrough
from langchain_core.output_parsers import StrOutputParser
from docx import Document
from docx.shared import Inches
from docx.enum.text import WD_PARAGRAPH_ALIGNMENT


# API 키 입력
api_key = getpass("OpenAI API 키를 입력하세요: ")
os.environ['OPENAI_API_KEY'] = api_key

# 파일 경로 설정
csv_path = r"C:\Users\toozi\OneDrive\문서\GitHub\BizLab\data\survey_data.csv"
json_path = r"C:\Users\toozi\OneDrive\문서\GitHub\BizLab\data\survey_result.json"
ref_path = r"C:\Users\toozi\OneDrive\문서\GitHub\BizLab\data\reference.pdf"
img_folder = r"C:\Users\toozi\OneDrive\바탕 화면\비즈랩\img"


# 1. 데이터 로딩
pd.read_csv(csv_path, encoding='utf-8')  # 필요 시 사용
with open(json_path, 'r', encoding='utf-8-sig') as f:
    survey_json = json.load(f)
    
ref_pdf = fitz.open(ref_path)

# 2. 이미지 img_path 리스트로 설정정

img_path = [os.path.join(img_folder, fname) 
            for fname in sorted(os.listdir(img_folder)) 
            if fname.endswith(".png")]

# 3. Prompt
template = '''
너는 설문 조사 결과에 대한 보고서를 한국어로 작성하는 AI야. 보고서의 구조는 아래와 같고 섹션 바뀔 때 페이지가 달라져야 돼 :
[1] 목차 
[2] 설문 주제 및 조사 개요 
[3] Introduction 
[4] 단일 질문 분석 
[5] 교차 분석
[6] 결론
[7] 기타

아래는 너가 해야할 일이야 :
1) [1] 목차에는 목차 제외 6개 섹션을 한 눈에 볼 수 있도록 각 섹션의 이름을 작성, 6개 섹션 제목에 하이퍼링크 설정해서 목차에서 바로 해당 섹션으로 이동 가능하도록 설정해.
2) 섹션이 바뀔 때마다 페이지가 변경되어야 돼.
3) [4] 단일 질문 분석 섹션 : {img_path}에 있는 모든 사진에 대해서 차례대로 {survey_result}를 바탕으로 해당 질문의 설문조사 결과를 해석해줘. 각 사진 아래에 해석이 한 줄씩 적혀있어야 돼. 아래 예시의 형태대로 작성해.
ex. SNS 채널 콘텐츠 만족도는 매우 만족 50.8%(827명), 만족 41.6%(677명)으로 92.4% 만족한다.  
4) 내가 언급하지 않은 섹션들은 제목만 존재하고 내용은 없어.
'''

prompt = ChatPromptTemplate.from_template(template)

# 4. LLM
model = ChatOpenAI(model='gpt-4o-mini', temperature=0)

# 5. 분석 파이프라인
## 5.1 Langcahin 실행
def get_analysis(img_idx, survey_json):
    """이미지 인덱스를 기반으로 LangChain 분석 실행"""
    chain = (
        {
            "img_path": lambda _: img_path[img_idx],
            "survey_result": lambda _: survey_json
        }
        | prompt
        | model
        | StrOutputParser()
    )
    return chain.invoke({})

## 5.2 [4] 단일 질문 분석 해석만 파싱
def parse_single_question_analysis(full_text):
    section = re.search(r"# \[4\] 단일 질문 분석\n(.*?)\n---", full_text, re.DOTALL)
    if not section:
        return []

    content = section.group(1)
    pattern = r"## 질문 (\d+)\n.*?\n- \*\*결과 해석\*\*: (.*?)\n"
    matches = re.findall(pattern, content)

    # 질문 번호 기준 정렬
    sorted_matches = sorted(matches, key=lambda x: int(x[0]))
    return [m[1] for m in sorted_matches]  # 해석만 리스트로 반환

analysis_full_text = get_analysis(0, survey_json)  
analysis_list = parse_single_question_analysis(analysis_full_text)

print(analysis_full_text)

# 6. Word 보고서 생성
doc = Document()

# 제목
doc.add_heading("ERG 이론에 따른 대학생의 SNS 사용 동기와 SNS 사용 만족도간의 관계 연구 설문조사 보고서", level=0)

# [1] 목차
doc.add_page_break()
doc.add_heading("[1] 목차", level=1)
sections = ["[2] 설문 주제 및 조사 개요", "[3] Introduction", "[4] 단일 질문 분석", "[5] 교차 분석", "[6] 결론", "[7] 기타"]
for section in sections:
    doc.add_paragraph(section)

# [2] 설문 주제 및 조사 개요
doc.add_page_break()
doc.add_heading("[2] 설문 주제 및 조사 개요", level=1)

# [3] Introduction
doc.add_page_break()
doc.add_heading("[3] Introduction", level=1)

# [4] 단일 질문 분석
doc.add_page_break()
doc.add_heading("[4] 단일 질문 분석", level=1)

# 각 이미지별 해석 생성
analysis_list = []
for idx in range(len(img_path)):
    analysis = get_analysis(idx, survey_json)
    parsed = parse_single_question_analysis(analysis)
    analysis_list.append(parsed[0] if parsed else "해석 없음")

# 단일 질문 분석 삽입
for i, img in enumerate(img_path):
    doc.add_heading(f"질문 {i+1}", level=2)

    # 이미지 삽입
    try:
        doc.add_picture(img, width=Inches(6))
    except Exception as e:
        doc.add_paragraph(f"이미지 삽입 오류: {e}")

    # 해석 삽입
    analysis_text = analysis_list[i] if i < len(analysis_list) else "해석 없음"
    p = doc.add_paragraph(analysis_text)
    p.alignment = WD_PARAGRAPH_ALIGNMENT.LEFT
    doc.add_paragraph("\n")

# [5] 교차 분석
doc.add_page_break()
doc.add_heading("[5] 교차 분석", level=1)

# [6] 결론
doc.add_page_break()
doc.add_heading("[6] 결론", level=1)

# [7] 기타
doc.add_page_break()
doc.add_heading("[7] 기타", level=1)

# 저장
output_name = "ERG 이론 설문조사_보고서.docx"
doc.save(output_name)
print(f"✅ Word 저장 완료: {output_name}")


# 보고서 PDF 양식
class PDF(FPDF):
    def __init__(self):
        super().__init__()
        self.set_auto_page_break(auto=True, margin=15)

        # 폰트 등록
        ## 제목 폰트
        bold_font_path = r"C:\\Users\\toozi\\OneDrive\\바탕 화면\\비즈랩\\font\\NanumHumanBold.ttf"
        self.add_font('NanumBold', '', bold_font_path, uni=True)

        ## 내용 폰트
        font_path = r"C:\\Users\\toozi\\OneDrive\\바탕 화면\\비즈랩\\font\\NanumHumanRegular.ttf"
        self.add_font('Nanum', '', font_path, uni=True)
        self.set_font('Nanum', '', 10)

    def add_question_title(self):
        self.set_font('NanumBold', '', 14)
        self.cell(0, 10, "단일 질문 분석", ln=True)

    def add_question_section(self, img_path, analysis_text):
        # 이미지 삽입
        img = Image.open(img_path)
        img_width, img_height = img.size
        max_width = 180
        ratio = max_width / img_width
        new_width = max_width
        new_height = img_height * ratio

        self.image(img_path, x=15, y=None, w=new_width, h=new_height)

        # 분석 텍스트
        self.ln(5)
        self.set_font('Nanum', '', 10)
        self.multi_cell(0, 10, analysis_text)
        self.ln(10)

'''
# 6. PDF 보고서 생성
pdf = PDF()
pdf.add_page()

# 전체 보고서 텍스트 먼저 삽입
pdf.set_font('Nanum', '', 11)
pdf.multi_cell(0, 10, analysis_full_text)

# 단일 질문 분석 섹션 시작
pdf.add_page()
pdf.add_question_title()

for i, img in enumerate(img_path):
    try:
        analysis_text = analysis_list[i] if i < len(analysis_list) else "해석 없음"
    except Exception as e:
        analysis_text = f"분석 실패: {e}"

    pdf.add_question_section(img, analysis_text)

output_name = "ERG 이론에 따른 대학생의 SNS 사용 동기와 SNS 사용 만족도간의 관계 연구 설문조사_보고서.pdf"
pdf.output(output_name)
print(f"✅ PDF 저장 완료: {output_name}")
'''