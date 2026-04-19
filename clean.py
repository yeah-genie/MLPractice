"""
유튜버 히아투스 레이더 — 데이터 정제 및 분석 지표 생성
data/raw/*.csv → data/cleaned/*.csv (Power BI 임포트용)

실행: python clean.py

생성 컬럼 목록:
──────────────────────────────────────────────
[업로드 패턴]
  days_since_prev     이전 영상 대비 경과일 (업로드 주기)
  gap_label           "정상/주의/이상징후" 3단계 분류
  rolling_gap         최근 4개 영상 업로드 주기 이동평균 ★

[영상 품질/노력]
  duration_sec        영상 길이 (초)
  duration_min        영상 길이 (분, Power BI용)
  title_length        제목 글자 수
  desc_length         설명란 글자 수
  rolling_duration    최근 4개 영상 길이 이동평균 ★

[반응/인게이지먼트]
  like_ratio          좋아요수 / 조회수 (팬심 지표)
  comment_ratio       댓글수 / 조회수
  rolling_views       최근 4개 영상 조회수 이동평균 ★
  rolling_like_ratio  최근 4개 영상 좋아요율 이동평균 ★

[이상탐지]
  z_gap               업로드 주기 Z-score (평소보다 얼마나 늦었나)
  z_views             조회수 Z-score (평소보다 얼마나 떨어졌나)
  z_like_ratio        좋아요율 Z-score
  risk_score          히아투스 위험 점수 0~100 ★

[비교 분석용]
  year_month          "YYYY-MM" (x축용)
  months_before_last  마지막 영상 기준 몇 달 전 영상인지 (채널 비교용) ★
──────────────────────────────────────────────
"""
import re
from pathlib import Path

import pandas as pd

RAW_DIR   = Path("data/raw")
CLEAN_DIR = Path("data/cleaned")


# ── 유틸 함수 ──────────────────────────────────────────────────────────────

def parse_duration_sec(iso: str) -> int:
    """
    YouTube API가 반환하는 ISO 8601 시간 형식을 초로 변환합니다.
    예) "PT10M30S" → 630초,  "PT1H5M" → 3900초,  "PT45S" → 45초
    """
    if not isinstance(iso, str) or not iso:
        return 0
    pattern = r"PT(?:(\d+)H)?(?:(\d+)M)?(?:(\d+)S)?"
    m = re.match(pattern, iso)
    if not m:
        return 0
    h, mi, s = (int(x) if x else 0 for x in m.groups())
    return h * 3600 + mi * 60 + s


def zscore_series(s: pd.Series) -> pd.Series:
    """
    Z-score를 계산합니다.
    Z-score = (현재값 - 평균) / 표준편차

    결과 해석:
      0에 가까움 → 평소와 비슷
      +2 이상    → 평소보다 매우 높음 (업로드 주기라면 위험 신호)
      -2 이하    → 평소보다 매우 낮음 (조회수라면 위험 신호)
    """
    std = s.std()
    if std == 0 or pd.isna(std):
        return pd.Series(0.0, index=s.index)
    return (s - s.mean()) / std


def add_risk_score(df: pd.DataFrame) -> pd.DataFrame:
    """
    히아투스 위험 점수 (0~100) 계산.

    세 가지 신호를 가중 합산합니다:
      40% — 업로드 주기 Z-score  (높을수록 오래 쉬는 중 → 위험)
      35% — 조회수 Z-score       (낮을수록 반응이 식는 중 → 위험, 부호 반전)
      25% — 좋아요율 Z-score     (낮을수록 팬심이 식는 중 → 위험, 부호 반전)

    최종 점수는 채널 내에서 0~100으로 정규화됩니다.
    """
    df["z_gap"]        = zscore_series(df["rolling_gap"].fillna(0))
    df["z_views"]      = zscore_series(df["rolling_views"].fillna(0))
    df["z_like_ratio"] = zscore_series(df["rolling_like_ratio"].fillna(0))

    raw = (
        df["z_gap"]        * 0.40
        + (-df["z_views"]) * 0.35
        + (-df["z_like_ratio"]) * 0.25
    )

    mn, mx = raw.min(), raw.max()
    if mx == mn:
        df["risk_score"] = 50.0
    else:
        df["risk_score"] = ((raw - mn) / (mx - mn) * 100).round(1)

    return df


# ── 메인 정제 함수 ──────────────────────────────────────────────────────────

def clean(df: pd.DataFrame) -> pd.DataFrame:

    # 1. 날짜 파싱 및 정렬
    df["published_at"] = pd.to_datetime(df["published_at"], utc=True)
    df = df.sort_values("published_at").reset_index(drop=True)

    # 2. 숫자 컬럼 정리
    for col in ["view_count", "like_count", "comment_count", "tag_count", "desc_length"]:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0).astype(int)

    # 3. 업로드 주기
    df["days_since_prev"] = df["published_at"].diff().dt.days

    df["gap_label"] = "첫영상"
    mask = df["days_since_prev"].notna()
    df.loc[mask, "gap_label"] = pd.cut(
        df.loc[mask, "days_since_prev"],
        bins=[-1, 14, 30, float("inf")],
        labels=["정상", "주의", "이상징후"],
    ).astype(str)

    # 4. 영상 길이
    if "duration_iso" in df.columns:
        df["duration_sec"] = df["duration_iso"].apply(parse_duration_sec)
    else:
        df["duration_sec"] = 0
    df["duration_min"] = (df["duration_sec"] / 60).round(1)

    # 5. 제목 길이
    df["title_length"] = df["title"].str.len().fillna(0).astype(int)

    # 6. 인게이지먼트 비율
    df["like_ratio"]    = (df["like_count"]    / df["view_count"].replace(0, float("nan"))).fillna(0).round(4)
    df["comment_ratio"] = (df["comment_count"] / df["view_count"].replace(0, float("nan"))).fillna(0).round(4)

    # 7. 이동평균 (window=4, 최근 4개 영상 기준)
    # 왜 4개?: 주 1회 업로드 기준 약 한 달 분량 / 들쭉날쭉한 노이즈를 줄여줌
    w = 4
    df["rolling_gap"]        = df["days_since_prev"].rolling(w, min_periods=1).mean().round(1)
    df["rolling_views"]      = df["view_count"].rolling(w, min_periods=1).mean().round(0)
    df["rolling_duration"]   = df["duration_sec"].rolling(w, min_periods=1).mean().round(0)
    df["rolling_like_ratio"] = df["like_ratio"].rolling(w, min_periods=1).mean().round(4)

    # 8. Z-score 이상탐지 + 위험 점수
    df = add_risk_score(df)

    # 9. 시간축 컬럼
    df["year_month"] = df["published_at"].dt.to_period("M").astype(str)

    last_date = df["published_at"].max()
    df["months_before_last"] = ((last_date - df["published_at"]).dt.days / 30).round(1)

    # 10. 컬럼 순서 정리
    ordered = [
        "channel_name", "video_id", "title", "published_at",
        "year_month", "months_before_last",
        "days_since_prev", "gap_label", "rolling_gap",
        "view_count", "like_count", "comment_count",
        "like_ratio", "comment_ratio",
        "rolling_views", "rolling_like_ratio",
        "duration_sec", "duration_min", "rolling_duration",
        "title_length", "desc_length", "tag_count",
        "z_gap", "z_views", "z_like_ratio", "risk_score",
        "subscriber_count",
    ]
    return df[[c for c in ordered if c in df.columns]]


def main():
    csv_files = list(RAW_DIR.glob("*.csv"))
    if not csv_files:
        print("data/raw/ 에 CSV 파일이 없습니다. 먼저 python collect.py 를 실행하세요.")
        return

    CLEAN_DIR.mkdir(parents=True, exist_ok=True)

    for f in csv_files:
        df = pd.read_csv(f, encoding="utf-8-sig")
        cleaned = clean(df)
        out = CLEAN_DIR / f.name
        cleaned.to_csv(out, index=False, encoding="utf-8-sig")
        print(f"정제 완료: {out} ({len(cleaned)}행, {len(cleaned.columns)}개 컬럼)")

    print("\nPower BI Desktop에서 data/cleaned/*.csv 를 임포트하면 됩니다.")


if __name__ == "__main__":
    main()
