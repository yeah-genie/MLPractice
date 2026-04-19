"""
S02 히아투스레이더 — YouTube 수집 데이터 정제
data/raw/s02_youtuber_hiatus/ 의 CSV를 읽어 Power BI용 cleaned CSV 생성

추가 컬럼:
- days_since_prev: 이전 영상 대비 경과일 (업로드 주기)
- upload_gap_flag: 30일 초과 = '이상징후', 14-30일 = '주의', 14일 이하 = '정상'
- year_month: 'YYYY-MM' (꺾은선 그래프 x축용)
- title_length: 제목 길이 (반복/짧은 제목 탐지용)
"""
import sys
from pathlib import Path
import pandas as pd

ROOT_DIR = Path(__file__).resolve().parents[3]
RAW_DIR = ROOT_DIR / "data" / "raw" / "s02_youtuber_hiatus"
CLEAN_DIR = ROOT_DIR / "data" / "cleaned" / "s02_youtuber_hiatus"


def clean(input_path: Path) -> pd.DataFrame:
    df = pd.read_csv(input_path, encoding="utf-8-sig")

    df["published_at"] = pd.to_datetime(df["published_at"], utc=True).dt.tz_convert(
        "Asia/Seoul"
    )
    df = df.sort_values("published_at").reset_index(drop=True)

    df["days_since_prev"] = (
        df.groupby("channel_id")["published_at"]
        .diff()
        .dt.days
    )

    df["upload_gap_flag"] = pd.cut(
        df["days_since_prev"],
        bins=[-1, 14, 30, float("inf")],
        labels=["정상", "주의", "이상징후"],
    )

    df["year_month"] = df["published_at"].dt.to_period("M").astype(str)
    df["title_length"] = df["title"].str.len()

    df["view_count"] = pd.to_numeric(df.get("view_count", 0), errors="coerce").fillna(0).astype(int)
    df["like_count"] = pd.to_numeric(df.get("like_count", 0), errors="coerce").fillna(0).astype(int)

    keep_cols = [
        "channel_id", "channel_name", "video_id", "title",
        "published_at", "year_month",
        "view_count", "like_count", "comment_count",
        "days_since_prev", "upload_gap_flag", "title_length",
        "duration",
    ]
    return df[[c for c in keep_cols if c in df.columns]]


def main():
    csv_files = list(RAW_DIR.glob("*.csv"))
    if not csv_files:
        print(f"raw 파일 없음: {RAW_DIR}")
        print("먼저 scripts/collect/s02_youtube_api_collect.py 를 실행하세요.")
        sys.exit(1)

    CLEAN_DIR.mkdir(parents=True, exist_ok=True)

    for f in csv_files:
        print(f"정제 중: {f.name}")
        df = clean(f)
        out = CLEAN_DIR / f.name
        df.to_csv(out, index=False, encoding="utf-8-sig")
        print(f"저장 완료: {out} ({len(df)}행)")


if __name__ == "__main__":
    main()
