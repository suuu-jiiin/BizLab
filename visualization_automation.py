import numpy as np
import json
import pandas as pd
from visualization import barh_plot, pie_plot, bar_plot, wordcloud_plot
from utils import set_korean_font

# 파일 경로 설정
result_json_path = r"C:\Users\toozi\OneDrive\문서\GitHub\BizLab\data\survey_result.json"

# 1. 데이터 로딩
with open(result_json_path, 'r', encoding='utf-8-sig') as f:
    survey_json = json.load(f)
    

# 2. 시각화 자동화 코드
def Generate_Report(json_results, file_name, imbalance):
  '''
  counter: json_result에서 각 문항에 접근하기 위함이지 question id 를 나타내는 것은 아님.
  imbalance: 데이터 불균형 판단 기준(percentage) - e.g. 80.0
  '''
  counter=0
  while counter<len(json_results):
    question_idx=json_results[counter]['질문 번호'] # question_id를 이용해 label_dict에 접근할 수 있음.
    question_type= json_results[counter]['질문 유형']

    if question_type=='객관식 질문':
      sum=np.sum(list(map(float, json_results[counter]['답변'].values()))) # 답변 개수의 합 -> 불균형 판단 위함.
      val_list=[val for val in json_results[counter]['답변'].values()] # 답변 별 개수 리스트 -> 불균형 판단 위함.

      # 가로 막대형
      if np.mean([len(label) for label in json_results[question_idx]['답변'].keys()]) >= 6:
        barh_plot(json_results, question_id=question_idx, file_name=file_name, design=None) # 객관식에서 label의 길이가 길 경우 barh_plot 이용하기 위한 조건문, mean/max/median 및 길이 기준은 선택 가능

      # pie chart
      elif max(val_list/sum*100)>=imbalance:
        pie_plot(json_results, question_id=counter, file_name=file_name, design=None) # 가로막대형 상황과 pie chart 상황을 둘 다 만족할 때 어떤 걸 우선시 할 것인가

      #세로 막대형
      else:
        bar_plot(json_results=json_results, question_id=counter, file_name=file_name, design=None) #json 확립 이후 변수 명 변경 예정.

    elif question_type=='주관식':
      wordcloud_plot(json_results=json_results, question_id=counter,file_name=file_name, design=None)
    elif question_type=='성별':
      pie_plot(json_results=json_results, question_id=counter, file_name=file_name, design=None)
    elif question_type=='전화번호':
      pass
    elif question_type=='이메일':
      pass
    elif question_type=='숫자':
      # box plot or histogram ?
      pass
    else:
      pass
    counter+=1

set_korean_font()
Generate_Report(survey_json,file_name='test', imbalance=80.0)