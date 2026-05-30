# Matchmind Front/Back Flyer System

This folder contains a reusable two-sided A5 acquisition flyer for the 2026 World Cup. It is designed for pub display, but the printed flyer is intentionally generic: it contains no referral codes, venue codes, or partner attribution.

The QR code links directly to:

```text
https://trymatchmind.com/
```

## Generate Flyers

Run from the repository root:

```bash
python3 scripts/generate_pub_flyer.py
```

The command generates English and Spanish flyers by default. Use `--language en` or `--language es` for one language.

To change the production domain later, pass a plain HTTPS URL without query parameters:

```bash
python3 scripts/generate_pub_flyer.py \
  --destination-url "https://trymatchmind.com/"
```

## Outputs

Generated files are written to `marketing/pub-flyers/generated/`:

- `matchmind-*-a5-front.svg`: editable front vector source
- `matchmind-*-a5-back.svg`: editable back vector source
- `matchmind-*-a5-front-back-print.pdf`: two-page print PDF
- `matchmind-*-a5-front-preview.png`: RGB front preview
- `matchmind-*-a5-back-preview.png`: RGB back preview

The editable source templates are:

- `marketing/pub-flyers/template-a5-front.svg`
- `marketing/pub-flyers/template-a5-back.svg`

## Print Settings

- Print double-sided at actual size, not "fit to page."
- Final trim size: A5 portrait, 148 x 210 mm.
- Supplied PDF page size: 154 x 216 mm, including 3 mm bleed on every edge.
- Ask the printer to trim to A5 and preserve the bleed.
- Confirm the printer's preferred flip edge for portrait duplex printing.
- Use a matte or silk stock around 170-250 gsm for pub display.
- Print one test copy and scan both QR codes from a short distance before bulk printing.

## Tooling

The generator uses macOS Core Image through `scripts/pub_flyer_qr.swift` to create and decode a real QR code. It uses the locally available Python packages Pillow and PyMuPDF to vectorize QR modules, render previews, and create the two-page PDF. No application dependency is added.

Every generation run verifies that the source QR and both rendered side previews decode exactly to the requested URL. It also checks that each print PDF has two `154 x 216 mm` pages.

## Compliance Note

Keep the visible footer on both sides: analysis only, no guarantees, no bet placement, and 18+. Spain-facing public marketing copy and pub distribution still need the short legal review listed in `docs/legal-compliance.md` before broad distribution.
