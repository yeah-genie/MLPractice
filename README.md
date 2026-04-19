# 유튜버 히아투스 레이더

6개월(180일) 이상 업로드가 없는 유튜버의 **휴재 전 패턴**을 분석합니다.

## 실행 순서

```bash
pip install -r requirements.txt

# 1. 데이터 수집 (6개월+ 쉰 채널만 자동 필터)
python collect.py

# 2. 데이터 정제 (Power BI용 CSV 생성)
python clean.py
```

## 파일 구조

```
collect.py       ← YouTube API 수집
clean.py         ← 데이터 정제 (업로드 주기, 이상징후 라벨 등)
data/raw/        ← 수집 원본 (gitignore)
data/cleaned/    ← Power BI 임포트 대상
.env             ← API 키 (gitignore)
```

## Power BI 분석 포인트

- **업로드 주기 꺾은선** — 휴재 전 12개월간 days_since_prev 추이
- **이상징후 비율 막대** — 월별 gap_label 분포 (정상/주의/이상징후)
- **조회수 vs 업로드 주기 산점도** — 조회수 하락과 업로드 주기 증가 상관관계
- **rolling_gap_30d** — 이동평균으로 트렌드 시각화

## 분석 대상 채널 기준

`collect.py`의 `CANDIDATE_CHANNELS` 리스트에서 마지막 업로드가 180일+인 채널만 자동 선별.
새 채널 추가: `("채널명", "채널ID")` 형태로 리스트에 추가.
