import matplotlib.pyplot as plt
import matplotlib.font_manager as fm
import platform

def set_korean_font():
    """
    시스템에 맞는 한글 폰트를 matplotlib에 설정하는 함수
    """
    if platform.system() == 'Windows':
        font_path = 'C:/Windows/Fonts/malgun.ttf'  # 맑은 고딕
    elif platform.system() == 'Darwin':  # macOS
        font_path = '/System/Library/Fonts/AppleGothic.ttf'
    else:  # Linux (예: 나눔고딕)
        font_path = '/usr/share/fonts/truetype/nanum/NanumGothic.ttf'

    try:
        font_name = fm.FontProperties(fname=font_path).get_name()
        plt.rc('font', family=font_name)
        plt.rcParams['axes.unicode_minus'] = False
    except Exception as e:
        print(f"[!] 한글 폰트 설정 실패: {e}")
