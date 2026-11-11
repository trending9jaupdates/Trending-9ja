#!/usr/bin/env python3
"""Sharing engine for Trending9ja (the file keeps its old name so the workflow does not change).

What it does on every run:
1. Shares stories YOU approved in Studio to the places you ticked:
   Telegram channel, Facebook Page, Instagram, Kit newsletter.
   (In share_mode "auto" the bot approves them itself.)
2. Tells YOU, in a private Telegram message, when new stories are waiting for your OK.
3. Writes bot/share_log.json and bot/review.json so Studio can show the results.

A target whose secret is not set is simply skipped, so you can connect them one by one.
"""
import datetime
import html
import json
import os
import re
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
BOT = ROOT / "bot"
CFG = json.load(open(BOT / "config.json", encoding="utf-8"))
EMOJI = {"Politics": "🗳️", "Business": "💼", "Entertainment": "🎬", "Sports": "🏅", "Football": "⚽",
         "Music": "🎤", "Movies": "🎥", "Health": "🩺", "Tech/AI": "📱"}
UA = {"User-Agent": "Mozilla/5.0 (compatible; Trending9jaBot/1.0)"}
ENV = os.environ.get


def log(*a):
    print(*a, flush=True)


def now_iso():
    return datetime.datetime.now(datetime.timezone.utc).isoformat()


# --------------------------------------------------------------------------- tiny HTTP helpers
def live(url):
    for method in ("HEAD", "GET"):
        try:
            req = urllib.request.Request(url, method=method, headers=UA)
            with urllib.request.urlopen(req, timeout=20) as r:
                return r.status == 200
        except urllib.error.HTTPError as e:
            if e.code == 404:
                return False
        except Exception:
            pass
    return False


def call(url, data=None, headers=None, form=False, method="POST", timeout=40):
    """Returns parsed JSON. Raises RuntimeError with a short, safe message (never the secret)."""
    hdrs = dict(UA)
    hdrs.update(headers or {})
    body = None
    if data is not None:
        if form:
            body = urllib.parse.urlencode(data).encode()
            hdrs["Content-Type"] = "application/x-www-form-urlencoded"
        else:
            body = json.dumps(data).encode()
            hdrs["Content-Type"] = "application/json"
    req = urllib.request.Request(url, data=body, headers=hdrs, method=method)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            raw = r.read().decode("utf-8", "ignore")
            return json.loads(raw) if raw.strip() else {}
    except urllib.error.HTTPError as e:
        msg = f"HTTP {e.code}"
        try:
            d = json.loads(e.read().decode("utf-8", "ignore"))
            err = d.get("error")
            if isinstance(err, dict):
                msg = err.get("message") or msg
            elif isinstance(err, str):
                msg = err
            elif d.get("description"):
                msg = d["description"]
            elif isinstance(d.get("errors"), list) and d["errors"]:
                msg = str(d["errors"][0])
        except Exception:
            pass
        raise RuntimeError(str(msg)[:200])
    except Exception as e:
        raise RuntimeError(f"no connection ({type(e).__name__})")


# --------------------------------------------------------------------------- what we can share to
def available_targets():
    t = []
    if ENV("TELEGRAM_BOT_TOKEN") and ENV("TELEGRAM_CHAT_ID"):
        t.append("telegram")
    if ENV("FACEBOOK_PAGE_ID") and ENV("FACEBOOK_PAGE_TOKEN"):
        t.append("facebook")
    # Instagram works on its own (INSTAGRAM_TOKEN), or through a Page that is linked to it
    if ENV("INSTAGRAM_TOKEN") or (ENV("FACEBOOK_PAGE_TOKEN") and ENV("INSTAGRAM_USER_ID")):
        t.append("instagram")
    if ENV("KIT_API_KEY"):
        t.append("newsletter")
    return t


def story_info(sid, base):
    """Title, summary and web addresses of a published story."""
    t = (ROOT / "news" / f"{sid}.html").read_text(encoding="utf-8")
    title = re.search(r"<h1>(.*?)</h1>", t, re.S)
    desc = re.search(r'<meta name="description" content="([^"]*)"', t)
    cat = re.search(r'<span class="category-tag">([^<]+)', t)
    return {"id": sid,
            "title": html.unescape(re.sub(r"<[^>]+>", "", title.group(1))).strip() if title else sid,
            "summary": html.unescape(desc.group(1)) if desc else "",
            "category": cat.group(1) if cat else "",
            "url": f"{base}/news/{sid}.html", "image": f"{base}/assets/img/{sid}.jpg"}


def hashtags(cat):
    tag = "#" + re.sub(r"[^A-Za-z0-9]", "", cat) if cat else ""
    return f"{tag} #Nigeria #Trending9ja".strip()


# --------------------------------------------------------------------------- one function per place
def share_telegram(st):
    token, chat = ENV("TELEGRAM_BOT_TOKEN"), ENV("TELEGRAM_CHAT_ID")
    parts = [f"{EMOJI.get(st['category'], '📰')} <b>{html.escape(st['title'])}</b>"]
    if st["summary"]:
        parts.append(html.escape(st["summary"][:420]))
    parts.append(f'🔗 <a href="{st["url"]}">Read the full story</a>')
    parts.append(hashtags(st["category"]))
    caption = "\n\n".join(parts)
    api = f"https://api.telegram.org/bot{token}/"
    try:
        call(api + "sendPhoto", {"chat_id": chat, "photo": st["image"], "caption": caption, "parse_mode": "HTML"})
    except RuntimeError:
        call(api + "sendMessage", {"chat_id": chat, "text": caption, "parse_mode": "HTML"})


def share_facebook(st):
    call(f"https://graph.facebook.com/{ENV('FACEBOOK_PAGE_ID')}/feed",
         {"message": f"{st['title']}\n\n{st['summary'][:300]}\n\n{hashtags(st['category'])}", "link": st["url"],
          "access_token": ENV("FACEBOOK_PAGE_TOKEN")}, form=True)


def share_instagram(st):
    """Route 1 (no Facebook Page needed): INSTAGRAM_TOKEN from Meta's 'Instagram API with Instagram Login'.
    Route 2: a Page token plus INSTAGRAM_USER_ID, when the account is linked to a Facebook Page."""
    caption = (f"{st['title']}\n\n{st['summary'][:600]}\n\nRead the full story - link in our bio "
               f"(trending9ja.com.ng)\n\n{hashtags(st['category'])}")[:2200]
    if ENV("INSTAGRAM_TOKEN"):
        host, who, hdr, extra = "https://graph.instagram.com", "me", {"Authorization": "Bearer " + ENV("INSTAGRAM_TOKEN")}, {}
    else:
        host, who, hdr = "https://graph.facebook.com", ENV("INSTAGRAM_USER_ID"), {}
        extra = {"access_token": ENV("FACEBOOK_PAGE_TOKEN")}
    made = call(f"{host}/{who}/media", dict({"image_url": st["image"], "caption": caption}, **extra), headers=hdr, form=True)
    cid = made.get("id")
    if not cid:
        raise RuntimeError("Instagram did not accept the picture")
    for _ in range(12):  # wait until Instagram has processed the picture
        q = urllib.parse.urlencode(dict({"fields": "status_code"}, **extra))
        s = call(f"{host}/{cid}?{q}", headers=hdr, method="GET")
        if s.get("status_code") == "FINISHED":
            break
        if s.get("status_code") == "ERROR":
            raise RuntimeError("Instagram could not process the picture")
        time.sleep(5)
    call(f"{host}/{who}/media_publish", dict({"creation_id": cid}, **extra), headers=hdr, form=True)


def share_newsletter(stories):
    """One email for all the stories approved in this run."""
    n = len(stories)
    subject = stories[0]["title"] if n == 1 else f"Trending9ja: {n} stories you may have missed"
    base = CFG["telegram_link_base"].rstrip("/")
    items = ""
    for st in stories:
        items += (f'<h2 style="margin:24px 0 6px"><a href="{st["url"]}" style="color:#006640;text-decoration:none">'
                  f'{html.escape(st["title"])}</a></h2>'
                  f'<p style="margin:0 0 6px;color:#333">{html.escape(st["summary"])}</p>'
                  f'<p style="margin:0"><a href="{st["url"]}">Read the full story</a></p>')
    content = ('<div style="font-family:Arial,sans-serif;max-width:600px;margin:auto">'
               f'<h1 style="color:#006640">Trending9ja</h1><p>The latest from {base.replace("https://", "")}</p>{items}'
               '<hr><p style="font-size:12px;color:#777">You get this because you subscribed to Trending9ja.</p></div>')
    send_at = (datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(minutes=6)).strftime("%Y-%m-%dT%H:%M:%SZ")
    call("https://api.kit.com/v4/broadcasts",
         {"subject": subject[:150], "description": f"Auto: {subject[:60]}", "content": content,
          "public": False, "send_at": send_at}, headers={"X-Kit-Api-Key": ENV("KIT_API_KEY")})


# --------------------------------------------------------------------------- owner notification
def find_owner_chat(state):
    token = ENV("TELEGRAM_BOT_TOKEN")
    if ENV("TELEGRAM_OWNER_CHAT_ID"):
        return ENV("TELEGRAM_OWNER_CHAT_ID")
    if state.get("owner_chat_id"):
        return state["owner_chat_id"]
    if not token:
        return None
    try:
        updates = call(f"https://api.telegram.org/bot{token}/getUpdates", method="GET").get("result", [])
    except RuntimeError:
        return None
    for u in reversed(updates):
        chat = (u.get("message") or {}).get("chat") or {}
        if chat.get("type") == "private":
            state["owner_chat_id"] = chat["id"]
            return chat["id"]
    return None


def notify_owner(state, waiting):
    token = ENV("TELEGRAM_BOT_TOKEN")
    if not token or not waiting:
        return
    chat = find_owner_chat(state)
    if not chat:
        log("Owner chat not found: open your bot in Telegram and press Start, then it can message you.")
        return
    lines = "\n".join(f"• {html.escape(w['title'])}" for w in waiting[:10])
    more = f"\n…and {len(waiting) - 10} more" if len(waiting) > 10 else ""
    text = (f"📝 <b>{len(waiting)} new stor{'y' if len(waiting) == 1 else 'ies'} to review</b>\n\n{lines}{more}\n\n"
            f"Open Studio, tap <b>Review</b>, change a picture if needed, then approve sharing:\n{CFG.get('studio_url', '')}")
    try:
        call(f"https://api.telegram.org/bot{token}/sendMessage",
             {"chat_id": chat, "text": text, "parse_mode": "HTML", "disable_web_page_preview": True})
        state["notified"] = (state.get("notified", []) + [w["id"] for w in waiting])[-300:]
    except RuntimeError as e:
        log("Could not message the owner:", e)


# --------------------------------------------------------------------------- Instagram token reminder
def instagram_token_check(state, problem=None):
    """INSTAGRAM_TOKEN lasts 60 days. Tell the owner (in Telegram) before it runs out, or when it has failed."""
    tok = ENV("INSTAGRAM_TOKEN")
    if not tok:
        return
    import hashlib
    key = hashlib.sha256(tok.encode()).hexdigest()[:12]
    seen = state.setdefault("ig_token_seen", {})
    now = datetime.datetime.now(datetime.timezone.utc)
    seen.setdefault(key, now.isoformat())
    for k in [k for k in seen if k != key]:
        seen.pop(k)  # an older token that has since been replaced
    age = (now - datetime.datetime.fromisoformat(seen[key])).days
    warn_at = CFG.get("instagram_token_warn_days", 50)
    last = state.get("ig_warned_at")
    recent = last and (now - datetime.datetime.fromisoformat(last)).days < 3
    expired_hint = problem and re.search(r"token|oauth|expired|session|permission", problem, re.I)
    if (age >= warn_at or expired_hint) and not recent:
        text = ("⚠️ <b>Instagram needs a fresh token</b>\n\n" +
                ("Instagram refused the last post: " + html.escape(problem[:120]) + "\n\n" if expired_hint else
                 f"The connection is {age} days old and expires at 60 days.\n\n") +
                "In the Meta developer dashboard open your app, go to Instagram API setup with Instagram Login, "
                "tap Generate token next to your account, then paste it into the GitHub secret INSTAGRAM_TOKEN.")
        chat = find_owner_chat(state)
        if chat and ENV("TELEGRAM_BOT_TOKEN"):
            try:
                call(f"https://api.telegram.org/bot{ENV('TELEGRAM_BOT_TOKEN')}/sendMessage",
                     {"chat_id": chat, "text": text, "parse_mode": "HTML"})
                state["ig_warned_at"] = now.isoformat()
            except RuntimeError as e:
                log("Could not send the Instagram reminder:", e)


# --------------------------------------------------------------------------- main
def main():
    state_path = BOT / "state.json"
    state = json.load(open(state_path, encoding="utf-8"))
    base = CFG.get("telegram_link_base", CFG["site_url"]).rstrip("/")
    targets_ok = available_targets()
    state["targets_available"] = targets_ok
    shared = state.setdefault("shared", {})
    approved = state.setdefault("approved_share", {})
    state.setdefault("pending_share", [])
    attempts = state.setdefault("share_attempts", {})
    log_path = BOT / "share_log.json"
    try:
        history = json.load(open(log_path, encoding="utf-8"))
    except Exception:
        history = []

    def record(sid, target, ok, msg):
        history.append({"id": sid, "target": target, "ok": ok, "message": msg, "at": now_iso()})
        log(f"   {'OK ' if ok else 'X  '}{target}: {sid} {'' if ok else '- ' + msg}")

    deadline = time.time() + CFG.get("telegram_wait_minutes", 8) * 60
    newsletter_batch = []
    for sid, wanted in list(approved.items()):
        if not (ROOT / "news" / f"{sid}.html").exists():
            approved.pop(sid, None)
            continue
        st = story_info(sid, base)
        while not live(st["url"]) and time.time() < deadline:
            log("   waiting for the page to go live ...")
            time.sleep(20)
        if not live(st["url"]):
            log(f"   not live yet, will try next run: {sid}")
            continue
        done = shared.setdefault(sid, {})
        remaining = []
        for target in wanted:
            if target in done:
                continue
            if target not in targets_ok:
                record(sid, target, False, "not connected yet (secret missing)")
                continue
            if target == "newsletter":
                newsletter_batch.append(st)
                remaining.append("newsletter")
                continue
            key = f"{sid}:{target}"
            try:
                {"telegram": share_telegram, "facebook": share_facebook, "instagram": share_instagram}[target](st)
                done[target] = now_iso()
                record(sid, target, True, "shared")
                time.sleep(3)
            except RuntimeError as e:
                attempts[key] = attempts.get(key, 0) + 1
                record(sid, target, False, str(e))
                if target == "instagram":
                    instagram_token_check(state, str(e))
                if attempts[key] < 3:
                    remaining.append(target)
        if remaining:
            approved[sid] = remaining
        else:
            approved.pop(sid, None)
    if newsletter_batch:
        ids = [st["id"] for st in newsletter_batch]
        try:
            share_newsletter(newsletter_batch)
            for sid in ids:
                shared.setdefault(sid, {})["newsletter"] = now_iso()
                approved[sid] = [t for t in approved.get(sid, []) if t != "newsletter"]
                if not approved[sid]:
                    approved.pop(sid, None)
                record(sid, "newsletter", True, "email scheduled")
        except RuntimeError as e:
            for sid in ids:
                k = f"{sid}:newsletter"
                attempts[k] = attempts.get(k, 0) + 1
                record(sid, "newsletter", False, str(e))
                if attempts[k] >= 3:
                    approved[sid] = [t for t in approved.get(sid, []) if t != "newsletter"]
                    if not approved[sid]:
                        approved.pop(sid, None)

    instagram_token_check(state)

    # tell the owner about stories waiting for an OK
    if CFG.get("share_mode", "approve") == "approve":
        fresh = [w for w in state["pending_share"] if w["id"] not in state.get("notified", [])]
        notify_owner(state, fresh)

    # tidy memory, then write the files Studio reads
    state["shared"] = dict(list(shared.items())[-200:])
    state["share_attempts"] = dict(list(attempts.items())[-200:])
    state_path.write_text(json.dumps(state, indent=1, ensure_ascii=False), encoding="utf-8")
    log_path.write_text(json.dumps(history[-80:], indent=1, ensure_ascii=False), encoding="utf-8")
    recent = [{"id": i, "targets": sorted(t.keys())} for i, t in list(state["shared"].items())[-12:]]
    (BOT / "review.json").write_text(json.dumps(
        {"pending": state["pending_share"], "approved": approved, "targets": targets_ok, "shared": recent,
         "updated": now_iso()}, indent=1, ensure_ascii=False), encoding="utf-8")

    step = ENV("GITHUB_STEP_SUMMARY")
    if step:
        cutoff = (datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(minutes=30)).isoformat()
        recent_h = [h for h in history if h["at"] >= cutoff]
        with open(step, "a", encoding="utf-8") as f:
            f.write("### Sharing\n")
            f.write(f"- Connected: {', '.join(targets_ok) or 'nothing yet'}\n")
            f.write(f"- Shared this run: {len([h for h in recent_h if h['ok']])} · "
                    f"problems: {len([h for h in recent_h if not h['ok']])}\n")
            f.write(f"- Waiting for your OK: {len(state['pending_share'])}\n")


if __name__ == "__main__":
    main()
