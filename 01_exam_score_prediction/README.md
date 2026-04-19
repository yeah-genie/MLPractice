# Exam Score Prediction - ML Project

학생의 학습 습관, 출석률, 수면 패턴 등을 기반으로 시험 점수를 예측하는 머신러닝 모델입니다.

## 📊 Dataset
- **13 features**: age, gender, course, study_hours, class_attendance, internet_access, sleep_hours, sleep_quality, study_method, facility_rating, exam_difficulty
- **Target**: exam_score (0-100)

## 🚀 Quick Start

```bash
# 1. 필요한 라이브러리 설치
pip install -r requirements.txt

# 2. 모델 학습
python train.py

# 3. 예측 테스트
python predict.py
```

## 📁 Project Structure
```
exam-score-prediction/
├── data.csv           # 원본 데이터
├── train.py           # 모델 학습 스크립트
├── predict.py         # 예측 스크립트
├── model.pkl          # 학습된 모델 (train.py 실행 후 생성)
└── requirements.txt   # 필수 라이브러리
```

## 🧠 ML Concepts Covered
1. **Data Preprocessing** - 결측치 처리, 인코딩
2. **Feature Engineering** - 범주형 → 숫자 변환
3. **Model Training** - RandomForest, 학습/테스트 분할
4. **Evaluation** - MAE, RMSE, R² Score

## 📈 Model Performance
Train 후 `results/` 폴더에서 성능 지표 확인 가능
