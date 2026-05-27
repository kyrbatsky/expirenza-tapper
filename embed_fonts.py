#!/usr/bin/env python3
"""
embed_fonts.py
Завантажує Nunito Sans (400, 700, 800) з Google Fonts
і вбудовує їх як base64 у expirenza-tapper.html та expirenza-tapper-iframe.html.

Запуск:  python3 embed_fonts.py
Потрібен Python 3.7+, без додаткових бібліотек.
"""

import urllib.request
import base64
import re
import os

# ── Налаштування ──────────────────────────────────────────────
FILES_TO_PATCH = [
    'expirenza-tapper.html',
    'expirenza-tapper-iframe.html',
]

FONT_VARIANTS = [
    {'weight': '400', 'style': 'normal'},
    {'weight': '700', 'style': 'normal'},
    {'weight': '800', 'style': 'normal'},
]

GFONTS_URL = (
    'https://fonts.googleapis.com/css2?'
    'family=Nunito+Sans:ital,opsz,wght@0,6..12,400;0,6..12,700;0,6..12,800'
    '&display=swap'
)

UA = (
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) '
    'AppleWebKit/537.36 (KHTML, like Gecko) '
    'Chrome/124.0.0.0 Safari/537.36'
)

# ── Крок 1: завантажити CSS від Google Fonts ──────────────────
print('⏳ Завантажую CSS від Google Fonts...')
req = urllib.request.Request(GFONTS_URL, headers={'User-Agent': UA})
css_text = urllib.request.urlopen(req).read().decode('utf-8')
print('   CSS отримано.')

# ── Крок 2: знайти всі woff2 URL у CSS ───────────────────────
font_urls = re.findall(r"url\((https://[^)]+\.woff2)\)", css_text)
print(f'   Знайдено {len(font_urls)} шрифтових файлів.')

# ── Крок 3: завантажити та закодувати кожен файл ─────────────
font_data = []
for url in font_urls:
    print(f'   Завантажую: {url.split("/")[-1]}...')
    data = urllib.request.urlopen(url).read()
    b64 = base64.b64encode(data).decode('ascii')
    font_data.append(b64)
    print(f'   ✓ {len(data):,} байт → {len(b64):,} символів base64')

# ── Крок 4: будуємо @font-face блок ──────────────────────────
# Розбиваємо CSS на окремі @font-face блоки
face_blocks = re.findall(r'@font-face\s*\{[^}]+\}', css_text, re.DOTALL)

new_css_lines = []
url_index = 0
for block in face_blocks:
    # Знаходимо URL у цьому блоці
    match = re.search(r"url\((https://[^)]+\.woff2)\)", block)
    if match:
        original_url = match.group(1)
        idx = font_urls.index(original_url)
        b64_data_uri = f"url(data:font/woff2;base64,{font_data[idx]}) format('woff2')"
        patched_block = re.sub(
            r"src:[^;]+;",
            f"src: {b64_data_uri};",
            block
        )
        new_css_lines.append(patched_block)

embedded_css = '\n'.join(new_css_lines)

# ── Крок 5: патчимо HTML файли ────────────────────────────────
IMPORT_PATTERN = re.compile(
    r"@import url\('https://fonts\.googleapis\.com[^']*'\);",
    re.IGNORECASE
)

for filename in FILES_TO_PATCH:
    if not os.path.exists(filename):
        print(f'⚠️  Файл не знайдено: {filename}, пропускаю.')
        continue

    with open(filename, 'r', encoding='utf-8') as f:
        html = f.read()

    if not IMPORT_PATTERN.search(html):
        print(f'⚠️  Google Fonts @import не знайдено у {filename}, пропускаю.')
        continue

    new_html = IMPORT_PATTERN.sub(embedded_css, html)

    with open(filename, 'w', encoding='utf-8') as f:
        f.write(new_html)

    size_kb = len(new_html.encode('utf-8')) / 1024
    print(f'✅ {filename} оновлено ({size_kb:.0f} KB)')

print('\n🎉 Готово! Шрифти вбудовано — зовнішніх запитів більше немає.')
