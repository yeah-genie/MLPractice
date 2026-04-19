"""
공통 유틸리티: API 요청, 저장, 환경변수 로드
"""
import os
import time
import requests
import pandas as pd
from datetime import datetime
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

ROOT_DIR = Path(__file__).resolve().parents[4]
RAW_DIR = ROOT_DIR / "02_instagram_data_analysis" / "data" / "raw"


def load_api_key(service: str) -> str:
    """
    .env 파일에서 API 키를 읽어옴.
    service: 'youtube', 'naver_client_id', 'naver_client_secret' 등
    """
    key = os.getenv(service.upper())
    if not key:
        raise EnvironmentError(
            f"환경변수 '{service.upper()}' 가 .env 파일에 없습니다. "
            f"프로젝트 루트의 .env 파일에 {service.upper()}=your_key_here 추가 필요."
        )
    return key


def rate_limited_get(url: str, params: dict = None, delay: float = 2.0) -> requests.Response:
    """정중한 딜레이를 포함한 GET 요청"""
    time.sleep(delay)
    response = requests.get(url, params=params, timeout=10)
    response.raise_for_status()
    return response


def save_raw(df: pd.DataFrame, series_code: str, filename: str) -> Path:
    """
    데이터프레임을 data/raw/{series_code}/ 에 저장.
    series_code 예: 's02_youtuber_hiatus'
    filename 예: 'UCxxxxxx_videos_20260419.csv'
    """
    folder = RAW_DIR / series_code
    folder.mkdir(parents=True, exist_ok=True)
    filepath = folder / filename
    df.to_csv(filepath, index=False, encoding="utf-8-sig")
    print(f"[저장완료] {filepath} ({len(df)}행)")
    return filepath


def today_str() -> str:
    return datetime.now().strftime("%Y%m%d")
