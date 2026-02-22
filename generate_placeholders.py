"""
Generate placeholder PNG sprites for all catalog items.

Run this once if your real sprite assets are not yet in assets/sprites/:

    python generate_placeholders.py

Each sprite is a coloured rounded rectangle with the item label on it.
Place your real PNG files with the same filenames to override them.
"""
from __future__ import annotations

import json
import os

import pygame

HERE        = os.path.dirname(os.path.abspath(__file__))
CATALOG     = os.path.join(HERE, "assets", "sprites", "catalog.json")
SPRITES_DIR = os.path.join(HERE, "assets", "sprites")


def main() -> None:
    pygame.init()
    # Off-screen surface — no window needed
    pygame.display.set_mode((1, 1), pygame.NOFRAME)

    font_lg = pygame.font.SysFont("Arial", 14, bold=True)
    font_sm = pygame.font.SysFont("Arial", 11)

    with open(CATALOG, "r", encoding="utf-8") as f:
        data = json.load(f)

    created = 0
    skipped = 0

    for item in data["items"]:
        out_path = os.path.join(SPRITES_DIR, item["sprite"])
        if os.path.isfile(out_path):
            skipped += 1
            continue

        w = item.get("nominal_w", 80)
        h = item.get("nominal_h", 80)
        colour = tuple(item.get("color", [120, 120, 120]))

        surf = pygame.Surface((w, h), pygame.SRCALPHA)
        # Background rounded rect
        bg = colour + (220,)
        pygame.draw.rect(surf, bg, pygame.Rect(0, 0, w, h), border_radius=8)
        # Border
        pygame.draw.rect(surf, (255, 255, 255, 150), pygame.Rect(0, 0, w, h), 2, border_radius=8)

        # Label — two lines if needed
        words = item["label"].split()
        lines = []
        line = ""
        for word in words:
            test = (line + " " + word).strip()
            if font_lg.size(test)[0] < w - 8:
                line = test
            else:
                if line:
                    lines.append(line)
                line = word
        if line:
            lines.append(line)

        total_text_h = len(lines) * font_lg.get_linesize()
        ty = (h - total_text_h) // 2
        for ln in lines:
            txt = font_lg.render(ln, True, (255, 255, 255))
            surf.blit(txt, ((w - txt.get_width()) // 2, ty))
            ty += font_lg.get_linesize()

        pygame.image.save(surf, out_path)
        created += 1
        print(f"  Created: {item['sprite']}")

    print(f"\nDone. {created} sprites created, {skipped} already existed.")
    pygame.quit()


if __name__ == "__main__":
    main()
