# handlers.py

import os
import logging
import asyncio

from telethon import events, Button
from fetcher import search_anime, fetch_episodes, fetch_sources_and_referer, fetch_tracks
from downloader import remux_hls, download_subtitle
from state import STATE

DOWNLOAD_DIR = os.getenv("DOWNLOAD_DIR", "./downloads")


async def register_handlers(client):
    # ── /search command ────────────────────────────────────────────────
    @client.on(events.NewMessage(
        pattern=r'^/search(?:@[\w_]+)?(?:\s+(.+))?',
        incoming=True, outgoing=True
    ))
    async def search_handler(event):
        query = (event.pattern_match.group(1) or "").strip()
        if not query:
            return await event.reply(
                "🔍 Usage: `/search <anime name>`",
                parse_mode="markdown"
            )

        try:
            results = search_anime(query)
        except Exception as e:
            logging.exception("Search failed")
            return await event.reply(f"❌ Search error: {e}")

        if not isinstance(results, list):
            return await event.reply("⚠️ Unexpected API response format.")

        # Clean and cast names to str
        clean = []
        for r in results:
            aid = r.get("id")
            raw_name = r.get("name", "")
            name = raw_name if isinstance(raw_name, str) else str(raw_name)
            if aid and name:
                clean.append((aid, name))

        if not clean:
            return await event.reply("🔍 No valid results found.")

        # Take up to 5 results
        choices = clean[:5]

        # Store id→name mapping in STATE
        chat = event.chat_id
        STATE.setdefault(chat, {})["anime_meta"] = {aid: nm for aid, nm in choices}

        # Build inline buttons
        buttons = [
            [Button.inline(name, data=f"ANIME|{aid}".encode())]
            for aid, name in choices
        ]

        await event.reply(
            "🔍 Select an anime:",
            buttons=buttons
        )

    # ── Anime selected: list episodes ────────────────────────────────────
    @client.on(events.CallbackQuery(data=lambda d: d and d.startswith(b"ANIME|")))
    async def on_select_anime(event):
        await event.answer()
        anime_id = event.data.decode().split("|", 1)[1]
        chat     = event.chat_id
        state    = STATE.setdefault(chat, {})

        anime_name = state.get("anime_meta", {}).get(anime_id, anime_id)
        state["current_anime_name"] = anime_name

        try:
            eps = fetch_episodes(anime_id)
        except Exception as e:
            logging.exception("Failed to fetch episodes")
            return await event.edit(
                f"❌ Could not load episodes for **{anime_name}**",
                parse_mode="markdown"
            )

        if not isinstance(eps, list) or not eps:
            return await event.edit("⚠️ No episodes found.")

        # Queue episode IDs and map them to numbers
        state["queue"] = [e["episodeId"] for e in eps if "episodeId" in e]
        state["episodes_map"] = {
            e["episodeId"]: e.get("number", "")
            for e in eps if "episodeId" in e
        }

        # Build buttons for each episode + Download All
        buttons = [
            [Button.inline(
                f"{e.get('number','?')}. {e.get('title','')}",
                data=f"EP|{e['episodeId']}".encode()
            )]
            for e in eps if "episodeId" in e
        ]
        buttons.append([Button.inline("▶️ Download All", data=f"ALL|{anime_id}".encode())])

        await event.edit(
            f"📺 Found {len(state['queue'])} episodes of **{anime_name}**.\n"
            "Pick one or Download All:",
            buttons=buttons,
            parse_mode="markdown"
        )

    # ── Single‐episode download ───────────────────────────────────────────
    @client.on(events.CallbackQuery(data=lambda d: d and d.startswith(b"EP|")))
    async def on_single_episode(event):
        await event.answer()
        episode_id = event.data.decode().split("|", 1)[1]
        await _download_episode(
            client, event.chat_id, episode_id, ctx_event=event
        )

    # ── Download All ─────────────────────────────────────────────────────
    @client.on(events.CallbackQuery(data=lambda d: d and d.startswith(b"ALL|")))
    async def on_all(event):
        await event.answer()
        chat  = event.chat_id
        queue = STATE.get(chat, {}).get("queue", [])
        if not queue:
            return await event.edit("⚠️ Nothing queued.")
        await event.edit("✅ Queued all episodes. Starting downloads…")
        asyncio.create_task(_process_queue(client, chat))


async def _download_episode(client, chat_id, episode_id, ctx_event=None):
    state      = STATE.get(chat_id, {})
    anime_name = state.get("current_anime_name", episode_id)
    ep_num     = state.get("episodes_map", {}).get(episode_id, "")
    safe_name  = "".join(c for c in anime_name if c.isalnum() or c in " _-").strip()

    edit_fn = ctx_event.edit if ctx_event else (
        lambda t, **k: client.send_message(chat_id, t, **k)
    )
    status = await edit_fn(
        f"⏳ Downloading **{anime_name}** ep-{ep_num}…",
        parse_mode="markdown"
    )

    try:
        out_dir = os.path.join(DOWNLOAD_DIR, safe_name)
        os.makedirs(out_dir, exist_ok=True)

        # 1) Remux video
        sources, referer = fetch_sources_and_referer(episode_id)
        m3u8     = sources[0].get("url") or sources[0].get("file")
        out_mp4  = os.path.join(out_dir, f"{safe_name} ep-{ep_num}.mp4")
        await asyncio.get_event_loop().run_in_executor(
            None, remux_hls, m3u8, referer, out_mp4
        )

        # 2) Download subtitle by priority
        tracks   = fetch_tracks(episode_id)
        sub_path = None
        for want in ("eng-2.vtt", "en.vtt", "eng.vtt", "english.vtt"):
            for tr in tracks:
                url = tr.get("file") or tr.get("url", "")
                if url.lower().endswith(want):
                    try:
                        sub_path = download_subtitle(tr, out_dir, episode_id)
                    except Exception:
                        logging.exception("Subtitle download failed")
                    break
            if sub_path:
                break

        # 3) Send video
        await client.send_file(
            chat_id, out_mp4,
            caption=f"▶️ **{anime_name}** ep-{ep_num}",
            parse_mode="markdown"
        )

        # 4) Send subtitle if found
        if sub_path and os.path.exists(sub_path):
            await client.send_file(
                chat_id, sub_path,
                caption="📄 Subtitle",
                file_name=os.path.basename(sub_path)
            )

    except Exception:
        logging.exception("Download error")
        await client.send_message(
            chat_id,
            f"❌ Failed downloading **{anime_name}** ep-{ep_num}"
        )
    finally:
        await status.delete()


async def _process_queue(client, chat_id):
    queue = STATE.get(chat_id, {}).get("queue", [])
    while queue:
        ep = queue.pop(0)
        try:
            await _download_episode(client, chat_id, ep)
        except Exception:
            logging.exception("Queued download failed")
            await client.send_message(chat_id, f"❌ Error on ep-{ep}")
    await client.send_message(chat_id, "✅ All downloads complete!")
