# Copyright (c) 2020, Timothée Mazzucotelli and contributors
#
# Permission to use, copy, modify, and/or distribute this software for any
# purpose with or without fee is hereby granted, provided that the above
# copyright notice and this permission notice appear in all copies.
#
# THE SOFTWARE IS PROVIDED "AS IS" AND THE AUTHOR DISCLAIMS ALL WARRANTIES
# WITH REGARD TO THIS SOFTWARE INCLUDING ALL IMPLIED WARRANTIES OF
# MERCHANTABILITY AND FITNESS. IN NO EVENT SHALL THE AUTHOR BE LIABLE FOR
# ANY SPECIAL, DIRECT, INDIRECT, OR CONSEQUENTIAL DAMAGES OR ANY DAMAGES
# WHATSOEVER RESULTING FROM LOSS OF USE, DATA OR PROFITS, WHETHER IN AN
# ACTION OF CONTRACT, NEGLIGENCE OR OTHER TORTIOUS ACTION, ARISING OUT OF
# OR IN CONNECTION WITH THE USE OR PERFORMANCE OF THIS SOFTWARE.

from __future__ import annotations

from typing import Any

import httpx2


class _ProviderError(Exception):
    """A search provider could not complete a request."""


async def _request_json(provider: str, url: str, *, params: dict[str, str] | None = None) -> dict[str, Any]:
    """Fetch JSON without exposing credentials in errors sent to logs or chats."""
    try:
        async with httpx2.AsyncClient(timeout=15, follow_redirects=True) as client:
            # Torrentio rejects the default Python client User-Agent. Identify this bot explicitly.
            response = await client.get(
                url,
                params=params,
                headers={"Accept": "application/json", "User-Agent": "pawabot"},
            )
            response.raise_for_status()
            data = response.json()
    except httpx2.HTTPStatusError as error:
        raise _ProviderError(f"{provider} returned HTTP {error.response.status_code}.") from None
    except httpx2.RequestError:
        raise _ProviderError(f"Could not reach {provider}. Please try again later.") from None
    except ValueError:
        raise _ProviderError(f"{provider} returned invalid JSON.") from None
    if not isinstance(data, dict):
        raise _ProviderError(f"{provider} returned an unexpected response.")
    return data


def _result_list(data: dict[str, Any], key: str, provider: str) -> list[dict[str, Any]]:
    """Validate a provider's result envelope."""
    items = data.get(key)
    if not isinstance(items, list) or any(not isinstance(item, dict) for item in items):
        raise _ProviderError(f"{provider} returned an unexpected response.")
    return items
