"""Radio Browser (music/radio) - adapted from SearXNG.

Changes:
- Removed EngineCache; server list cached in module-global with 24h expiry
- Removed fetch_traits + babel locale mapping (no language/country filtering)
"""

import logging
import random
import socket
import time
from urllib.parse import urlencode

logger = logging.getLogger("scoutlet.engines.radio_browser")

about = {
    "website": "https://www.radio-browser.info/",
    "wikidata_id": "Q111664849",
    "official_api_documentation": "https://de1.api.radio-browser.info/",
    "use_official_api": True,
    "require_api_key": False,
    "results": "JSON",
}

paging = True
categories = ["music", "radio"]

number_of_results = 10

# Module-global server list cache (no persistence)
_servers_cache: dict = {"servers": [], "expires": 0.0}


def server_list():
    now = time.time()
    if _servers_cache["servers"] and _servers_cache["expires"] > now:
        return _servers_cache["servers"]

    servers = []
    try:
        ips = socket.getaddrinfo("all.api.radio-browser.info", 80, 0, 0, socket.IPPROTO_TCP)
        for ip_tuple in ips:
            ip = ip_tuple[4][0]
            try:
                hostname = socket.gethostbyaddr(ip)[0]
            except socket.herror:
                continue
            srv = "https://" + hostname
            if srv not in servers:
                servers.append(srv)
    except socket.gaierror:
        logger.exception("Failed to resolve radio-browser servers")

    _servers_cache["servers"] = servers
    _servers_cache["expires"] = now + 60 * 60 * 24
    return servers


def request(query, params):
    servers = server_list()
    if not servers:
        logger.error("Fetched server list is empty!")
        params["url"] = None
        return None

    server = random.choice(servers)

    args = {
        "name": query,
        "order": "votes",
        "offset": (params["pageno"] - 1) * number_of_results,
        "limit": number_of_results,
        "hidebroken": "true",
        "reverse": "true",
    }

    params["url"] = f"{server}/json/stations/search?{urlencode(args)}"
    return params


def response(resp):
    results = []
    json_resp = resp.json()

    for result in json_resp:
        url = result.get("homepage") or ""
        if not url:
            url = result.get("url_resolved", "")

        content = []
        tags = ", ".join((result.get("tags") or "").split(","))
        if tags:
            content.append(tags)
        for x in ["state", "country"]:
            v = result.get(x)
            if v:
                content.append(str(v).strip())

        metadata = []
        codec = result.get("codec")
        if codec and codec.lower() != "unknown":
            metadata.append(f"{codec} radio")
        for label, key in [("bitrate", "bitrate"), ("votes", "votes"), ("clicks", "clickcount")]:
            v = result.get(key)
            if v:
                metadata.append(f"{label} {v}")

        results.append({
            "url": url,
            "title": result.get("name", ""),
            "thumbnail": (result.get("favicon") or "").replace("http://", "https://"),
            "content": " | ".join(content),
            "metadata": " | ".join(metadata),
            "iframe_src": (result.get("url_resolved") or "").replace("http://", "https://"),
        })

    return results
