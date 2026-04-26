"""
이용약관 가독성 분석
====================
data/raw/tos_readability/*.txt 를 읽어 가독성 지표를 계산합니다.

지표:
  - 총 글자 수 (공백 제외)
  - 총 문장 수
  - 평균 문장 길이 (글자 수 기준)
  - 법률 용어 수 / 법률 용어 밀도 (1000자당)
  - 복잡성 지수 0~100 (문장 길이 + 법률 밀도 합산)
  - 예상 읽기 시간 (분, 한국인 평균 독해 속도 700자/분 기준)
  - 가독성 등급 (A~F)

실행: python topics/tos_readability/analyze.py
결과: data/cleaned/tos_readability/tos_analysis.csv
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

# Power BI용 복잡성 점수 색상 매핑
GRADE_MAP = [
    (80, "F", "매우 어려움"),
    (65, "D", "어려움"),
    (50, "C", "보통"),
    (35, "B", "쉬운 편"),
    (0,  "A", "읽기 쉬움"),
]

READING_SPEED = 700  # 한국인 평균 독해 속도 (자/분)


def split_sentences(text: str) -> list[str]:
    sents = SENT_PATTERN.split(text)
    return [s.strip() for s in sents if len(s.strip()) > 10]


def count_legal_terms(text: str) -> dict[str, int]:
    return {term: text.count(term) for term in LEGAL_TERMS}


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


def analyze_file(path: Path) -> dict:
    text = path.read_text(encoding="utf-8")

    # 기본 정제: 연속 공백/줄바꿈 제거
    clean = re.sub(r"\s+", " ", text).strip()
    chars = len(clean.replace(" ", ""))  # 공백 제외 글자 수

    sentences   = split_sentences(clean)
    sent_count  = len(sentences)
    # 공백 제외 글자 수로 통일 (chars 계산과 일관성)
    avg_sent    = round(sum(len(s.replace(" ", "")) for s in sentences) / max(sent_count, 1), 1)

    term_counts = count_legal_terms(clean)
    legal_total = sum(term_counts.values())
    legal_dens  = round(legal_total / max(chars, 1) * 1000, 2)

    score   = complexity_score(avg_sent, legal_dens)
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
        "복잡성_지수":       score,
        "가독성_등급":       g,
        "등급_설명":         glabel,
        "예상_읽기_시간_분": read_min,
        "주요_법률_용어":    top5,
    }


def main():
    txt_files = sorted(RAW_DIR.glob("*.txt"))
    if not txt_files:
        print(f"텍스트 파일 없음: {RAW_DIR}")
        print("먼저 collect.py 를 실행하세요.")
        return

    print("이용약관 가독성 분석 시작")
    print("─" * 60)

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

    df = pd.DataFrame(rows).sort_values("복잡성_지수", ascending=False)

    out = CLEAN_DIR / "tos_analysis.csv"
    df.to_csv(out, index=False, encoding="utf-8-sig")

    print("\n─" * 60)
    print(f"저장: {out}")

    print("\n=== 가독성 최악 TOP 3 ===")
    for _, r in df.head(3).iterrows():
        print(
            f"  {r['앱']}: 복잡성 {r['복잡성_지수']} ({r['등급_설명']}) | "
            f"읽는 데 {r['예상_읽기_시간_분']}분"
        )

    print("\n=== 가장 읽기 쉬운 앱 ===")
    best = df.iloc[-1]
    print(f"  {best['앱']}: 복잡성 {best['복잡성_지수']} ({best['등급_설명']})")


if __name__ == "__main__":
    main()
