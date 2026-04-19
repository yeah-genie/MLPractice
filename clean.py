"""
유튜버 히아투스 레이더 — 수집 데이터 정제
data/raw/*.csv → data/cleaned/*.csv (Power BI 임포트용)

추가 컬럼:
- days_since_prev  : 이전 영상 대비 경과일 (업로드 주기)
- gap_label        : "정상(<14일)" / "주의(14-30일)" / "이상징후(30일+)"
- year_month       : "YYYY-MM" (x축용)
- rolling_gap_30d  : 최근 30일 이동평균 업로드 주기
- is_last_6months  : 마지막 업로드 6개월 이내 여부 (False = 휴재 구간)

실행: python clean.py
"""
from pathlib import Path
import pandas as pd

RAW_DIR = Path("data/raw")
CLEAN_DIR = Path("data/cleaned")


def clean(df: pd.DataFrame) -> pd.DataFrame:
    df["published_at"] = pd.to_datetime(df["published_at"], utc=True)
    df = df.sort_values("published_at").reset_index(drop=True)

    df["days_since_prev"] = df["published_at"].diff().dt.days

    df["gap_label"] = pd.cut(
        df["days_since_prev"],
        bins=[-1, 14, 30, float("inf")],
        labels=["정상", "주의", "이상징후"],
    ).astype(str)
    df.loc[df["days_since_prev"].isna(), "gap_label"] = "첫영상"

    df["year_month"] = df["published_at"].dt.to_period("M").astype(str)

    df["rolling_gap_30d"] = (
        df["days_since_prev"]
        .rolling(window=4, min_periods=1)
        .mean()
        .round(1)
    )

    last_date = df["published_at"].max()
    cutoff = last_date - pd.Timedelta(days=180)
    df["is_last_6months"] = df["published_at"] >= cutoff

    num_cols = ["view_count", "like_count", "comment_count"]
    for col in num_cols:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0).astype(int)

    return df


def main():
    csv_files = list(RAW_DIR.glob("*.csv"))
    if not csv_files:
        print(f"data/raw/ 에 CSV 파일 없음. 먼저 python collect.py 를 실행하세요.")
        return

    CLEAN_DIR.mkdir(parents=True, exist_ok=True)

    for f in csv_files:
        df = pd.read_csv(f, encoding="utf-8-sig")
        cleaned = clean(df)
        out = CLEAN_DIR / f.name
        cleaned.to_csv(out, index=False, encoding="utf-8-sig")
        print(f"정제 완료: {out} ({len(cleaned)}행)")

    print("\nPower BI에서 data/cleaned/*.csv 를 임포트하세요.")


if __name__ == "__main__":
    main()
