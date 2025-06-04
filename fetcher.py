# fetcher.py

import requests
from config import API_BASE

def _extract_id(raw_id):
    """
    Turn a Mongo‐style ObjectId dict into its string, or else just str(raw_id).
    """
    if isinstance(raw_id, dict):
        for key in ("$oid", "id", "value"):
            if key in raw_id:
                return raw_id[key]
        return str(raw_id)
    return raw_id

def _normalize_list_of_lists(raw):
    """
    Turn [[id,name,poster,...], …] into
    [ {"id":id, "name":name, "poster":poster}, … ]
    """
    out = []
    for item in raw:
        if isinstance(item, list):
            id_, name, *rest = item
            out.append({
                "id":     _extract_id(id_),
                "name":   name,
                "poster": rest[0] if rest else ""
            })
        elif isinstance(item, dict):
            # if id is nested, extract it
            item["id"] = _extract_id(item.get("id"))
            out.append(item)
    return out

def search_anime(query: str, page: int = 1):
    resp = requests.get(f"{API_BASE}/search", params={"q": query, "page": page})
    resp.raise_for_status()
    data = resp.json().get("data", [])
    # if it’s a dict mapping, take its values
    raw = list(data.values()) if isinstance(data, dict) else data
    return _normalize_list_of_lists(raw)

def fetch_episodes(anime_id: str):
    resp = requests.get(f"{API_BASE}/anime/{anime_id}/episodes")
    resp.raise_for_status()
    data = resp.json().get("data", [])
    episodes = []

    # Case A: API returns a list of lists like [[raw_id, number, title, …], …]
    if isinstance(data, list) and data and isinstance(data[0], list):
        for item in data:
            raw_id, number, title, *_ = item
            episodes.append({
                "episodeId": _extract_id(raw_id),
                "number":    number,
                "title":     title
            })

    # Case B: API returns a list of dicts, e.g. [{"episodeId":…, "number":…, "title":…}, …]
    elif isinstance(data, list) and data and isinstance(data[0], dict):
        for ep in data:
            ep_id = _extract_id(ep.get("episodeId") or ep.get("id"))
            episodes.append({
                "episodeId": ep_id,
                "number":    ep.get("number"),
                "title":     ep.get("title")
            })

    # Case C: API returns a list of raw strings (IDs)
    elif isinstance(data, list):
        for raw in data:
            if isinstance(raw, str):
                episodes.append({
                    "episodeId": _extract_id(raw),
                    "number":    None,
                    "title":     ""
                })

    return episodes

def fetch_sources_and_referer(episode_id: str):
    resp = requests.get(f"{API_BASE}/episode/{episode_id}/sources")
    resp.raise_for_status()
    blob = resp.json().get("data", {}) or {}
    return blob.get("sources", []), blob.get("referer", "")

def fetch_tracks(episode_id: str):
    resp = requests.get(f"{API_BASE}/episode/{episode_id}/tracks")
    resp.raise_for_status()
    data = resp.json().get("data", [])
    return data or []
