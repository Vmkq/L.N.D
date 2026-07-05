"""
discord_sender.py
All Discord webhook calls for L.N.D Tribe Logs.
"""
import requests
import json
from io import BytesIO
from PIL import Image

HEADERS = {"Content-Type": "application/json"}


def _post(webhook_url: str, payload: dict):
    try:
        r = requests.post(webhook_url, json=payload, timeout=8)
        if r.status_code in (200, 204):
            return True, ""
        return False, f"HTTP {r.status_code}: {r.text[:200]}"
    except Exception as e:
        return False, str(e)


def _post_with_file(webhook_url: str, payload: dict,
                    file_bytes: bytes, filename="screenshot.png"):
    try:
        files = {
            "file": (filename, file_bytes, "image/png"),
            "payload_json": (None, json.dumps(payload), "application/json"),
        }
        r = requests.post(webhook_url, files=files, timeout=8)
        if r.status_code in (200, 204):
            return True, ""
        return False, f"HTTP {r.status_code}: {r.text[:200]}"
    except Exception as e:
        return False, str(e)


def _pil_to_bytes(img: Image.Image) -> bytes:
    buf = BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()


# ── colour → embed style ──────────────────────────────────────────────────────

def _style_from_colour(colour: str) -> tuple:
    """Returns (emoji, discord_colour_int) for a detected log line colour."""
    return {
        "red":     ("💀", 0xe03050),   # death / destroyed  → PING
        "magenta": ("⚔️",  0xdd44dd),  # killed enemy / claimed baby → PING
        "yellow":  ("🔨", 0xf0c000),   # demolished structure → PING
        "white":   ("❄️",  0xcccccc),  # froze dino → silent
        "green":   ("🦖", 0x30c88a),   # tamed dino → silent
        "blue":    ("👤", 0x4a7fff),   # new tribe member → silent
        "unknown": ("📋", 0x2d5be3),
    }.get(colour, ("📋", 0x2d5be3))


# ── test message ─────────────────────────────────────────────────────────────

def send_test_message(webhook_url: str):
    payload = {
        "username": "L.N.D Tribe Logs",
        "embeds": [{
            "title": "✅ L.N.D Tribe Logs — Test",
            "description": "Bot is working correctly!",
            "color": 0x2d5be3,
            "footer": {"text": "L.N.D Tribe Logs • L.N.D"}
        }]
    }
    return _post(webhook_url, payload)


# ── tribe log event ───────────────────────────────────────────────────────────

def send_tribe_log_event(webhook_url: str, role_id: str,
                         line: str, colour: str = "unknown",
                         should_ping: bool = False, label: str = ""):
    """
    Send a single tribe log line to Discord.
    colour      — detected screen colour (red/magenta/yellow/white/green/blue)
    should_ping — if True + role_id set, @mention the role
    label       — human-readable category e.g. '💀 DEATH/DESTROYED'
    """
    emoji, embed_colour = _style_from_colour(colour)
    content = f"<@&{role_id}>" if (role_id and should_ping) else ""
    payload = {
        "username": "L.N.D Tribe Logs",
        "content": content,
        "embeds": [{
            "description": f"{emoji} {line}",
            "color": embed_colour,
            "footer": {"text": f"L.N.D Tribe Logs  •  {label if label else 'L.N.D'}"}
        }]
    }
    return _post(webhook_url, payload)


# ── parasaur alert ────────────────────────────────────────────────────────────

def send_parasaur_alert(webhook_url: str, role_id: str, detail: str = ""):
    content = f"<@&{role_id}>" if role_id else ""
    desc = f"**Enemy detected near your base!**"
    if detail:
        desc += f"\n`{detail}`"
    payload = {
        "username": "L.N.D Tribe Logs",
        "content": content,
        "embeds": [{
            "title": "🚨 PARASAUR ALERT",
            "description": desc,
            "color": 0xe03050,
            "footer": {"text": "L.N.D Tribe Logs • L.N.D"}
        }]
    }
    return _post(webhook_url, payload)


def send_parasaur_cleared(webhook_url: str, role_id: str):
    """Sent when the parasaur alert disappears — enemy left detection range."""
    content = f"<@&{role_id}>" if role_id else ""
    payload = {
        "username": "L.N.D Tribe Logs",
        "content": content,
        "embeds": [{
            "title": "✅ Parasaur Alert Cleared",
            "description": "**Enemy has left detection range.**",
            "color": 0x30c88a,
            "footer": {"text": "L.N.D Tribe Logs • L.N.D"}
        }]
    }
    return _post(webhook_url, payload)


# ── tribe member status ───────────────────────────────────────────────────────

def send_member_status(webhook_url: str, role_id: str,
                       total: int, members: list,
                       screenshot: Image.Image = None):
    lines = []
    for m in members:
        dot = "🟢" if m["online"] else "🔴"
        lines.append(f"{dot} **{m['name']}** ({m['role']})")

    content = f"<@&{role_id}>" if role_id else ""
    payload = {
        "username": "L.N.D Tribe Logs",
        "content": content,
        "embeds": [{
            "title": f"👥 Member Status — Total online: {total}",
            "description": "\n".join(lines) if lines else "No members detected.",
            "color": 0x2d5be3,
            "footer": {"text": "L.N.D Tribe Logs • L.N.D"}
        }]
    }
    if screenshot:
        return _post_with_file(webhook_url, payload,
                               _pil_to_bytes(screenshot), "members.png")
    return _post(webhook_url, payload)


# ── generator alerts ──────────────────────────────────────────────────────────

def send_generator_alert(webhook_url: str, role_id: str,
                         name: str, days: int, hours: int, location: str = ""):
    content  = f"<@&{role_id}>" if role_id else ""
    loc_str  = f" • {location}" if location else ""
    colour   = 0xe03050 if (days == 0 and hours < 6) else 0xf0a500
    payload  = {
        "username": "L.N.D Tribe Logs",
        "content": content,
        "embeds": [{
            "title": f"⚡ Generator Low Fuel — {name}{loc_str}",
            "description": f"Fuel remaining: **{days}d {hours}h**",
            "color": colour,
            "footer": {"text": "L.N.D Tribe Logs • L.N.D"}
        }]
    }
    return _post(webhook_url, payload)


def send_generator_list(webhook_url: str, generators: list):
    if not generators:
        return True, ""
    lines = []
    for g in generators:
        alive = g["days"] > 0 or g["hours"] > 0
        dot   = "🟢" if alive else "🔴"
        loc   = f" • {g['location']}" if g.get("location") else ""
        lines.append(
            f"{dot} **{g['name']}**{loc} — {g['days']}d {g['hours']}h remaining")
    payload = {
        "username": "L.N.D Tribe Logs",
        "embeds": [{
            "title": "⚡ Active Generators",
            "description": "\n".join(lines),
            "color": 0x2d5be3,
            "footer": {"text": "L.N.D Tribe Logs • L.N.D"}
        }]
    }
    return _post(webhook_url, payload)


# ── upload timer alert ────────────────────────────────────────────────────────

def send_upload_timer_alert(webhook_url: str, role_id: str, items: list):
    content = f"<@&{role_id}>" if role_id else ""
    lines   = [f"⚠️ **{i['name']}** — {i['remaining_str']} remaining"
               for i in items]
    payload = {
        "username": "L.N.D Tribe Logs",
        "content": content,
        "embeds": [{
            "title": "⏱️ Upload Timer Alert",
            "description": "\n".join(lines),
            "color": 0xf0a500,
            "footer": {"text": "L.N.D Tribe Logs • L.N.D"}
        }]
    }
    return _post(webhook_url, payload)