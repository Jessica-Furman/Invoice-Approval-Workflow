---
name: upbound-design
description: Use this skill to generate well-branded interfaces and assets for Upbound Group, either for production or throwaway prototypes/mocks/etc. Contains essential design guidelines, colors, type, fonts, assets, and UI kit components for prototyping.
user-invocable: true
---

Read the README.md file within this skill, and explore the other available files.
If creating visual artifacts (slides, mocks, throwaway prototypes, etc), copy assets out and create static HTML files for the user to view. If working on production code, you can copy assets and read the rules here to become an expert in designing with this brand.
If the user invokes this skill without any other guidance, ask them what they want to build or design, ask some questions, and act as an expert designer who outputs HTML artifacts _or_ production code, depending on the need.

## Quick reference
- **Mission:** elevate financial opportunity for all. Gut-check: *does this move the audience upward?*
- **Colors:** Upbound Green `#B3FF33` (accent, ~10% max, never green text on light), Deep Navy `#35323D`, Near Black `#1A1A1A`, Charcoal `#3A3A3B`, Cool Grey `#C3C2C5`, Off White `#F4F4F5`. Follow the 60/30/10 rule (dark / neutral / green).
- **Type:** Poppins for headlines/display, Inter for body/UI. Never reverse; never add a third family. Sentence case; ALL-CAPS only for tracked labels.
- **Signatures:** the 30° diagonal cut (rising left→right) and the green dot as punctuation.
- **Voice:** clear, confident, optimistic, human. "We" / "you". Benefit-first. No emoji, no jargon.
- **Icons:** single-weight, monochrome, rounded line icons (Lucide substitute set via CDN). Green on at most one icon per view.

## Files
- `styles.css` — link this one file to get all tokens + fonts.
- `readme.md` — full design guide (content fundamentals, visual foundations, iconography).
- `tokens/` — CSS custom properties.
- `components/core/` — React primitives (Button, Input, Card, Dialog, …). Load `_ds_bundle.js` and read from `window.UpboundGroupDesignSystem_ca0950`.
- `ui_kits/marketing/` — interactive marketing-site recreation.
- `guidelines/` — foundation specimen cards.

## Logo note
No logo artwork was supplied. Render the brand name **"upbound"** in Poppins (lowercase, semibold), optionally with the green dot, wherever a mark is needed. Do not redraw the real wordmark.
