"""GitHub code search engine - adapted from SearXNG.

Changes from SearXNG original:
- from searx.* → from scoutlet.*
- Removed res.types.Code (requires Pygments), results returned as plain dicts
- Simplified extract_code to return text content instead of Code result type
- Removed SXNG_Response type annotation
"""

import typing as t
from urllib.parse import urlencode

from scoutlet.network import raise_for_httperror

about = {
    "website": "https://github.com/",
    "wikidata_id": "Q364",
    "official_api_documentation": "https://docs.github.com/en/rest/search/search?apiVersion=2022-11-28#search-code",
    "use_official_api": True,
    "require_api_key": False,
    "results": "JSON",
}

categories = ["code", "it"]

search_url = "https://api.github.com/search/code?sort=indexed&{query}&{page}"
accept_header = "application/vnd.github.text-match+json"
paging = True

ghc_auth = {
    "type": "none",
    "token": "",
}

ghc_highlight_matching_lines = True
ghc_strip_new_lines = True
ghc_strip_whitespace = False
ghc_api_version = "2022-11-28"
ghc_insert_block_separator = False


def request(query: str, params: dict[str, t.Any]) -> None:
    params["url"] = search_url.format(
        query=urlencode({"q": query}), page=urlencode({"page": params["pageno"]})
    )
    params["headers"]["Accept"] = accept_header
    params["headers"]["X-GitHub-Api-Version"] = ghc_api_version

    if ghc_auth["type"] == "none":
        params["headers"]["Authorization"] = "placeholder"
    if ghc_auth["type"] == "personal_access_token":
        params["headers"]["Authorization"] = f"token {ghc_auth['token']}"
    if ghc_auth["type"] == "bearer":
        params["headers"]["Authorization"] = f"Bearer {ghc_auth['token']}"

    params["raise_for_httperror"] = False


def _extract_code_text(code_matches: list[dict[str, t.Any]]) -> str:
    """Extract code fragments from text_matches and return as plain text."""
    blocks: list[str] = []

    for i, match in enumerate(code_matches):
        if i > 0 and ghc_insert_block_separator:
            blocks.append("...")

        code: str = match["fragment"]

        if ghc_strip_whitespace:
            code = code.strip()
        if ghc_strip_new_lines:
            code = code.strip("\n")

        if ghc_highlight_matching_lines and match.get("matches"):
            lines = code.split("\n")
            highlight_groups = [hg["indices"] for hg in match["matches"]]
            highlighted = []
            for li, line in enumerate(lines):
                for hg in highlight_groups:
                    after, before = hg[0], hg[1]
                    if after <= li < before:
                        line = f">> {line}"
                        break
                highlighted.append(line)
            blocks.append("\n".join(highlighted))
        else:
            blocks.append(code)

    return "\n".join(blocks)


def response(resp) -> list[dict[str, t.Any]]:
    if resp.status_code == 422:
        return []
    if resp.status_code == 401:
        # GitHub code search API requires authentication
        return []

    raise_for_httperror(resp)

    results = []
    for item in resp.json().get("items", []):
        repo: dict[str, str] = item.get("repository", {})
        text_matches: list[dict[str, t.Any]] = item.get("text_matches", [])
        code_matches = [
            m
            for m in text_matches
            if m.get("object_type") == "FileContent" and m.get("property") == "content"
        ]
        code_text = _extract_code_text(code_matches)

        results.append(
            {
                "url": item.get("html_url"),
                "title": f"{repo.get('full_name', '')} · {item.get('name', '')}",
                "content": code_text or repo.get("description", ""),
            }
        )

    return results
