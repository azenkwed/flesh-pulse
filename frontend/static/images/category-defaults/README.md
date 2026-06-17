# Category Default Images

Drop one generated image per category into this directory. Use `.webp` files with
these exact filenames:

- `surveillance-privacy.webp`
- `censorship-information-control.webp`
- `authoritarian-governance.webp`
- `corporate-control.webp`
- `climate-collapse.webp`
- `ai-technology-control.webp`
- `economic-oppression.webp`
- `war-militarization.webp`
- `biopolitics-body-control.webp`

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

With the text watermark:

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

Use this shared style clause for every image:

```text
Editorial documentary-style digital illustration for an independent news archive, realistic but not depicting identifiable real people, cinematic natural lighting, restrained color palette, high detail, no text, no logos, no flags, no UI, no watermark, 16:9 landscape.
```

## Prompts

### Surveillance & Privacy

```text
A dense modern city at dusk with security cameras, phone screens, and soft reflections in glass suggesting digital monitoring and privacy erosion, no identifiable people. Editorial documentary-style digital illustration for an independent news archive, realistic but not depicting identifiable real people, cinematic natural lighting, restrained color palette, high detail, no text, no logos, no flags, no UI, no watermark, 16:9 landscape.
```

### Censorship & Information Control

```text
A quiet newsroom desk with scattered papers, a darkened monitor, crossed-out newspaper columns, and a muted printing press in the background, suggesting blocked information and media pressure. Editorial documentary-style digital illustration for an independent news archive, realistic but not depicting identifiable real people, cinematic natural lighting, restrained color palette, high detail, no text, no logos, no flags, no UI, no watermark, 16:9 landscape.
```

### Authoritarian Governance

```text
An imposing government building seen from a public square through rain-streaked glass, with distant anonymous silhouettes and stark security barriers, suggesting concentrated state power. Editorial documentary-style digital illustration for an independent news archive, realistic but not depicting identifiable real people, cinematic natural lighting, restrained color palette, high detail, no text, no logos, no flags, no UI, no watermark, 16:9 landscape.
```

### Corporate Control

```text
A towering corporate office interior with reflective glass, abstract data charts, and small anonymous workers below, suggesting market concentration and algorithmic management. Editorial documentary-style digital illustration for an independent news archive, realistic but not depicting identifiable real people, cinematic natural lighting, restrained color palette, high detail, no text, no logos, no flags, no UI, no watermark, 16:9 landscape.
```

### Climate Collapse

```text
A city edge under extreme weather, cracked dry ground in the foreground and floodwater reflecting distant buildings, suggesting environmental instability and climate risk. Editorial documentary-style digital illustration for an independent news archive, realistic but not depicting identifiable real people, cinematic natural lighting, restrained color palette, high detail, no text, no logos, no flags, no UI, no watermark, 16:9 landscape.
```

### AI & Technology Control

```text
A server room and urban transit platform blended together, with abstract machine-vision light patterns tracking anonymous silhouettes, suggesting AI systems shaping public life. Editorial documentary-style digital illustration for an independent news archive, realistic but not depicting identifiable real people, cinematic natural lighting, restrained color palette, high detail, no text, no logos, no flags, no UI, no watermark, 16:9 landscape.
```

### Economic Oppression

```text
A stark urban street with a luxury high-rise reflected in a closed storefront window, unpaid bills and job notices on a table, suggesting inequality and financial pressure. Editorial documentary-style digital illustration for an independent news archive, realistic but not depicting identifiable real people, cinematic natural lighting, restrained color palette, high detail, no text, no logos, no flags, no UI, no watermark, 16:9 landscape.
```

### War & Militarization

```text
An empty checkpoint road at dawn with armored vehicles in the distance, surveillance lights, and concrete barriers, suggesting militarization without active violence. Editorial documentary-style digital illustration for an independent news archive, realistic but not depicting identifiable real people, cinematic natural lighting, restrained color palette, high detail, no text, no logos, no flags, no UI, no watermark, 16:9 landscape.
```

### Biopolitics & Body Control

```text
A clinical public health checkpoint with biometric scanners, medical forms, and anonymous silhouettes waiting under cool fluorescent light, suggesting bodily governance and institutional control. Editorial documentary-style digital illustration for an independent news archive, realistic but not depicting identifiable real people, cinematic natural lighting, restrained color palette, high detail, no text, no logos, no flags, no UI, no watermark, 16:9 landscape.
```
