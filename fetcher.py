# fetcher.py

import requests
from config import API_BASE

def _normalize(data):
    # If the API gives you a dict, return its values as a list
    if isinstance(data, dict):
        return list(data.values())
    return data or []

def search_anime(query: str, page: int = 1):
    resp = requests.get(f"{API_BASE}/search", params={"q": query, "page": page})
    resp.raise_for_status()
    return _normalize(resp.json().get("data"))

def fetch_episodes(anime_id: str):
    resp = requests.get(f"{API_BASE}/anime/{anime_id}/episodes")
    resp.raise_for_status()
    return _normalize(resp.json().get("data"))

def fetch_sources_and_referer(episode_id: str):
    resp = requests.get(f"{API_BASE}/episode/{episode_id}/sources")
    resp.raise_for_status()
    data = resp.json().get("data", {})
    # data["sources"] might already be a list
    sources = data.get("sources", [])
    return sources, data.get("referer", "")

def fetch_tracks(episode_id: str):
    resp = requests.get(f"{API_BASE}/episode/{episode_id}/tracks")
    resp.raise_for_status()
    return _normalize(resp.json().get("data"))
