# MLPractice — 데이터 분석 학습 레포

데이터 분석 공부 + 인스타그램 계정 [@데이터_탐정] 운영을 위한 레포

---

## 프로젝트 구조

```
MLPractice/
├── 01_exam_score_prediction/   # 학생 시험점수 예측 ML 프로젝트 (학습용)
└── 02_instagram_data_analysis/ # 인스타 콘텐츠용 데이터 분석 프로젝트
```

---

## 01_exam_score_prediction

학습/수면/출석 등 행동 데이터로 시험 점수를 예측하는 Random Forest 모델.

- `train.py` — 모델 학습
- `predict.py` — 예측 실행
- `data.csv` — 20,000명 학생 데이터

```bash
pip install -r requirements.txt
cd 01_exam_score_prediction
python train.py
python predict.py
```

---

## 02_instagram_data_analysis

**콘셉트:** "아무도 분석하지 않은 것들을 분석합니다"  
**계정:** @데이터_탐정 | 격주 발행

### 8개 시리즈

| 코드 | 시리즈 | 핵심 질문 |
|------|--------|---------|
| S01 | [공약탐정] | 당선 후 공약은 언제 사라지나? |
| S02 | [히아투스레이더] | 유튜버 휴재 전 6개월 패턴은? |
| S03 | [편의점경제] | 신제품 몇 %가 6개월 살아남나? |
| S04 | [드라마공식] | K-드라마 첫 키스는 평균 몇 화? |
| S05 | [아이돌생존율] | 데뷔 3년 내 해체 비율은? |
| S06 | [부동산탐정] | 부동산 전문가 예측 정답률은? |
| S07 | [검색고고학] | 가장 빠르게 사라진 검색어는? |
| S08 | [리뷰해부학] | 진짜 vs 가짜 리뷰 패턴 차이는? |

### 데이터 파이프라인

```
원본 데이터
  → scripts/collect/*.py   (API 수집)
  → data/raw/              (원본 보존, 수동 편집 X)
  → scripts/clean/*.py     (정제)
  → data/cleaned/          (Power BI 임포트 대상)
  → powerbi/s0X/*.pbix     (분석 및 시각화)
  → exports/*.png          (인스타 카드뉴스용 PNG)
```

### 빠른 시작 (S02 히아투스레이더)

1. `.env` 파일에 YouTube API 키 추가:
   ```
   YOUTUBE=your_youtube_data_api_v3_key_here
   ```

2. 데이터 수집:
   ```bash
   cd 02_instagram_data_analysis/scripts/collect
   python s02_youtube_api_collect.py --channel_id UC_xxxx --channel_name 채널명
   ```

3. 데이터 정제:
   ```bash
   cd ../clean
   python s02_clean_youtube.py
   ```

4. Power BI Desktop에서 `data/cleaned/s02_youtuber_hiatus/*.csv` 임포트

### API 키 발급

- **YouTube Data API v3**: Google Cloud Console → API 및 서비스 → YouTube Data API v3 활성화
- **네이버 데이터랩**: developers.naver.com → 애플리케이션 등록 → 검색어트렌드 권한 추가

---

## 환경 설정

```bash
pip install -r requirements.txt
cp .env.example .env  # 발급한 API 키 입력
```

`.env` 파일 (절대 커밋하지 말 것):
```
YOUTUBE=AIza...
NAVER_CLIENT_ID=...
NAVER_CLIENT_SECRET=...
```
