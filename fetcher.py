import requests
from config import API_BASE

def search_anime(query: str, page: int = 1):
    resp = requests.get(f"{API_BASE}/search", params={"q": query, "page": page})
    resp.raise_for_status()
    return resp.json().get("data", [])

def fetch_episodes(anime_id: str):
    resp = requests.get(f"{API_BASE}/anime/{anime_id}/episodes")
    resp.raise_for_status()
    return resp.json().get("data", [])

def fetch_sources_and_referer(episode_id: str):
    resp = requests.get(f"{API_BASE}/episode/{episode_id}/sources")
    resp.raise_for_status()
    data = resp.json().get("data", {})
    return data.get("sources", []), data.get("referer", "")

def fetch_tracks(episode_id: str):
    resp = requests.get(f"{API_BASE}/episode/{episode_id}/tracks")
    resp.raise_for_status()
    return resp.json().get("data", [])
