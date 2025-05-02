import os
import ast
import json
import numpy as np
import pandas as pd
from csv2json import simplify_data
from cross_analysis import cross_likertXdemo, read_likertXdemo, cross_response_dist, cross_likertXlikert_h, read_likertXlikert, cross_likertXlikert
  
# 1. json 파일 저장 함수
def save2json(folder_name, chart_reading):
  base_dir = os.path.dirname(os.path.abspath(__file__))
  data_dir = os.path.join(base_dir, 'data', f'{folder_name}') 
  json_path = os.path.join(data_dir, f'{folder_name}_cross.json')
        
  with open(json_path, 'w', encoding='utf-8') as f:
    json.dump(chart_reading, f, ensure_ascii=False, indent=4)

# 2. 교차 분석 시각화 자동화 함수
def GeneratePlotsForCross(data, json_result, input, personal_info,folder_name,design='Pastel1'):
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
    valid_types = ['객관식 질문', '평가형'] # horizontal/vertical 차트

    n=len(input) # 교차 분석을 시행해야하는 횟수
    idx=0

    while idx < n:
      q1= input[idx][0] # gpt가 묶은 쌍 중, 첫번째 질문 (q1,q2) 중 q1
      q1+=1
      q2= input[idx][1] # gpt가 묶은 쌍 중, 두번째 질문 (q1,q2) 중 q2
      q2+=1
      q1_type= index[q1][0]
      q2_type= index[q2][0]

      # 1. 개인정보 포함된 경우 -> cross_likertXdemo 사용
      if q1_type in personal_info:
        cross_likertXdemo(index=index, data=data, targetQ_id=q2, pInfo_id=q1, folder_name=folder_name, design=design)
        read=read_likertXdemo(index=index, data=data, targetQ_id=q2, pInfo_id=q1)

        chart_reading[f"{q1},{q2}"]= read
        save2json(folder_name, chart_reading) # json파일 로컬에 저장

      elif q2_type in personal_info:
        cross_likertXdemo(index=index, data=data, targetQ_id=q1, pInfo_id=q2, folder_name=folder_name, design=design)
        read=read_likertXdemo(index=index, data=data, targetQ_id=q1, pInfo_id=q2)

        chart_reading[f"{q1},{q2}"]= read
        save2json(folder_name, chart_reading) # json파일 로컬에 저장

      # 2. 둘 다 '객관식 질문' 혹은 '평가형' 경우 -> label 길이에 따라 horizontal/vertical
      elif q1_type in valid_types and q2_type in valid_types:
        #likert2likert함수에 들어갈 category_name 생성 부분
        q2_categories_raw = index[q2][1]
        q2_parsed = ast.literal_eval(q2_categories_raw)

        if isinstance(q2_parsed, dict):
            q2_categories = list(q2_parsed.values())  # 질문 유형이 '평가형'이어서 index가 딕셔너리일 경우 value만 추출
        elif isinstance(q2_parsed, list):
            q2_categories = q2_parsed  # 질문 유형이 '객관식 질문'이어서 index가 리스트면 그대로 사용
        else:
            raise ValueError("지원하지 않는 q2_categories 형식입니다.")


        temp = cross_response_dist(index, data,  q1, q2)

        # 레이블이 길 경우 → 가로 막대 그래프
        if (np.mean([len(label) for label in data[q1].unique()]) > 4) or (np.mean([len(label) for label in data[q2].unique()]) > 4):
          cross_likertXlikert_h(temp, q2_categories,  q1, q2, folder_name, design=design)
          read=read_likertXlikert(temp,q2_categories,  q1, q2)

        else:
          cross_likertXlikert(temp, q2_categories,  q1, q2,folder_name, design=design)
          read=read_likertXlikert(temp, q2_categories,  q1, q2)

        chart_reading[f"{q1},{q2}"]= read
        
        save2json(folder_name, chart_reading)

      # 기타 타입일 경우는 필요에 따라 여기에 조건 추가 가능
      else:
        print(f"아직 정의되지 않은 질문 유형 조합입니다: {q1_type}, {q2_type}")

      idx += 1
