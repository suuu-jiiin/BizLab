import re
import os 
import ast
import json
import pandas as pd

# 1. 질문 유형이 '평가형'인 경우에 숫자와 의미 매칭하는 함수
def likert_mapping(data):
  for col in data.columns:
      # 해당 질문에 대한 option_text(숫자와 의미 매칭된 거) 가져오기
      option_text = data.loc[1, col]  # 2번째 행 (index=1)이 option_text임
      try:
          mapping = json.loads(option_text)
          data[col] = data[col].replace(mapping)
      except Exception as e:
          pass
      
# 2. survey data 해석
## survey 결과 csv 파일 -> json 형태로 변환
def survey_result(file, folder_name, json_name):
    likert_mapping(file)
    
    # 질문 내용, 질문 유형, 문항 내용 추출 (csv 파일 내에서 1~3행)
    question_texts = file.columns[1:].tolist()  # 첫 번째 열은 열의 이름이 나와있기에 제외
    question_types = file.iloc[0][1:].tolist()
    option_texts = file.iloc[1][1:].tolist()

    # 응답 데이터만 추출
    resp_data = file.iloc[2:].reset_index(drop=True)

    json_data = []
    question_num=0

     # '객관식 질문', '평가형', '그리드 형' 질문 유형만 보기 별로 답변 개수 카운팅
    for q_text_raw, q_type, opt_text in zip(question_texts, question_types, option_texts):
        # 정규표현식을 사용해 질문 번호와 질문 내용 분리
        match = re.match(r"(?:Q)?([\d\-]+)\.\s*(.+)", q_text_raw)
        if match:
            q_text = match.group(2)
        else:
            q_text = q_text_raw  # 혹시 매칭 안 되면 원본 사용

        entry = {"질문 번호": question_num, "질문 내용": q_text, "질문 유형": q_type}
        question_num+=1

        # 질문 유형이 '단답형', '장문형'인 경우에 json 파일에 '답변'과 'null'값만 저장 
        if q_type == '단답형' or q_type == '장문형':
           entry["답변"] = resp_data[q_text_raw].dropna().astype(str).tolist()
           entry["null"] = resp_data[q_text_raw].isna().sum()

        # 질문 유형이 '객관식 질문', '성별'인 경우
        elif q_type == '객관식 질문' or q_type == '성별':
            if pd.isna(opt_text):  # opt_text가 결측값이면 건너뛰기 또는 빈 리스트 처리
               option_list = []
            else:
               option_list = ast.literal_eval(opt_text)
               option_list = [str(opt).strip() for opt in option_list]
            resp_cnt = {opt: 0 for opt in option_list}
            resp_cnt["기타"] = 0  # 응답자가 '기타'로 보기에 없는 응답한 경우 "기타" 항목 추가해서 카운팅 
            
            for resp in resp_data[q_text_raw].dropna():
              try:
                  parsed = ast.literal_eval(resp)
                  # 중복 응답으로 인한 리스트형 응답을 고려하기 위해서 모든 응답을 리스트형으로 통일
                  if isinstance(parsed, list):
                      items = parsed
                  else:
                      items = [parsed]
              except:
                  resp_str = str(resp).strip()
                  # 쉼표가 보기에 포함되어 있으면 split하지 않고 그대로 처리 (보기 자체가 쉼표로 표현된 경우 ex.'1시간 이상, 2시간 미만')
                  if any(',' in opt for opt in option_list):
                      items = [resp_str]
                  else:
                      items = resp_str.split(',')
                      
              # 모든 리스트의 원소 값 하나하나 다 카운팅  
              for item in items:
                  item = str(item).strip()
                  if item in resp_cnt:
                      resp_cnt[item] +=1
                  else:
                      resp_cnt["기타"] += 1 # option_list에 없는 항목은 '기타'로 처리
            
            # "기타" 응답이 없을 경우 삭제
            if resp_cnt["기타"] == 0: 
                del resp_cnt["기타"]
            
            entry["답변"] = resp_cnt
            entry["null"] = resp_data[q_text_raw].isna().sum()

        # 질문 유형이 '평가형'인 경우
        elif q_type == '평가형':
            if pd.isna(opt_text):
                entry["답변"] = "보기 없음"
                entry["null"] = resp_data[q_text_raw].isna().sum()
            else:
                try:
                    # opt_text 파싱 (JSON 또는 Python literal)
                    try:
                        parsed_opts = json.loads(opt_text)
                    except json.JSONDecodeError:
                        parsed_opts = ast.literal_eval(opt_text)

                    # parsed_opts가 dict인 경우 (value 목록 사용)
                    if isinstance(parsed_opts, dict):
                        value_labels = list(parsed_opts.values())
                    elif isinstance(parsed_opts, list):
                        value_labels = parsed_opts
                    else:
                        raise ValueError("지원하지 않는 형식입니다.")

                    value_labels = [str(v).strip() for v in value_labels]

                    resp_cnt = {label: 0 for label in value_labels}

                    for resp in resp_data[q_text_raw].dropna():
                        resp_str = str(resp).strip()
                        if resp_str in resp_cnt:
                            resp_cnt[resp_str] += 1

                    entry["답변"] = resp_cnt
                    entry["null"] = resp_data[q_text_raw].isna().sum()

                except Exception as e:
                    entry["답변"] = f"오류 발생: {e}"
                    entry["null"] = resp_data[q_text_raw].isna().sum()
        
        # 질문 유형이 '파일 업로드'인 경우    
        elif q_type == '파일 업로드':
          try:
              resp_cnt = {"파일 제출": 0, "파일 미제출": 0}

              for resp in resp_data[q_text_raw]:
                  if pd.notna(resp) and str(resp).strip() != "":
                      resp_cnt["파일 제출"] += 1
                  else:
                      resp_cnt["파일 미제출"] += 1

              entry["답변"] = resp_cnt
              entry["null"] = resp_data[q_text_raw].isna().sum()

          except Exception as e:
              entry["답변"] = f"오류 발생: {e}"
              entry["null"] = resp_data[q_text_raw].isna().sum()

        elif q_type == '그리드 형':
          try:
              # opt_text는 column 값 리스트 (re로 파싱)
              column_options = re.findall(r"'(.*?)'", opt_text)

              row_counts = {}
              row_nulls = {}

              for resp in resp_data[q_text_raw].dropna():
                  try:
                      resp_dict = json.loads(resp)

                      for row_label in resp_dict:
                          col_val = resp_dict[row_label]

                          # row_counts 초기화
                          if row_label not in row_counts:
                              row_counts[row_label] = {opt: 0 for opt in column_options}
                          if row_label not in row_nulls:
                              row_nulls[row_label] = 0

                          # 응답 값이 비어있지 않으면 카운트
                          if col_val and col_val in row_counts[row_label]:
                              row_counts[row_label][col_val] += 1
                          else:
                              row_nulls[row_label] += 1  # 해당 row 항목 null 처리

                  except Exception as e:
                      print(f"응답 파싱 오류: {resp} -> {e}")

              entry["답변"] = row_counts
              entry["null"] = row_nulls  # row별 null 카운트로 변경

          except Exception as e:
              entry["답변"] = f"오류 발생: {e}"
              entry["null"] = {}

        json_data.append(entry)

    # json 파일 로컬에 저장
    base_dir = os.path.dirname(os.path.abspath(__file__))
    local = os.path.join(base_dir, 'data', f'{folder_name}')
    json_path = os.path.join(local, f'{json_name}')
    with open(json_path, "w", encoding="utf-8-sig") as f:
        json.dump(json_data, f, ensure_ascii=False, indent=4, default=str)

# 3. 간소화
## 1) 원본 CSV 데이터 컬럼명을 질문 번호 형식(예: '1.1', '2.3')으로 간소화
def simplify_data(survey_data):
    likert_mapping(survey_data)
    
    new_columns=[i for i in range(len(survey_data.columns))]
    
    # 새로운 컬럼명을 대입한 DataFrame 반환
    survey_data.columns = new_columns
    return survey_data

## 2) JSON 파일 간소화
'''
타이틀: 질문 -> 번호화({“서비스에 만족합니까?”:1}) => 이건 질문 번호로 대체 가능
레이블 -> 번호화 ({“매우 만족”:5, “만족”:4, })
'''

def simplify_answers(json_data):
    question_option_mapping = {}  # 문항 번호 대응표 저장할 딕셔너리

    for entry in json_data:
        if "답변" in entry:
            original_answers = entry["답변"]

            # '주관식' 또는 리스트형 답변일 경우 간소화 스킵
            if isinstance(original_answers, list):
                continue

            keys = list(original_answers.keys())

            # 이미 간소화된 경우는 skip
            if all(k.strip().isdigit() for k in keys):
                continue

            # 매핑 생성 및 답변 간소화
            new_answers = {}
            mapping = {}
            for i, option_text in enumerate(keys, start=1):
                new_key = str(i)
                new_answers[new_key] = original_answers[option_text]
                mapping[new_key] = option_text

            entry["답변"] = new_answers

            # 문항 번호에 대응표 저장
            question_num = entry.get("질문 번호", f"Q{len(question_option_mapping)+1}")
            question_option_mapping[question_num] = mapping

    return json_data, question_option_mapping