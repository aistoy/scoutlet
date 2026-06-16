"""IMDB (movies) - adapted from SearXNG."""

import logging
import json

logger = logging.getLogger("scoutlet.engines.imdb")

about = {
    "website": "https://imdb.com/",
    "wikidata_id": "Q37312",
    "official_api_documentation": None,
    "use_official_api": False,
    "require_api_key": False,
    "results": "HTML",
}

categories = ["movies"]
paging = False

suggestion_url = "https://v2.sg.media-imdb.com/suggestion/{letter}/{query}.json"
href_base = "https://imdb.com/{category}/{entry_id}"
search_categories = {"nm": "name", "tt": "title", "kw": "keyword", "co": "company", "ep": "episode"}


def request(query, params):
    query = query.replace(" ", "_").lower()
    params["url"] = suggestion_url.format(letter=query[0] if query else "_", query=query)
    return params


def response(resp):
    suggestions = json.loads(resp.text)
    results = []

    for entry in suggestions.get("d", []):
        entry_id = entry.get("id", "")
        categ = search_categories.get(entry_id[:2])
        if categ is None:
            logger.error("skip unknown category tag %s in %s", entry_id[:2], entry_id)
            continue

        title = entry.get("l", "")
        if "q" in entry:
            title += " (%s)" % entry["q"]

        content = ""
        if "rank" in entry:
            content += "(%s) " % entry["rank"]
        if "y" in entry:
            content += str(entry["y"]) + " - "
        if "s" in entry:
            content += str(entry["s"])

        image_url = (entry.get("i") or {}).get("imageUrl")
        if image_url:
            image_url_name, image_url_prefix = image_url.rsplit(".", 1)
            magic = "QL75_UX280_CR0,0,280,414_"
            if not image_url_name.endswith("_V1_"):
                magic = "_V1_" + magic
            image_url = image_url_name + magic + "." + image_url_prefix

        results.append({
            "title": title,
            "url": href_base.format(category=categ, entry_id=entry_id),
            "content": content,
            "thumbnail": image_url,
        })

    return results
