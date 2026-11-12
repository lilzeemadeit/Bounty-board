"""Turn the pictures in wallpapers/ into the app's built-in background choices.

Drop images into wallpapers/ (on GitHub: open the folder, Add file -> Upload files). This script, run by the
"Update wallpapers" action, makes a phone-sized copy and a small thumbnail of each one in wp/, and writes
wp/list.json, which the app reads to show them under Background -> Wallpapers.

File names become the labels:
  "2 Sunny at sea by @kaito.jpg"  ->  shown 2nd, labelled "Sunny at sea", credited "Art by @kaito"
  - an optional number at the start sets the order (otherwise A to Z)
  - anything after the last " by " is the artist credit
Delete a picture from wallpapers/ and it disappears from the app.
"""
import hashlib, json, pathlib, re, sys
from PIL import Image, ImageOps

try:  # iPhone photos (.heic) when the helper is installed
    import pillow_heif
    pillow_heif.register_heif_opener()
except ImportError:
    pass

root = pathlib.Path(__file__).resolve().parent.parent
src, out = root / "wallpapers", root / "wp"
out.mkdir(exist_ok=True)
EXT = {".jpg", ".jpeg", ".png", ".webp", ".heic", ".heif", ".gif", ".avif"}


def lin(v):
    v /= 255
    return v / 12.92 if v <= 0.04045 else ((v + 0.055) / 1.055) ** 2.4


def label(stem):
    m = re.match(r"^\s*(\d+)[\s._-]+(.*)$", stem)
    order, rest = (int(m.group(1)), m.group(2)) if m else (10**6, stem)
    name, credit = rest, ""
    i = rest.lower().rfind(" by ")
    if i > 0:
        name, credit = rest[:i], rest[i + 4:]
    tidy = lambda s: re.sub(r"[_]+", " ", s).strip(" -")
    return order, tidy(name) or "Wallpaper", tidy(credit)


items, keep = [], {"list.json"}
for f in sorted(p for p in src.iterdir() if p.is_file() and p.suffix.lower() in EXT) if src.exists() else []:
    raw = f.read_bytes()
    key = hashlib.sha1(raw).hexdigest()[:10]
    big, small = f"{key}.jpg", f"{key}-t.jpg"
    keep |= {big, small}
    try:
        im = ImageOps.exif_transpose(Image.open(f)).convert("RGB")
    except Exception as e:
        print(f"skipped {f.name}: not a picture I can open ({e})", file=sys.stderr)
        continue
    if not (out / big).exists():
        b = im.copy(); b.thumbnail((1600, 1600)); b.save(out / big, "JPEG", quality=84, optimize=True, progressive=True)
    if not (out / small).exists():
        t = im.copy(); t.thumbnail((360, 360)); t.save(out / small, "JPEG", quality=80, optimize=True)
    sm = im.resize((24, 24))
    px = [sm.getpixel((x, y)) for x in range(24) for y in range(24)]
    lum = sum(0.2126 * lin(r) + 0.7152 * lin(g) + 0.0722 * lin(b) for r, g, b in px) / len(px)
    order, name, credit = label(f.stem)
    items.append({"id": key, "name": name, "credit": credit, "src": f"wp/{big}", "thumb": f"wp/{small}",
                  "lum": round(lum, 3), "_o": (order, f.name.lower())})

items.sort(key=lambda x: x.pop("_o"))
(out / "list.json").write_text(json.dumps(items, ensure_ascii=False, indent=1), encoding="utf-8")
for p in out.iterdir():  # clean up copies of pictures that were removed
    if p.name not in keep:
        p.unlink()
print(f"{len(items)} wallpaper(s)")
