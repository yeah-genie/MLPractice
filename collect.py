"""
유튜버 히아투스 레이더 — 채널 검색 + 데이터 수집

실행: python collect.py
결과: data/raw/{채널명}_videos.csv

수집 기준:
- 구독자 30만 명 이상
- 마지막 업로드가 180일(6개월) 이상 전인 채널
"""
import os
import re
from datetime import datetime, timezone, timedelta
from pathlib import Path

import pandas as pd
from googleapiclient.discovery import build
from dotenv import load_dotenv

load_dotenv()

HIATUS_THRESHOLD_DAYS = 180   # 6개월 이상 업로드 없으면 휴재로 판단
MIN_SUBSCRIBERS       = 300_000  # 30만 명 이상인 채널만 분석

# ─────────────────────────────────────────────
# 분석 후보 채널 이름 목록 (35개)
# - 활동 중인 채널은 날짜 필터에서 자동으로 제외됩니다
# - 채널명이 부정확하면 콘솔에 경고가 표시됩니다
# ─────────────────────────────────────────────
CANDIDATE_NAMES = [
    "보겸TV",
    "씬님",
    "허팝",
    "양띵",
    "악어",
    "장삐쭈",
    "쏘영",
    "도티TV",
    "진용진",
    "PONY 신디",
    "이사배",
    "강유미",
    "해쭈",
    "라이나",
    "박막례 할머니",
    "육식맨",
    "봉준",
    "김블루",
    "총몇명",
    "다나카",
    "홍사운드",
    "수리노을",
    "꽁냥이커플",
    "연두부",
    "최고다이순신",
    "헤이지니",
    "소근소근",
    "별다줄",
    "문복희",
    "하쿠나마타타",
    "웃긴대학",
    "손가락수녀",
    "수박씨닷컴",
    "감스트",
    "수위왕",
]


def build_youtube():
    api_key = os.getenv("YOUTUBE")
    if not api_key:
        raise EnvironmentError(".env 파일에 YOUTUBE=키 를 추가해주세요.")
    import httplib2
    http = httplib2.Http(disable_ssl_certificate_validation=True)
    return build("youtube", "v3", developerKey=api_key, http=http)


def search_channel(yt, name: str) -> tuple[str, str, int] | None:
    """
    채널 이름으로 검색해서 (채널ID, 실제채널명, 구독자수) 반환.
    찾지 못하면 None.
    """
    res = yt.search().list(
        q=name,
        type="channel",
        part="id,snippet",
        maxResults=1,
        regionCode="KR",
    ).execute()

    items = res.get("items", [])
    if not items:
        return None

    channel_id = items[0]["id"]["channelId"]
    found_title = items[0]["snippet"]["title"]

    # 구독자 수 확인
    ch_res = yt.channels().list(
        part="statistics,contentDetails",
        id=channel_id,
    ).execute()
    ch_items = ch_res.get("items", [])
    if not ch_items:
        return None

    subs = int(ch_items[0]["statistics"].get("subscriberCount", 0))
    playlist_id = ch_items[0]["contentDetails"]["relatedPlaylists"]["uploads"]
    return channel_id, found_title, subs, playlist_id


def get_last_upload_date(yt, playlist_id: str) -> datetime | None:
    res = yt.playlistItems().list(
        part="snippet",
        playlistId=playlist_id,
        maxResults=1,
    ).execute()
    items = res.get("items", [])
    if not items:
        return None
    ts = items[0]["snippet"]["publishedAt"]
    return datetime.fromisoformat(ts.replace("Z", "+00:00"))


def fetch_all_videos(yt, playlist_id: str, channel_name: str) -> list[dict]:
    """재생목록에서 전체 영상 목록 수집 (제목, 날짜)"""
    videos = []
    next_page = None
    while True:
        res = yt.playlistItems().list(
            part="snippet",
            playlistId=playlist_id,
            maxResults=50,
            pageToken=next_page,
        ).execute()
        for item in res["items"]:
            s = item["snippet"]
            if s["title"] == "Deleted video" or s["title"] == "Private video":
                continue
            videos.append({
                "channel_name": channel_name,
                "video_id":     s["resourceId"]["videoId"],
                "title":        s["title"],
                "published_at": s["publishedAt"],
            })
        next_page = res.get("nextPageToken")
        if not next_page:
            break
    return videos


def fetch_video_details(yt, video_ids: list[str]) -> dict:
    """
    영상 ID 목록으로 상세 정보 수집 (50개씩 배치)

    수집 항목:
    - view_count, like_count, comment_count : 조회수 / 좋아요 / 댓글 수
    - duration_iso   : 영상 길이 (ISO 8601 형식, 예: "PT10M30S")
    - tag_count      : 태그 개수 (전략적으로 줄이는 경우 포착용)
    - desc_length    : 설명란 글자 수 (설명란이 짧아지면 신호일 수 있음)
    """
    details = {}
    for i in range(0, len(video_ids), 50):
        batch = video_ids[i : i + 50]
        res = yt.videos().list(
            part="statistics,contentDetails,snippet",
            id=",".join(batch),
        ).execute()
        for item in res["items"]:
            vid = item["id"]
            stats   = item.get("statistics",      {})
            content = item.get("contentDetails",  {})
            snippet = item.get("snippet",         {})
            details[vid] = {
                "view_count":    int(stats.get("viewCount",    0)),
                "like_count":    int(stats.get("likeCount",    0)),
                "comment_count": int(stats.get("commentCount", 0)),
                "duration_iso":  content.get("duration", ""),
                "tag_count":     len(snippet.get("tags", [])),
                "desc_length":   len(snippet.get("description", "")),
            }
    return details


def main():
    yt  = build_youtube()
    now    = datetime.now(timezone.utc)
    cutoff = now - timedelta(days=HIATUS_THRESHOLD_DAYS)

    Path("data/raw").mkdir(parents=True, exist_ok=True)

    print("=" * 70)
    print(f"  기준: 구독자 {MIN_SUBSCRIBERS:,}명 이상 + 마지막 업로드 {HIATUS_THRESHOLD_DAYS}일 이상 전")
    print("=" * 70)
    print(f"{'검색어':<16} {'찾은 채널명':<20} {'구독자':>8}  {'마지막업로드':^12}  {'상태'}")
    print("-" * 70)

    collected = []
    skipped   = []

    for name in CANDIDATE_NAMES:
        result = search_channel(yt, name)
        if not result:
            print(f"{name:<16} {'검색실패':^20}  {'—':>8}  {'—':^12}  ✗")
            skipped.append(name)
            continue

        channel_id, found_title, subs, playlist_id = result

        # 구독자 필터
        if subs < MIN_SUBSCRIBERS:
            print(f"{name:<16} {found_title[:18]:<20}  {subs:>8,}  {'—':^12}  ✗ 구독자 부족")
            skipped.append(name)
            continue

        last = get_last_upload_date(yt, playlist_id)
        if not last:
            print(f"{name:<16} {found_title[:18]:<20}  {subs:>8,}  {'영상없음':^12}  ✗")
            skipped.append(name)
            continue

        days_silent = (now - last).days
        is_hiatus   = last < cutoff

        if not is_hiatus:
            print(f"{name:<16} {found_title[:18]:<20}  {subs:>8,}  {str(last.date()):^12}  ✗ 활동중")
            skipped.append(name)
            continue

        print(f"{name:<16} {found_title[:18]:<20}  {subs:>8,}  {str(last.date()):^12}  ✓ 수집 ({days_silent}일 휴재)")

        # 전체 영상 수집
        videos = fetch_all_videos(yt, playlist_id, found_title)
        video_ids = [v["video_id"] for v in videos]
        details   = fetch_video_details(yt, video_ids)

        for v in videos:
            v.update(details.get(v["video_id"], {}))
        v["subscriber_count"] = subs

        df = pd.DataFrame(videos)
        df["subscriber_count"] = subs
        df["published_at"] = pd.to_datetime(df["published_at"])
        df = df.sort_values("published_at").reset_index(drop=True)

        safe_name = re.sub(r'[\\/:*?"<>|]', "_", found_title)
        out = Path("data/raw") / f"{safe_name}_videos.csv"
        df.to_csv(out, index=False, encoding="utf-8-sig")
        print(f"  → {len(df)}개 영상 저장: {out}")
        collected.append(found_title)

    print()
    print(f"수집 완료 ({len(collected)}개): {collected}")
    print(f"스킵 ({len(skipped)}개): {skipped}")
    if collected:
        print("\n다음 단계: python clean.py")


if __name__ == "__main__":
    main()
