"""Mastodon (social media) - adapted from SearXNG."""

import logging
from urllib.parse import urlencode
from datetime import datetime

logger = logging.getLogger("scoutlet.engines.mastodon")

about = {
    "website": "https://joinmastodon.org/",
    "wikidata_id": "Q27986619",
    "official_api_documentation": "https://docs.joinmastodon.org/api/",
    "use_official_api": True,
    "require_api_key": False,
    "results": "JSON",
}

categories = ["social media"]

base_url = "https://mastodon.social"
mastodon_type = "accounts"
page_size = 40


def request(query, params):
    args = {
        "q": query,
        "resolve": "false",
        "type": mastodon_type,
        "limit": page_size,
    }
    params["url"] = f"{base_url}/api/v2/search?{urlencode(args)}"
    return params


def response(resp):
    results = []
    json_data = resp.json()

    for result in json_data.get(mastodon_type, []):
        if mastodon_type == "accounts":
            publishedDate = None
            if result.get("created_at"):
                try:
                    publishedDate = datetime.strptime(result["created_at"][:10], "%Y-%m-%d")
                except ValueError:
                    pass
            results.append({
                "url": result.get("uri", ""),
                "title": result.get("username", "") + f" ({result.get('followers_count', 0)} followers)",
                "content": result.get("note", ""),
                "thumbnail": result.get("avatar"),
                "publishedDate": publishedDate,
            })
        elif mastodon_type == "hashtags":
            uses_count = sum(int(entry.get("uses", 0)) for entry in result.get("history", []))
            user_count = sum(int(entry.get("accounts", 0)) for entry in result.get("history", []))
            results.append({
                "url": result.get("url", ""),
                "title": result.get("name", ""),
                "content": f"Hashtag has been used {uses_count} times by {user_count} different users",
            })
        else:
            raise ValueError(f"Unsupported mastodon type: {mastodon_type}")

    return results
