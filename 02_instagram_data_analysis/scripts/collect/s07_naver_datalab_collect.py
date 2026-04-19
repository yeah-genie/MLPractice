"""
S07 검색고고학 — 네이버 데이터랩 검색어 트렌드 수집
사용법: python s07_naver_datalab_collect.py --keywords 다이어트 운동 --start 2020-01-01 --end 2024-12-31
필요 환경변수: NAVER_CLIENT_ID, NAVER_CLIENT_SECRET
네이버 개발자센터(developers.naver.com)에서 '검색어트렌드 API' 등록 후 발급
"""
import argparse
import json
import pandas as pd
import requests
from utils.api_helpers import load_api_key, save_raw, today_str

DATALAB_URL = "https://openapi.naver.com/v1/datalab/search"


def fetch_trend(client_id: str, client_secret: str, keywords: list[str], start: str, end: str) -> pd.DataFrame:
    """
    keywords: 비교할 검색어 목록 (최대 5개 그룹)
    start/end: 'YYYY-MM-DD' 형식
    """
    keyword_groups = [{"groupName": kw, "keywords": [kw]} for kw in keywords]

    body = {
        "startDate": start,
        "endDate": end,
        "timeUnit": "week",
        "keywordGroups": keyword_groups,
        "device": "",
        "ages": [],
        "gender": "",
    }

    headers = {
        "X-Naver-Client-Id": client_id,
        "X-Naver-Client-Secret": client_secret,
        "Content-Type": "application/json",
    }

    response = requests.post(DATALAB_URL, headers=headers, data=json.dumps(body), timeout=10)
    response.raise_for_status()
    data = response.json()

    rows = []
    for result in data["results"]:
        keyword = result["title"]
        for point in result["data"]:
            rows.append({
                "keyword": keyword,
                "period": point["period"],
                "ratio": point["ratio"],
            })

    return pd.DataFrame(rows)


def main():
    parser = argparse.ArgumentParser(description="네이버 데이터랩 검색어 트렌드 수집")
    parser.add_argument("--keywords", nargs="+", required=True, help="비교할 검색어 목록 (최대 5개)")
    parser.add_argument("--start", default="2020-01-01", help="시작일 YYYY-MM-DD")
    parser.add_argument("--end", default="2024-12-31", help="종료일 YYYY-MM-DD")
    args = parser.parse_args()

    if len(args.keywords) > 5:
        print("경고: 네이버 데이터랩은 한 번에 최대 5개 키워드만 비교 가능합니다. 처음 5개만 사용합니다.")
        args.keywords = args.keywords[:5]

    client_id = load_api_key("naver_client_id")
    client_secret = load_api_key("naver_client_secret")

    print(f"키워드 {args.keywords} 트렌드 수집 중... ({args.start} ~ {args.end})")
    df = fetch_trend(client_id, client_secret, args.keywords, args.start, args.end)
    print(f"총 {len(df)}행 수집 완료")

    keyword_tag = "_".join(args.keywords[:2])
    filename = f"{keyword_tag}_trend_{today_str()}.csv"
    save_raw(df, "s07_search_archaeology", filename)
    print("다음 단계: scripts/clean/s07_clean_naver.py 실행")


if __name__ == "__main__":
    main()
