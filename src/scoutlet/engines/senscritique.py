"""SensCritique (movies) - adapted from SearXNG.

Changes:
- from searx.result_types.MainResult -> return plain dict
"""

import logging
from json import dumps, loads

logger = logging.getLogger("scoutlet.engines.senscritique")

about = {
    "website": "https://www.senscritique.com/",
    "wikidata_id": "Q16676060",
    "official_api_documentation": None,
    "use_official_api": False,
    "require_api_key": False,
    "results": "JSON",
    "language": "fr",
}

categories = ["movies"]
paging = True
page_size = 16
graphql_url = "https://apollo.senscritique.com/"

graphql_query = """query SearchProductExplorer($query: String, $offset: Int, $limit: Int,
                    $sortBy: SearchProductExplorerSort) {
  searchProductExplorer(
    query: $query
    filters: []
    sortBy: $sortBy
    offset: $offset
    limit: $limit
  ) {
    items {
      category
      dateRelease
      duration
      id
      originalTitle
      rating
      title
      url
      yearOfProduction
      medias {
        picture
      }
      countries {
        name
      }
      genresInfos {
        label
      }
      directors {
        name
      }
      stats {
        ratingCount
      }
    }
  }
}"""


def request(query, params):
    offset = (params["pageno"] - 1) * page_size

    data = {
        "operationName": "SearchProductExplorer",
        "variables": {"offset": offset, "limit": page_size, "query": query, "sortBy": "RELEVANCE"},
        "query": graphql_query,
    }

    params["url"] = graphql_url
    params["method"] = "POST"
    params["headers"]["Content-Type"] = "application/json"
    params["data"] = dumps(data)
    return params


def _build_content_parts(item, title, original_title):
    parts = []
    if item.get("category"):
        parts.append(item["category"])
    if original_title and original_title != title:
        parts.append(f"Original title: {original_title}")
    if item.get("directors"):
        directors = [d["name"] for d in item["directors"]]
        parts.append("Director(s): " + ", ".join(directors))
    if item.get("countries"):
        countries = [c["name"] for c in item["countries"]]
        parts.append("Country: " + ", ".join(countries))
    if item.get("genresInfos"):
        genres = [g["label"] for g in item["genresInfos"]]
        parts.append("Genre(s): " + ", ".join(genres))
    if item.get("duration"):
        minutes = item["duration"] // 60
        if minutes > 0:
            parts.append(f"Duration: {minutes} min")
    if item.get("rating") and (item.get("stats") or {}).get("ratingCount"):
        parts.append(f"Rating: {item['rating']}/10 ({item['stats']['ratingCount']} votes)")
    return parts


def _parse_item(item):
    title = item.get("title", "")
    if not title:
        return None
    year = item.get("yearOfProduction")
    original_title = item.get("originalTitle")

    thumbnail = ""
    medias = item.get("medias") or {}
    if medias.get("picture"):
        thumbnail = medias["picture"]

    content_parts = _build_content_parts(item, title, original_title)
    url = f"https://www.senscritique.com{item.get('url', '')}"

    return {
        "url": url,
        "title": title + (f" ({year})" if year else ""),
        "content": " | ".join(content_parts),
        "thumbnail": thumbnail,
    }


def response(resp):
    results = []
    response_data = loads(resp.text)

    items = (response_data.get("data") or {}).get("searchProductExplorer", {}).get("items", [])
    if not items:
        return results

    for item in items:
        result = _parse_item(item)
        if result:
            results.append(result)

    return results
