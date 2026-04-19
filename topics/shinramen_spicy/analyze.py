"""
신라면 맵기 인플레이션 분석 — 감성 분류 + 지표 산출
=====================================================
수집된 블로그 리뷰를 읽어:
  - 맵기 인식 분류: "더 매움 / 비슷함 / 덜 매움 / 불명확"
  - 브랜드별 맵기 인플레이션 지수 산출
  - Power BI용 두 가지 CSV 생성

실행: python topics/shinramen_spicy/analyze.py
결과:
  data/cleaned/shinramen/reviews_classified.csv   리뷰 1건 = 1행
  data/cleaned/shinramen/brand_summary.csv         브랜드 집계 요약
"""
import re
from pathlib import Path

import pandas as pd

RAW_DIR   = Path("data/raw/shinramen")
CLEAN_DIR = Path("data/cleaned/shinramen")

# ──────────────────────────────────────────────────────────
# 맵기 감성 사전
# 각 리스트의 단어/구절이 텍스트에 포함되면 해당 감성으로 분류
# ──────────────────────────────────────────────────────────

# 신라면보다 더 맵다는 표현
SPICIER = [
    "더 맵", "훨씬 맵", "엄청 맵", "생각보다 맵", "예상보다 맵",
    "신라면 수준이 아니", "신라면보다 훨씬", "신라면보다 맵",
    "신라면 맵기가 아니야", "신라면 맵기가 아닌",
    "죽는 줄", "입에서 불", "매워서 눈물", "매워서 땀",
    "킬링 맵기", "엽기 수준", "불지옥", "지옥 맵기",
    "인생 맵기", "역대급으로 맵", "이렇게 맵",
]

# 신라면 수준이라는 표현
SIMILAR = [
    "딱 신라면", "신라면이랑 비슷", "신라면 맵기 맞", "신라면 정도",
    "신라면 같은 맵기", "신라면 맞아요", "신라면 맞다",
    "신라면 수준", "딱 맞는", "적당히 맵", "보통 맵기",
    "신라면 맵기랑 똑같", "신라면 맵기랑 비슷",
]

# 신라면보다 덜 맵다 / 과대광고라는 표현
MILDER = [
    "별로 안 맵", "맵지 않", "신라면보다 안 맵", "생각보다 안 맵",
    "순한 편", "약한 편", "안 맵다", "하나도 안 맵",
    "신라면 맵기라더니", "신라면보다 약해", "이게 신라면",
    "사기", "속았", "과대광고", "거짓말", "신라면 맵기 아니",
    "신라면도 아니", "신라면보다 순", "의외로 안 맵",
    "낚였", "실망", "맵기 사기",
]


def classify_spiciness(text: str) -> str:
    """
    텍스트를 읽어 맵기 인식을 4단계로 분류합니다.

    판단 순서:
    1. 더 매운 표현이 있으면 → '더 매움'
    2. 덜 매운 표현이 있으면 → '덜 매움'  (순서 주의: 사기, 속았 등이 명확)
    3. 비슷하다는 표현이 있으면 → '비슷함'
    4. 판단 불가 → '불명확'

    더 매움과 덜 매움이 동시에 있으면 점수 합산으로 결정.
    """
    t = text.lower()

    score_spicier = sum(1 for kw in SPICIER if kw in t)
    score_milder  = sum(1 for kw in MILDER  if kw in t)
    score_similar = sum(1 for kw in SIMILAR if kw in t)

    if score_spicier == 0 and score_milder == 0 and score_similar == 0:
        return "불명확"

    if score_spicier > score_milder and score_spicier > score_similar:
        return "더 매움"
    if score_milder > score_spicier and score_milder >= score_similar:
        return "덜 매움"
    if score_similar > 0:
        return "비슷함"
    return "불명확"


def matched_keywords(text: str) -> str:
    """실제로 매칭된 키워드를 콤마로 반환 (검수용)"""
    t = text.lower()
    matched = (
        [kw for kw in SPICIER if kw in t]
        + [kw for kw in MILDER  if kw in t]
        + [kw for kw in SIMILAR if kw in t]
    )
    return ", ".join(matched)


def main():
    csv_files = list(RAW_DIR.glob("*_reviews.csv"))
    if not csv_files:
        print("data/raw/shinramen/ 에 CSV 없음. 먼저 collect.py 를 실행하세요.")
        return

    CLEAN_DIR.mkdir(parents=True, exist_ok=True)

    # ① 전체 리뷰 합치기
    dfs = []
    for f in csv_files:
        df = pd.read_csv(f, encoding="utf-8-sig")
        if not df.empty:
            dfs.append(df)

    if not dfs:
        print("수집된 리뷰가 없습니다.")
        return

    reviews = pd.concat(dfs, ignore_index=True)
    reviews = reviews.drop_duplicates(subset=["full_text"])   # 중복 제거
    print(f"총 리뷰 수: {len(reviews)}건 (중복 제거 후)")

    # ② 맵기 분류
    reviews["spiciness_label"] = reviews["full_text"].apply(classify_spiciness)
    reviews["matched_keywords"] = reviews["full_text"].apply(matched_keywords)

    # ③ 날짜 파싱
    reviews["post_date"] = pd.to_datetime(reviews["post_date"], format="%Y%m%d", errors="coerce")
    reviews["year_month"] = reviews["post_date"].dt.to_period("M").astype(str)

    # ④ 분류 결과 저장 (리뷰 1건 = 1행)
    out_reviews = CLEAN_DIR / "reviews_classified.csv"
    reviews.to_csv(out_reviews, index=False, encoding="utf-8-sig")
    print(f"리뷰 분류 저장: {out_reviews}")

    # ⑤ 브랜드별 집계 요약
    #    각 브랜드에서 "더 매움 / 비슷함 / 덜 매움" 비율 계산
    labeled = reviews[reviews["spiciness_label"] != "불명확"]

    summary_rows = []
    for brand, group in labeled.groupby("brand"):
        total = len(group)
        counts = group["spiciness_label"].value_counts()

        n_spicier = counts.get("더 매움", 0)
        n_similar = counts.get("비슷함",   0)
        n_milder  = counts.get("덜 매움",  0)

        # 맵기 인플레이션 지수: "덜 매움" 비율
        # 높을수록 "신라면 맵기라고 써놨지만 실제론 더 약하다"는 리뷰가 많음
        inflation_idx = round(n_milder / total * 100, 1)

        # 맵기 신뢰도 점수: 1(덜 매움)~3(더 매움) 가중 평균, 2가 신라면 기준
        trust_score = round(
            (n_spicier * 3 + n_similar * 2 + n_milder * 1) / total, 2
        )

        summary_rows.append({
            "brand":              brand,
            "total_reviews":      total,
            "더매움_count":       n_spicier,
            "비슷함_count":       n_similar,
            "덜매움_count":       n_milder,
            "더매움_pct":         round(n_spicier / total * 100, 1),
            "비슷함_pct":         round(n_similar / total * 100, 1),
            "덜매움_pct":         round(n_milder  / total * 100, 1),
            # 맵기 인플레이션 지수: 높을수록 "사기" 리뷰가 많다는 뜻
            "inflation_index":    inflation_idx,
            # 맵기 신뢰도: 2.0 = 딱 신라면 / 2.0 이상 = 실제로 더 매움 / 이하 = 과대광고
            "trust_score":        trust_score,
        })

    summary = pd.DataFrame(summary_rows).sort_values("inflation_index", ascending=False)

    out_summary = CLEAN_DIR / "brand_summary.csv"
    summary.to_csv(out_summary, index=False, encoding="utf-8-sig")
    print(f"브랜드 요약 저장: {out_summary}")

    # ⑥ 콘솔 결과 미리보기
    print()
    print("=" * 65)
    print(f"  {'브랜드':<12} {'리뷰수':>6}  {'더매움':>6}  {'비슷함':>6}  {'덜매움':>6}  {'인플레이션':>10}")
    print("-" * 65)
    for _, row in summary.iterrows():
        print(
            f"  {row['brand']:<12} {row['total_reviews']:>6}  "
            f"{row['더매움_pct']:>5.1f}%  {row['비슷함_pct']:>5.1f}%  "
            f"{row['덜매움_pct']:>5.1f}%  {row['inflation_index']:>9.1f}%"
        )
    print("=" * 65)
    print()
    print("인플레이션 지수가 높을수록 '신라면 맵기'라고 표시했지만 실제론 더 약하다는 리뷰가 많은 브랜드.")
    print("\nPower BI에서 brand_summary.csv + reviews_classified.csv 를 임포트하세요.")


if __name__ == "__main__":
    main()
