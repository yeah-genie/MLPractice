"""
유튜버 히아투스 레이더 — 영상 자막 분석
data/raw/*.csv 에서 video_id 를 읽어 자막을 수집하고
번아웃/이상 신호 키워드를 분석합니다.

실행: python analyze_transcripts.py
결과: data/cleaned/{채널명}_transcripts.csv

Power BI에서 video_id 를 키로 기존 영상 데이터와 연결(관계)하면
"언제 힘들다는 말이 늘었는가"를 타임라인으로 볼 수 있습니다.

주의:
- 자막이 없는 영상은 자동으로 건너뜁니다
- 자동 생성 자막(auto-generated)도 분석합니다
- 채널당 수백 개 영상이면 수 분 소요될 수 있습니다
"""
import time
from pathlib import Path

import pandas as pd
from youtube_transcript_api import YouTubeTranscriptApi, NoTranscriptFound, TranscriptsDisabled

RAW_DIR   = Path("data/raw")
CLEAN_DIR = Path("data/cleaned")

# ──────────────────────────────────────────────────────────
# 분석할 키워드 사전
# 카테고리별로 묶어서 관리합니다
# ──────────────────────────────────────────────────────────
KEYWORD_CATEGORIES: dict[str, list[str]] = {

    # 지침/번아웃 — 가장 직접적인 신호
    "번아웃": [
        "쉬고싶", "지쳤", "힘들어", "힘든데", "힘드네", "번아웃",
        "슬럼프", "지쳐", "못하겠", "그만두고싶", "쉬어야", "방전",
        "지친", "탈진", "소진", "버겁", "한계", "뭔가 이상",
    ],

    # 사과 / 업로드 지연 — "오랜만이에요" 같은 말이 늘어날 때
    "사과_지연": [
        "미안해", "미안합니다", "죄송해", "죄송합니다", "늦었어",
        "오랜만", "오래됐", "뜸했", "못올렸", "업로드를 못",
        "자주 못", "기다리셨", "기다렸죠", "오래 기다",
    ],

    # 불확실 / 고민 — 앞날을 모르겠다는 뉘앙스
    "불확실_고민": [
        "모르겠어", "고민이에요", "고민 중", "어떻게 해야", "앞으로",
        "생각이 많", "걱정되", "불안해", "어렵네요", "갈피를",
        "방향을", "어떻게될지", "확실하지", "변화가 있을",
    ],

    # 건강 / 피로 — 몸 상태에 대한 언급
    "건강_피로": [
        "아파", "아프", "몸이", "건강이", "피곤", "피로",
        "잠을 못", "못잤", "두통", "스트레스", "체력이",
        "병원", "입원", "쉬라고",
    ],

    # 감사 / 작별 뉘앙스 — 마지막 인사 같은 분위기
    "감사_작별": [
        "감사합니다", "고마워요", "고맙습니다", "사랑해요",
        "사랑합니다", "응원해줘서", "함께해줘서", "봐줘서",
        "지켜봐줘서", "여기까지",
    ],
}

# 위험 점수 가중치 (합계 = 1.0)
WEIGHTS = {
    "번아웃":      0.40,
    "사과_지연":   0.25,
    "불확실_고민": 0.20,
    "건강_피로":   0.15,
    "감사_작별":   0.00,   # 점수엔 반영 안 하되 카운트는 기록
}


def fetch_transcript(video_id: str) -> list[dict] | None:
    """
    YouTube 자막을 가져옵니다.
    한국어 자막을 우선하고, 없으면 자동 생성 자막을 사용합니다.
    자막 자체가 없으면 None 반환.
    """
    try:
        transcript_list = YouTubeTranscriptApi.list_transcripts(video_id)

        # 1순위: 수동 한국어 자막
        try:
            return transcript_list.find_manually_created_transcript(["ko"]).fetch()
        except Exception:
            pass

        # 2순위: 자동 생성 한국어 자막
        try:
            return transcript_list.find_generated_transcript(["ko"]).fetch()
        except Exception:
            pass

        # 3순위: 한국어 번역본 (드물지만 시도)
        try:
            first = next(iter(transcript_list))
            return first.translate("ko").fetch()
        except Exception:
            pass

        return None

    except (NoTranscriptFound, TranscriptsDisabled):
        return None
    except Exception:
        return None


def analyze_text(text: str) -> dict:
    """
    전체 자막 텍스트에서 카테고리별 키워드 빈도를 계산합니다.

    단순 포함 여부가 아니라 등장 횟수를 셉니다.
    자막 길이가 다른 영상끼리 비교하기 위해 1000자당 빈도로 정규화합니다.
    """
    text_len = len(text)
    if text_len == 0:
        return {}

    counts = {}
    for category, keywords in KEYWORD_CATEGORIES.items():
        count = sum(text.count(kw) for kw in keywords)
        # 1000자당 빈도 (정규화)
        counts[f"{category}_count"] = count
        counts[f"{category}_per1k"]  = round(count / text_len * 1000, 3)

    return counts


def compute_verbal_risk(row: dict) -> float:
    """
    카테고리별 per1k 수치를 가중 합산해 언급 위험 점수(raw) 반환.
    이 값은 나중에 clean 단계에서 0~100으로 정규화됩니다.
    """
    score = 0.0
    for category, weight in WEIGHTS.items():
        score += row.get(f"{category}_per1k", 0) * weight
    return round(score, 4)


def process_channel(csv_path: Path) -> None:
    df = pd.read_csv(csv_path, encoding="utf-8-sig")
    if "video_id" not in df.columns:
        print(f"  video_id 컬럼 없음 — 스킵: {csv_path.name}")
        return

    channel_name = df["channel_name"].iloc[0] if "channel_name" in df.columns else csv_path.stem
    video_ids    = df["video_id"].tolist()
    total        = len(video_ids)

    print(f"\n[{channel_name}] 총 {total}개 영상 자막 분석 시작...")

    rows = []
    success = 0
    skipped = 0

    for i, video_id in enumerate(video_ids, 1):
        if i % 20 == 0:
            print(f"  {i}/{total} 처리 중...")

        transcript = fetch_transcript(video_id)

        if transcript is None:
            skipped += 1
            rows.append({"video_id": video_id, "transcript_available": False})
            time.sleep(0.3)
            continue

        # 자막 텍스트 전체 합치기
        full_text = " ".join(seg["text"] for seg in transcript)
        counts    = analyze_text(full_text)

        row = {
            "video_id":             video_id,
            "transcript_available": True,
            "transcript_length":    len(full_text),
            **counts,
        }
        row["verbal_risk_raw"] = compute_verbal_risk(row)
        rows.append(row)
        success += 1

        time.sleep(0.5)  # 요청 간격 (차단 방지)

    result_df = pd.DataFrame(rows)

    # verbal_risk_raw 를 0~100으로 정규화
    if "verbal_risk_raw" in result_df.columns:
        mn = result_df["verbal_risk_raw"].min()
        mx = result_df["verbal_risk_raw"].max()
        if mx > mn:
            result_df["verbal_risk_score"] = (
                (result_df["verbal_risk_raw"] - mn) / (mx - mn) * 100
            ).round(1)
        else:
            result_df["verbal_risk_score"] = 50.0

    # 이동평균 (4개 영상 기준)
    if "verbal_risk_score" in result_df.columns:
        result_df["rolling_verbal_risk"] = (
            result_df["verbal_risk_score"]
            .rolling(4, min_periods=1)
            .mean()
            .round(1)
        )

    CLEAN_DIR.mkdir(parents=True, exist_ok=True)
    out = CLEAN_DIR / csv_path.name.replace("_videos.csv", "_transcripts.csv")
    result_df.to_csv(out, index=False, encoding="utf-8-sig")

    print(f"  완료 — 자막 있음: {success}개, 없음: {skipped}개")
    print(f"  저장: {out}")


def main():
    csv_files = list(RAW_DIR.glob("*_videos.csv"))
    if not csv_files:
        print("data/raw/ 에 영상 CSV가 없습니다. 먼저 python collect.py 를 실행하세요.")
        return

    print("=" * 60)
    print("  유튜버 히아투스 레이더 — 자막 키워드 분석")
    print("=" * 60)

    for f in csv_files:
        process_channel(f)

    print("\n\n모든 채널 완료!")
    print("Power BI에서 video_id 기준으로 *_transcripts.csv 를 *_videos.csv 와 연결하세요.")


if __name__ == "__main__":
    main()
