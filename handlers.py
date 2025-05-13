import os
import logging
import asyncio

from telethon import events, Button
from fetcher import search_anime, fetch_episodes, fetch_sources_and_referer, fetch_tracks
from downloader import remux_hls, download_subtitle
from state import STATE

DOWNLOAD_DIR = os.getenv("DOWNLOAD_DIR", "./downloads")

async def register_handlers(client):
    @client.on(events.NewMessage(
        pattern=r'^/search(?:@[\w_]+)?\s+(.+)$',
        incoming=True, outgoing=True
    ))
    async def search_handler(event):
        query, chat = event.pattern_match.group(1).strip(), event.chat_id
        try:
            results = search_anime(query)
        except Exception as e:
            logging.exception("Search failed")
            return await event.reply(f"❌ Search error: {e}")

        if not results:
            return await event.reply("🔍 No results found.")

        # store titles
        meta = {a["id"]: a["name"] for a in results[:5]}
        STATE.setdefault(chat, {}).update(anime_meta=meta)

        buttons = [
            [Button.inline(a["name"], data=f"ANIME|{a['id']}".encode())]
            for a in results[:5]
        ]
        await event.reply("🔍 Select an anime:", buttons=buttons)

    @client.on(events.CallbackQuery(data=lambda d: d and d.startswith(b"ANIME|")))
    async def on_select_anime(event):
        await event.answer()
        anime_id = event.data.decode().split("|",1)[1]
        chat = event.chat_id
        state = STATE.setdefault(chat, {})
        anime_name = state["anime_meta"].get(anime_id, anime_id)
        state["current_anime_name"] = anime_name

        try:
            eps = fetch_episodes(anime_id)
        except Exception as e:
            logging.exception("Fetch eps failed")
            return await event.edit(f"❌ Could not load episodes: {e}")

        if not eps:
            return await event.edit("⚠️ No episodes found.")

        # queue & map
        state["queue"] = [e["episodeId"] for e in eps]
        state["episodes_map"] = {e["episodeId"]: e["number"] for e in eps}

        buttons = [
            [Button.inline(f"{e['number']}. {e.get('title','')}",
                           data=f"EP|{e['episodeId']}".encode())]
            for e in eps
        ]
        buttons.append([Button.inline("▶️ Download All", data=f"ALL|{anime_id}".encode())])

        await event.edit(
            f"📺 Found {len(eps)} episodes of **{anime_name}**.\nPick one or Download All:",
            buttons=buttons,
            parse_mode="markdown"
        )

    @client.on(events.CallbackQuery(data=lambda d: d and d.startswith(b"EP|")))
    async def on_single_episode(event):
        await event.answer()
        ep = event.data.decode().split("|",1)[1]
        await _download_episode(client, event.chat_id, ep, ctx_event=event)

    @client.on(events.CallbackQuery(data=lambda d: d and d.startswith(b"ALL|")))
    async def on_all(event):
        await event.answer()
        chat = event.chat_id
        queue = STATE.get(chat, {}).get("queue", [])
        if not queue:
            return await event.edit("⚠️ Nothing queued.")
        await event.edit("✅ Queued all episodes. Starting…")
        asyncio.create_task(_process_queue(client, chat))


async def _download_episode(client, chat_id, episode_id, ctx_event=None):
    state = STATE.get(chat_id, {})
    name  = state.get("current_anime_name", episode_id)
    num   = state.get("episodes_map", {}).get(episode_id, "")
    safe  = "".join(c for c in name if c.isalnum() or c in " _-").strip()

    edit = ctx_event.edit if ctx_event else (lambda t, **k: client.send_message(chat_id, t, **k))
    status = await edit(f"⏳ Downloading **{name}** ep-{num}…", parse_mode="markdown")

    try:
        out_dir = os.path.join(DOWNLOAD_DIR, safe)
        os.makedirs(out_dir, exist_ok=True)

        sources, referer = fetch_sources_and_referer(episode_id)
        m3u8 = sources[0].get("url") or sources[0].get("file")
        mp4 = os.path.join(out_dir, f"{safe} ep-{num}.mp4")

        # remux
        await asyncio.get_event_loop().run_in_executor(
            None, remux_hls, m3u8, referer, mp4
        )

        # pick subtitle by priority
        tracks = fetch_tracks(episode_id)
        sub = None
        for want in ("eng-2.vtt","en.vtt","eng.vtt","english.vtt"):
            for tr in tracks:
                url = tr.get("file") or tr.get("url","")
                if url.lower().endswith(want):
                    try:
                        sub = download_subtitle(tr, out_dir, episode_id)
                    except Exception:
                        logging.exception("Subtitle download failed")
                    break
            if sub: break

        # send video
        await client.send_file(chat_id, mp4, caption=f"▶️ **{name}** ep-{num}", parse_mode="markdown")

        # send subse
        if sub:
            await client.send_file(chat_id, sub, caption="📄 Subtitle", file_name=os.path.basename(sub))

    except Exception as e:
        logging.exception("Download error")
        await client.send_message(chat_id, f"❌ Failed downloading ep-{num}: {e}")
    finally:
        await status.delete()


async def _process_queue(client, chat_id):
    queue = STATE.get(chat_id, {}).get("queue", [])
    while queue:
        ep = queue.pop(0)
        try:
            await _download_episode(client, chat_id, ep)
        except Exception:
            logging.exception("Queue failed")
            await client.send_message(chat_id, f"❌ Error on ep-{ep}")
    await client.send_message(chat_id, "✅ All downloads complete!")
