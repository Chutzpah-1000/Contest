from __future__ import annotations

from dataclasses import dataclass

from etl.extract.kma_asos import build_kma_asos_url
from etl.extract.seoul_data import (
    SeoulDataset,
    build_seoul_open_data_url,
    download_seoul_datasets,
)


@dataclass(frozen=True)
class FakeResponse:
    content: bytes

    @staticmethod
    def raise_for_status() -> None:
        return None


class FakeClient:
    def __init__(self) -> None:
        self.urls: list[str] = []

    def get(self, url: str, timeout: int) -> FakeResponse:
        self.urls.append(f"{url}|timeout={timeout}")
        return FakeResponse(content=b"name,value\nsample,1\n")


def test_seoul_open_data_url_uses_required_path_order() -> None:
    url = build_seoul_open_data_url(
        api_key="sample",
        service_name="SearchParkInfoService",
        start_index=1,
        end_index=5,
    )

    assert url == "http://openapi.seoul.go.kr:8088/sample/csv/SearchParkInfoService/1/5/"


def test_download_seoul_datasets_writes_csv(tmp_path) -> None:
    client = FakeClient()
    written = download_seoul_datasets(
        api_key="sample",
        output_dir=tmp_path,
        datasets=(SeoulDataset("SearchParkInfoService", "parks.csv"),),
        client=client,
    )

    assert written["parks.csv"].read_bytes() == b"name,value\nsample,1\n"
    assert client.urls[0].startswith(
        "http://openapi.seoul.go.kr:8088/sample/csv/SearchParkInfoService/1/1000/",
    )


def test_kma_asos_url_contains_core_parameters() -> None:
    url = build_kma_asos_url(
        api_key="secret-key",
        start_date="20250501",
        end_date="20250531",
        station_id="108",
    )

    assert "serviceKey=secret-key" in url
    assert "startDt=20250501" in url
    assert "endDt=20250531" in url
    assert "stnIds=108" in url
