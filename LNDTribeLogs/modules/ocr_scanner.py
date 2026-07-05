"""
ocr_scanner.py
Screen capture + OCR + colour classification for ARK: Survival Ascended tribe log.
"""
import pytesseract
from PIL import ImageGrab, Image, ImageFilter
import numpy as np
import re
import os

TESSERACT_PATH = r"C:\Program Files\Tesseract-OCR\tesseract.exe"
if os.path.exists(TESSERACT_PATH):
    pytesseract.pytesseract.tesseract_cmd = TESSERACT_PATH

DEBUG_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "debug")
os.makedirs(DEBUG_DIR, exist_ok=True)


# ── Screen capture ────────────────────────────────────────────────────────────

def capture_region(x: int, y: int, w: int, h: int) -> Image.Image:
    return ImageGrab.grab(bbox=(x, y, x + w, y + h), all_screens=True)

def save_debug_screenshot(img: Image.Image, name: str):
    try:
        img.save(os.path.join(DEBUG_DIR, f"{name}_raw.png"))
        preprocess_for_ocr(img).save(os.path.join(DEBUG_DIR, f"{name}_processed.png"))
    except Exception:
        pass


# ── Preprocessing ─────────────────────────────────────────────────────────────

def preprocess_for_ocr(img: Image.Image) -> Image.Image:
    """
    ARK log has busy game scenery (rocks/foliage) showing through a
    semi-transparent panel. A loose colour threshold picks up speckle
    noise from that scenery, which destroys OCR accuracy.

    Strategy:
      1. Stricter brightness requirement — real text is solidly bright
         on at least one channel, not just "warmer than blue"
      2. Scale UP FIRST (3x) — this makes thin letter strokes (1-2px)
         become thick enough (3-6px) to survive denoising
      3. THEN median filter to remove noise specks — at this scale,
         specks stay tiny while letter strokes are now wide enough
         to survive the filter intact (this ordering is the key fix)
      4. Sharpen for final OCR clarity
    """
    arr = np.array(img.convert("RGB")).astype(int)
    r, g, b = arr[:,:,0], arr[:,:,1], arr[:,:,2]
    brightness = (r + g + b) / 3

    is_white_text  = (r > 130) & (g > 130) & (b > 130)
    is_colour_text = ((r > 130) | (g > 130)) & (brightness > 80)
    text_mask = is_white_text | is_colour_text

    result = np.zeros((arr.shape[0], arr.shape[1]), dtype=np.uint8)
    result[text_mask] = 255

    out = Image.fromarray(result, mode="L")
    # Upscale FIRST so letter strokes become thick enough to survive denoising
    out = out.resize((out.width * 3, out.height * 3), Image.LANCZOS)
    # NOW denoise — noise specks are still ~3px, letter strokes are now ~9px+
    out = out.filter(ImageFilter.MedianFilter(size=3))
    out = out.filter(ImageFilter.SHARPEN)
    return out


# ── Colour classification ─────────────────────────────────────────────────────

def classify_colour(r: float, g: float, b: float) -> str:
    mx = max(r, g, b, 1)
    rn, gn, bn = r/mx, g/mx, b/mx
    if rn > 0.85 and gn < 0.45 and bn < 0.45:  return "red"
    if rn > 0.75 and gn < 0.45 and bn > 0.65:  return "magenta"
    if rn > 0.80 and gn > 0.75 and bn < 0.40:  return "yellow"
    if rn < 0.45 and gn > 0.80 and bn < 0.55:  return "green"
    if rn < 0.55 and bn > 0.75:                 return "blue"
    if rn > 0.75 and gn > 0.75 and bn > 0.75:  return "white"
    return "unknown"

def get_line_colour(strip: np.ndarray) -> str:
    """
    Sample the dominant bright-pixel colour from a horizontal image strip.
    Only looks at pixels brighter than the blue background.
    """
    r = strip[:,:,0].astype(float)
    g = strip[:,:,1].astype(float)
    b = strip[:,:,2].astype(float)
    # Exclude pure-blue background pixels — only sample actual text pixels
    # Text pixels: R or G is notably high, or R+G beats pure blue
    text_mask = (r > 140) | (g > 140) | ((r + g) > (b + 60))
    if text_mask.sum() < 5:
        return "unknown"
    return classify_colour(
        r[text_mask].mean(),
        g[text_mask].mean(),
        b[text_mask].mean()
    )


# ── Labels / tags ─────────────────────────────────────────────────────────────

PING_COLOURS = {"red", "magenta", "yellow"}

def should_ping(colour: str) -> bool: return colour in PING_COLOURS

def colour_label(colour: str) -> str:
    return {
        "red":     "💀 DEATH/DESTROYED",
        "magenta": "⚔️ KILL/CLAIM",
        "yellow":  "🔨 DEMOLISHED",
        "white":   "❄️ FROZE DINO",
        "green":   "🦖 TAMED",
        "blue":    "👤 NEW MEMBER",
        "unknown": "📋 LOG",
    }.get(colour, "📋 LOG")

def ui_tag(colour: str) -> str:
    return {
        "red":     "danger",
        "magenta": "magenta",
        "yellow":  "warn",
        "white":   "dim",
        "green":   "ok",
        "blue":    "blue",
        "unknown": "dim",
    }.get(colour, "dim")


# ── Dedup helpers ─────────────────────────────────────────────────────────────

# Tolerant of OCR misreading ':' as '.', '°', ';' and 'Day N' where the
# digit itself can occasionally misread (rare) — day number is \d+ already
# permissive. Time separators tolerate punctuation variants.
_DAY_RE       = re.compile(r"^Day\s+[\d/]+,\s*\d{1,2}[:.;°]\d{2}[:.;°]\d{2}", re.IGNORECASE)
_DEDUP_KEY_RE = re.compile(r"Day\s+[\d/]+,\s*\d{1,2}[:.;°]\d{2}[:.;°]\d{2}", re.IGNORECASE)

def is_new_entry(line: str) -> bool:
    return bool(_DAY_RE.match(line.strip()))

def normalise_line(line: str) -> str:
    return re.sub(r"\s+", " ", line.strip().lower())

def dedup_key(line: str) -> str:
    """
    Timestamp-only dedup key. Normalises separator variants ('.','°',';')
    to ':' and stray '/' (common OCR misread of '7') so equivalent
    OCR readings of the same event produce the SAME key.
    """
    m = _DEDUP_KEY_RE.search(line.strip())
    if not m:
        return normalise_line(line)
    key = m.group(0).lower()
    key = re.sub(r"[:.;°]", ":", key)
    key = key.replace("/", "7")
    return key


# ── Line merging ──────────────────────────────────────────────────────────────

def merge_wrapped_lines(raw_lines: list) -> list:
    """
    Merge continuation lines back onto the previous Day entry.
    Returns list of [full_text, start_raw_line_index].
    """
    merged = []
    for i, line in enumerate(raw_lines):
        if is_new_entry(line):
            merged.append([line, i])
        elif merged:
            merged[-1][0] = merged[-1][0].rstrip() + " " + line.strip()
    return merged


# ── Main OCR pipeline ─────────────────────────────────────────────────────────

def ocr_region_with_colours(x: int, y: int, w: int, h: int,
                              save_debug: bool = False) -> list:
    """
    Full pipeline: capture → preprocess → OCR → merge lines → colour sample.
    Colour is sampled from the RAW image (before preprocessing) using the
    EXACT pixel row of each entry's first line — tight single-line strip only.
    """
    img  = capture_region(x, y, w, h)
    if save_debug:
        save_debug_screenshot(img, "tribelog")

    raw_arr = np.array(img.convert("RGB"))   # colour source — unprocessed
    h_px    = raw_arr.shape[0]

    proc      = preprocess_for_ocr(img)
    raw_text  = pytesseract.image_to_string(proc, config="--psm 6 --oem 3")
    raw_lines = [ln.strip() for ln in raw_text.splitlines() if ln.strip()]

    if not raw_lines:
        return []

    merged = merge_wrapped_lines(raw_lines)
    if not merged:
        return []

    # One pixel band per OCR line
    line_h  = h_px / max(len(raw_lines), 1)
    results = []

    for full_text, raw_idx in merged:
        key = dedup_key(full_text)
        if not key:
            continue

        # Sample ONE tight line strip from the raw colour image
        y0 = int(raw_idx * line_h)
        y1 = min(int((raw_idx + 1) * line_h), h_px)
        if y1 <= y0:
            y1 = min(y0 + 2, h_px)
        colour = get_line_colour(raw_arr[y0:y1, :, :])

        # Yellow tiebreak: unclaim uses same yellow as demolish
        if colour == "yellow":
            if "unclaim" in full_text.lower():
                colour = "white"

        results.append({
            "line":   full_text,
            "colour": colour,
            "ping":   should_ping(colour),
            "label":  colour_label(colour),
            "key":    key,
        })

    return results


# ── Parasaur detection ────────────────────────────────────────────────────────
#
# The alert is a small dark box with cyan-outlined text in the top-left.
# The processed image shows the text perfectly — so we skip the cyan pixel
# check entirely and just run OCR directly every scan. It's a small region
# so OCR is fast enough.

_PARASAUR_PHRASES = [
    "detected an enemy",
    "parasaur) detected",
    "(parasaur)",
    "detected an enem",
]

def detect_parasaur_alert(x: int, y: int, w: int, h: int,
                           save_debug: bool = False) -> bool:
    """
    OCR the parasaur region directly. No pixel pre-check needed.
    Returns True if '(Parasaur) detected an enemy' is found.
    Uses --psm 6 (uniform block) which handles background noise
    around the alert box better than --psm 7 (single line).
    """
    img = capture_region(x, y, w, h)
    if save_debug:
        save_debug_screenshot(img, "parasaur")

    proc = preprocess_for_ocr(img)
    text = pytesseract.image_to_string(
        proc, config="--psm 6 --oem 3").lower()
    return any(phrase in text for phrase in _PARASAUR_PHRASES)


# ── Member list parser ────────────────────────────────────────────────────────

def ocr_member_region(x: int, y: int, w: int, h: int) -> list:
    """
    Plain OCR for the tribe member list — NOT routed through the tribe-log
    pipeline, since member rows have no 'Day X, HH:MM:SS' timestamp and
    would be silently dropped by merge_wrapped_lines() otherwise.
    Returns raw OCR lines for parse_member_lines() to process.
    """
    img  = capture_region(x, y, w, h)
    proc = preprocess_for_ocr(img)
    raw  = pytesseract.image_to_string(proc, config="--psm 6 --oem 3")
    return [ln.strip() for ln in raw.splitlines() if ln.strip()]

# ARK member rows look like: "Demon(...)   (Owner)   ONLINE"
# OCR sometimes reads parentheses as curly braces: "Demon(...} {Owner} ONLINE"
# We normalise all bracket variants to () before parsing.

_BRACKET_NORMALISE = str.maketrans("{}[]", "()()")

def parse_member_lines(lines: list) -> list:
    """
    Parses ARK tribe member list OCR lines into structured records.
    Returns [{"name": str, "role": str, "online": bool}, ...]
    """
    members = []
    for raw_line in lines:
        line = raw_line.translate(_BRACKET_NORMALISE)
        upper = line.upper()

        if "ONLINE" not in upper and "OFFLINE" not in upper:
            continue
        online = "ONLINE" in upper and "OFFLINE" not in upper

        # strip the status word off the end
        clean = re.sub(r"\b(ONLINE|OFFLINE)\b", "", line, flags=re.IGNORECASE).strip()

        # find all (...) groups — first is usually "(...)" placeholder
        # after the name (ARK truncates long names with "..."), second
        # is the role e.g. "(Owner)" or "(Admin)"
        groups = re.findall(r"\(([^)]*)\)", clean)

        # ARK always shows "Name(...)" right after the name — the "..."
        # is a reliable anchor even when OCR mangles the parentheses
        # themselves (e.g. "Von(...)" -> "Vont...}" merges '(' into the name).
        # Find the "..." and treat everything before it as the name.
        dots_match = re.search(r"\.{2,}", clean)
        if dots_match:
            name = clean[:dots_match.start()]
            # strip a single trailing stray character that's actually
            # the mangled '(' (e.g. "Vont" -> "Von")
            name = re.sub(r"[\(\[\{t]$", "", name, flags=re.IGNORECASE)
        elif "(" in clean:
            name = clean[:clean.index("(")]
        else:
            name = clean

        # role = the LAST non-empty, non-"..." bracket group found
        role = ""
        for g in reversed(groups):
            g = g.strip()
            if g and not re.fullmatch(r"\.+", g):
                role = g.capitalize()
                break

        name = name.strip().rstrip(".").strip()
        if name and len(name) > 1:
            members.append({
                "name": name.title(),
                "role": role,
                "online": online,
            })

    return members