import pandas as pd
import matplotlib.pyplot as plt
import json
import re
import seaborn as sns
import pandas as pd
from wordcloud import WordCloud
import os

'''
<수정할 부분>
1. 이미지 저장하는 코드 중복 됨 -> 함수화하기
'''

# 현재 파일의 경로를 기준으로 상대경로 설정
base_dir = os.path.dirname(os.path.abspath(__file__))
raw_path = os.path.join(base_dir, 'data', 'survey_data.csv')

# 1. 데이터 로딩
raw_data = pd.read_csv(raw_path, encoding='utf-8-sig')

## survey 결과 csv 파일 -> json 형태로 변환
def survey_result(file):
    # 질문 내용, 질문 유형, 문항 내용 추출 (csv 파일 내에서 1~3행)
    question_texts = file.columns[1:].tolist()  # 첫 번째 열은 열의 이름이 나와있기에 제외
    question_types = file.iloc[0][1:].tolist()
    option_texts = file.iloc[1][1:].tolist()

    # 응답 데이터만 추출
    response_data = file.iloc[3:].reset_index(drop=True)

    json_data = []
    question_num=0

    for q_text_raw, q_type, opt_text in zip(question_texts, question_types, option_texts):
        # 정규표현식을 사용해 질문 번호와 질문 내용 분리
        match = re.match(r"([\d\-]+)\.\s*(.+)", q_text_raw)
        if match:
            #question_num = match.group(1)
            q_text = match.group(2)
        else:
            #question_num = ""
            q_text = q_text_raw  # 혹시 매칭 안 되면 원본 사용

        entry = {"질문 번호": question_num, "질문 내용": q_text, "질문 유형": q_type}
        question_num+=1

        # 리커트 척도(1~5) 응답 개수 집계
        if q_type == '주관식':
           entry["답변"] = response_data[q_text_raw].dropna().astype(str).tolist()
           entry["null"] = response_data[q_text_raw].isna().sum()

        elif pd.notna(opt_text) and isinstance(opt_text, str) and opt_text.startswith("[1,2,3,4,5]"):
            options = [str(x) for x in range(1, 6)]
            response_counts = {opt: 0 for opt in options}

            for response in response_data[q_text_raw].dropna():
                response_str = str(response).strip()
                if response_str in response_counts:
                    response_counts[response_str] += 1

            entry["답변"] = response_counts
            entry["null"] = response_data[q_text_raw].isna().sum()

        # 일반 객관식 질문 응답 개수 집계
        elif pd.notna(opt_text) and isinstance(opt_text, str) and opt_text.startswith("["):
            # 정규 표현식을 사용하여 따옴표 안의 옵션 값 추출
            option_list = re.findall(r"'(.*?)'", opt_text)
            response_counts = {opt: 0 for opt in option_list}

            for response in response_data[q_text_raw].dropna():
                response_str = str(response).strip()
                if response_str in response_counts:
                    response_counts[response_str] += 1

            entry["답변"] = response_counts
            entry["null"] = response_data[q_text_raw].isna().sum()

        json_data.append(entry)

    return json_data

result_json = survey_result(raw_data)

# json 파일 로컬에 저장
base_dir = os.path.dirname(os.path.abspath(__file__))
local = os.path.join(base_dir, 'data')
with open(local + "\\survey_result.json", "w", encoding="utf-8-sig") as f:
    json.dump(result_json, f, ensure_ascii=False, indent=4, default=str)
    
# 2. 간소화
## 1) 원본 CSV 데이터 컬럼명을 질문 번호 형식(예: '1.1', '2.3')으로 간소화
def simplify_data(survey_data):
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

# 3. 차트
## 1) bar chart
def bar_plot(json_results, question_id, file_name, design=None):
    resp_cat=json_results[question_id]['답변'].keys() #response category
    resp_cnt=json_results[question_id]['답변'].values() #response count
    title=json_results[question_id]['질문 내용']

    colors = sns.color_palette('ocean',len(resp_cat)) ## 색상 지정

    fig,ax=plt.subplots(figsize=(8, 6))
    bar_container=ax.bar(resp_cat, resp_cnt, color=colors) #'#457B9D' # '#E76F51'
    ax.set(title=title, ylim=(0,max(resp_cnt)+5))
    if len(title)>=30:
      fontsize='12'
    else:
      fontsize='14'
    ax.set_title(f'<질문{question_id+1}. {title}>', fontdict= {'fontsize': fontsize, \
                                                 'fontweight': 'bold',\
                                                  'color': 'black'}) # fontweight='bold', fontstyle='normal', )

    ax.bar_label(bar_container,fmt='{:,.0f}')
    
    fig.tight_layout()
    
    # 이미지 저장    
    base_dir = os.path.dirname(os.path.abspath(__file__))  # 현재 스크립트 위치
    folder_path = os.path.join(base_dir, 'img', f'{file_name}')  # 상대경로 설정
    
    if not os.path.exists(folder_path):
        os.makedirs(folder_path)
        
    fig.savefig(f'{folder_path}\\{file_name}_{question_id:02d}.png')
  

## 2) bar horizontal chart
def barh_plot(json_results, question_id, file_name, design=None):
    resp_cat=json_results[question_id]['답변'].keys() #response category
    resp_cnt=json_results[question_id]['답변'].values() #response count
    title=json_results[question_id]['질문 내용']
    colors = sns.color_palette('ocean',len(resp_cat)) ## 색상 지정
    # https://matplotlib.org/3.1.1/gallery/color/colormap_reference.html  -> 팔레트 종류 선택 가능
    fig,ax=plt.subplots(figsize=(8, 6))
    #fig.set_size_inches(8, 6)
    bar_container=ax.barh(resp_cat, resp_cnt, color=colors)
    ax.set(title=title)
    if len(title)>=30:
      fontsize='12'
    else:
      fontsize='14'
    ax.set_title(f'<질문{question_id+1}. {title}>', fontdict= {'fontsize': fontsize, \
                                                 'fontweight': 'bold',\
                                                  'color': 'black'}) # fontweight='bold', fontstyle='normal', )
    ax.bar_label(bar_container,fmt='{:,.0f}')
    
    fig.tight_layout()
    
    # 이미지 저장
    base_dir = os.path.dirname(os.path.abspath(__file__))  # 현재 스크립트 위치
    folder_path = os.path.join(base_dir, 'img', f'{file_name}')  # 상대경로 설정
    
    if not os.path.exists(folder_path):
        os.makedirs(folder_path)
        
    fig.savefig(f'{folder_path}\\{file_name}_{question_id:02d}.png')
  
## 3) pie chart
def pie_plot(json_results, question_id,  file_name, design=None):
    resp_cat=json_results[question_id]['답변'].keys() #response category
    resp_cnt=json_results[question_id]['답변'].values() #response count
    title=json_results[question_id]['질문 내용']
    
    if design==None:
        pass
      
    colors = sns.color_palette('ocean',len(resp_cat)) ## 색상 지정
    # https://matplotlib.org/3.1.1/gallery/color/colormap_reference.html  -> 팔레트 종류 선택 가능

    #explode = (0, 0, 0, 0, 0.1)  # only "explode" the 2nd slice
    explode = [0.1 if i == len(resp_cat)-1  else 0 for i in range(len(resp_cat))]
    fig, ax = plt.subplots(figsize=(8, 6))
    ax.pie(resp_cnt, labels=resp_cat, explode=explode, autopct='%1.1f%%', shadow=True, startangle=90, colors=colors)
    #ax.pie(resp_cnt, labels=label, autopct='%1.1f%%', pctdistance=1.25, labeldistance=.6, shadow=True, startangle=90)
    if len(title)>=30:
      fontsize='12'
    else:
      fontsize='14'
    ax.set_title(f'<질문{question_id+1}. {title}>', fontdict= {'fontsize': fontsize, \
                                                 'fontweight': 'bold',\
                                                  'color': 'black'}) # fontweight='bold', fontstyle='normal', )
    ax.legend()
    
    fig.tight_layout()
    
    # 이미지 저장
    base_dir = os.path.dirname(os.path.abspath(__file__))  # 현재 스크립트 위치
    folder_path = os.path.join(base_dir, 'img', f'{file_name}')  # 상대경로 설정
    
    if not os.path.exists(folder_path):
        os.makedirs(folder_path)
        
    fig.savefig(f'{folder_path}\\{file_name}_{question_id:02d}.png')


## 4) wordcloud
def wordcloud_plot(json_results, question_id, file_name, design=None):
    font_path=  r'C:\Windows\Fonts\malgun.ttf'
    cloud = WordCloud(width=800, height=600, collocations=False, background_color = 'white',font_path=font_path).generate(" ".join(json_results[question_id]['답변']))
    plt.figure(figsize=(8, 6))
    plt.imshow(cloud)
    title=json_results[question_id]['질문 내용']
    if len(title)>=30:
      fontsize=12
    else:
      fontsize=14
    plt.title(f'<질문{question_id+1}. {title}>',ha='center', size=fontsize, weight='bold')
    plt.axis('off')
    plt.savefig(f'{file_name}_{question_id:02d}.png')
    
    plt.tight_layout()
    
    # 이미지 저장
    base_dir = os.path.dirname(os.path.abspath(__file__))  # 현재 스크립트 위치
    folder_path = os.path.join(base_dir, 'img', f'{file_name}')  # 상대경로 설정
    
    if not os.path.exists(folder_path):
        os.makedirs(folder_path)
        
    plt.savefig(f'{folder_path}\\{file_name}_{question_id:02d}.png')



