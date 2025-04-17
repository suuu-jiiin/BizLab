import os

# 이미지 폴더 경로
img_folder = r"C:\Users\toozi\OneDrive\바탕 화면\비즈랩\img"

# 해당 폴더 안의 .png 파일 목록을 가져와 img_path 리스트로 설정
img_path = [os.path.join(img_folder, fname) 
            for fname in sorted(os.listdir(img_folder)) 
            if fname.endswith(".png")]

# img_path가 정상적으로 잘 들어갔는지 출력해보기
print(img_path)