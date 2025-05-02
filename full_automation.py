import os
import re
import json
import pandas as pd
from utils import set_korean_font
from csv2json import survey_result
from visualization_automation import GeneratePlotsForSingleQ
from cross_analysis_automation import GeneratePlotsForCross
from report import survey_report
from llm import get_analysis, get_cross_tab_questions, get_cross_analy_questions

# 0. 변수 설정
#folder_name = 'ESG.test'
folder_name = 'SmartphoneUsage.test'
file_name = 'survey_data.csv'
#file_name = 'Pseudo_Survey_Results.csv'
survey_outline_name = 'survey_outline.json'
singleq_json_name = 'survey_result.json'

## 교차 분석 변수
personal_info=['성별', '나이'] # 설문 조사 질문 유형 중 개인정보에 속하는 유형

## 보고서 변수
#title = "대학생의 SNS 사용동기가 만족도와 사용시간에 미친 영향 연구– Alderfer의 ERG 이론을 중심으로"
title = "현대인의 생활 행태와 웰빙 수준에 관한 실태조사 보고서"
sections = ["[1] 설문 주제 및 조사 개요", "[2] 단일 질문 분석", "[3] 교차 분석"]
#output_name = '(docx) ERG이론 설문조사 결과 보고서.docx'
output_name = '(docx) 생활 행태와 웰빙 수준 설문조사 결과 보고서.docx'

# 1. 데이터 로딩
base_dir = os.path.dirname(os.path.abspath(__file__))
local = os.path.join(base_dir, 'data', f'{folder_name}')
raw_path = os.path.join(local, f'{file_name}') # 설문 조사 결과 csv
result_json_path = os.path.join(local, f'{singleq_json_name}') # 단일 질문 결과 json
outline_json_path = os.path.join(local, f'{survey_outline_name}') # 설문 조사 개요 json

raw_data = pd.read_csv(raw_path, encoding='utf-8-sig') # raw data (csv 파일)

with open(outline_json_path, "r", encoding="utf-8") as f:
    outline_data = json.load(f)

# 2. 단일 질문 해석 json 파일 생성 
survey_result(raw_data, folder_name, json_name=singleq_json_name)

with open(result_json_path, 'r', encoding='utf-8-sig') as f: # raw data 해석한 json 파일
    survey_json = json.load(f)
    

# 3. utils에 저장된 한글 불러오기
set_korean_font()

# 4. 단일 질문 시각화 
GeneratePlotsForSingleQ(survey_json, imbalance=80.0, folder_name=folder_name, design='Pastel1')

# 5. 교차 분석 시각화
## (1) llm을 통해 교차 분석 질문 쌍 추천
cross_tab_result = get_cross_tab_questions(outline_data, survey_json)
pairs = re.findall(r'\((\d+),\s*(\d+)\)', cross_tab_result) # 정규표현식으로 (숫자, 숫자) 형식 추출 => gpt의 결과가 [추천 문항 쌍]으로 한글도 함께 나와서 해당 코드 추가함
cross_tab_result_cleaned = [(int(a), int(b)) for a, b in pairs] # 튜플 리스트로 변환
print(cross_tab_result_cleaned)

## (2) 교차 분석 시각화
GeneratePlotsForCross(data=raw_data, json_result=survey_json, input=cross_tab_result_cleaned, personal_info=personal_info, folder_name=folder_name)

# 6. 보고서 생성을 위한 데이터 로딩
cross_result_path = os.path.join(local, f'{folder_name}_cross.json') # 교차 분석 결과 json
img_folder = os.path.join(base_dir, 'img',  f'{folder_name}' ) # 단일 질문 시각화 이미지
cross_img_folder = os.path.join(base_dir, 'img',  f'{folder_name}_cross') # 교차 분석 시각화 이미지

with open(cross_result_path, 'r', encoding='utf-8') as f:
    cross_result_text = json.load(f)
    
 
## 단일 질문 시각화 이미지 img_path 리스트로 설정
img_path = [os.path.join(img_folder, fname) 
            for fname in sorted(os.listdir(img_folder)) 
            if fname.endswith(".png")]

# 7. llm 결과값
## (1) 단일 질문 해석
survey_content = []

for idx in range(len(survey_json)):
    try:
        result = get_analysis(idx, survey_json)
        survey_content.append(result)
    except Exception as e:
        survey_content.append(f"해석 실패: {e}")

## (2) 교차 분석 결과 해석
cross_analy_result = get_cross_analy_questions(outline_data, cross_result_text)

# 정규 표현식으로 분석 텍스트와 질문 쌍을 추출
cross_analy_text = []
pattern = r'\[(.*?)\]\s*(.*?)(?=\[|$)'

matches = re.findall(pattern, cross_analy_result, re.DOTALL)

# 결과 저장
for match in matches:
    questions = match[0]  # [번호 질문, 번호 질문]
    text = match[1].strip()  # 해당 분석 텍스트
    cross_analy_text.append(text)

# 8. 보고서 생성
survey_report(title, sections, outline_data, img_path, survey_content, cross_img_folder, cross_analy_text, local, output_name)
