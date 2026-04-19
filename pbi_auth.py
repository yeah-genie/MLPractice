"""
Power BI 액세스 토큰 발급 + Claude Code MCP 연결용 환경변수 설정
=================================================================
Claude Code 에서 Power BI MCP 서버를 쓰려면 토큰이 필요합니다.

사용법:
  # 1. 토큰 발급 후 환경변수에 주입하면서 Claude Code 실행
  source <(python pbi_auth.py)
  claude

  # 또는 토큰만 확인
  python pbi_auth.py --print

첫 실행 시 브라우저에서 Microsoft 로그인 1회 필요.
이후엔 캐시에서 자동 갱신.
"""
import argparse
import os
from pathlib import Path

import msal
from dotenv import load_dotenv

load_dotenv()

CLIENT_ID  = os.getenv("POWERBI_CLIENT_ID")
AUTHORITY  = "https://login.microsoftonline.com/common"
SCOPES     = ["https://analysis.windows.net/powerbi/api/Dataset.ReadWrite.All"]
CACHE_FILE = ".pbi_token_cache.json"


def get_token() -> str:
    if not CLIENT_ID:
        raise EnvironmentError(
            ".env 에 POWERBI_CLIENT_ID 가 없습니다.\n"
            "powerbi_push.py 상단의 '앱 등록 방법' 을 참고하세요."
        )

    cache = msal.SerializableTokenCache()
    if Path(CACHE_FILE).exists():
        cache.deserialize(Path(CACHE_FILE).read_text())

    app = msal.PublicClientApplication(CLIENT_ID, authority=AUTHORITY, token_cache=cache)

    accounts = app.get_accounts()
    result   = None
    if accounts:
        result = app.acquire_token_silent(SCOPES, account=accounts[0])

    if not result:
        flow = app.initiate_device_flow(scopes=SCOPES)
        print(flow["message"], flush=True)
        result = app.acquire_token_by_device_flow(flow)

    if cache.has_state_changed:
        Path(CACHE_FILE).write_text(cache.serialize())

    if "access_token" not in result:
        raise RuntimeError(f"인증 실패: {result.get('error_description')}")

    return result["access_token"]


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--print", action="store_true", help="토큰만 출력")
    args = parser.parse_args()

    token = get_token()

    if args.print:
        print(token)
    else:
        # source <(python pbi_auth.py) 로 실행하면 쉘 환경변수로 주입됨
        print(f"export POWERBI_ACCESS_TOKEN={token}")
