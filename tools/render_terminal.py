"""Render a captured program log as a terminal screenshot."""

from __future__ import annotations

import argparse
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

FONT = "/System/Library/Fonts/Supplemental/Courier New.ttf"


def render(text: str, destination: Path, title: str) -> None:
    font = ImageFont.truetype(FONT, 18)
    title_font = ImageFont.truetype(FONT, 16)
    lines = text.replace("\t", "    ").splitlines() or [""]
    padding = 18
    line_height = 24
    title_height = 36
    width = 1100
    max_line = max(font.getlength(line) for line in lines)
    width = max(width, int(max_line) + padding * 2)
    height = title_height + padding * 2 + line_height * len(lines)
    image = Image.new("RGB", (width, height), "#1e1e1e")
    draw = ImageDraw.Draw(image)
    draw.rectangle((0, 0, width, title_height), fill="#333333")
    for color, offset in (("#ff5f57", 16), ("#febc2e", 36), ("#28c840", 56)):
        draw.ellipse((offset, 12, offset + 12, 24), fill=color)
    draw.text((80, 8), title, font=title_font, fill="#dddddd")
    y = title_height + padding
    for line in lines:
        draw.text((padding, y), line, font=font, fill="#d6f5d6")
        y += line_height
    destination.parent.mkdir(parents=True, exist_ok=True)
    image.save(destination)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("source")
    parser.add_argument("destination")
    parser.add_argument("--title", required=True)
    args = parser.parse_args()
    render(Path(args.source).read_text(encoding="utf-8"), Path(args.destination), args.title)


if __name__ == "__main__":
    main()
