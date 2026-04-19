"""
🎯 train.py - 학생 시험 점수 예측 모델 학습

이 스크립트는 ML의 전체 흐름을 배울 수 있도록 각 단계마다
상세한 한국어 주석을 포함하고 있습니다.

실행: python train.py
"""

# ============================================
# 1️⃣ 라이브러리 임포트
# ============================================
# pandas: 데이터프레임 (엑셀 같은 표 형식 데이터) 처리
# numpy: 수학 연산 (배열, 행렬)
# sklearn: 머신러닝 라이브러리 (Scikit-Learn)

import pandas as pd
import numpy as np
from sklearn.model_selection import train_test_split  # 데이터 분할
from sklearn.preprocessing import LabelEncoder        # 문자 → 숫자 변환
from sklearn.ensemble import RandomForestRegressor    # 랜덤포레스트 (예측 모델)
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
import joblib  # 모델 저장
import os

print("🚀 시험 점수 예측 모델 학습 시작!\n")

# ============================================
# 2️⃣ 데이터 로드
# ============================================
# CSV 파일을 pandas DataFrame으로 읽어옵니다.
# DataFrame은 엑셀 시트처럼 행(row)과 열(column)로 구성됩니다.

print("📊 Step 1: 데이터 로드")
df = pd.read_csv('data.csv')

print(f"   - 총 데이터 수: {len(df):,}행")
print(f"   - 컬럼 수: {len(df.columns)}개")
print(f"   - 컬럼 목록: {list(df.columns)}")
print()

# 데이터 미리보기 (첫 5행)
print("   - 데이터 미리보기:")
print(df.head())
print()

# ============================================
# 3️⃣ 데이터 전처리 (Preprocessing)
# ============================================
# 머신러닝 모델은 "숫자"만 이해할 수 있습니다.
# 따라서 문자(categorical) 데이터를 숫자로 변환해야 합니다.
# 예: male → 0, female → 1, other → 2

print("🔧 Step 2: 데이터 전처리")

# student_id는 예측에 불필요하므로 제거
df = df.drop('student_id', axis=1)
print("   - student_id 컬럼 제거 (예측에 불필요)")

# 범주형(categorical) 컬럼 식별
# 숫자가 아닌 모든 컬럼을 찾습니다
categorical_columns = df.select_dtypes(include=['object']).columns.tolist()
print(f"   - 범주형 컬럼 (문자 데이터): {categorical_columns}")

# LabelEncoder를 사용해 각 범주형 컬럼을 숫자로 변환
# 예: gender 컬럼의 'male'은 0, 'female'은 1, 'other'는 2가 됩니다
encoders = {}
for col in categorical_columns:
    le = LabelEncoder()
    df[col] = le.fit_transform(df[col])
    encoders[col] = le
    print(f"   - {col}: {list(le.classes_)} → {list(range(len(le.classes_)))}")

print()

# ============================================
# 4️⃣ Feature와 Target 분리
# ============================================
# Feature (X): 예측에 사용할 입력 데이터 (공부 시간, 출석률 등)
# Target (y): 예측하려는 값 (시험 점수)
#
# 비유: X는 "문제", y는 "정답"
# 모델은 X를 보고 y를 맞추는 법을 배웁니다.

print("📌 Step 3: Feature와 Target 분리")

X = df.drop('exam_score', axis=1)  # exam_score를 제외한 모든 컬럼
y = df['exam_score']               # exam_score만

print(f"   - Feature (X) shape: {X.shape}")  # (행 수, 컬럼 수)
print(f"   - Target (y) shape: {y.shape}")
print(f"   - Feature 컬럼: {list(X.columns)}")
print()

# ============================================
# 5️⃣ Train/Test 분할
# ============================================
# 왜 분할하나요?
# - 모델이 "암기"가 아닌 "일반화"를 잘하는지 확인하기 위해
# - Train 셋으로 학습하고, Test 셋으로 성능을 평가합니다
# - 보통 80% 학습, 20% 테스트로 나눕니다
#
# 비유: 수학 문제집의 80%를 풀면서 공부하고,
#       나머지 20%의 새로운 문제로 실력을 테스트

print("✂️ Step 4: Train/Test 분할 (80:20)")

X_train, X_test, y_train, y_test = train_test_split(
    X, y, 
    test_size=0.2,   # 20%를 테스트용으로
    random_state=42  # 재현성을 위한 고정 시드 (같은 결과를 보장)
)

print(f"   - Train 셋: {len(X_train)}개")
print(f"   - Test 셋: {len(X_test)}개")
print()

# ============================================
# 6️⃣ 모델 학습 (Training)
# ============================================
# RandomForestRegressor를 사용합니다.
#
# 🌲 Random Forest란?
# - 여러 개의 Decision Tree(결정 트리)를 만들어서
# - 각 트리의 예측을 평균내는 앙상블 기법
# - 장점: 과적합에 강하고, 성능이 좋음
# - 단점: 학습 시간이 조금 더 걸림
#
# n_estimators: 사용할 트리의 개수 (100 = 100개의 트리)
# random_state: 재현성을 위한 고정 시드

print("🌲 Step 5: Random Forest 모델 학습")

model = RandomForestRegressor(
    n_estimators=100,    # 트리 100개 사용
    max_depth=10,        # 트리 최대 깊이 (과적합 방지)
    random_state=42,
    n_jobs=-1            # 모든 CPU 코어 사용 (빠른 학습)
)

# fit() = 학습! 모델이 X_train을 보고 y_train을 맞추는 패턴을 배웁니다
model.fit(X_train, y_train)

print("   - 학습 완료!")
print()

# ============================================
# 7️⃣ 예측 및 평가 (Evaluation)
# ============================================
# 학습된 모델로 Test 셋을 예측하고 성능을 평가합니다.
#
# 📊 평가 지표:
# - MAE (Mean Absolute Error): 평균 절대 오차 (점수 차이의 평균)
# - RMSE (Root Mean Squared Error): 평균 제곱근 오차 (큰 오차에 더 민감)
# - R² Score: 결정 계수 (1에 가까울수록 좋음)

print("📈 Step 6: 예측 및 성능 평가")

# 예측
y_pred = model.predict(X_test)

# 평가 지표 계산
mae = mean_absolute_error(y_test, y_pred)
rmse = np.sqrt(mean_squared_error(y_test, y_pred))
r2 = r2_score(y_test, y_pred)

print(f"   - MAE (평균 절대 오차): {mae:.2f}점")
print(f"     → 평균적으로 {mae:.2f}점 정도의 오차로 예측")
print()
print(f"   - RMSE (평균 제곱근 오차): {rmse:.2f}점")
print(f"     → 큰 오차에 더 가중치를 둔 지표")
print()
print(f"   - R² Score: {r2:.4f}")
print(f"     → 1에 가까울수록 좋음 (현재 {r2*100:.1f}%의 변동을 설명)")
print()

# ============================================
# 8️⃣ Feature Importance (변수 중요도)
# ============================================
# 어떤 Feature가 예측에 가장 큰 영향을 미치는지 확인합니다.
# Random Forest는 각 Feature의 중요도를 자동으로 계산해줍니다.

print("🎯 Step 7: Feature 중요도 분석")
print("   (어떤 요소가 점수에 가장 큰 영향을 줄까?)")
print()

feature_importance = pd.DataFrame({
    'feature': X.columns,
    'importance': model.feature_importances_
}).sort_values('importance', ascending=False)

for idx, row in feature_importance.iterrows():
    bar = "█" * int(row['importance'] * 50)
    print(f"   {row['feature']:20} {bar} ({row['importance']*100:.1f}%)")

print()

# ============================================
# 9️⃣ 모델 저장
# ============================================
# 학습된 모델을 파일로 저장합니다.
# 나중에 이 파일을 불러와서 새로운 데이터를 예측할 수 있습니다.

print("💾 Step 8: 모델 저장")

joblib.dump(model, 'model.pkl')
joblib.dump(encoders, 'encoders.pkl')

print("   - model.pkl 저장 완료!")
print("   - encoders.pkl 저장 완료!")
print()

# ============================================
# 🎉 완료!
# ============================================
print("=" * 50)
print("🎉 학습 완료!")
print(f"   모델 성능: R² = {r2:.4f} (MAE = {mae:.2f}점)")
print("   predict.py를 실행해서 새로운 학생 점수를 예측해보세요!")
print("=" * 50)
