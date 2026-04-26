"""
Power BI 자동 데이터 푸시
========================
data/cleaned/ 의 CSV를 Power BI Service 데이터셋에 자동으로 올려줍니다.

실행: python powerbi_push.py

첫 실행 시:
  브라우저가 열리면서 Microsoft 로그인 요청 → 1회만 인증하면
  이후엔 토큰 캐시(.pbi_token_cache.json)를 재사용합니다.

필요 사항:
  1. Power BI 계정 (무료도 개인 워크스페이스는 가능)
  2. .env 에 POWERBI_CLIENT_ID 추가 (아래 '앱 등록 방법' 참고)

앱 등록 방법 (5분):
  1. https://portal.azure.com 접속 → Microsoft Entra ID → 앱 등록 → 새 등록
  2. 이름: MLPractice-PowerBI   /   지원 계정: 모든 Microsoft 계정
  3. 등록 후 나오는 '애플리케이션(클라이언트) ID' 를 .env 에 저장
  4. 왼쪽 메뉴 → 인증 → 플랫폼 추가 → 모바일 및 데스크톱 앱 선택
       리디렉션 URI: https://login.microsoftonline.com/common/oauth2/nativeclient  체크
  5. 왼쪽 메뉴 → API 사용 권한 → 권한 추가 → Power BI Service
       위임된 권한: Dataset.ReadWrite.All  추가
"""
import json
import os
from pathlib import Path

import msal
import pandas as pd
import requests
from dotenv import load_dotenv

load_dotenv()

# ── 설정 ────────────────────────────────────────────────────────────────────
CLIENT_ID   = os.getenv("POWERBI_CLIENT_ID")
AUTHORITY   = "https://login.microsoftonline.com/common"
SCOPES      = ["https://analysis.windows.net/powerbi/api/Dataset.ReadWrite.All"]
PBI_BASE    = "https://api.powerbi.com/v1.0/myorg"
CACHE_FILE  = ".pbi_token_cache.json"

CLEAN_DIR   = Path("data/cleaned")

# ── 업로드할 데이터셋 정의 ────────────────────────────────────────────────────
# {데이터셋 이름: [CSV 파일 경로, ...]}
DATASETS = {
    "유튜버 히아투스 레이더": [
        CLEAN_DIR / "장삐쭈_videos.csv",
    ],
    "신라면 맵기 분석": [
        CLEAN_DIR / "shinramen" / "brand_summary.csv",
        CLEAN_DIR / "shinramen" / "reviews_classified.csv",
    ],
    "이용약관 가독성 분석": [
        CLEAN_DIR / "tos_readability" / "tos_analysis.csv",
    ],
}

# pandas dtype → Power BI dataType 변환표
DTYPE_MAP = {
    "object":          "string",
    "string":          "string",
    "int64":           "Int64",
    "int32":           "Int64",
    "float64":         "Double",
    "float32":         "Double",
    "bool":            "Boolean",
    "datetime64[ns]":  "DateTime",
    "datetime64[ns, UTC]": "DateTime",
    "period[M]":       "string",
    "category":        "string",
}


# ── 인증 ─────────────────────────────────────────────────────────────────────

def get_access_token() -> str:
    if not CLIENT_ID:
        raise EnvironmentError(
            ".env 에 POWERBI_CLIENT_ID 가 없습니다.\n"
            "앱 등록 방법은 이 파일 상단 주석을 확인하세요."
        )

    cache = msal.SerializableTokenCache()
    if Path(CACHE_FILE).exists():
        cache.deserialize(Path(CACHE_FILE).read_text())

    app = msal.PublicClientApplication(
        CLIENT_ID,
        authority=AUTHORITY,
        token_cache=cache,
    )

    # 1. 캐시된 토큰 먼저 시도
    accounts = app.get_accounts()
    result = None
    if accounts:
        result = app.acquire_token_silent(SCOPES, account=accounts[0])

    # 2. 캐시 없으면 디바이스 코드 인증 (브라우저 열림)
    if not result:
        flow = app.initiate_device_flow(scopes=SCOPES)
        print("\n" + "=" * 55)
        print(flow["message"])   # "브라우저에서 URL 열고 코드를 입력하세요" 안내
        print("=" * 55 + "\n")
        result = app.acquire_token_by_device_flow(flow)

    if cache.has_state_changed:
        Path(CACHE_FILE).write_text(cache.serialize())

    if "access_token" not in result:
        raise RuntimeError(f"인증 실패: {result.get('error_description', '알 수 없는 오류')}")

    return result["access_token"]


# ── Power BI REST API ─────────────────────────────────────────────────────────

def pbi_headers(token: str) -> dict:
    return {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}


def list_datasets(token: str) -> dict:
    """기존 데이터셋 목록 반환 {이름: id}"""
    res = requests.get(f"{PBI_BASE}/datasets", headers=pbi_headers(token))
    res.raise_for_status()
    return {d["name"]: d["id"] for d in res.json().get("value", [])}


def df_to_pbi_columns(df: pd.DataFrame) -> list[dict]:
    """DataFrame 컬럼 → Power BI 스키마 컬럼 정의"""
    cols = []
    for col in df.columns:
        dtype_str = str(df[col].dtype)
        pbi_type  = DTYPE_MAP.get(dtype_str, "string")
        cols.append({"name": col, "dataType": pbi_type})
    return cols


def create_dataset(token: str, name: str, tables: list[dict]) -> str:
    """Push 데이터셋 생성 후 dataset_id 반환"""
    body = {
        "name":        name,
        "defaultMode": "Push",
        "tables":      tables,
    }
    res = requests.post(
        f"{PBI_BASE}/datasets",
        headers=pbi_headers(token),
        data=json.dumps(body),
    )
    if res.status_code not in (200, 201):
        raise RuntimeError(f"데이터셋 생성 실패 [{res.status_code}]: {res.text}")
    return res.json()["id"]


def clear_table(token: str, dataset_id: str, table_name: str) -> None:
    """기존 행 전부 삭제 (덮어쓰기 전 초기화)"""
    requests.delete(
        f"{PBI_BASE}/datasets/{dataset_id}/tables/{table_name}/rows",
        headers=pbi_headers(token),
    )


def push_rows(token: str, dataset_id: str, table_name: str, df: pd.DataFrame) -> None:
    """DataFrame 행을 100개씩 나눠서 Push"""
    # datetime 컬럼을 ISO 문자열로 변환
    df = df.copy()
    for col in df.select_dtypes(include=["datetime64[ns, UTC]", "datetime64[ns]"]).columns:
        df[col] = df[col].astype(str)

    rows = df.where(pd.notna(df), None).to_dict(orient="records")

    for i in range(0, len(rows), 100):
        batch = rows[i : i + 100]
        res = requests.post(
            f"{PBI_BASE}/datasets/{dataset_id}/tables/{table_name}/rows",
            headers=pbi_headers(token),
            data=json.dumps({"rows": batch}),
        )
        if res.status_code not in (200, 201):
            print(f"  ⚠ 배치 {i//100 + 1} 업로드 실패 [{res.status_code}]: {res.text[:200]}")


# ── 메인 ─────────────────────────────────────────────────────────────────────

def main():
    print("Power BI 데이터 업로드 시작")
    print("─" * 50)

    token       = get_access_token()
    existing    = list_datasets(token)

    for dataset_name, csv_paths in DATASETS.items():
        # 실제로 존재하는 CSV만 대상으로
        available = [p for p in csv_paths if Path(p).exists()]
        if not available:
            print(f"\n[{dataset_name}] 건너뜀 — CSV 없음 (collect/analyze 먼저 실행)")
            continue

        print(f"\n[{dataset_name}]")

        # 테이블 스키마 구성
        tables = []
        dfs    = {}
        for path in available:
            df         = pd.read_csv(path, encoding="utf-8-sig")
            table_name = Path(path).stem   # 파일명 = 테이블명
            tables.append({
                "name":    table_name,
                "columns": df_to_pbi_columns(df),
            })
            dfs[table_name] = df

        # 데이터셋 생성 또는 기존 것 재사용
        if dataset_name in existing:
            dataset_id = existing[dataset_name]
            print(f"  기존 데이터셋 재사용: {dataset_id}")
        else:
            dataset_id = create_dataset(token, dataset_name, tables)
            print(f"  새 데이터셋 생성: {dataset_id}")

        # 각 테이블 행 업로드
        for table_name, df in dfs.items():
            clear_table(token, dataset_id, table_name)
            push_rows(token, dataset_id, table_name, df)
            print(f"  ✓ {table_name}: {len(df)}행 업로드 완료")

        print(f"  → Power BI Service에서 확인: https://app.powerbi.com")

    print("\n모든 업로드 완료!")
    print("Power BI Desktop: 홈 → 데이터 가져오기 → Power BI 데이터셋 → 위 데이터셋 선택")


if __name__ == "__main__":
    main()
