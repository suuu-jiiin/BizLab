import pandas as pd
import json
import numpy as np
import os
from utils import set_korean_font
from cross_analysis import cross_likertXdemo, read_likertXdemo, cross_response_dist, cross_likertXlikert_h, read_likertXlikert, cross_likertXlikert
from visualization import simplify_data

# 현재 파일의 경로를 기준으로 상대경로 설정
base_dir = os.path.dirname(os.path.abspath(__file__))
raw_path = os.path.join(base_dir, 'data', 'survey_data.csv')
result_json_path = os.path.join(base_dir, 'data', 'survey_result.json')

# 1. 데이터 로딩
with open(result_json_path, 'r', encoding='utf-8-sig') as f:
    survey_json = json.load(f)
    
raw_data = pd.read_csv(raw_path)

# 2. 자동화 함수
def GeneratePlotsForCross(data, json_result, input, personal_info,file_name,design=None):
  simple_data = simplify_data(data)

  #simple_data -> data & index로 분리
  index=simple_data[:2]
  data=simple_data[2:]

  #json result에서 질문 내용만 가져와서 index에 추가
  question_list=[q['질문 내용'] for q in json_result]
  question_list.insert(0,'question')
  question_df=pd.DataFrame(question_list)
  index=pd.concat([index,question_df.T], axis=0,ignore_index=True)


  chart_reading={} # ->.json : 차트 내용 읽어오는 딕셔너리

  n=len(input) # 교차 분석을 시행해야하는 횟수
  idx=0

  while idx < n:
    q1= input[idx][0] # gpt가 묶은 쌍 중, 첫번째 문항 (q1,q2) 중 q1
    q2= input[idx][1] # gpt가 묶은 쌍 중, 두번째 질문 (q1,q2) 중 q2
    q1_type= index[q1][0]
    q2_type= index[q2][0]

    # 1. 개인정보 포함된 경우 -> cross_likertXdemo 사용
    if q1_type in personal_info:
      cross_likertXdemo(index=index, data=data, targetQ_id=q2, pInfo_id=q1, file_name=file_name, design=None)
      read=read_likertXdemo(index=index, data=data, targetQ_id=q2, pInfo_id=q1)

      chart_reading[f"{q1},{q2}"]= read
      with open(f'{file_name}_cross.json', 'w', encoding='utf-8') as f:
        json.dump(chart_reading, f, ensure_ascii=False, indent=4)

    elif q2_type in personal_info:
      cross_likertXdemo(index=index, data=data, targetQ_id=q1, pInfo_id=q2, file_name=file_name, design=None)
      read=read_likertXdemo(index=index, data=data, targetQ_id=q1, pInfo_id=q2)

      chart_reading[f"{q1},{q2}"]= read
      with open(f'{file_name}_cross.json', 'w', encoding='utf-8') as f:
        json.dump(chart_reading, f, ensure_ascii=False, indent=4)

    # 2. 둘 다 객관식 질문인 경우 -> label 길이에 따라 horizontal/vertical
    elif q1_type == '객관식 질문' and q2_type == '객관식 질문':
      #likert2likert함수에 들어갈 category_name 생성 부분
      q2_categories =  index[q2][1]
      q2_categories = q2_categories.strip('[]')
      q2_categories = q2_categories.split(',')

      temp = cross_response_dist(data,  q1, q2)

      # 레이블이 길 경우 → 가로 막대 그래프
      if (np.mean([len(label) for label in data[q1].unique()]) > 4) or (np.mean([len(label) for label in data[q2].unique()]) > 4):
        cross_likertXlikert_h(temp, q2_categories,  q1, q2, file_name, design=None)
        read=read_likertXlikert(temp,q2_categories,  q1, q2)

      else:
        cross_likertXlikert(temp, q2_categories,  q1, q2,file_name, design=None)
        read=read_likertXlikert(temp, q2_categories,  q1, q2)

      chart_reading[f"{q1},{q2}"]= read
      with open(f'{file_name}_cross.json', 'w', encoding='utf-8') as f:
        json.dump(chart_reading, f, ensure_ascii=False, indent=4)

    # 기타 타입일 경우는 필요에 따라 여기에 조건 추가 가능
    else:
      print(f"아직 정의되지 않은 질문 유형 조합입니다: {q1_type}, {q2_type}")


    idx += 1

set_korean_font()

input = [(9,12),(3,7),(5,8)]
personal_info=['성별', '나이']
GeneratePlotsForCross(data=raw_data, json_result=survey_json, input=input, personal_info=personal_info,file_name='ESG.test')