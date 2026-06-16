"""Hacker News search (via Algolia API) - adapted from SearXNG.

Changes from SearXNG original:
- from searx.* → from scoutlet.*
- Replaced dateutil.relativedelta.relativedelta with datetime.timedelta
- Replaced flask_babel.gettext with plain strings
- Removed TYPE_CHECKING blocks and type annotations
- Return list[dict] from response()
"""

import logging
from datetime import datetime, timedelta, timezone
from urllib.parse import urlencode

logger = logging.getLogger("scoutlet.engines.hackernews")

about = {
    "website": "https://news.ycombinator.com/",
    "wikidata_id": "Q491526",
    "official_api_documentation": "https://hn.algolia.com/api",
    "use_official_api": True,
    "require_api_key": False,
    "results": "JSON",
}

categories = ["it", "news"]
paging = True

search_url = "https://hn.algolia.com/api/v1/search?{query}"

# Time range mapping to Algolia's date filters
time_range_map = {
    "day": 1,
    "week": 7,
    "month": 30,
    "year": 365,
}

time_range_support = True


def request(query, params):
    args = {
        "query": query,
        "page": params["pageno"] - 1,  # Algolia is 0-indexed
        "tags": "story",
    }

    # If a time range is specified, add a numeric filter for created_at_i
    time_range = params.get("time_range")
    if time_range and time_range in time_range_map:
        now = datetime.now(tz=timezone.utc)
        delta = timedelta(days=time_range_map[time_range])
        since = int((now - delta).timestamp())
        args["numericFilters"] = f"created_at_i>{since}"

    params["url"] = search_url.format(query=urlencode(args))
    return params


def response(resp):
    results = []
    data = resp.json()

    for hit in data.get("hits", []):
        title = hit.get("title", "")
        url = hit.get("url", "")
        content = hit.get("story_text") or hit.get("comment_text") or ""

        # If no external URL, link to the HN discussion
        if not url:
            object_id = hit.get("objectID", "")
            url = f"https://news.ycombinator.com/item?id={object_id}"

        # Published date
        publishedDate = None
        created_at = hit.get("created_at")
        if created_at:
            try:
                publishedDate = datetime.fromisoformat(created_at.replace("Z", "+00:00"))
            except (ValueError, AttributeError):
                pass

        # Build content with metadata
        metadata_parts = []
        points = hit.get("points")
        if points is not None:
            metadata_parts.append(f"{points} points")
        num_comments = hit.get("num_comments")
        if num_comments is not None:
            metadata_parts.append(f"{num_comments} comments")
        author = hit.get("author")
        if author:
            metadata_parts.append(f"by {author}")

        if content:
            # Strip HTML tags from content
            import re
            content = re.sub(r"<[^>]+>", "", content)
            if len(content) > 300:
                content = content[:300] + "..."

        if metadata_parts:
            content = " | ".join(metadata_parts) + (" -- " + content if content else "")

        results.append({
            "url": url,
            "title": title,
            "content": content,
            "publishedDate": publishedDate,
            "author": author,
            "points": points,
            "num_comments": num_comments,
        })

    return results
