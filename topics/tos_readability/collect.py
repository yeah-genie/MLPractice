"""
이용약관 텍스트 수집
====================
주요 앱 10개의 이용약관 페이지를 크롤링해서 텍스트를 저장합니다.

실행: python topics/tos_readability/collect.py
결과: data/raw/tos_readability/{앱명}.txt
"""
import time
from pathlib import Path

import requests
from bs4 import BeautifulSoup

RAW_DIR = Path("data/raw/tos_readability")
RAW_DIR.mkdir(parents=True, exist_ok=True)

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "ko-KR,ko;q=0.9",
}

# 앱명: (URL, 텍스트 추출 셀렉터)
# 셀렉터가 None이면 <body> 전체 텍스트 사용
#
# ⚠ JS 렌더링 앱 주의: 유튜브·인스타그램·틱톡은 React/SPA라 requests+BS4로는
#   빈 HTML만 반환될 수 있습니다. 실패 시 브라우저에서 직접 텍스트 복사 후
#   data/raw/tos_readability/{앱명}.txt 로 저장하세요.
TARGETS = {
    "카카오": (
        "https://www.kakao.com/policy/terms",
        "div.policy_content",
    ),
    "네이버": (
        "https://www.naver.com/policy/service",
        "div#content",
    ),
    "쿠팡": (
        "https://www.coupang.com/np/landing/terms-and-conditions",
        None,
    ),
    "배달의민족": (
        "https://policy.baemin.com/terms-of-service/kr/baemin-user/",  # ToS (개인정보처리방침 아님)
        "div.terms-content",
    ),
    "당근마켓": (
        "https://policy.daangn.com/terms-of-service/",
        "main",
    ),
    "토스": (
        "https://toss.im/legal/terms-of-service",
        None,
    ),
    "유튜브": (  # JS 렌더링 — 실패 시 수동 수집 필요
        "https://www.youtube.com/t/terms?hl=ko",
        "div.ytd-section-list-renderer",
    ),
    "인스타그램": (  # JS 렌더링 — 실패 시 수동 수집 필요
        "https://help.instagram.com/581066165581870",
        "div._4b-8",
    ),
    "틱톡": (  # JS 렌더링 — 실패 시 수동 수집 필요
        "https://www.tiktok.com/legal/page/row/terms-of-service/ko-KR",
        None,
    ),
    "라인": (
        "https://terms.line.me/line_terms?lang=ko",
        "div#wrapper",
    ),
}


def fetch_text(app: str, url: str, selector: str | None) -> str | None:
    try:
        resp = requests.get(url, headers=HEADERS, timeout=15)
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, "html.parser")

        if selector:
            el = soup.select_one(selector)
            if el:
                return el.get_text(separator="\n", strip=True)
            # 셀렉터 실패 시 body 전체로 폴백
            print(f"  ⚠ [{app}] 셀렉터 미일치, body 전체 사용")

        body = soup.find("body")
        return body.get_text(separator="\n", strip=True) if body else None

    except requests.RequestException as e:
        print(f"  ✗ [{app}] 요청 실패: {e}")
        return None


def main():
    print("이용약관 텍스트 수집 시작")
    print("─" * 50)

    results = {}
    for app, (url, selector) in TARGETS.items():
        print(f"[{app}] 수집 중...", end=" ", flush=True)
        text = fetch_text(app, url, selector)

        if text and len(text) > 500:
            out = RAW_DIR / f"{app}.txt"
            out.write_text(text, encoding="utf-8")
            char_count = len(text.replace(" ", "").replace("\n", ""))
            print(f"완료 ({char_count:,}자)")
            results[app] = char_count
        else:
            print("실패 또는 텍스트 부족 (수동 수집 필요)")

        time.sleep(1.5)  # 서버 부담 최소화

    print("\n─" * 50)
    print(f"수집 완료: {len(results)}/{len(TARGETS)}개")
    print(f"저장 위치: {RAW_DIR.resolve()}")

    if len(results) < len(TARGETS):
        failed = [a for a in TARGETS if a not in results]
        print(f"\n수동 수집 필요: {', '.join(failed)}")
        print("→ 해당 앱 이용약관 페이지에서 텍스트 복사 후 data/raw/tos_readability/{앱명}.txt 로 저장")


if __name__ == "__main__":
    main()
