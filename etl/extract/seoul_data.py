from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Final, Protocol

import requests

from etl.paths import (
    BRONZE_BUILDINGS,
    BRONZE_GROUNDWATER,
    BRONZE_PARKS,
    BRONZE_ROADS,
)

if TYPE_CHECKING:
    from collections.abc import Mapping
    from pathlib import Path

SEOUL_API_BASE_URL: Final = "http://openapi.seoul.go.kr:8088"
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


@dataclass(frozen=True)
class SeoulDataset:
    """A Seoul Open Data API dataset binding."""

    service_name: str
    filename: str


DEFAULT_SEOUL_DATASETS: Final[tuple[SeoulDataset, ...]] = (
    SeoulDataset("SearchGroundWaterOutflowInfo", BRONZE_GROUNDWATER),
    SeoulDataset("SearchParkInfoService", BRONZE_PARKS),
    SeoulDataset("SearchRoadFacilityInfo", BRONZE_ROADS),
    SeoulDataset("SearchBuildingRegisterInfo", BRONZE_BUILDINGS),
)


def build_seoul_open_data_url(
    api_key: str,
    service_name: str,
    start_index: int = 1,
    end_index: int = 1000,
    result_type: str = "csv",
) -> str:
    """Build a Seoul Open Data API URL.

    Seoul Open Data uses a fixed path format:
    /{key}/{type}/{service}/{start}/{end}/.

    Returns:
        Fully-qualified Seoul Open Data API URL.
    """
    safe_key = api_key.strip()
    safe_service = service_name.strip()
    return (
        f"{SEOUL_API_BASE_URL}/{safe_key}/{result_type}/{safe_service}/{start_index}/{end_index}/"
    )


def download_seoul_datasets(
    api_key: str,
    output_dir: Path,
    datasets: tuple[SeoulDataset, ...] = DEFAULT_SEOUL_DATASETS,
    client: HttpClient | None = None,
) -> Mapping[str, Path]:
    """Download configured Seoul datasets into bronze CSV files.

    Returns:
        Mapping from bronze filename to written path.

    Raises:
        ValueError: If the API key is empty.
    """
    if not api_key.strip():
        raise ValueError("A Seoul Open Data API key is required.")

    http_client = client or requests
    output_dir.mkdir(parents=True, exist_ok=True)
    written: dict[str, Path] = {}
    for dataset in datasets:
        url = build_seoul_open_data_url(api_key=api_key, service_name=dataset.service_name)
        response = http_client.get(url, timeout=REQUEST_TIMEOUT_S)
        response.raise_for_status()
        path = output_dir / dataset.filename
        path.write_bytes(response.content)
        written[dataset.filename] = path
    return written
