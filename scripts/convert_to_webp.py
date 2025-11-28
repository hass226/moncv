#!/usr/bin/env python3
import sys
from pathlib import Path

def convert(path: Path, quality=85):
    try:
        from PIL import Image
    except ImportError:
        print("Pillow n'est pas installé. Exécutez: python3 -m pip install --user Pillow")
        raise
    p = Path(path)
    if not p.exists():
        print(f"Fichier introuvable: {p}")
        return 1
    out = p.with_suffix('.webp')
    try:
        img = Image.open(p)
        if img.mode in ("RGBA", "LA"):
            img = img.convert('RGBA')
        else:
            img = img.convert('RGB')
        img.save(out, 'WEBP', quality=quality, method=6)
        print(f"Converti {p} -> {out}")
        return 0
    except Exception as e:
        print(f"Erreur lors de la conversion de {p}: {e}")
        return 2

if __name__ == '__main__':
    if len(sys.argv) < 2:
        print("Usage: convert_to_webp.py <image1.jpg> [image2.jpg ...]")
        sys.exit(1)
    rc = 0
    for a in sys.argv[1:]:
        rc |= convert(a)
    sys.exit(rc)
