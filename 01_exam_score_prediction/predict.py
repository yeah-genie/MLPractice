"""
🔮 predict.py - 새로운 학생의 시험 점수 예측

사용법:
1. 먼저 train.py를 실행해서 model.pkl을 생성하세요
2. 그 다음 이 스크립트를 실행하면 예측 결과를 볼 수 있습니다

실행: python predict.py
"""

import pandas as pd
import joblib

print("🔮 시험 점수 예측기\n")

# ============================================
# 1️⃣ 학습된 모델 로드
# ============================================
print("📂 모델 로드 중...")

try:
    model = joblib.load('model.pkl')
    encoders = joblib.load('encoders.pkl')
    print("   - model.pkl 로드 완료!")
    print("   - encoders.pkl 로드 완료!")
except FileNotFoundError:
    print("❌ 오류: model.pkl 파일이 없습니다!")
    print("   먼저 'python train.py'를 실행해주세요.")
    exit(1)

print()

# ============================================
# 2️⃣ 예측할 학생 데이터 정의
# ============================================
# 아래 값을 수정해서 다양한 학생을 예측해보세요!

print("👤 예측할 학생 데이터:")
print("-" * 40)

# 예시 학생 3명
students = [
    {
        "name": "학생A (열심히 공부)",
        "age": 20,
        "gender": "female",
        "course": "b.tech",
        "study_hours": 6.0,        # 하루 공부 시간
        "class_attendance": 90.0,  # 출석률 (%)
        "internet_access": "yes",
        "sleep_hours": 7.5,        # 수면 시간
        "sleep_quality": "good",
        "study_method": "mixed",   # 공부 방법
        "facility_rating": "high", # 시설 평가
        "exam_difficulty": "moderate"
    },
    {
        "name": "학생B (보통)",
        "age": 21,
        "gender": "male",
        "course": "bca",
        "study_hours": 3.0,
        "class_attendance": 70.0,
        "internet_access": "yes",
        "sleep_hours": 6.0,
        "sleep_quality": "average",
        "study_method": "online videos",
        "facility_rating": "medium",
        "exam_difficulty": "moderate"
    },
    {
        "name": "학생C (불성실)",
        "age": 19,
        "gender": "other",
        "course": "diploma",
        "study_hours": 1.0,
        "class_attendance": 50.0,
        "internet_access": "no",
        "sleep_hours": 4.0,
        "sleep_quality": "poor",
        "study_method": "self-study",
        "facility_rating": "low",
        "exam_difficulty": "hard"
    }
]

# ============================================
# 3️⃣ 각 학생 예측
# ============================================
print("📊 예측 결과:")
print("=" * 50)

for student in students:
    name = student.pop("name")
    
    # DataFrame으로 변환
    df = pd.DataFrame([student])
    
    # 범주형 변수 인코딩 (문자 → 숫자)
    for col, encoder in encoders.items():
        if col in df.columns:
            df[col] = encoder.transform(df[col])
    
    # 예측
    predicted_score = model.predict(df)[0]
    
    # 결과 출력
    print(f"\n🎓 {name}")
    print(f"   공부 시간: {student['study_hours']}시간")
    print(f"   출석률: {student['class_attendance']}%")
    print(f"   수면 시간: {student['sleep_hours']}시간")
    print(f"   ─────────────────────")
    print(f"   📈 예측 점수: {predicted_score:.1f}점")
    
    # 등급 표시
    if predicted_score >= 90:
        grade = "A+ (우수)"
    elif predicted_score >= 80:
        grade = "A (좋음)"
    elif predicted_score >= 70:
        grade = "B (양호)"
    elif predicted_score >= 60:
        grade = "C (보통)"
    elif predicted_score >= 50:
        grade = "D (노력 필요)"
    else:
        grade = "F (위험)"
    
    print(f"   📋 예상 등급: {grade}")

print("\n" + "=" * 50)
print("💡 Tip: students 리스트를 수정해서 다른 학생도 예측해보세요!")
