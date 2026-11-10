"""Build index.html for GitHub Pages: app template + card data + a proper page head (charset, phone viewport, install icons)."""
import json, pathlib
root = pathlib.Path(__file__).resolve().parent.parent
data = (root / "tools" / "cards.json").read_text(encoding="utf-8").replace("</", "<\\/")
app = (root / "src" / "app-template.html").read_text(encoding="utf-8").replace("__DATA__", data)
head = """<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">
<meta name="theme-color" content="#E4D8C0" media="(prefers-color-scheme: light)">
<meta name="theme-color" content="#12110F" media="(prefers-color-scheme: dark)">
<meta name="description" content="Bounty Board: a One Piece Card Game deck builder.">
<link rel="manifest" href="manifest.webmanifest">
<link rel="icon" type="image/png" href="icon-192.png">
<link rel="apple-touch-icon" href="apple-touch-icon.png">
<meta name="apple-mobile-web-app-capable" content="yes">
<meta name="mobile-web-app-capable" content="yes">
<meta name="apple-mobile-web-app-status-bar-style" content="default">
<meta name="apple-mobile-web-app-title" content="Bounty Board">
"""
(root / "index.html").write_text(head + app + "\n</html>\n", encoding="utf-8")
print("index.html", (root / "index.html").stat().st_size // 1024, "KB")
