"""
S02 히아투스레이더 — YouTube 채널 영상 메타데이터 수집
사용법: python s02_youtube_api_collect.py --channel_id UC_xxxx --channel_name 채널명
필요 환경변수: YOUTUBE (YouTube Data API v3 키)
"""
import argparse
import pandas as pd
from googleapiclient.discovery import build
from utils.api_helpers import load_api_key, save_raw, today_str


def get_uploads_playlist_id(youtube, channel_id: str) -> str:
    res = youtube.channels().list(
        part="contentDetails",
        id=channel_id,
    ).execute()
    items = res.get("items", [])
    if not items:
        raise ValueError(f"채널 ID를 찾을 수 없습니다: {channel_id}")
    return items[0]["contentDetails"]["relatedPlaylists"]["uploads"]


def fetch_all_videos(youtube, playlist_id: str) -> list[dict]:
    videos = []
    next_page_token = None

    while True:
        res = youtube.playlistItems().list(
            part="snippet,contentDetails",
            playlistId=playlist_id,
            maxResults=50,
            pageToken=next_page_token,
        ).execute()

        for item in res["items"]:
            snippet = item["snippet"]
            videos.append({
                "video_id": snippet["resourceId"]["videoId"],
                "title": snippet["title"],
                "published_at": snippet["publishedAt"],
                "description": snippet.get("description", "")[:200],
            })

        next_page_token = res.get("nextPageToken")
        if not next_page_token:
            break

    return videos


def fetch_video_stats(youtube, video_ids: list[str]) -> dict:
    """50개씩 배치로 조회수/좋아요 수 가져오기"""
    stats = {}
    for i in range(0, len(video_ids), 50):
        batch = video_ids[i : i + 50]
        res = youtube.videos().list(
            part="statistics,contentDetails",
            id=",".join(batch),
        ).execute()
        for item in res["items"]:
            vid = item["id"]
            s = item.get("statistics", {})
            d = item.get("contentDetails", {})
            stats[vid] = {
                "view_count": int(s.get("viewCount", 0)),
                "like_count": int(s.get("likeCount", 0)),
                "comment_count": int(s.get("commentCount", 0)),
                "duration": d.get("duration", ""),
            }
    return stats


def main():
    parser = argparse.ArgumentParser(description="YouTube 채널 영상 데이터 수집")
    parser.add_argument("--channel_id", required=True, help="YouTube 채널 ID (UC로 시작)")
    parser.add_argument("--channel_name", required=True, help="채널명 (파일명에 사용)")
    args = parser.parse_args()

    api_key = load_api_key("youtube")
    youtube = build("youtube", "v3", developerKey=api_key)

    print(f"채널 '{args.channel_name}' 업로드 목록 수집 중...")
    playlist_id = get_uploads_playlist_id(youtube, args.channel_id)
    videos = fetch_all_videos(youtube, playlist_id)
    print(f"총 {len(videos)}개 영상 발견")

    video_ids = [v["video_id"] for v in videos]
    stats = fetch_video_stats(youtube, video_ids)

    for v in videos:
        v.update(stats.get(v["video_id"], {}))

    df = pd.DataFrame(videos)
    df["published_at"] = pd.to_datetime(df["published_at"])
    df["channel_id"] = args.channel_id
    df["channel_name"] = args.channel_name

    safe_name = args.channel_name.replace(" ", "_")
    filename = f"{safe_name}_videos_{today_str()}.csv"
    save_raw(df, "s02_youtuber_hiatus", filename)
    print(f"수집 완료! 다음 단계: scripts/clean/s02_clean_youtube.py 실행")


if __name__ == "__main__":
    main()
