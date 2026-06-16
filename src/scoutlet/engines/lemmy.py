"""Lemmy (social media) - adapted from SearXNG.

Changes:
- Replaced flask_babel gettext with plain strings
- Replaced markdown_to_text with a minimal markdown stripper (no markdown dep)
"""

import logging
import re
from datetime import datetime
from urllib.parse import urlencode

logger = logging.getLogger("scoutlet.engines.lemmy")

about = {
    "website": "https://lemmy.ml/",
    "wikidata_id": "Q84777032",
    "official_api_documentation": "https://join-lemmy.org/api/",
    "use_official_api": True,
    "require_api_key": False,
    "results": "JSON",
}

paging = True
categories = ["social media"]

base_url = "https://lemmy.ml/"
lemmy_type = "Communities"


_MD_LINK_RE = re.compile(r"\[([^\]]+)\]\([^)]+\)")
_MD_BOLD_RE = re.compile(r"\*\*([^*]+)\*\*")
_MD_ITALIC_RE = re.compile(r"\*([^*]+)\*")
_MD_HEADER_RE = re.compile(r"^#+\s*", re.M)
_MD_LIST_RE = re.compile(r"^\s*[-*+]\s+", re.M)


def markdown_to_text(md: str) -> str:
    """Minimal markdown-to-text: strips links, bold, italic, headers, lists."""
    if not md:
        return ""
    s = _MD_LINK_RE.sub(r"\1", md)
    s = _MD_BOLD_RE.sub(r"\1", s)
    s = _MD_ITALIC_RE.sub(r"\1", s)
    s = _MD_HEADER_RE.sub("", s)
    s = _MD_LIST_RE.sub("", s)
    return s.strip()


def request(query, params):
    args = {"q": query, "page": params["pageno"], "type_": lemmy_type}
    params["url"] = f"{base_url}api/v3/search?{urlencode(args)}"
    return params


def _get_communities(json_data):
    results = []
    for result in json_data.get("communities", []):
        counts = result.get("counts") or {}
        community = result.get("community") or {}
        metadata = (
            f"subscribers: {counts.get('subscribers', 0)}"
            f" | posts: {counts.get('posts', 0)}"
            f" | active users: {counts.get('users_active_half_year', 0)}"
        )
        publishedDate = None
        if counts.get("published"):
            try:
                publishedDate = datetime.strptime(counts["published"][:19], "%Y-%m-%dT%H:%M:%S")
            except ValueError:
                pass
        results.append({
            "url": community.get("actor_id", ""),
            "title": community.get("title", ""),
            "content": markdown_to_text(community.get("description", "")),
            "thumbnail": community.get("icon") or community.get("banner"),
            "publishedDate": publishedDate,
            "metadata": metadata,
        })
    return results


def _get_users(json_data):
    results = []
    for result in json_data.get("users", []):
        person = result.get("person") or {}
        results.append({
            "url": person.get("actor_id", ""),
            "title": person.get("name", ""),
            "content": markdown_to_text(person.get("bio", "")),
        })
    return results


def _get_posts(json_data):
    results = []
    for result in json_data.get("posts", []):
        creator = result.get("creator") or {}
        post = result.get("post") or {}
        counts = result.get("counts") or {}
        community = result.get("community") or {}
        user = creator.get("display_name") or creator.get("name", "")

        thumbnail = None
        if post.get("thumbnail_url"):
            thumbnail = post["thumbnail_url"] + "?format=webp&thumbnail=208"

        metadata = (
            f"&#x25B2; {counts.get('upvotes', 0)} &#x25BC; {counts.get('downvotes', 0)}"
            f" | user: {user}"
            f" | comments: {counts.get('comments', 0)}"
            f" | community: {community.get('title', '')}"
        )

        body = post.get("body", "") or ""
        content = markdown_to_text(body) if body.strip() else ""

        publishedDate = None
        if post.get("published"):
            try:
                publishedDate = datetime.strptime(post["published"][:19], "%Y-%m-%dT%H:%M:%S")
            except ValueError:
                pass

        results.append({
            "url": post.get("ap_id", ""),
            "title": post.get("name", ""),
            "content": content,
            "thumbnail": thumbnail,
            "publishedDate": publishedDate,
            "metadata": metadata,
        })
    return results


def _get_comments(json_data):
    results = []
    for result in json_data.get("comments", []):
        creator = result.get("creator") or {}
        comment = result.get("comment") or {}
        counts = result.get("counts") or {}
        community = result.get("community") or {}
        post = result.get("post") or {}
        user = creator.get("display_name") or creator.get("name", "")

        metadata = (
            f"&#x25B2; {counts.get('upvotes', 0)} &#x25BC; {counts.get('downvotes', 0)}"
            f" | user: {user}"
            f" | community: {community.get('title', '')}"
        )

        publishedDate = None
        if comment.get("published"):
            try:
                publishedDate = datetime.strptime(comment["published"][:19], "%Y-%m-%dT%H:%M:%S")
            except ValueError:
                pass

        results.append({
            "url": comment.get("ap_id", ""),
            "title": post.get("name", ""),
            "content": markdown_to_text(comment.get("content", "")),
            "publishedDate": publishedDate,
            "metadata": metadata,
        })
    return results


def response(resp):
    json_data = resp.json()

    if lemmy_type == "Communities":
        return _get_communities(json_data)
    if lemmy_type == "Users":
        return _get_users(json_data)
    if lemmy_type == "Posts":
        return _get_posts(json_data)
    if lemmy_type == "Comments":
        return _get_comments(json_data)
    raise ValueError(f"Unsupported lemmy type: {lemmy_type}")
