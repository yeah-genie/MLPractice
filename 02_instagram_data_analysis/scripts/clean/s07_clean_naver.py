"""
S07 검색고고학 — 네이버 데이터랩 수집 데이터 정제
data/raw/s07_search_archaeology/ 의 CSV를 읽어 Power BI용 cleaned CSV 생성

추가 컬럼:
- date: 'YYYY-MM-DD' datetime (period 문자열 변환)
- year: 연도 (연도별 슬라이서용)
- quarter: 분기 (Q1~Q4)
- peak_rank: 해당 키워드의 전체 기간 내 최고 비율 대비 현재 비율 순위
"""
import sys
from pathlib import Path
import pandas as pd

ROOT_DIR = Path(__file__).resolve().parents[3]
RAW_DIR = ROOT_DIR / "data" / "raw" / "s07_search_archaeology"
CLEAN_DIR = ROOT_DIR / "data" / "cleaned" / "s07_search_archaeology"


def clean(input_path: Path) -> pd.DataFrame:
    df = pd.read_csv(input_path, encoding="utf-8-sig")

    df["date"] = pd.to_datetime(df["period"])
    df["year"] = df["date"].dt.year
    df["quarter"] = df["date"].dt.quarter.map({1: "Q1", 2: "Q2", 3: "Q3", 4: "Q4"})
    df["ratio"] = pd.to_numeric(df["ratio"], errors="coerce").fillna(0)

    peak = df.groupby("keyword")["ratio"].max().rename("peak_ratio")
    df = df.merge(peak, on="keyword")
    df["pct_of_peak"] = (df["ratio"] / df["peak_ratio"] * 100).round(1)

    return df[["keyword", "date", "year", "quarter", "ratio", "peak_ratio", "pct_of_peak"]]


def main():
    csv_files = list(RAW_DIR.glob("*.csv"))
    if not csv_files:
        print(f"raw 파일 없음: {RAW_DIR}")
        print("먼저 scripts/collect/s07_naver_datalab_collect.py 를 실행하세요.")
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
