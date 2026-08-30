"""Consistent collection of complete ESI list resources."""

from __future__ import annotations

from collections.abc import Mapping

from eve_dolphin.esi.client import EveEsiClient
from eve_dolphin.esi.errors import EsiProtocolError
from eve_dolphin.esi.models import EsiResponse

MAX_PAGES = 1000


class EsiPaginator:
    def __init__(self, client: EveEsiClient) -> None:
        self._client = client

    def get_list(
        self,
        path: str,
        *,
        access_token: str,
        character_id: int,
        params: Mapping[str, str | int | bool] | None = None,
    ) -> tuple[tuple[object, ...], str | None]:
        base_params = dict(params or {})
        if "page" in base_params:
            raise ValueError("page is managed by EsiPaginator")
        first = self._client.get_json(
            path,
            params={**base_params, "page": 1},
            access_token=access_token,
            character_id=character_id,
        )
        total_pages = first.pages or 1
        if total_pages > MAX_PAGES:
            raise EsiProtocolError("ESI resource exceeds the page safety limit")
        records = list(_list_payload(first))
        expected_last_modified = first.last_modified
        for page in range(2, total_pages + 1):
            response = self._client.get_json(
                path,
                params={**base_params, "page": page},
                access_token=access_token,
                character_id=character_id,
            )
            if response.pages is not None and response.pages != total_pages:
                raise EsiProtocolError("ESI page count changed during synchronization")
            if response.last_modified != expected_last_modified:
                raise EsiProtocolError("ESI pages have inconsistent Last-Modified values")
            records.extend(_list_payload(response))
        return tuple(records), expected_last_modified


def _list_payload(response: EsiResponse) -> list[object]:
    if not isinstance(response.payload, list):
        raise EsiProtocolError("ESI paginated resource is not a list")
    return response.payload
