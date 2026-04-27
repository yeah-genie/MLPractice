"""
이용약관 가독성 분석
====================
data/raw/tos_readability/*.txt 를 읽어 가독성 지표를 계산합니다.

출력 파일:
  - data/cleaned/tos_readability/tos_analysis.csv       ← Power BI 메인
  - data/cleaned/tos_readability/card_news_summary.csv  ← 카드뉴스 바로 사용

카드뉴스 전용 컬럼:
  - 복잡성_순위          : 1 = 가장 어려움
  - 최하위_대비_복잡성   : 가장 쉬운 앱 대비 몇 배 어려운지
  - 읽기시간_비유        : "뉴스기사 8편", "드라마 1화 절반" 등 체감 비유
  - 법률문장_비율        : 법률 용어가 1개 이상 포함된 문장의 비율 (%)
  - 카드뉴스_인사이트    : 카드 1장에 바로 쓸 수 있는 한 줄 멘트
  - 강조                 : "최악" / "최선" / "" (바 차트 색 강조용)
"""
import re
from pathlib import Path

import pandas as pd

RAW_DIR     = Path("data/raw/tos_readability")
CLEAN_DIR   = Path("data/cleaned/tos_readability")
CLEAN_DIR.mkdir(parents=True, exist_ok=True)

# 한국 법률/계약 문서 전용 어려운 용어 28개
# 제외 기준: 일반 문어체에서도 흔한 단어(이하·이행·갑·을), 현대어 의미가 다른 단어(전보)
LEGAL_TERMS = [
    "귀책사유", "불가항력", "준거법", "관할법원", "면책",
    "위탁", "손해배상", "채무불이행", "소송", "중재",
    "합의관할", "유효기간", "효력발생", "명시적", "묵시적",
    "취소불가", "철회불가", "전항", "본조", "단서",
    "제3자", "법적 구속력", "이용계약", "관련 법령",
    "개인정보처리방침", "포함하되 이에 한정하지 않는",
    "기재된 바에 따라", "이에 동의하는 것으로 간주",
]

# 숫자 뒤 마침표(소수점·조항번호)는 문장 끝으로 보지 않음, 공백 필수
SENT_PATTERN = re.compile(r"(?<!\d)[.。!?]\s+")

GRADE_MAP = [
    (80, "F", "매우 어려움"),
    (65, "D", "어려움"),
    (50, "C", "보통"),
    (35, "B", "쉬운 편"),
    (0,  "A", "읽기 쉬움"),
]

READING_SPEED = 700  # 한국인 평균 독해 속도 (자/분)


# ── 기본 분석 ────────────────────────────────────────────────────────────────

def split_sentences(text: str) -> list[str]:
    sents = SENT_PATTERN.split(text)
    return [s.strip() for s in sents if len(s.strip()) > 10]


def count_legal_terms(text: str) -> dict[str, int]:
    return {term: text.count(term) for term in LEGAL_TERMS}


def legal_sentence_ratio(sentences: list[str]) -> float:
    """법률 용어가 1개 이상 포함된 문장 비율 (%)"""
    if not sentences:
        return 0.0
    hits = sum(1 for s in sentences if any(t in s for t in LEGAL_TERMS))
    return round(hits / len(sentences) * 100, 1)


def complexity_score(avg_sent_len: float, legal_density: float) -> float:
    """
    복잡성 지수 0~100
    avg_sent_len: 평균 문장 길이 (공백 제외 글자 수)
    legal_density: 1000자당 법률 용어 수

    천장값 근거:
      - 120자: 한국 법률 문서 상위 10% 문장 길이 (공백 제외)
      - 15개: 정제된 법률 용어 기준 고밀도 임계값
    """
    sent_score  = min(avg_sent_len / 120, 1.0) * 60
    legal_score = min(legal_density / 15, 1.0) * 40
    return round(sent_score + legal_score, 1)


def grade(score: float) -> tuple[str, str]:
    for threshold, g, label in GRADE_MAP:
        if score >= threshold:
            return g, label
    return "A", "읽기 쉬움"


def reading_time_analogy(minutes: float) -> str:
    """읽기 시간을 체감 비유로 변환 (카드뉴스용)"""
    if minutes < 3:
        return f"뉴스기사 {max(1, round(minutes / 1.5))}편"
    elif minutes < 6:
        return f"뉴스기사 {round(minutes / 1.5)}편"
    elif minutes < 10:
        return f"유튜브 영상 1편"
    elif minutes < 15:
        return f"유튜브 영상 {round(minutes / 8)}편"
    elif minutes < 25:
        return f"드라마 예고편 {round(minutes / 3)}편"
    elif minutes < 40:
        return f"드라마 1화 절반"
    else:
        return f"드라마 1화 전체"


def analyze_file(path: Path) -> dict:
    text = path.read_text(encoding="utf-8")

    clean     = re.sub(r"\s+", " ", text).strip()
    chars     = len(clean.replace(" ", ""))

    sentences  = split_sentences(clean)
    sent_count = len(sentences)
    avg_sent   = round(sum(len(s.replace(" ", "")) for s in sentences) / max(sent_count, 1), 1)

    term_counts  = count_legal_terms(clean)
    legal_total  = sum(term_counts.values())
    legal_dens   = round(legal_total / max(chars, 1) * 1000, 2)
    legal_s_ratio = legal_sentence_ratio(sentences)

    score    = complexity_score(avg_sent, legal_dens)
    g, glabel = grade(score)
    read_min = round(chars / READING_SPEED, 1)

    top_terms = sorted(term_counts.items(), key=lambda x: -x[1])
    top5 = ", ".join(f"{t}({c})" for t, c in top_terms[:5] if c > 0)

    return {
        "앱":               path.stem,
        "총_글자수":         chars,
        "문장_수":           sent_count,
        "평균_문장_길이":    avg_sent,
        "법률_용어_총수":    legal_total,
        "법률_용어_밀도":    legal_dens,
        "법률문장_비율":     legal_s_ratio,
        "복잡성_지수":       score,
        "가독성_등급":       g,
        "등급_설명":         glabel,
        "예상_읽기_시간_분": read_min,
        "주요_법률_용어":    top5,
    }


# ── 카드뉴스 전용 컬럼 추가 ──────────────────────────────────────────────────

def add_card_news_columns(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()

    # 순위 (복잡성 내림차순, 1 = 가장 어려움)
    df["복잡성_순위"]  = df["복잡성_지수"].rank(ascending=False, method="min").astype(int)
    df["읽기시간_순위"] = df["예상_읽기_시간_분"].rank(ascending=False, method="min").astype(int)

    # 가장 쉬운 앱(최솟값) 대비 몇 배 어려운지
    min_score = max(df["복잡성_지수"].min(), 0.1)  # 0 나눗셈 방지
    max_score = df["복잡성_지수"].max()
    df["최하위_대비_복잡성"] = (df["복잡성_지수"] / min_score).round(1)

    # 읽기 시간 체감 비유
    df["읽기시간_비유"] = df["예상_읽기_시간_분"].apply(reading_time_analogy)

    # 강조 태그 (바 차트 색 강조용 — 공동 1위면 읽기시간 가장 긴 앱 강조)
    worst_idx = df["예상_읽기_시간_분"].idxmax()  # 복잡성 동점 시 읽기시간으로 결정
    best_idx  = df["복잡성_지수"].idxmin()
    df["강조"] = ""
    df.loc[worst_idx, "강조"] = "최악"
    df.loc[best_idx,  "강조"] = "최선"

    # 카드뉴스 한 줄 인사이트
    n         = len(df)
    avg_score = df["복잡성_지수"].mean()
    insights  = []

    for _, r in df.iterrows():
        score = r["복잡성_지수"]
        mins  = r["예상_읽기_시간_분"]
        dens  = r["법률_용어_밀도"]
        ratio_vs_worst = round(max_score / max(score, 0.1), 1)  # 가장 어려운 앱 대비 몇 배 쉬운지

        if r["강조"] == "최악":
            insights.append(
                f"{n}개 앱 중 읽기 가장 오래 걸리는 이용약관 — "
                f"완독 {mins:.0f}분 ({reading_time_analogy(mins)})"
            )
        elif r["강조"] == "최선":
            insights.append(
                f"가장 읽기 쉬운 이용약관 — "
                f"1위보다 {ratio_vs_worst:.1f}배 쉽고 {mins:.0f}분이면 완독"
            )
        elif score >= 95:
            insights.append(
                f"완독 {mins:.0f}분 — {reading_time_analogy(mins)} 분량의 이용약관"
            )
        elif dens > 40:
            insights.append(
                f"1000자당 법률 용어 {dens:.0f}개 — 계약서 수준의 밀도"
            )
        elif mins > 15:
            insights.append(
                f"완독 {mins:.0f}분 ({reading_time_analogy(mins)}) — "
                f"복잡성 {r['복잡성_순위']}위"
            )
        else:
            compare = "평균보다 어려움" if score > avg_score else "평균보다 쉬운 편"
            insights.append(f"복잡성 {score}점 — {compare} ({r['복잡성_순위']}위/{n}위)")

    df["카드뉴스_인사이트"] = insights
    return df


# ── 카드뉴스 요약 파일 ────────────────────────────────────────────────────────

def save_card_news_summary(df: pd.DataFrame) -> None:
    """
    card_news_summary.csv
    카드뉴스 제작 시 바로 복사해서 쓸 수 있는 핵심 수치 모음
    """
    total_apps   = len(df)
    total_chars  = df["총_글자수"].sum()
    max_read_min = df["예상_읽기_시간_분"].max()
    avg_complex  = round(df["복잡성_지수"].mean(), 1)
    worst_app    = df.loc[df["복잡성_지수"].idxmax(), "앱"]
    best_app     = df.loc[df["복잡성_지수"].idxmin(), "앱"]
    ratio_gap    = df.loc[df["복잡성_지수"].idxmax(), "최하위_대비_복잡성"]

    # Card 03 메트릭 박스 (METRIC 01/02/03)
    metrics = pd.DataFrame([
        {
            "card_slot": "METRIC 01",
            "수치":      f"{total_apps}개",
            "설명":      "분석한 앱 수",
            "부연":      "국내 주요 플랫폼",
        },
        {
            "card_slot": "METRIC 02",
            "수치":      f"{total_chars // 10000}만자",
            "설명":      "이용약관 총 글자 수",
            "부연":      f"평균 {total_chars // total_apps // 1000}천자/앱",
        },
        {
            "card_slot": "METRIC 03",
            "수치":      f"{max_read_min:.0f}분",
            "설명":      "최장 완독 시간",
            "부연":      f"{worst_app} 이용약관 기준",
        },
    ])

    # Cover card 한 줄 훅 문구 (카드 1장)
    cover = pd.DataFrame([
        {
            "구분":   "커버_훅",
            "문구":   f"당신이 '동의' 누른 이용약관, 다 읽으면 {max_read_min:.0f}분입니다",
            "서브":   f"국내 주요 앱 {total_apps}개 이용약관 가독성 전수 분석",
        },
        {
            "구분":   "결론_반전",
            "문구":   f"{best_app}는 {ratio_gap:.0f}배 쉽게 썼다",
            "서브":   f"{worst_app}와 {best_app}, 같은 '이용약관'인데 복잡성 {ratio_gap:.0f}배 차이",
        },
        {
            "구분":   "평균_수치",
            "문구":   f"10개 앱 평균 복잡성 {avg_complex}점 (100점 만점)",
            "서브":   f"F등급(매우 어려움): {len(df[df['가독성_등급']=='F'])}개 앱",
        },
    ])

    metrics.to_csv(CLEAN_DIR / "card_metrics.csv",  index=False, encoding="utf-8-sig")
    cover.to_csv(  CLEAN_DIR / "card_hook.csv",     index=False, encoding="utf-8-sig")

    print(f"\n저장: card_metrics.csv  ← Card 03 메트릭 박스 3개")
    print(f"저장: card_hook.csv     ← Cover/결론 카드 훅 문구")


def main():
    txt_files = sorted(RAW_DIR.glob("*.txt"))
    if not txt_files:
        print(f"텍스트 파일 없음: {RAW_DIR}")
        print("먼저 collect.py 를 실행하세요.")
        return

    print("이용약관 가독성 분석 시작")
    print("─" * 65)

    rows = []
    for f in txt_files:
        row = analyze_file(f)
        rows.append(row)
        print(
            f"[{row['앱']:8s}] {row['총_글자수']:>7,}자 | "
            f"문장 {row['문장_수']:>4}개 | "
            f"평균 {row['평균_문장_길이']:>5.1f}자 | "
            f"법률 {row['법률_용어_밀도']:>5.2f}/1000자 | "
            f"복잡성 {row['복잡성_지수']:>5.1f} ({row['가독성_등급']})"
        )

    df = pd.DataFrame(rows).sort_values("복잡성_지수", ascending=False).reset_index(drop=True)
    df = add_card_news_columns(df)

    out = CLEAN_DIR / "tos_analysis.csv"
    df.to_csv(out, index=False, encoding="utf-8-sig")
    print(f"\n저장: {out}")

    save_card_news_summary(df)

    print("\n─" * 65)
    print("\n=== 카드뉴스 바 차트용 TOP 3 (Card 05) ===")
    for _, r in df.head(3).iterrows():
        print(
            f"  {r['복잡성_순위']}위 {r['앱']:8s} | "
            f"복잡성 {r['복잡성_지수']:>5.1f} | "
            f"{r['예상_읽기_시간_분']}분 ({r['읽기시간_비유']}) | "
            f"{r['카드뉴스_인사이트']}"
        )

    best = df.iloc[-1]
    ratio_vs_worst = round(df["복잡성_지수"].max() / max(best["복잡성_지수"], 0.1), 1)
    print(f"\n=== 가장 읽기 쉬운 앱 (Card 07 결론용) ===")
    print(
        f"  {best['앱']} | 복잡성 {best['복잡성_지수']} | "
        f"1위 대비 {ratio_vs_worst}배 쉬움 | "
        f"{best['카드뉴스_인사이트']}"
    )


if __name__ == "__main__":
    main()
