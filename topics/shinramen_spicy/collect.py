"""
신라면 맵기 인플레이션 분석 — 네이버 블로그 리뷰 수집
=====================================================
"배달앱에서 '신라면 맵기'를 선택했는데, 진짜 신라면만큼 맵다고 느꼈을까?"

실행: python topics/shinramen_spicy/collect.py
결과: data/raw/shinramen/{브랜드명}_reviews.csv

필요 환경변수 (.env):
  NAVER_CLIENT_ID     = 네이버 개발자센터 클라이언트 ID
  NAVER_CLIENT_SECRET = 네이버 개발자센터 클라이언트 시크릿

네이버 API 발급 (무료, 5분):
  1. https://developers.naver.com 접속
  2. Application 등록 → '검색' API 선택
  3. 발급된 Client ID / Secret 을 .env 에 저장
"""
import os
import re
import time
import html
from pathlib import Path

import requests
import pandas as pd
from dotenv import load_dotenv

load_dotenv()

NAVER_BLOG_URL = "https://openapi.naver.com/v1/search/blog"
RAW_DIR = Path("data/raw/shinramen")

# ──────────────────────────────────────────────────────────
# 브랜드별 검색 쿼리
# 각 브랜드 + "신라면 맵기" 로 검색해 브랜드별 비교가 가능하도록 구성
# ──────────────────────────────────────────────────────────
BRAND_QUERIES = [
    ("죠스떡볶이",   "죠스떡볶이 신라면 맵기"),
    ("엽기떡볶이",   "엽기떡볶이 신라면 맵기"),
    ("신전떡볶이",   "신전떡볶이 신라면 맵기"),
    ("국대떡볶이",   "국대떡볶이 신라면 맵기"),
    ("마라탕",       "마라탕 신라면 맵기"),
    ("마라샹궈",     "마라샹궈 신라면 맵기"),
    ("불닭볶음면",   "불닭볶음면 신라면 맵기"),
    ("핵불닭",       "핵불닭 신라면 맵기"),
    ("치킨",         "매운치킨 신라면 맵기"),
    ("일반떡볶이",   "떡볶이 신라면 맵기 솔직"),
    ("배달일반",     "배달 신라면 맵기 솔직 후기"),
]


def get_headers() -> dict:
    client_id     = os.getenv("NAVER_CLIENT_ID")
    client_secret = os.getenv("NAVER_CLIENT_SECRET")
    if not client_id or not client_secret:
        raise EnvironmentError(
            ".env 에 NAVER_CLIENT_ID 와 NAVER_CLIENT_SECRET 이 필요합니다.\n"
            "발급: https://developers.naver.com → Application 등록 → 검색 API"
        )
    return {
        "X-Naver-Client-Id":     client_id,
        "X-Naver-Client-Secret": client_secret,
    }


def clean_html(text: str) -> str:
    """HTML 태그 제거 + 엔티티 디코딩"""
    text = re.sub(r"<[^>]+>", " ", text)   # <b>, </b> 등 태그 제거
    text = html.unescape(text)              # &amp; &lt; 등 디코딩
    text = re.sub(r"\s+", " ", text).strip()
    return text


def search_blog(headers: dict, query: str, display: int = 100) -> list[dict]:
    """
    네이버 블로그 검색 API 호출.
    한 번에 최대 100건, 관련도순(sim)으로 정렬.
    """
    params = {
        "query":   query,
        "display": display,
        "sort":    "sim",   # 관련도순 (date 로 바꾸면 최신순)
    }
    resp = requests.get(NAVER_BLOG_URL, headers=headers, params=params, timeout=10)
    resp.raise_for_status()
    return resp.json().get("items", [])


def main():
    headers = get_headers()
    RAW_DIR.mkdir(parents=True, exist_ok=True)

    print("=" * 60)
    print("  신라면 맵기 인플레이션 — 블로그 리뷰 수집")
    print("=" * 60)

    total_collected = 0

    for brand, query in BRAND_QUERIES:
        print(f"\n[{brand}] 검색 중: '{query}'")
        try:
            items = search_blog(headers, query)
        except Exception as e:
            print(f"  오류: {e}")
            continue

        rows = []
        for item in items:
            title       = clean_html(item.get("title", ""))
            description = clean_html(item.get("description", ""))
            full_text   = f"{title} {description}"

            # 신라면 맵기 관련 내용이 실제로 포함된 글만 저장
            if "신라면" not in full_text and "맵기" not in full_text:
                continue

            rows.append({
                "brand":       brand,
                "query":       query,
                "title":       title,
                "description": description,
                "full_text":   full_text,
                "link":        item.get("link", ""),
                "blog_name":   item.get("bloggername", ""),
                "post_date":   item.get("postdate", ""),   # YYYYMMDD
            })

        df = pd.DataFrame(rows)
        out = RAW_DIR / f"{brand}_reviews.csv"
        df.to_csv(out, index=False, encoding="utf-8-sig")
        print(f"  → {len(df)}건 저장 (필터 후): {out}")
        total_collected += len(df)

        time.sleep(0.3)   # API 호출 간격

    print(f"\n수집 완료: 총 {total_collected}건")
    print("다음 단계: python topics/shinramen_spicy/analyze.py")


if __name__ == "__main__":
    main()
