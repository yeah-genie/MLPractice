"""
유튜버 히아투스 레이더 — 채널 영상 데이터 수집
분석 대상: 6개월(180일) 이상 업로드가 없는 한국 유튜버

실행: python collect.py
결과: data/raw/{채널명}_videos.csv
"""
import os
from datetime import datetime, timezone, timedelta
from pathlib import Path
import pandas as pd
from googleapiclient.discovery import build
from dotenv import load_dotenv

load_dotenv()

HIATUS_THRESHOLD_DAYS = 180  # 6개월

# 분석 후보 채널 목록 (name, channel_id)
# API로 마지막 업로드 날짜를 확인하고, 6개월 이상 쉰 채널만 수집
CANDIDATE_CHANNELS = [
    ("보겸TV",       "UCpkZ6UBrKDjG7HsLFfXCeOQ"),
    ("씬님",         "UCQMtgO4N6caSIOMVEFkvpHw"),
    ("수위왕",       "UCfePuvEFWi9UbbxRMnCd6VQ"),
    ("도티TV",       "UCQo3HzHl4ooDITFRdqKPQww"),
    ("허팝",         "UC8wgFQvFGJFO6-8FRPmMTBg"),
    ("대도서관TV",   "UCRUgDP_JMQVoR8PvI1JOPJA"),
    ("양띵",         "UC6FvEPUrQTR4FCWH3wsgaKw"),
    ("악어",         "UCgwdUPXVd87B1Uz2tmP3nLg"),
    ("장삐쭈",       "UCgMJGgniKGjBqgAyNPSoUSQ"),
    ("쏘영",         "UCrBqWqobWguLHb1UoqGY8dw"),
]


def build_youtube():
    api_key = os.getenv("YOUTUBE")
    if not api_key:
        raise EnvironmentError(".env 파일에 YOUTUBE 키가 없습니다.")
    return build("youtube", "v3", developerKey=api_key)


def get_uploads_playlist_id(yt, channel_id: str) -> str | None:
    res = yt.channels().list(part="contentDetails,snippet", id=channel_id).execute()
    items = res.get("items", [])
    if not items:
        return None
    return items[0]["contentDetails"]["relatedPlaylists"]["uploads"]


def get_last_upload_date(yt, playlist_id: str) -> datetime | None:
    res = yt.playlistItems().list(
        part="snippet",
        playlistId=playlist_id,
        maxResults=1,
    ).execute()
    items = res.get("items", [])
    if not items:
        return None
    published = items[0]["snippet"]["publishedAt"]
    return datetime.fromisoformat(published.replace("Z", "+00:00"))


def fetch_all_videos(yt, playlist_id: str, channel_name: str) -> list[dict]:
    videos = []
    next_page = None
    while True:
        res = yt.playlistItems().list(
            part="snippet,contentDetails",
            playlistId=playlist_id,
            maxResults=50,
            pageToken=next_page,
        ).execute()
        for item in res["items"]:
            s = item["snippet"]
            videos.append({
                "channel_name": channel_name,
                "video_id": s["resourceId"]["videoId"],
                "title": s["title"],
                "published_at": s["publishedAt"],
            })
        next_page = res.get("nextPageToken")
        if not next_page:
            break
    return videos


def fetch_video_stats(yt, video_ids: list[str]) -> dict:
    stats = {}
    for i in range(0, len(video_ids), 50):
        batch = video_ids[i:i+50]
        res = yt.videos().list(part="statistics", id=",".join(batch)).execute()
        for item in res["items"]:
            s = item.get("statistics", {})
            stats[item["id"]] = {
                "view_count":    int(s.get("viewCount",    0)),
                "like_count":    int(s.get("likeCount",    0)),
                "comment_count": int(s.get("commentCount", 0)),
            }
    return stats


def main():
    yt = build_youtube()
    now = datetime.now(timezone.utc)
    cutoff = now - timedelta(days=HIATUS_THRESHOLD_DAYS)

    Path("data/raw").mkdir(parents=True, exist_ok=True)

    collected = []
    skipped = []

    print(f"{'채널명':<15} {'마지막 업로드':^22} {'휴재일수':^8} {'수집여부'}")
    print("-" * 60)

    for name, channel_id in CANDIDATE_CHANNELS:
        playlist_id = get_uploads_playlist_id(yt, channel_id)
        if not playlist_id:
            print(f"{name:<15} {'채널 없음':^22} {'—':^8} 스킵")
            skipped.append(name)
            continue

        last = get_last_upload_date(yt, playlist_id)
        if not last:
            print(f"{name:<15} {'영상 없음':^22} {'—':^8} 스킵")
            skipped.append(name)
            continue

        days_silent = (now - last).days
        is_hiatus = last < cutoff
        status = "✓ 수집" if is_hiatus else "✗ 활동중"

        print(f"{name:<15} {str(last.date()):^22} {days_silent:^8} {status}")

        if not is_hiatus:
            skipped.append(name)
            continue

        # 6개월+ 쉰 채널이면 전체 영상 수집
        videos = fetch_all_videos(yt, playlist_id, name)
        video_ids = [v["video_id"] for v in videos]
        stats = fetch_video_stats(yt, video_ids)
        for v in videos:
            v.update(stats.get(v["video_id"], {}))

        df = pd.DataFrame(videos)
        df["published_at"] = pd.to_datetime(df["published_at"])
        df = df.sort_values("published_at").reset_index(drop=True)

        out = Path("data/raw") / f"{name}_videos.csv"
        df.to_csv(out, index=False, encoding="utf-8-sig")
        print(f"  → {len(df)}개 영상 저장: {out}")
        collected.append(name)

    print()
    print(f"수집 완료: {collected}")
    print(f"스킵 (활동중 또는 없음): {skipped}")
    if collected:
        print("\n다음 단계: python clean.py")


if __name__ == "__main__":
    main()
