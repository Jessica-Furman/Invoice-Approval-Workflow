# Upbound Group — Design System

> **Mission:** To elevate financial opportunity for all.

Upbound Group is a modern, enterprise-focused organization. The brand expresses **forward momentum, clarity, and confidence** — optimistic and ambitious, but grounded and trustworthy. Every expression, visual or verbal, should reinforce a sense of upward motion, progress, and positive trajectory. The internal gut-check: *does this move the audience upward?*

This design system turns the Upbound Group brand guidelines (v1.0, 2026) into working tokens, components, specimen cards, a product UI kit, and slide templates so any designer or agent can produce on-brand work fast.

## Sources

- `uploads/Upbound_Group_Brand_Guidelines.txt` — the master brand guidelines (visual & verbal identity standards, v1.0). Everything here derives from that document.
- No codebase, Figma file, product screenshots, or logo artwork were provided. Components, the UI kit, and slides are **original interpretations built strictly from the written guidelines** — not recreations of an existing product.

---

## CONTENT FUNDAMENTALS

How Upbound writes. The voice is a **confident, optimistic guide**: plain-spoken, benefit-first, always conveying forward motion. Tone adapts to the moment (enterprise partner, investor, candidate) but the voice never changes.

- **We are:** clear and direct · confident and optimistic · warm and human · ambitious but grounded.
- **We're not:** jargon-heavy or corporate-stiff · hyped or overpromising · cold or transactional · vague or wishy-washy.
- **Person:** speak as "we"; address the reader as "you." Lead with the benefit *to the reader*.
- **Casing:** sentence case for headlines and body (never Title Case sentences). ALL CAPS only for tracked labels/eyebrows and sub-brand descriptors.
- **Punctuation:** clean and calm. The green dot can punctuate the end of a statement or a sub-brand name — sparingly.
- **Emoji:** not used. This is an enterprise financial brand; keep copy typographic.
- **Numbers/stats:** used only when they earn their place (key data gets the green accent). No data slop.

**In practice**
- ❌ *"We leverage synergistic solutions to optimize stakeholder outcomes."*
- ✅ **"We help people move their finances forward."**

Voice at a glance: **Clear · Confident · Optimistic · Human.**

---

## VISUAL FOUNDATIONS

**Color.** A bold, energetic green paired with deep, sophisticated darks. The **60 / 30 / 10 rule** governs every composition: 60% dark foundation (Deep Navy `#35323D`, Near Black `#1A1A1A`, Charcoal `#3A3A3B`), 30% neutrals (Off White `#F4F4F5`, Cool Grey `#C3C2C5`) for space and legibility, 10% **Upbound Green `#B3FF33`** as the accent. Green never dominates and is **never** used as text on light/grey/navy — it is a background behind near-black text (buttons) or a small accent on dark surfaces. One clear green call-to-action per view.

**Type.** Two families only. **Poppins** (geometric sans, rounded terminals — echoes the wordmark) for headlines, display, subheads, pull quotes. **Inter** (neutral grotesque) for body, UI, captions, long-form. Never reverse the pairing; never add a third family. Hierarchy comes from weight and size, not new fonts. Body copy stays in a single Inter weight for calm, readable blocks. Display/H1 is Bold sentence case with tight leading; labels are Inter Bold, all-caps, tracked. Office/email fallback is Arial or Calibri only.

**Backgrounds.** No gradient soup, no busy textures. Surfaces are flat: dark navy/near-black for hero and premium moments, off-white for light sections. Photography is real, candid, optimistic, diverse people in natural light — never stiff stock clichés. The imagery vibe is warm and human, not cold or over-processed.

**The Diagonal.** A dynamic diagonal cut (~30°, rising left to right) is a recurring device — dividing image from surface, or navy from grey. It reinforces upward motion and gives layouts energy. Keep the angle consistent.

**The Green Dot.** A small green dot / accent shape is the brand's signature "spark." Use it to punctuate — beside a sub-brand name, at the end of a statement, as a bullet — never as decoration for its own sake.

**Spacing & layout.** 4px base scale. Generous whitespace; neutrals carry the breathing room. Content maxes around 1200px; long-form narrows to ~760px.

**Corner radii.** Approachable but not bubbly, echoing the rounded wordmark — 8–12px on cards and inputs, pill radius for tags/small buttons, full circle for the dot. Nothing sharp-cornered, nothing overly round.

**Cards.** Flat white (or charcoal on dark) with a hairline border and a soft, single-layer cool-toned shadow (`--shadow-sm`/`--shadow-md`). No colored left-border accents, no heavy drop shadows.

**Borders & shadows.** Hairline 1px borders in cool greys. Shadows are soft, single-layer, low-opacity near-black — used for lift, not drama. No inner shadows as a rule.

**Animation.** Quick and confident, never bouncy. Durations 120–280ms, ease-out for entrances (`cubic-bezier(0.22, 1, 0.36, 1)`). Fades and short upward translations (a few px rising) suit the "upbound" idea. Respect `prefers-reduced-motion`. No infinite decorative loops.

**Hover states.** Green buttons darken slightly (`--up-green-hover`). Text/links reduce opacity (~0.7). Dark surfaces lighten to a subtle raised tone. Cards lift with a slightly deeper shadow.

**Press states.** A small scale-down (~0.98) and/or a touch darker. Fast (`--dur-fast`).

**Transparency & blur.** Used minimally — dividers on dark use low-alpha cool grey; occasional translucent overlay on imagery for text legibility. No frosted-glass everywhere.

---

## ICONOGRAPHY

The guidelines specify: **simple, geometric line icons with rounded corners, single weight, monochrome** — with green reserved for the one element that matters most. There is no supplied icon font or SVG set.

- **Substitution (flagged):** we use **[Lucide](https://lucide.dev)** via CDN — geometric, single-weight, rounded-corner line icons that match the described style closely. Default stroke width `1.75`, `currentColor`. This is a substitution for a not-yet-supplied brand icon set; if Upbound has an official icon library, please share it and we'll swap it in.
- **Usage:** monochrome (inherit text color). Reserve green for at most one icon in a view. Match icon stroke weight to the surrounding type weight; don't mix filled and line styles.
- **Emoji / unicode as icons:** never.
- The `Icon` component wraps Lucide so consumers get consistent sizing and the single-weight rule for free.

---

## Logo

**No logo artwork was supplied.** The Upbound wordmark is described as a distinctive rounded lowercase sans-serif (Poppins-like), set in black on light and white on dark, with full-color green reserved for small accents. Per system rules we do **not** redraw or reconstruct the real mark. Wherever a logo would go, we render the brand name **"upbound"** in plain Poppins type (lowercase, semibold) as a stand-in, optionally followed by the green dot. **Please supply the official wordmark files** (black + white) to replace the type stand-in.

Sub-brand lockups (e.g. *Upbound Digital*): "upbound" wordmark with an all-caps, letter-spaced descriptor set below it, descriptor in Upbound Green on dark surfaces, never larger than the wordmark.

---

## Index / Manifest

**Root**
- `styles.css` — global entry point (imports all tokens + fonts + base). Consumers link this one file.
- `readme.md` — this document.
- `SKILL.md` — portable Agent-Skill wrapper.

**`tokens/`** — `fonts.css` (Poppins + Inter), `colors.css`, `typography.css`, `spacing.css` (radii/shadows/motion), `base.css` (element defaults).

**`guidelines/`** — foundation specimen cards (Colors, Type, Spacing, Brand) shown in the Design System tab.

**`components/core/`** — reusable primitives: Button, IconButton, Icon, Input, Textarea, Select, Checkbox, Radio, Switch, Card, Badge, Tag, Tabs, Dialog, Toast, Tooltip. Each has `.jsx` + `.d.ts` + `.prompt.md`; the group card is `components/core/core.card.html`.

**`ui_kits/marketing/`** — Upbound Group marketing site recreation (hero, product, investors, careers) as interactive click-through screens composing the core components.

**`slides/`** — branded slide templates (title, section, content, big quote, stat, comparison, closing) at 1280×720.

### Intentional additions
Since no source defined a component inventory, a standard primitive set was authored, sized to the brand. **`Icon`** wraps the Lucide substitute set so the single-weight/monochrome rule is enforced centrally.
