import re
import pandas as pd
import matplotlib.pyplot as plt
import numpy as np
import seaborn as sns
import os

#1. Likert x Demographics (sex, age)
def cross_likertXdemo(index, data, targetQ_id, pInfo_id, file_name, design=None):
    '''
    targetQ_id: target 질문 id (Likert scale type)
    pInfo_id: 개인 정보 담은 질문 id (e.g., sex, age)
    '''
    scale_order = ['매우 그렇다', '그렇다', '보통이다', '그렇지 않다', '전혀 그렇지 않다'] # 출력되는 순서 지정
    target_labels = [label for label in scale_order if label in data[targetQ_id].unique()] # X-axis: Likert options
    pinfo_labels = sorted(data[pInfo_id].unique())  # Grouping by personal info
    pinfo_type = index[pInfo_id][0] #  sex, age, etc.

    counts = {}
    for i in range(len(pinfo_labels)):
        counts[pinfo_labels[i]] = [
            len(data[(data[targetQ_id] == target_labels[j]) & (data[pInfo_id] == pinfo_labels[i])])
            for j in range(len(target_labels))
        ]
    total = sum([sum(v) for v in counts.values()])  # 전체 응답 수
    width = 0.6
    fig, ax = plt.subplots(figsize=(10, 6))
    bottom = np.zeros(len(target_labels))

    # Set seaborn color palette
    colors = sns.color_palette('Set2', len(pinfo_labels))  # Color palette per group

    for i, sex in enumerate(counts):
        sex_count = counts[sex]
        p = ax.bar(target_labels, sex_count, width, label=sex, bottom=bottom, color=colors[i])

        percentages = [f'{(v / total * 100):.1f}%' if v > 0 else '' for v in sex_count]
        ax.bar_label(p,labels=percentages, label_type='center')
        bottom += sex_count

    ax.set_title(f'<{targetQ_id}번 질문에 대한 {pinfo_type} 분포>', fontsize=14, fontweight='bold')
    ax.set_xlabel(f"{targetQ_id}번. {index[targetQ_id][2]}",  fontstyle='italic', fontsize=12)
    ax.set_yticks([]) # y축 눈금 없애기 위함
    ax.legend(title=f"{pinfo_type}")
    
    fig.tight_layout()
    
    # 이미지 저장
    base_dir = os.path.dirname(os.path.abspath(__file__))  # 현재 스크립트 위치
    folder_path = os.path.join(base_dir, 'img', f'{file_name}_cross')  # 상대경로 설정
    
    if not os.path.exists(folder_path):
        os.makedirs(folder_path)
        
    fig.savefig(f'{folder_path}\\{file_name}_({targetQ_id}, {pInfo_id})_교차분석.png')

#2. Likert X Likert
def cross_response_dist(data, base_qnum, target_qnum):
    '''
    응답 개수 카운팅하는 함수
    
    simple_data : 원본 데이터에서 질문 내용을 간소화한 버전
    base_qnum, target_num : base_qnum에서 선택한 항목별로 target_qnum에서 어떤 선택을 했는지 집계하는 함수
    '''
    # Likert scale 순서 정의
    scale_order = ['매우 그렇다', '그렇다', '보통이다', '그렇지 않다', '전혀 그렇지 않다']

    # 결과 딕셔너리 초기화
    result = {base: [0] * len(scale_order) for base in scale_order}

    # 값 카운팅
    for base_val, target_val in zip(data[base_qnum], data[target_qnum]):
        if pd.isna(base_val) or pd.isna(target_val):
            continue
        if base_val in scale_order and target_val in scale_order:
            row = scale_order.index(base_val)
            col = scale_order.index(target_val)
            result[scale_order[row]][col] += 1

    return result

## 1) 누적 가로 막대 그래프
def cross_likertXlikert_h(results, category_names, base_qnum, target_qnum, file_name,design=None):
    labels = list(results.keys())
    data = np.array(list(results.values()))

    # 비율(%)로 변환
    data_percent = data / data.sum(axis=1, keepdims=True)

    data_cum = data_percent.cumsum(axis=1)
    category_colors = plt.colormaps['Set2'](np.linspace(0.15, 0.85, data.shape[1]))

    fig, ax = plt.subplots(figsize=(10, 5))
    ax.invert_yaxis()
    ax.set_xlim(0, 1)  # 100% 범위

    for i, (colname, color) in enumerate(zip(category_names, category_colors)):
        widths = data_percent[:, i]
        starts = data_cum[:, i] - widths
        rects = ax.barh(labels, widths, left=starts, height=0.5,
                        label=colname, color=color)

        r, g, b, _ = color
        text_color = 'black'

        for rect, width in zip(rects, widths):
            if width > 0.01:  # 1% 이상일 때만 표시
                ax.text(rect.get_x() + rect.get_width() / 2,
                        rect.get_y() + rect.get_height() / 2,
                        f'{width*100:.0f}%',  # 퍼센트로 표기
                        ha='center', va='center', color=text_color, fontsize=10)

    ax.set_xticks(np.linspace(0, 1, 11))
    ax.set_xticklabels([f'{int(x*100)}%' for x in np.linspace(0, 1, 11)])

    ax.legend(title=f"{target_qnum}번 질문", ncols=1, bbox_to_anchor=(1.05, 0.5), loc='center left', fontsize='medium')
    ax.set_ylabel(f"{base_qnum}번 질문", fontsize=12)
    ax.set_xlabel(f"{base_qnum}번 질문에 대한 {target_qnum}번 질문 응답 비율 (%)", fontsize=12)
    ax.set_title(f"<{base_qnum}번 질문과 {target_qnum}번 질문 비교>", fontsize=14, fontweight='bold')

    fig.tight_layout()
    
    # 이미지 저장
    base_dir = os.path.dirname(os.path.abspath(__file__))  # 현재 스크립트 위치
    folder_path = os.path.join(base_dir, 'img', f'{file_name}_cross')  # 상대경로 설정
    
    if not os.path.exists(folder_path):
        os.makedirs(folder_path)
        
    fig.savefig(f'{folder_path}\\{file_name}_({base_qnum}, {target_qnum})_교차분석.png')


## 2) 누적 세로 막대 그래프
def cross_likertXlikert(results, category_names, base_qnum, target_qnum, index, file_name, design=None):
    labels = list(results.keys())
    data = np.array(list(results.values()))

    # 각 항목별 총합으로 비율(%) 계산
    data_percent = data / data.sum(axis=1, keepdims=True)
    data_cum = data_percent.cumsum(axis=1)
    category_colors = plt.colormaps['Set2'](np.linspace(0.15, 0.85, data.shape[1]))

    fig, ax = plt.subplots(figsize=(9, 5))

    # 세로 누적 막대 그래프
    for i, (colname, color) in enumerate(zip(category_names, category_colors)):
        heights = data_percent[:, i]
        starts = data_cum[:, i] - heights

        rects = ax.bar(
            labels, heights, bottom=starts,
            label=colname, color=color, width=0.6
        )

        text_color = 'black'
        for rect, height in zip(rects, heights):
            if height > 0.01:  # 1% 이상일 때만 표시
                ax.text(rect.get_x() + rect.get_width() / 2,
                        rect.get_y() + rect.get_height() / 2,
                        f'{height*100:.0f}%',
                        ha='center', va='center', color=text_color, fontsize=10)

    ax.set_ylabel(f"{base_qnum}번 문항에 대한 {target_qnum}번 질문 응답 비율 (%)", fontsize=12)
    #ax.set_ylabel(f"{target_qnum}번. {index[target_qnum][2]})", fontsize=12)
    ax.set_xlabel(f"{base_qnum}번. {index[base_qnum][2]}\n{target_qnum}번. {index[target_qnum][2]}")
    ax.set_ylim(0, 1)  # y축 100% 고정
    ax.set_yticks(np.linspace(0, 1, 11))
    ax.set_yticklabels([f"{int(y*100)}%" for y in np.linspace(0, 1, 11)])

    ax.set_xticks(np.arange(len(labels)))
    ax.set_xticklabels(labels)

    ax.set_title(f"<{base_qnum}번 질문과 {target_qnum}번 질문 비교>", fontsize=14, fontweight='bold')
    ax.legend(title=f"{target_qnum}번 질문", ncols=1, bbox_to_anchor=(1.05, 0.5), loc='center left', fontsize='medium')

    fig.tight_layout()

    # 이미지 저장
    base_dir = os.path.dirname(os.path.abspath(__file__))  # 현재 스크립트 위치
    folder_path = os.path.join(base_dir, 'img', f'{file_name}_cross')  # 상대경로 설정
    
    if not os.path.exists(folder_path):
        os.makedirs(folder_path)
        
    fig.savefig(f'{folder_path}\\{file_name}_({base_qnum}, {target_qnum})_교차분석.png')
    
# 2. 교차 분석 결과 정리
## 1) Likert X 개인 정보
def read_likertXdemo(index, data, targetQ_id, pInfo_id):
    target_labels = sorted(data[targetQ_id].unique())  # likert 값들
    pinfo_labels = sorted(data[pInfo_id].unique())     # 성별, 나이 등

    interpretation_json = {}

    for pinfo in pinfo_labels:
        filtered = data[data[pInfo_id] == pinfo]
        total = len(filtered)
        if total == 0:
            continue
        inner_dict = {}
        for target in target_labels:
            count = len(filtered[filtered[targetQ_id] == target])
            percent = round(count / total * 100, 2)
            inner_dict[f"{target}을 선택한 비율"] = percent
        interpretation_json[f"{pinfo} 중"] = inner_dict

    return interpretation_json

## 2) Likert X Likert
def read_likertXlikert(results, category_names, base_qnum, target_qnum):
    interpretation_json = {}

    for base_val, counts in results.items():
        total = sum(counts)
        if total == 0:
            continue  # 응답자가 없는 경우 생략
        key = f"{base_qnum}번 문항에서 '{base_val}'을(를) 선택한 사람 중:"
        value = {}
        for i, count in enumerate(counts):
            percent = round(count / total * 100, 2)
            value[f"{target_qnum}번 질문에서 '{category_names[i]}'을(를) 선택한 비율"] = percent
        interpretation_json[key] = value

    return interpretation_json
