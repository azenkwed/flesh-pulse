# Category Default Images

Drop one generated image per category into this directory. Use `.webp` files with
these exact filenames:

- `sexual-health-wellness.webp`
- `reproductive-health-policy.webp`
- `maternal-child-health.webp`
- `infectious-diseases-stis.webp`
- `mental-health-sexuality.webp`
- `lgbtq-rights-issues.webp`
- `sex-education-literacy.webp`
- `sexual-violence-consent.webp`
- `sex-workers-adult-industry.webp`

Recommended output:

- Size: `1600 x 900 px`
- Aspect ratio: `16:9` landscape
- Format: WebP
- Quality: `80-85`
- Target file size: `150 KB - 400 KB` each

Good alternatives:

- `1920 x 1080 px` for higher quality
- `1280 x 720 px` for smaller files

## Convert and Size

If a generated PNG is not exactly 16:9, crop and resize it during conversion:

```bash
magick input.png \
  -resize 1600x900^ -gravity center -extent 1600x900 \
  -quality 85 output.webp
```

With copyright watermark:

```bash
magick input.png \
  -resize 1600x900^ -gravity center -extent 1600x900 \
  -gravity southeast \
  -font /System/Library/Fonts/Supplemental/Arial.ttf -pointsize 32 \
  -fill "rgba(255,255,255,0.72)" \
  -undercolor "rgba(0,0,0,0.35)" \
  -annotate +32+32 "© 2026 Sex Health News" \
  -quality 85 output.webp
```

## Shared Style

Use this shared style clause at the end of every prompt:

```text
Editorial documentary-style digital illustration for an independent sexual health news archive, warm and human-centered composition, diverse anonymous individuals, soft natural lighting, modern healthcare aesthetic, no explicit or sexual content, no text, no logos, no UI, no watermark, 16:9 landscape.
```

## Prompts

### Sexual Health & Wellness

```text
A warmly lit healthcare consultation room with anatomical health posters on the wall, wellness brochures fanned on a desk, and a stethoscope resting beside a plant, suggesting supportive and open sexual health care. Editorial documentary-style digital illustration for an independent sexual health news archive, warm and human-centered composition, diverse anonymous individuals, soft natural lighting, modern healthcare aesthetic, no explicit or sexual content, no text, no logos, no UI, no watermark, 16:9 landscape.
```

### Reproductive Health & Policy

```text
A modern clinical desk with contraceptive packaging, a medical intake form, and a blurred government building visible through a rain-streaked window in the background, suggesting the intersection of reproductive medicine and public policy. Editorial documentary-style digital illustration for an independent sexual health news archive, warm and human-centered composition, diverse anonymous individuals, soft natural lighting, modern healthcare aesthetic, no explicit or sexual content, no text, no logos, no UI, no watermark, 16:9 landscape.
```

### Maternal & Child Health

```text
A soft-lit prenatal care room with an ultrasound machine, a handwritten journal open on a side table, and infant health materials on a consultation desk, suggesting attentive maternal care and family support. Editorial documentary-style digital illustration for an independent sexual health news archive, warm and human-centered composition, diverse anonymous individuals, soft natural lighting, modern healthcare aesthetic, no explicit or sexual content, no text, no logos, no UI, no watermark, 16:9 landscape.
```

### Infectious Diseases & STIs

```text
A clinical laboratory workbench with test tubes in a rack, microscope slides, diagnostic result charts, and blue-white overhead light, suggesting medical research and disease prevention. Editorial documentary-style digital illustration for an independent sexual health news archive, warm and human-centered composition, diverse anonymous individuals, soft natural lighting, modern healthcare aesthetic, no explicit or sexual content, no text, no logos, no UI, no watermark, 16:9 landscape.
```

### Mental Health & Sexuality

```text
A quiet therapy office with two chairs facing each other, a notepad and pen on a side table, a potted plant, and soft diffused light through frosted glass, suggesting emotional support, trust, and mental wellness. Editorial documentary-style digital illustration for an independent sexual health news archive, warm and human-centered composition, diverse anonymous individuals, soft natural lighting, modern healthcare aesthetic, no explicit or sexual content, no text, no logos, no UI, no watermark, 16:9 landscape.
```

### LGBTQ+ Rights & Issues

```text
A busy city street during daytime with a large rainbow flag hanging from a building facade and smaller flags visible along the sidewalk, anonymous diverse pedestrians in motion below, warm sunlight catching the colors, suggesting public visibility, pride, and community rights. Editorial documentary-style digital illustration for an independent sexual health news archive, warm and human-centered composition, diverse anonymous individuals, soft natural lighting, modern healthcare aesthetic, no explicit or sexual content, no text, no logos, no UI, no watermark, 16:9 landscape.
```

### Sex Education & Literacy

```text
A community classroom or health center table with open anatomy notebooks, informational health diagrams, and educational materials spread out under bright natural light, suggesting open discussion, learning, and access to knowledge. Editorial documentary-style digital illustration for an independent sexual health news archive, warm and human-centered composition, diverse anonymous individuals, soft natural lighting, modern healthcare aesthetic, no explicit or sexual content, no text, no logos, no UI, no watermark, 16:9 landscape.
```

### Sexual Violence & Consent

```text
An extreme close-up of bare hands raised defensively against encroaching darkness, palms forward, fingers spread, a single harsh directional light source casting sharp shadows, suggesting fear, resistance, and violation of bodily autonomy. Editorial documentary-style digital illustration for an independent sexual health news archive, raw and unflinching composition, no identifiable faces, dramatic chiaroscuro lighting, no explicit or sexual content, no text, no logos, no UI, no watermark, 16:9 landscape.
```

### Sex Workers & Adult Industry

```text
A woman's silhouette standing in a glowing doorway at night, backlit by warm pink and red neon light, fishnet stockings and high heels visible, wet city pavement reflecting the neon colors below, suggesting the adult industry and nightlife without explicit content. Cinematic editorial digital illustration, dramatic neon noir lighting, anonymous figure, no face visible, no nudity, no text, no logos, no UI, no watermark, 16:9 landscape.
```
