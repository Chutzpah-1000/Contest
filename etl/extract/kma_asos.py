from __future__ import annotations

from typing import TYPE_CHECKING, Final, Protocol
from urllib.parse import urlencode

import requests

from etl.paths import BRONZE_ASOS

if TYPE_CHECKING:
    from pathlib import Path

KMA_ASOS_BASE_URL: Final = "https://apis.data.go.kr/1360000/AsosDalyInfoService/getWthrDataList"
REQUEST_TIMEOUT_S: Final = 30


class HttpResponse(Protocol):
    """Minimal response interface used by the extractor."""

    content: bytes

    def raise_for_status(self) -> None:
        """Raise an HTTP error for non-success responses."""
        ...


class HttpClient(Protocol):
    """Minimal HTTP client interface used by the extractor."""

    def get(self, url: str, timeout: int) -> HttpResponse:
        """Return an HTTP response for a URL."""
        ...


def build_kma_asos_url(
    api_key: str,
    start_date: str,
    end_date: str,
    station_id: str = "108",
    page_size: int = 999,
) -> str:
    """Build a KMA ASOS daily weather API URL.

    Returns:
        Fully-qualified KMA ASOS URL.
    """
    query = urlencode(
        {
            "serviceKey": api_key,
            "pageNo": "1",
            "numOfRows": str(page_size),
            "dataType": "CSV",
            "dataCd": "ASOS",
            "dateCd": "DAY",
            "startDt": start_date,
            "endDt": end_date,
            "stnIds": station_id,
        },
    )
    return f"{KMA_ASOS_BASE_URL}?{query}"


def download_kma_asos(
    api_key: str,
    output_dir: Path,
    start_date: str,
    end_date: str,
    station_id: str = "108",
    client: HttpClient | None = None,
) -> Path:
    """Download KMA ASOS observations into a bronze CSV file.

    Returns:
        Path to the written bronze CSV file.

    Raises:
        ValueError: If the API key is empty.
    """
    if not api_key.strip():
        raise ValueError("A KMA API key is required.")

    http_client = client or requests
    output_dir.mkdir(parents=True, exist_ok=True)
    url = build_kma_asos_url(
        api_key=api_key,
        start_date=start_date,
        end_date=end_date,
        station_id=station_id,
    )
    response = http_client.get(url, timeout=REQUEST_TIMEOUT_S)
    response.raise_for_status()
    path = output_dir / BRONZE_ASOS
    path.write_bytes(response.content)
    return path
