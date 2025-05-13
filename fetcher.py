# fetcher.py

import requests
from config import API_BASE

def _normalize_list_of_lists(raw):
    """
    Turn a [[id,name,poster,...], …] into
    [ {"id":id, "name":name, "poster":poster}, … ]
    """
    out = []
    for item in raw:
        if isinstance(item, list):
            # unpack at least id & name; poster if present
            id_, name, *rest = item
            out.append({
                "id":     id_,
                "name":   name,
                "poster": rest[0] if rest else ""
            })
        elif isinstance(item, dict):
            out.append(item)
    return out

def search_anime(query: str, page: int = 1):
    resp = requests.get(f"{API_BASE}/search", params={"q": query, "page": page})
    resp.raise_for_status()
    data = resp.json().get("data", [])
    # If it’s a dict (legacy), take its values; if list, normalize
    if isinstance(data, dict):
        raw = list(data.values())
    else:
        raw = data
    return _normalize_list_of_lists(raw)

def fetch_episodes(anime_id: str):
    resp = requests.get(f"{API_BASE}/anime/{anime_id}/episodes")
    resp.raise_for_status()
    data = resp.json().get("data", [])
    # episodes may also come back as list-of-lists
    if isinstance(data, list) and data and isinstance(data[0], list):
        eps = []
        for item in data:
            # [episodeId, number, title, ...]
            ep_id, number, title, *_ = item
            eps.append({"episodeId": ep_id, "number": number, "title": title})
        return eps
    # otherwise assume it’s already a list of dicts
    return data or []

def fetch_sources_and_referer(episode_id: str):
    resp = requests.get(f"{API_BASE}/episode/{episode_id}/sources")
    resp.raise_for_status()
    blob = resp.json().get("data", {})
    return blob.get("sources", []), blob.get("referer", "")

def fetch_tracks(episode_id: str):
    resp = requests.get(f"{API_BASE}/episode/{episode_id}/tracks")
    resp.raise_for_status()
    data = resp.json().get("data", [])
    # likely list-of-dicts already, so just return
    return data or []
