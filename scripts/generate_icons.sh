#!/usr/bin/env bash
# generate_icons.sh — Generate all icon sizes from a master image using ImageMagick
#
# Usage:
#   ./scripts/generate_icons.sh path/to/master.png
#
# Requirements:
#   macOS:  brew install imagemagick
#   Linux:  sudo apt install imagemagick
#
# The master image should be at least 2048×2048px, square, PNG or SVG.

set -e

INPUT="${1:-frontend/static/icons/master.png}"
OUT="frontend/static/icons"

# ── Checks ────────────────────────────────────────────────────────────────────

if [[ ! -f "$INPUT" ]]; then
  echo "Error: file not found — $INPUT"
  exit 1
fi

# Support both 'magick' (ImageMagick 7) and 'convert' (ImageMagick 6)
if command -v magick &>/dev/null; then
  IM="magick"
elif command -v convert &>/dev/null; then
  IM="convert"
else
  echo "Error: ImageMagick not found."
  echo "  macOS:  brew install imagemagick"
  echo "  Linux:  sudo apt install imagemagick"
  exit 1
fi

mkdir -p "$OUT"

# ── Warn if icons already exist ───────────────────────────────────────────────

if ls "$OUT"/icon-*.png "$OUT"/apple-touch-icon.png "frontend/static/favicon.ico" \
      &>/dev/null 2>&1; then
  echo "Warning: existing icons found in $OUT/"
  echo ""
  read -r -p "Overwrite them? [y/N] " CONFIRM
  if [[ ! "$CONFIRM" =~ ^[Yy]$ ]]; then
    echo "Aborted."
    exit 0
  fi
  echo ""
fi

# Shared flags:
#   -filter Lanczos     best quality for downscaling
#   -strip              remove EXIF/metadata
#   -define png:compression-level=9   smallest file size
RESIZE="$IM $INPUT -filter Lanczos -strip -define png:compression-level=9"

echo "Source:  $INPUT"
echo "Output:  $OUT/"
echo ""

# ── PWA icons ─────────────────────────────────────────────────────────────────

echo "PWA icons..."
$RESIZE -resize 512x512   "$OUT/icon-512.png"   && echo "  ✓ icon-512.png"
$RESIZE -resize 384x384   "$OUT/icon-384.png"   && echo "  ✓ icon-384.png"
$RESIZE -resize 192x192   "$OUT/icon-192.png"   && echo "  ✓ icon-192.png"
$RESIZE -resize 152x152   "$OUT/icon-152.png"   && echo "  ✓ icon-152.png"
$RESIZE -resize 144x144   "$OUT/icon-144.png"   && echo "  ✓ icon-144.png"

# ── Apple ─────────────────────────────────────────────────────────────────────

echo "Apple icons..."
$RESIZE -resize 180x180   "$OUT/apple-touch-icon.png" && echo "  ✓ apple-touch-icon.png"

# ── Favicon ───────────────────────────────────────────────────────────────────

echo "Favicon..."
$RESIZE -resize 48x48     "$OUT/favicon-48.png" && echo "  ✓ favicon-48.png"
$RESIZE -resize 32x32     "$OUT/favicon-32.png" && echo "  ✓ favicon-32.png"
$RESIZE -resize 16x16     "$OUT/favicon-16.png" && echo "  ✓ favicon-16.png"

# Multi-size .ico — goes in static root so browsers find it at /favicon.ico
$IM "$OUT/favicon-16.png" "$OUT/favicon-32.png" "$OUT/favicon-48.png" \
    "frontend/static/favicon.ico" && echo "  ✓ favicon.ico  → frontend/static/favicon.ico"

# ── Social media ──────────────────────────────────────────────────────────────

echo "Social media..."
$RESIZE -resize 800x800   "$OUT/social-800.png" && echo "  ✓ social-800.png  (YouTube)"
$RESIZE -resize 400x400   "$OUT/social-400.png" && echo "  ✓ social-400.png  (Twitter / X)"
$RESIZE -resize 300x300   "$OUT/social-300.png" && echo "  ✓ social-300.png  (LinkedIn)"
$RESIZE -resize 170x170   "$OUT/social-170.png" && echo "  ✓ social-170.png  (Facebook)"

# ── Done ──────────────────────────────────────────────────────────────────────

echo ""
echo "All icons written to $OUT/"
echo ""
echo "Next steps:"
echo "  1. Check the favicon at 16px — simplify the mark if details are lost"
echo "  2. Copy social-*.png files to each platform's profile settings"
echo "  3. Bump CACHE in frontend/static/sw.js (e.g. flesh-pulse-v2) so browsers reload icons"
