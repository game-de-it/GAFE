#!/usr/bin/env python3
import ctypes
import functools
import json
import os
import subprocess
import struct
import sys
import threading
import time
from pathlib import Path

from PIL import Image, ImageDraw, ImageEnhance, ImageFont, ImageOps


WIDTH = 720
HEIGHT = 480
GAFE_DIR = Path("/mnt/mmc/Roms/PORTS/GAFE")
GAFE_HOME = Path("/mnt/mmc/GAFE_HOME")
PLAYLIST = Path("/mnt/vendor/deep/retro/playlists/Nintendo - Game Boy Advance.lpl")
BOXART_DIR = Path("/mnt/vendor/deep/retro/thumbnails/Nintendo - Game Boy Advance/Named_Boxarts")
ROM_DIR = Path("/mnt/mmc/Roms/GBA")
CORE = "/mnt/vendor/deep/retro/cores/mgba_libretro.so"
RETROARCH = "/mnt/vendor/deep/retro/retroarch"
RA_CONFIG = str(GAFE_DIR / "retroarch.cfg")
GAME_CONFIG = str(GAFE_DIR / "gba-game.cfg")
STOCK_RESTORE = Path("/mnt/mmc/Roms/PORTS/GAFE-OFF.sh")
GAFE_MARKER = Path("/etc/gafe-mode")
SESSION_ACTION_FILE = GAFE_HOME / "session-action"
STATE_FILE = GAFE_HOME / "state.json"
VOLUME_STATE_FILE = GAFE_HOME / "volume.json"
FONT_REGULAR = "/mnt/vendor/deep/retro/assets/fonts/mplus-1p-regular.ttf"
FONT_BOLD = "/mnt/vendor/deep/retro/assets/ozone/bold.ttf"

BG = (222, 225, 225, 255)
INK = (27, 30, 34, 255)
MUTED = (101, 108, 114, 255)
ACCENT = (194, 48, 52, 255)
GREEN = (60, 170, 109, 255)
RESAMPLE = getattr(Image, "Resampling", Image).LANCZOS
FAST_RESAMPLE = getattr(Image, "Resampling", Image).BILINEAR


def font(size, bold=False, text=""):
    # The Ozone bold font omits some Japanese glyphs, including U+8EE2 (転).
    primary = FONT_REGULAR if bold and any(ord(char) > 127 for char in text) else (FONT_BOLD if bold else FONT_REGULAR)
    candidates = [
        primary,
        "/System/Library/Fonts/ヒラギノ角ゴシック W6.ttc" if bold else "/System/Library/Fonts/ヒラギノ角ゴシック W3.ttc",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf" if bold else "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
    ]
    for path in candidates:
        if Path(path).exists():
            return ImageFont.truetype(path, size)
    return ImageFont.load_default()


def fit_text(draw, text, max_width, start_size=27, min_size=14, bold=False):
    size = start_size
    while size > min_size:
        face = font(size, bold, text)
        if draw.textbbox((0, 0), text, font=face)[2] <= max_width:
            return face
        size -= 1
    return font(min_size, bold, text)


def rounded_mask(size, radius):
    mask = Image.new("L", size, 0)
    ImageDraw.Draw(mask).rounded_rectangle((0, 0, size[0] - 1, size[1] - 1), radius, fill=255)
    return mask


def load_games():
    games = []
    seen = set()
    if PLAYLIST.exists():
        try:
            items = json.loads(PLAYLIST.read_text(errors="replace")).get("items", [])
        except (OSError, json.JSONDecodeError):
            items = []
        for item in items:
            label = str(item.get("label") or "").strip()
            content = str(item.get("path") or "").replace("/mnt/sdcard/", "/mnt/mmc/")
            archive = content.split("#", 1)[0].split("#?", 1)[0]
            if Path(archive).suffix.lower() in (".zip", ".7z"):
                # Playlist member names may be mojibake for Japanese archives.
                # Let RetroArch extract the sole GBA entry from the archive.
                content = archive
            key = label.casefold()
            if label and key not in seen and Path(archive).exists():
                games.append({"label": label, "path": content})
                seen.add(key)
    for path in sorted(ROM_DIR.glob("*"), key=lambda p: p.name.casefold()):
        if path.suffix.lower() not in (".gba", ".zip", ".7z"):
            continue
        label = path.stem
        if label.casefold() not in seen:
            games.append({"label": label, "path": str(path)})
            seen.add(label.casefold())
    return games


def load_state():
    try:
        return json.loads(STATE_FILE.read_text())
    except (OSError, json.JSONDecodeError):
        return {}


def save_state(state):
    STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
    tmp = STATE_FILE.with_suffix(".tmp")
    tmp.write_text(json.dumps(state, ensure_ascii=False, indent=2))
    tmp.replace(STATE_FILE)


def normalize_retroarch_volume():
    path = Path(RA_CONFIG)
    try:
        lines = path.read_text().splitlines()
    except OSError:
        return
    replacement = 'audio_volume = "0.000000"'
    changed = False
    for index, line in enumerate(lines):
        if line.startswith("audio_volume ="):
            changed = line != replacement
            lines[index] = replacement
            break
    else:
        lines.append(replacement)
        changed = True
    if changed:
        tmp = path.with_suffix(".volume.tmp")
        tmp.write_text("\n".join(lines) + "\n")
        tmp.replace(path)


class VolumeController:
    EVENT = struct.Struct("@llHHi")
    KEY_VOLUMEDOWN = 114
    KEY_VOLUMEUP = 115

    def __init__(self):
        self.level = self.load_level()
        self.apply()
        threading.Thread(target=self.run, name="volume-control", daemon=True).start()

    def load_level(self):
        try:
            value = int(json.loads(VOLUME_STATE_FILE.read_text()).get("level", 22))
        except (OSError, ValueError, TypeError, json.JSONDecodeError):
            value = 22
        return max(0, min(31, value))

    def save(self):
        VOLUME_STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
        tmp = VOLUME_STATE_FILE.with_suffix(".tmp")
        tmp.write_text(json.dumps({"level": self.level}, indent=2))
        tmp.replace(VOLUME_STATE_FILE)

    def apply(self):
        subprocess.run(
            ["amixer", "-q", "-c", "0", "cset", "name=lineout volume", str(self.level)],
            check=False, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
        )

    @staticmethod
    def input_device():
        for name_file in Path("/sys/class/input").glob("event*/device/name"):
            try:
                if name_file.read_text().strip() == "ANBERNIC-keys":
                    return Path("/dev/input") / name_file.parents[1].name
            except OSError:
                continue
        return Path("/dev/input/event1")

    def run(self):
        while True:
            try:
                with self.input_device().open("rb", buffering=0) as device:
                    while True:
                        data = device.read(self.EVENT.size)
                        if len(data) != self.EVENT.size:
                            break
                        _, _, event_type, code, value = self.EVENT.unpack(data)
                        if event_type != 1 or value not in (1, 2):
                            continue
                        previous = self.level
                        if code == self.KEY_VOLUMEUP:
                            self.level = min(31, self.level + 2)
                        elif code == self.KEY_VOLUMEDOWN:
                            self.level = max(0, self.level - 2)
                        if self.level != previous:
                            self.apply()
                            self.save()
            except OSError:
                time.sleep(1)


def read_battery():
    base = Path("/sys/class/power_supply/axp2202-battery")
    try:
        return max(0, min(100, int((base / "capacity").read_text().strip())))
    except (OSError, ValueError):
        return None


def wifi_enabled():
    try:
        out = subprocess.run(
            ["nmcli", "-t", "-f", "WIFI", "general"],
            check=False, capture_output=True, text=True, timeout=3,
        ).stdout.strip()
        return out == "enabled"
    except (OSError, subprocess.TimeoutExpired):
        return False


def wifi_connected():
    try:
        out = subprocess.run(
            ["nmcli", "-t", "-f", "DEVICE,TYPE,STATE", "device"],
            check=False, capture_output=True, text=True, timeout=3,
        ).stdout
        return any(":wifi:connected" in line for line in out.splitlines())
    except (OSError, subprocess.TimeoutExpired):
        return False


def set_wifi(enabled):
    subprocess.run(["nmcli", "radio", "wifi", "on" if enabled else "off"], check=False, timeout=8)


def split_nmcli(line):
    fields = []
    current = []
    escaped = False
    for char in line:
        if escaped:
            current.append(char)
            escaped = False
        elif char == "\\":
            escaped = True
        elif char == ":":
            fields.append("".join(current))
            current = []
        else:
            current.append(char)
    fields.append("".join(current))
    return fields


def scan_networks():
    try:
        result = subprocess.run(
            ["nmcli", "-t", "-f", "IN-USE,SSID,SIGNAL,SECURITY", "device", "wifi", "list", "--rescan", "yes"],
            check=False, capture_output=True, text=True, timeout=15,
        )
    except (OSError, subprocess.TimeoutExpired):
        return []
    networks = {}
    for line in result.stdout.splitlines():
        fields = split_nmcli(line)
        if len(fields) < 4 or not fields[1]:
            continue
        active, ssid, signal, security = fields[:4]
        try:
            strength = int(signal)
        except ValueError:
            strength = 0
        previous = networks.get(ssid)
        entry = {"ssid": ssid, "signal": strength, "security": security, "active": active == "*"}
        if (
            previous is None
            or (entry["active"] and not previous["active"])
            or (entry["active"] == previous["active"] and entry["signal"] > previous["signal"])
        ):
            networks[ssid] = entry
    return sorted(networks.values(), key=lambda n: (not n["active"], -n["signal"], n["ssid"].casefold()))


def connect_network(ssid, password=None):
    command = ["nmcli", "device", "wifi", "connect", ssid]
    if password:
        command.extend(["password", password])
    try:
        result = subprocess.run(command, check=False, capture_output=True, text=True, timeout=30)
        return result.returncode == 0
    except (OSError, subprocess.TimeoutExpired):
        return False


def saved_wifi_connections():
    try:
        result = subprocess.run(
            ["nmcli", "-t", "-f", "TYPE,NAME", "connection", "show"],
            check=False, capture_output=True, text=True, timeout=5,
        )
    except (OSError, subprocess.TimeoutExpired):
        return set()
    saved = set()
    for line in result.stdout.splitlines():
        fields = split_nmcli(line)
        if len(fields) >= 2 and fields[0] == "802-11-wireless":
            saved.add(fields[1])
    return saved


def wifi_icon(draw, x, y, connected, enabled, scale=1.0):
    color = GREEN if connected else ((145, 151, 156, 255) if enabled else (75, 80, 85, 255))
    width = max(2, int(3 * scale))
    for inset in (0, 8, 16):
        box = (x + inset, y + inset, x + int(38 * scale) - inset, y + int(38 * scale) - inset)
        draw.arc(box, 215, 325, fill=color, width=width)
    draw.ellipse((x + 17, y + 29, x + 23, y + 35), fill=color)
    if not enabled:
        draw.line((x + 3, y + 3, x + 35, y + 35), fill=ACCENT, width=3)


def battery_icon(draw, x, y, value):
    draw.rounded_rectangle((x, y, x + 42, y + 20), 4, outline=(205, 209, 212, 255), width=2)
    draw.rectangle((x + 43, y + 6, x + 46, y + 14), fill=(205, 209, 212, 255))
    if value is not None:
        fill = GREEN if value > 20 else ACCENT
        inner = int(36 * value / 100)
        if inner:
            draw.rounded_rectangle((x + 3, y + 3, x + 3 + inner, y + 17), 2, fill=fill)


def draw_header(image, wifi_on, connected, battery, wifi_focus=False):
    draw = ImageDraw.Draw(image)
    draw.rectangle((0, 0, WIDTH, 49), fill=INK)
    if wifi_focus:
        draw.rounded_rectangle((13, 5, 62, 44), 6, fill=(52, 57, 62, 255))
    wifi_icon(draw, 20, 8, connected, wifi_on)
    now = time.strftime("%H:%M")
    clock_font = font(22, True)
    clock_box = draw.textbbox((0, 0), now, font=clock_font)
    draw.text(((WIDTH - clock_box[2]) // 2, 10), now, font=clock_font, fill=(245, 246, 246, 255))
    battery_icon(draw, 646, 14, battery)
    if battery is not None:
        value = str(battery)
        small = font(13, True)
        box = draw.textbbox((0, 0), value, font=small)
        draw.text((625 - box[2], 16), value, font=small, fill=(220, 223, 225, 255))


def load_boxart(label):
    path = BOXART_DIR / f"{label}.png"
    try:
        return Image.open(path).convert("RGBA")
    except OSError:
        return None


@functools.lru_cache(maxsize=8)
def build_cartridge(label):
    base_w, base_h = 432, 294
    cart = Image.new("RGBA", (base_w, base_h), (0, 0, 0, 0))
    d = ImageDraw.Draw(cart)

    d.rounded_rectangle((8, 9, 424, 286), 20, fill=(24, 27, 30, 80))
    d.rounded_rectangle((4, 2, 428, 280), 18, fill=(47, 51, 54, 255), outline=(20, 22, 24, 255), width=4)
    d.rectangle((4, 38, 428, 276), fill=(47, 51, 54, 255))
    d.rounded_rectangle((13, 8, 419, 52), 14, fill=(57, 61, 64, 255), outline=(81, 85, 88, 255), width=2)
    d.line((24, 47, 408, 47), fill=(29, 32, 34, 255), width=3)

    embossed = font(16, True)
    text = "GAME BOY ADVANCE"
    box = d.textbbox((0, 0), text, font=embossed)
    tx = (base_w - box[2]) // 2
    d.text((tx + 1, 17), text, font=embossed, fill=(26, 29, 31, 255))
    d.text((tx, 16), text, font=embossed, fill=(100, 104, 106, 255))

    art = load_boxart(label)
    if art is not None:
        # Preserve the complete image and make the physical label frame follow
        # its aspect ratio, avoiding both cropping and letterbox bars.
        art = ImageOps.contain(art, (336, 170), method=RESAMPLE)
        art_x = (base_w - art.width) // 2
        art_y = 66 + (170 - art.height) // 2
        label_box = (art_x, art_y, art_x + art.width, art_y + art.height)
    else:
        art = Image.new("RGBA", (336, 170), (196, 199, 198, 255))
        ad = ImageDraw.Draw(art)
        ad.rectangle((0, 0, 336, 12), fill=ACCENT)
        title_font = fit_text(ad, label, 286, 24, 13, True)
        words = label.replace(" - ", "\n").splitlines()[:3]
        ad.multiline_text((24, 48), "\n".join(words), font=title_font, fill=INK, spacing=4)
        label_box = (48, 66, 384, 236)
    d.rounded_rectangle(
        (label_box[0] - 5, label_box[1] - 5, label_box[2] + 5, label_box[3] + 5),
        10, fill=(17, 19, 21, 255), outline=(12, 14, 15, 255), width=3,
    )
    cart.paste(art, (label_box[0], label_box[1]), rounded_mask(art.size, 6))
    d.rounded_rectangle(label_box, 6, outline=(113, 117, 119, 255), width=2)

    d.polygon(((184, 280), (216, 258), (248, 280)), fill=(29, 32, 34, 255))
    d.line((184, 280, 216, 258, 248, 280), fill=(78, 82, 85, 255), width=2)
    for gx in range(24, 415, 9):
        d.point((gx, 56 + (gx % 5)), fill=(72, 76, 79, 255))
    return cart


@functools.lru_cache(maxsize=64)
def transformed_cartridge(label, step):
    step = max(0, min(8, step))
    scale = 0.60 + step * (0.50 / 8)
    level = 0.65 + step * (0.35 / 8)
    cart = build_cartridge(label)
    if abs(scale - 1.0) > 0.001:
        size = (int(432 * scale), int(294 * scale))
        cart = cart.resize(size, FAST_RESAMPLE)
    if level < 0.999:
        cart = ImageEnhance.Brightness(cart).enhance(level)
    return cart


def draw_cartridge(canvas, center_x, top, scale, label, selected=True, brightness=None):
    step = max(0, min(8, round((scale - 0.60) / (0.50 / 8))))
    cart = transformed_cartridge(label, step)
    w, h = cart.size
    x = int(center_x - w / 2)
    y = int(top)
    canvas.alpha_composite(cart, (x, y))


def render_main_position(games, position, wifi_on, connected, battery, wifi_focus=False):
    image = Image.new("RGBA", (WIDTH, HEIGHT), BG)
    draw_header(image, wifi_on, connected, battery, wifi_focus)
    if not games:
        draw = ImageDraw.Draw(image)
        face = font(24, True)
        text = "GBA"
        box = draw.textbbox((0, 0), text, font=face)
        draw.text(((WIDTH - box[2]) // 2, 226), text, font=face, fill=MUTED)
        return image

    first = int(position // 1)
    slots = []
    for raw_index in range(first - 2, first + 4):
        distance = raw_index - position
        if abs(distance) <= 1.7:
            slots.append((abs(distance), raw_index, distance))
    for _, raw_index, distance in sorted(slots, reverse=True):
        amount = min(1.0, abs(distance))
        center_x = WIDTH / 2 + 375 * distance
        scale = 1.10 - 0.50 * amount
        top = 55 + 85 * amount
        brightness = 1.0 - 0.35 * amount
        game = games[raw_index % len(games)]
        draw_cartridge(image, center_x, top, scale, game["label"], brightness=brightness)

    draw = ImageDraw.Draw(image)
    index = round(position) % len(games)
    current = games[index]
    title = current["label"]
    title_font = fit_text(draw, title, 640, 28, 16, True)
    box = draw.textbbox((0, 0), title, font=title_font)
    draw.text(((WIDTH - box[2]) // 2, 406), title, font=title_font, fill=INK)
    if len(games) > 1:
        visible = min(9, len(games))
        start = max(0, min(index - visible // 2, len(games) - visible))
        dot_y = 459
        total_w = visible * 12
        for offset, item_index in enumerate(range(start, start + visible)):
            cx = (WIDTH - total_w) // 2 + offset * 12 + 6
            color = ACCENT if item_index == index else (160, 165, 168, 255)
            radius = 4 if item_index == index else 3
            draw.ellipse((cx - radius, dot_y - radius, cx + radius, dot_y + radius), fill=color)
    return image


def render_main(games, index, wifi_on, connected, battery, wifi_focus=False):
    return render_main_position(games, float(index), wifi_on, connected, battery, wifi_focus)


def signal_icon(draw, x, y, strength, active=False):
    color = GREEN if active else INK
    for i, height in enumerate((5, 9, 13, 17)):
        fill = color if strength >= (i + 1) * 20 else (172, 177, 179, 255)
        draw.rounded_rectangle((x + i * 6, y + 18 - height, x + i * 6 + 4, y + 18), 2, fill=fill)


def render_wifi(networks, selected, wifi_on, battery, busy=False):
    image = Image.new("RGBA", (WIDTH, HEIGHT), BG)
    draw_header(image, wifi_on, wifi_connected(), battery, True)
    draw = ImageDraw.Draw(image)
    title_font = font(25, True)
    draw.text((26, 68), "Wi-Fi", font=title_font, fill=INK)
    toggle_x = 615
    if selected == -1:
        draw.rounded_rectangle((toggle_x - 5, 60, toggle_x + 79, 100), 20, outline=ACCENT, width=2)
    draw.rounded_rectangle((toggle_x, 65, toggle_x + 74, 95), 15, fill=GREEN if wifi_on else (133, 138, 142, 255))
    knob_x = toggle_x + 47 if wifi_on else toggle_x + 3
    draw.ellipse((knob_x, 68, knob_x + 24, 92), fill=(248, 249, 249, 255))
    if busy:
        draw.arc((340, 116, 380, 156), 30, 290, fill=ACCENT, width=4)
        return image
    if not wifi_on:
        return image

    top = max(0, selected - 5)
    shown = networks[top:top + 7]
    for row, network in enumerate(shown):
        actual = top + row
        y = 112 + row * 48
        if actual == selected:
            draw.rounded_rectangle((20, y - 4, 700, y + 38), 6, fill=(247, 248, 248, 255), outline=ACCENT, width=2)
        if network["active"]:
            draw.ellipse((34, y + 9, 44, y + 19), fill=GREEN)
        name_font = fit_text(draw, network["ssid"], 530, 21, 15, actual == selected)
        draw.text((55, y + 3), network["ssid"], font=name_font, fill=INK)
        if network["security"]:
            draw.rounded_rectangle((628, y + 6, 639, y + 19), 2, outline=MUTED, width=2)
            draw.arc((629, y, 638, y + 12), 180, 360, fill=MUTED, width=2)
        signal_icon(draw, 656, y + 4, network["signal"], network["active"])
    return image


KEYBOARD_ALPHA = [
    list("1234567890"),
    list("qwertyuiop"),
    list("asdfghjkl-"),
    list("zxcvbnm_@."),
]

KEYBOARD_SYMBOLS = [
    ["!", "@", "#", "$", "%", "^", "&", "*", "(", ")"],
    ["-", "_", "=", "+", "[", "]", "{", "}", "<", ">"],
    ["/", "?", "\\", "|", ":", ";", "'", '"', ",", "."],
    [" ", "0", "1", "2", "3", "4", "5", "6", "7", "8"],
]


def render_keyboard(ssid, password, cursor, shift, symbols, error, wifi_on, battery):
    image = Image.new("RGBA", (WIDTH, HEIGHT), BG)
    draw_header(image, wifi_on, wifi_connected(), battery)
    draw = ImageDraw.Draw(image)
    name_font = fit_text(draw, ssid, 650, 23, 15, True)
    draw.text((28, 68), ssid, font=name_font, fill=INK)
    mode = "#+=" if symbols else ("ABC" if shift else "abc")
    draw.text((632, 71), mode, font=font(16, True), fill=ACCENT if symbols else MUTED)
    shown = "*" * len(password)
    outline = ACCENT if error else (173, 177, 180, 255)
    draw.rounded_rectangle((28, 108, 692, 150), 5, fill=(248, 249, 249, 255), outline=outline, width=2)
    draw.text((42, 113), shown, font=font(20), fill=INK)

    cell_w, cell_h = 60, 51
    origin_x, origin_y = 58, 177
    keyboard = KEYBOARD_SYMBOLS if symbols else KEYBOARD_ALPHA
    for row, chars in enumerate(keyboard):
        for col, char in enumerate(chars):
            x = origin_x + col * cell_w
            y = origin_y + row * cell_h
            active = cursor == (row, col)
            draw.rounded_rectangle((x, y, x + 48, y + 39), 5, fill=(248, 249, 249, 255) if active else (202, 206, 207, 255), outline=ACCENT if active else None, width=2)
            value = "SP" if char == " " else (char.upper() if shift and not symbols else char)
            face = font(20, active)
            box = draw.textbbox((0, 0), value, font=face)
            draw.text((x + (48 - box[2]) // 2, y + 6), value, font=face, fill=INK)
    draw.rounded_rectangle((185, 393, 535, 438), 7, fill=(248, 249, 249, 255))
    draw.line((337, 416, 383, 416), fill=INK, width=3)
    draw.line((374, 407, 383, 416, 374, 425), fill=INK, width=3)
    return image


def render_system(action, confirm, choice, wifi_on, connected, battery):
    image = Image.new("RGBA", (WIDTH, HEIGHT), BG)
    draw_header(image, wifi_on, connected, battery)
    draw = ImageDraw.Draw(image)

    if not confirm:
        labels = ("Restore StockOS", "Restart", "Shut Down")
        for index, text in enumerate(labels):
            y = 88 + index * 100
            selected = index == action
            draw.rounded_rectangle(
                (128, y, 592, y + 78), 7,
                fill=(248, 249, 249, 255) if selected else (202, 206, 207, 255),
                outline=ACCENT if selected else None, width=2,
            )
            icon_x = 194
            icon_y = y + 39
            if index == 0:
                draw.rounded_rectangle((170, y + 13, 218, y + 65), 5, outline=INK, width=4)
                draw.line((194, icon_y, 252, icon_y), fill=INK, width=4)
                draw.line((239, icon_y - 13, 252, icon_y, 239, icon_y + 13), fill=INK, width=4)
            elif index == 1:
                draw.arc((169, y + 13, 221, y + 65), 35, 320, fill=INK, width=4)
                draw.polygon(((216, y + 13), (230, y + 17), (219, y + 27)), fill=INK)
            else:
                draw.arc((170, y + 13, 222, y + 65), 315, 225, fill=INK, width=4)
                draw.line((196, y + 10, 196, y + 39), fill=INK, width=4)
            face = font(25, selected, text)
            draw.text((280, y + 22), text, font=face, fill=INK)
        return image

    prompt = ("Restore StockOS?", "Restart the system?", "Shut down the system?")[action]
    face = font(27, True, prompt)
    box = draw.textbbox((0, 0), prompt, font=face)
    draw.text(((WIDTH - box[2]) // 2, 132), prompt, font=face, fill=INK)
    options = ("No", "Yes")
    for index, text in enumerate(options):
        x = 171 + index * 205
        selected = index == choice
        draw.rounded_rectangle(
            (x, 222, x + 174, 282), 7,
            fill=(248, 249, 249, 255) if selected else (202, 206, 207, 255),
            outline=ACCENT if selected else None, width=2,
        )
        option_font = font(23, selected, text)
        option_box = draw.textbbox((0, 0), text, font=option_font)
        draw.text((x + (174 - option_box[2]) // 2, 236), text, font=option_font, fill=INK)
    return image


class Display:
    def __init__(self):
        self.sdl2 = None
        self.window = None
        self.renderer = None
        self.texture = None
        self.joystick = None
        self.open()

    def open(self):
        import sdl2
        self.sdl2 = sdl2
        if sdl2.SDL_Init(sdl2.SDL_INIT_VIDEO | sdl2.SDL_INIT_JOYSTICK) != 0:
            raise RuntimeError(sdl2.SDL_GetError().decode())
        sdl2.SDL_ShowCursor(sdl2.SDL_DISABLE)
        sdl2.SDL_JoystickEventState(sdl2.SDL_ENABLE)
        if sdl2.SDL_NumJoysticks() > 0:
            self.joystick = sdl2.SDL_JoystickOpen(0)
        self.window = sdl2.SDL_CreateWindow(
            b"GAFE", sdl2.SDL_WINDOWPOS_UNDEFINED, sdl2.SDL_WINDOWPOS_UNDEFINED,
            WIDTH, HEIGHT, sdl2.SDL_WINDOW_FULLSCREEN,
        )
        if not self.window:
            raise RuntimeError(sdl2.SDL_GetError().decode())
        self.renderer = sdl2.SDL_CreateRenderer(self.window, -1, sdl2.SDL_RENDERER_ACCELERATED | sdl2.SDL_RENDERER_PRESENTVSYNC)
        if not self.renderer:
            self.renderer = sdl2.SDL_CreateRenderer(self.window, -1, sdl2.SDL_RENDERER_SOFTWARE)
        self.texture = sdl2.SDL_CreateTexture(
            self.renderer, sdl2.SDL_PIXELFORMAT_ABGR8888, sdl2.SDL_TEXTUREACCESS_STREAMING, WIDTH, HEIGHT,
        )

    def show(self, image):
        data = image.convert("RGBA").tobytes()
        buffer = ctypes.create_string_buffer(data)
        self.sdl2.SDL_UpdateTexture(self.texture, None, buffer, WIDTH * 4)
        self.sdl2.SDL_RenderClear(self.renderer)
        self.sdl2.SDL_RenderCopy(self.renderer, self.texture, None, None)
        self.sdl2.SDL_RenderPresent(self.renderer)

    def events(self):
        event = self.sdl2.SDL_Event()
        while self.sdl2.SDL_PollEvent(ctypes.byref(event)):
            if event.type == self.sdl2.SDL_QUIT:
                yield "quit"
            elif event.type == self.sdl2.SDL_KEYDOWN and not event.key.repeat:
                yield event.key.keysym.sym
            elif event.type == self.sdl2.SDL_JOYBUTTONDOWN:
                # RGSP kernel mapping observed from ANBERNIC-keys/event1.
                button_to_key = {
                    0: self.sdl2.SDLK_x,       # A / BTN_SOUTH
                    1: self.sdl2.SDLK_z,       # B / BTN_EAST
                    2: self.sdl2.SDLK_a,       # Y / BTN_C
                    3: self.sdl2.SDLK_s,       # X / BTN_NORTH
                    4: self.sdl2.SDLK_q,       # L / BTN_WEST
                    5: self.sdl2.SDLK_w,       # R / BTN_Z
                    6: self.sdl2.SDLK_RSHIFT,  # SELECT / BTN_TL
                    7: self.sdl2.SDLK_RETURN,  # START / BTN_TR
                }
                mapped = button_to_key.get(event.jbutton.button)
                if mapped is not None:
                    yield mapped
            elif event.type == self.sdl2.SDL_JOYHATMOTION:
                value = event.jhat.value
                if value & self.sdl2.SDL_HAT_UP:
                    yield self.sdl2.SDLK_UP
                elif value & self.sdl2.SDL_HAT_DOWN:
                    yield self.sdl2.SDLK_DOWN
                elif value & self.sdl2.SDL_HAT_LEFT:
                    yield self.sdl2.SDLK_LEFT
                elif value & self.sdl2.SDL_HAT_RIGHT:
                    yield self.sdl2.SDLK_RIGHT

    def close(self):
        if self.sdl2:
            if self.joystick:
                self.sdl2.SDL_JoystickClose(self.joystick)
            if self.texture:
                self.sdl2.SDL_DestroyTexture(self.texture)
            if self.renderer:
                self.sdl2.SDL_DestroyRenderer(self.renderer)
            if self.window:
                self.sdl2.SDL_DestroyWindow(self.window)
            self.sdl2.SDL_Quit()
        self.sdl2 = self.window = self.renderer = self.texture = self.joystick = None


class App:
    def __init__(self):
        self.games = load_games()
        self.state = load_state()
        self.index = min(int(self.state.get("index", 0)), max(0, len(self.games) - 1))
        self.mode = "main"
        self.networks = []
        self.network_index = 0
        self.wifi_on = wifi_enabled()
        self.connected = wifi_connected()
        self.battery = read_battery()
        self.last_status = 0
        self.dirty = True
        self.running = True
        self.password = ""
        self.keyboard_cursor = (0, 0)
        self.keyboard_shift = False
        self.keyboard_symbols = False
        self.connection_error = False
        self.pending_ssid = ""
        self.system_confirm = False
        self.system_choice = 0
        self.system_action = 0
        normalize_retroarch_volume()
        self.volume = VolumeController()
        self.display = Display()
        self.cache_target = self.index
        self.queue_cache_warm(self.index)

    def queue_cache_warm(self, index):
        self.cache_target = index

        def warm():
            for offset in (-2, -1, 0, 1, 2):
                if self.cache_target != index or not self.games:
                    return
                label = self.games[(index + offset) % len(self.games)]["label"]
                for step in range(9):
                    transformed_cartridge(label, step)

        threading.Thread(target=warm, name="cartridge-cache", daemon=True).start()

    def refresh_status(self):
        now = time.monotonic()
        if now - self.last_status >= 10:
            self.wifi_on = wifi_enabled()
            self.connected = wifi_connected()
            self.battery = read_battery()
            self.last_status = now
            self.dirty = True

    def refresh_networks(self):
        self.display.show(render_wifi([], 0, self.wifi_on, self.battery, True))
        self.networks = scan_networks() if self.wifi_on else []
        self.network_index = -1
        self.dirty = True

    def launch(self):
        if not self.games:
            return
        game = self.games[self.index]
        self.state["index"] = self.index
        self.state["last_game"] = game["label"]
        save_state(self.state)
        self.display.close()
        command = [
            RETROARCH, "--config", RA_CONFIG,
            "--appendconfig", GAME_CONFIG,
            "-L", CORE, game["path"],
        ]
        print(f"Launching: {game['label']} ({game['path']})", flush=True)
        result = subprocess.run(command, check=False)
        print(f"RetroArch exited with status {result.returncode}", flush=True)
        normalize_retroarch_volume()
        self.display.open()
        self.dirty = True
        self.last_status = 0

    def animate_selection(self, direction):
        if len(self.games) < 2:
            return
        origin = self.index
        target = (origin + direction) % len(self.games)
        started = time.monotonic()
        duration = 0.22
        while self.running:
            elapsed = time.monotonic() - started
            progress = min(1.0, elapsed / duration)
            eased = progress * progress * (3.0 - 2.0 * progress)
            position = origin + direction * eased
            frame = render_main_position(
                self.games, position, self.wifi_on, self.connected, self.battery,
            )
            self.display.show(frame)
            if progress >= 1.0:
                break
            time.sleep(0.006)
        self.index = target
        self.state["index"] = self.index
        save_state(self.state)
        self.queue_cache_warm(target)
        self.dirty = True

    def main_key(self, key):
        s = self.display.sdl2
        if key in (s.SDLK_LEFT, s.SDLK_UP, s.SDLK_q):
            self.animate_selection(-1)
        elif key in (s.SDLK_RIGHT, s.SDLK_DOWN, s.SDLK_w):
            self.animate_selection(1)
        elif key == s.SDLK_x:
            self.launch()
        elif key in (s.SDLK_RETURN, s.SDLK_s):
            self.mode = "wifi"
            self.refresh_networks()
        elif key == s.SDLK_RSHIFT:
            self.mode = "system"
            self.system_confirm = False
            self.system_choice = 0
            self.system_action = 0
        self.dirty = True

    def wifi_key(self, key):
        s = self.display.sdl2
        if key in (s.SDLK_z, s.SDLK_RETURN):
            self.mode = "main"
        elif key == s.SDLK_LEFT and self.network_index == -1:
            set_wifi(False)
            self.wifi_on = False
            self.networks = []
        elif key == s.SDLK_RIGHT and self.network_index == -1:
            set_wifi(True)
            self.wifi_on = True
            self.refresh_networks()
        elif key == s.SDLK_UP:
            self.network_index = max(-1, self.network_index - 1)
        elif key == s.SDLK_DOWN and self.networks:
            self.network_index = min(len(self.networks) - 1, self.network_index + 1)
        elif key == s.SDLK_x and self.network_index == -1:
            self.wifi_on = not self.wifi_on
            set_wifi(self.wifi_on)
            self.refresh_networks()
        elif key == s.SDLK_x and self.networks:
            network = self.networks[self.network_index]
            if network["active"]:
                return
            saved = network["ssid"] in saved_wifi_connections()
            if (not network["security"] or saved) and connect_network(network["ssid"]):
                self.refresh_networks()
            elif network["security"]:
                self.pending_ssid = network["ssid"]
                self.password = ""
                self.keyboard_cursor = (0, 0)
                self.keyboard_shift = False
                self.keyboard_symbols = False
                self.connection_error = False
                self.mode = "keyboard"
        elif key in (s.SDLK_r, s.SDLK_a):
            self.refresh_networks()
        self.dirty = True

    def keyboard_key(self, key):
        s = self.display.sdl2
        row, col = self.keyboard_cursor
        keyboard = KEYBOARD_SYMBOLS if self.keyboard_symbols else KEYBOARD_ALPHA
        if key == s.SDLK_LEFT:
            col = (col - 1) % len(keyboard[row])
        elif key == s.SDLK_RIGHT:
            col = (col + 1) % len(keyboard[row])
        elif key == s.SDLK_UP:
            row = (row - 1) % len(keyboard)
            col = min(col, len(keyboard[row]) - 1)
        elif key == s.SDLK_DOWN:
            row = (row + 1) % len(keyboard)
            col = min(col, len(keyboard[row]) - 1)
        elif key == s.SDLK_x:
            char = keyboard[row][col]
            self.password += char.upper() if self.keyboard_shift and not self.keyboard_symbols else char
            self.connection_error = False
        elif key in (s.SDLK_s, s.SDLK_BACKSPACE):
            self.password = self.password[:-1]
            self.connection_error = False
        elif key == s.SDLK_a:
            self.keyboard_shift = not self.keyboard_shift
        elif key in (s.SDLK_LSHIFT, s.SDLK_RSHIFT):
            self.keyboard_symbols = not self.keyboard_symbols
        elif key == s.SDLK_RETURN:
            if connect_network(self.pending_ssid, self.password):
                self.mode = "wifi"
                self.refresh_networks()
            else:
                self.connection_error = True
        elif key == s.SDLK_z:
            self.mode = "wifi"
        self.keyboard_cursor = (row, col)
        self.dirty = True

    def restore_stock(self):
        if not STOCK_RESTORE.is_file():
            self.system_confirm = False
            self.dirty = True
            return
        subprocess.Popen(
            [str(STOCK_RESTORE), "--from-fe"],
            stdin=subprocess.DEVNULL,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            start_new_session=True,
        )
        deadline = time.monotonic() + 3
        while GAFE_MARKER.exists() and time.monotonic() < deadline:
            time.sleep(0.05)
        self.running = False

    def request_session_action(self, action):
        GAFE_HOME.mkdir(parents=True, exist_ok=True)
        tmp = SESSION_ACTION_FILE.with_suffix(".tmp")
        tmp.write_text(action + "\n")
        tmp.replace(SESSION_ACTION_FILE)
        self.running = False

    def system_key(self, key):
        s = self.display.sdl2
        if key == s.SDLK_z:
            if self.system_confirm:
                self.system_confirm = False
                self.system_choice = 0
            else:
                self.mode = "main"
        elif not self.system_confirm and key == s.SDLK_UP:
            self.system_action = (self.system_action - 1) % 3
        elif not self.system_confirm and key == s.SDLK_DOWN:
            self.system_action = (self.system_action + 1) % 3
        elif not self.system_confirm and key == s.SDLK_x:
            self.system_confirm = True
            self.system_choice = 0
        elif self.system_confirm and key in (s.SDLK_LEFT, s.SDLK_RIGHT):
            self.system_choice = 1 - self.system_choice
        elif self.system_confirm and key == s.SDLK_x:
            if self.system_choice == 1:
                if self.system_action == 0:
                    self.restore_stock()
                elif self.system_action == 1:
                    self.request_session_action("reboot")
                else:
                    self.request_session_action("poweroff")
            else:
                self.system_confirm = False
        self.dirty = True

    def render(self):
        if self.mode == "main":
            return render_main(self.games, self.index, self.wifi_on, self.connected, self.battery)
        if self.mode == "wifi":
            return render_wifi(self.networks, self.network_index, self.wifi_on, self.battery)
        if self.mode == "system":
            return render_system(
                self.system_action, self.system_confirm, self.system_choice,
                self.wifi_on, self.connected, self.battery,
            )
        return render_keyboard(
            self.pending_ssid, self.password, self.keyboard_cursor,
            self.keyboard_shift, self.keyboard_symbols, self.connection_error,
            self.wifi_on, self.battery,
        )

    def run(self):
        try:
            while self.running:
                self.refresh_status()
                for key in self.display.events():
                    if key == "quit":
                        self.running = False
                    elif self.mode == "main":
                        self.main_key(key)
                    elif self.mode == "wifi":
                        self.wifi_key(key)
                    elif self.mode == "system":
                        self.system_key(key)
                    else:
                        self.keyboard_key(key)
                if self.dirty:
                    self.display.show(self.render())
                    self.dirty = False
                time.sleep(0.01)
        finally:
            self.state["index"] = self.index
            save_state(self.state)
            self.display.close()


def render_preview(path):
    samples = [
        {"label": "Densetsu no Stafy 3 (Japan)", "path": ""},
        {"label": "Metroid Fusion (Japan)", "path": ""},
        {"label": "Mario _ Luigi RPG (Japan)", "path": ""},
    ]
    global BOXART_DIR
    if not BOXART_DIR.exists():
        BOXART_DIR = Path(__file__).resolve().parent.parent / "gba-fe-assets"
    render_main(samples, 1, True, True, 94).convert("RGB").save(path)


if __name__ == "__main__":
    if len(sys.argv) == 3 and sys.argv[1] == "--render-preview":
        render_preview(sys.argv[2])
    else:
        App().run()
