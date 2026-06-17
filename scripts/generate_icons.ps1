# generate_icons.ps1 — Generate all icon sizes from a master image using ImageMagick
#
# Usage:
#   .\scripts\generate_icons.ps1 path\to\master.png
#
# Requirements:
#   winget install ImageMagick.ImageMagick
#   (or download from https://imagemagick.org/script/download.php#windows)
#
# The master image should be at least 2048x2048px, square, PNG or SVG.

param(
    [string]$Source = ".\frontend\static\icons\master.png"
)

$OUT = "frontend/static/icons"

# ── Checks ────────────────────────────────────────────────────────────────────

if (-not (Test-Path $Source)) {
    Write-Error "Error: file not found — $Source"
    exit 1
}

# Support both 'magick' (ImageMagick 7) and 'convert' (ImageMagick 6)
$IM = $null
if (Get-Command magick -ErrorAction SilentlyContinue) {
    $IM = "magick"
} elseif (Get-Command convert -ErrorAction SilentlyContinue) {
    $IM = "convert"
} else {
    Write-Error "Error: ImageMagick not found."
    Write-Host "  Install: winget install ImageMagick.ImageMagick"
    Write-Host "  Or download from: https://imagemagick.org/script/download.php#windows"
    exit 1
}

New-Item -ItemType Directory -Force -Path $OUT | Out-Null

# ── Warn if icons already exist ───────────────────────────────────────────────

$existing = (Get-ChildItem "$OUT/icon-*.png" -ErrorAction SilentlyContinue) -or
            (Test-Path "$OUT/apple-touch-icon.png") -or
            (Test-Path "frontend/static/favicon.ico")

if ($existing) {
    Write-Host "Warning: existing icons found in $OUT/"
    Write-Host ""
    $confirm = Read-Host "Overwrite them? [y/N]"
    if ($confirm -notmatch "^[Yy]$") {
        Write-Host "Aborted."
        exit 0
    }
    Write-Host ""
}

# Shared flags: Lanczos filter, strip metadata, max PNG compression
function Resize($size, $dest) {
    & $IM $Source -filter Lanczos -strip -define png:compression-level=9 -resize "${size}x${size}" $dest
    if ($LASTEXITCODE -eq 0) { Write-Host "  OK $dest" } else { Write-Error "  FAILED $dest" }
}

Write-Host "Source:  $Source"
Write-Host "Output:  $OUT/"
Write-Host ""

# ── PWA icons ─────────────────────────────────────────────────────────────────

Write-Host "PWA icons..."
Resize 512  "$OUT/icon-512.png"
Resize 384  "$OUT/icon-384.png"
Resize 192  "$OUT/icon-192.png"
Resize 152  "$OUT/icon-152.png"
Resize 144  "$OUT/icon-144.png"

# ── Apple ─────────────────────────────────────────────────────────────────────

Write-Host "Apple icons..."
Resize 180  "$OUT/apple-touch-icon.png"

# ── Favicon ───────────────────────────────────────────────────────────────────

Write-Host "Favicon..."
Resize 48   "$OUT/favicon-48.png"
Resize 32   "$OUT/favicon-32.png"
Resize 16   "$OUT/favicon-16.png"

# Multi-size .ico — goes in static root so browsers find it at /favicon.ico
& $IM "$OUT/favicon-16.png" "$OUT/favicon-32.png" "$OUT/favicon-48.png" "frontend/static/favicon.ico"
if ($LASTEXITCODE -eq 0) { Write-Host "  OK favicon.ico  -> frontend/static/favicon.ico" } else { Write-Error "  FAILED favicon.ico" }

# ── Social media ──────────────────────────────────────────────────────────────

Write-Host "Social media..."
Resize 800  "$OUT/social-800.png"
Resize 400  "$OUT/social-400.png"
Resize 300  "$OUT/social-300.png"
Resize 170  "$OUT/social-170.png"

# ── Done ──────────────────────────────────────────────────────────────────────

Write-Host ""
Write-Host "All icons written to $OUT/"
Write-Host ""
Write-Host "Next steps:"
Write-Host "  1. Check the favicon at 16px — simplify the mark if details are lost"
Write-Host "  2. Copy social-*.png files to each platform's profile settings"
Write-Host "  3. Bump CACHE in frontend/static/sw.js (e.g. panoptiqa-v2) so browsers reload icons"
