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


# API 키 입력
api_key = getpass("OpenAI API 키를 입력하세요: ")
os.environ['OPENAI_API_KEY'] = api_key

# 파일 경로 설정
csv_path = r"C:\Users\toozi\OneDrive\바탕 화면\비즈랩\data\survey_data.csv"
pdf_path = r"C:\Users\toozi\OneDrive\바탕 화면\비즈랩\data\single_question.pdf"
json_path = r"C:\Users\toozi\OneDrive\바탕 화면\비즈랩\data\survey_result.json"
ref_path = r"C:\Users\toozi\OneDrive\바탕 화면\비즈랩\data\reference.pdf"

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


# 1. 데이터 로딩
pd.read_csv(csv_path, encoding='utf-8')  # 필요 시 사용
with open(json_path, 'r', encoding='utf-8-sig') as f:
    survey_json = json.load(f)
    
ref_pdf = fitz.open(ref_path)

# 2. 단일 질문 시각화 PDF -> 이미지 변환
pdf_doc = fitz.open(pdf_path)
img_folder = r"C:\Users\toozi\OneDrive\바탕 화면\비즈랩\img"
os.makedirs(img_folder, exist_ok=True)

img_paths = []
for page_num in range(len(pdf_doc)):
    pix = pdf_doc[page_num].get_pixmap(dpi=200)
    img_path = os.path.join(img_folder, f"page_{page_num + 1}.png")
    pix.save(img_path)
    img_paths.append(img_path)


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
2) [4] 단일 질문 분석 섹션 : {img_path}에 있는 모든 img에 대해서 차례대로 {survey_result}를 바탕으로 해당 질문의 설문조사 결과를 해석해줘. 각 사진 아래에 해석이 한 줄씩 적혀있어야 돼. 아래 예시의 형태대로 작성해.
ex. SNS 채널 콘텐츠 만족도는 매우 만족 50.8%(827명), 만족 41.6%(677명)으로 92.4% 만족한다.  
3) 내가 언급하지 않은 섹션들은 제목만 존재하고 내용은 없어.
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
            "img_path": lambda _: img_paths[img_idx],
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


# 6. PDF 보고서 생성
pdf = PDF()
pdf.add_page()

# 전체 보고서 텍스트 먼저 삽입
pdf.set_font('Nanum', '', 11)
pdf.multi_cell(0, 10, analysis_full_text)

# 단일 질문 분석 섹션 시작
pdf.add_page()
pdf.add_question_title()

for i, img_path in enumerate(img_paths):
    try:
        analysis_text = analysis_list[i] if i < len(analysis_list) else "해석 없음"
    except Exception as e:
        analysis_text = f"분석 실패: {e}"

    pdf.add_question_section(img_path, analysis_text)

output_name = "ERG 이론에 따른 대학생의 SNS 사용 동기와 SNS 사용 만족도간의 관계 연구 설문조사_보고서.pdf"
pdf.output(output_name)
print(f"✅ PDF 저장 완료: {output_name}")