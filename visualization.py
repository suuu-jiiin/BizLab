import os
import textwrap
import numpy as np
import pandas as pd
import seaborn as sns
import matplotlib.pyplot as plt
from wordcloud import WordCloud
from konlpy.tag import Okt


# 0. 단일 질문 시각화 이미지 저장 함수
def saveimg(folder_name, fig, question_id): 
    base_dir = os.path.dirname(os.path.abspath(__file__))  # 현재 스크립트 위치
    folder_path = os.path.join(base_dir, 'img', f'{folder_name}')  # 상대경로 설정
    
    if not os.path.exists(folder_path):
        os.makedirs(folder_path)
        
    fig.savefig(f'{folder_path}\\{folder_name}_{question_id:02d}.png')

# 1. bar chart
def bar_plot(json_results, question_id, folder_name, design='Pastel1'):
    resp_cat = list(json_results[question_id]['답변'].keys()) #response category
    resp_cnt = list(json_results[question_id]['답변'].values()) #response count
    title=json_results[question_id]['질문 내용']

    colors = sns.color_palette(design,len(resp_cat)) ## 색상 지정

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
    
    percentages = [f'{(count / sum(resp_cnt) * 100):.1f}%' for count in resp_cnt]
    ax.bar_label(bar_container, labels=percentages)
        
    fig.tight_layout()
    
    saveimg(folder_name, fig, question_id)
    
    plt.close(fig)
  

#2. bar horizontal chart
def barh_plot(json_results, question_id, folder_name, design='Pastel1'):
    resp_cat=list(json_results[question_id]['답변'].keys()) # response category
    resp_cnt=list(json_results[question_id]['답변'].values()) # response count
    
    title=json_results[question_id]['질문 내용']
    colors = sns.color_palette(design,len(resp_cat)) ## 색상 지정

    fig,ax=plt.subplots(figsize=(8, 6))

    bar_container=ax.barh(resp_cat, resp_cnt, color=colors)
    ax.set(title=title)
    if len(title)>=30:
      fontsize='12'
    else:
      fontsize='14'
    ax.set_title(f'<질문{question_id+1}. {title}>', fontdict= {'fontsize': fontsize, \
                                                 'fontweight': 'bold',\
                                                  'color': 'black'}) # fontweight='bold', fontstyle='normal', )

    #bar_label for percentage
    percentages = [f'{(count / sum(resp_cnt) * 100):.1f}%' for count in resp_cnt]
    ax.bar_label(bar_container, labels=percentages)
    
    fig.tight_layout()
    
    saveimg(folder_name, fig, question_id)
    
    plt.close(fig)
  
# 3. Grid bar chart
def grid_plot(json_results, question_id, folder_name, design='Pastel1'):

    # 데이터 추출
    answer_dict = json_results[question_id]['답변']  # dict of dict
    title = json_results[question_id]['질문 내용']

    # dict -> DataFrame
    df = pd.DataFrame(answer_dict).T.fillna(0)  # <-- TRANSPOSE으로 그리드의 row, column을 각각 x값, 범례로 설정
    columns = df.columns.tolist()  # 그리드의 행
    x_labels = df.index.tolist()   # 그리드의 열

    # 색상 팔레트
    cmap = plt.get_cmap(design)
    colors = [cmap(i) for i in range(len(columns))]
    #colors = sns.color_palette(design, len(columns))

    # 시각화
    fig, ax = plt.subplots(figsize=(10, 6))
    bar_width = 0.8 / len(columns)
    x = np.arange(len(x_labels))
    total_sum = df.values.sum()

    for i, col in enumerate(columns):
        values = df[col].values
        bars = ax.bar(x + i * bar_width, values, width=bar_width, label=col, color=colors[i])

        for j, bar in enumerate(bars):
            count = values[j]
            percent = (count / total_sum) * 100 if total_sum > 0 else 0
            ax.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 0.2,
                    f'{percent:.1f}%',
                    ha='center', va='bottom', fontsize=9)

    # 제목 및 축
    wrapped_title = "\n".join(textwrap.wrap(title, width=40))
    ax.set_title(f'<질문{question_id+1}. {wrapped_title}>', fontsize=14, fontweight='bold', color='black')
    ax.set_xticks(x + bar_width * (len(columns)-1) / 2)
    ax.set_xticklabels(x_labels)
    ax.set_ylabel('응답 수')
    ax.set_ylim(0, df.values.max() + 3)

    # 범례
    ax.legend(title='시간대', bbox_to_anchor=(1.05, 1), loc='upper left')

    fig.tight_layout()
    
    # 이미지 저장
    saveimg(folder_name, fig, question_id)
    
    plt.close(fig)

# 4. pie chart
def pie_plot(json_results, question_id,  folder_name,  design='Pastel1'):
    resp_cat=list(json_results[question_id]['답변'].keys()) #response category
    resp_cnt=list(json_results[question_id]['답변'].values()) #response count
    title=json_results[question_id]['질문 내용']

    colors = sns.color_palette(design,len(resp_cat)) ## 색상 지정

    explode = [0.1 if i == len(resp_cat)-1  else 0 for i in range(len(resp_cat))]
    fig, ax = plt.subplots(figsize=(8, 6))
    ax.pie(resp_cnt, labels=resp_cat, explode=explode, autopct='%1.1f%%', shadow=True, startangle=90, colors=colors)

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
    saveimg(folder_name, fig, question_id)
    
    plt.close(fig)


# 4. wordcloud
def merge_compound_words(sentence, compound_words):
    for word in compound_words:
        if word in sentence:
            sentence = sentence.replace(word, f' {word} ')  # 합성어를 분리하여 처리
    return sentence.strip()
  
def extract_nouns_and_verbs_and_remove_stopwords(okt, sentence, stopwords):
    # 형태소 분석 후 명사와 동사 추출
    nouns_and_verbs = okt.pos(sentence)  # 형태소 분석 후 품사 정보 포함
    # 명사와 동사만 필터링, 불용어 제거
    return [word for word, tag in nouns_and_verbs if (tag in ['Noun', 'Verb']) and word not in stopwords]
  
def StopWordsRemoval(short_answers):
  # 불용어 리스트 (필요에 따라 수정)
  stop_words = ['은', '는', '이', '가', '을', '를', '의', '과', '와', '에게', '에서', '도', '으로', '로', '뿐', '수', '곳', '할', '것', '이라']
  # 형태소 분석기
  okt = Okt()
  # 단답형 문자열 리스트
  sentence_list = short_answers
  # 불용어 제거 후 명사와 동사 추출한 결과
  cleaned_sentences = [extract_nouns_and_verbs_and_remove_stopwords(okt, sentence, stop_words) for sentence in sentence_list]

  flat_list = [item for sublist in cleaned_sentences for item in sublist]
  result = ' '.join(flat_list)

  # 결과 출력
  return result

def wordcloud_plot(json_results, question_id, folder_name, design='white'):
  font_path=  r'C:\Windows\Fonts\malgun.ttf'
  
  result=StopWordsRemoval(json_results[question_id]['답변'])
  cloud = WordCloud(width=800, height=600, collocations=False, background_color = design,font_path=font_path).generate(result)
  plt.figure(figsize=(8, 6))
  plt.imshow(cloud)
  title=json_results[question_id]['질문 내용']
  if len(title)>=30:
    fontsize=12
  else:
    fontsize=14
  plt.title(f'<질문{question_id+1}. {title}>',ha='center', size=fontsize, weight='bold')
  plt.axis('off')
  
  plt.tight_layout()
    
  # 이미지 저장
  saveimg(folder_name, plt, question_id)
  
  plt.close()




