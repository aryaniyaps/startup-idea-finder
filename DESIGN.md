---
name: Scout — Startup Idea Dashboard
description: AI-powered startup idea discovery. Expedition Log design system.
colors:
  primary: "#e3a83b"
  primary-hover: "#f0b84a"
  primary-muted: "#8a6d2c"
  bg: "#191613"
  surface: "#221e1a"
  surface-raised: "#2b2722"
  border: "#3a352e"
  ink: "#ece7df"
  ink-secondary: "#a09888"
  ink-tertiary: "#6b6559"
  accent: "#5a9e8c"
  green: "#4d9e5c"
  blue: "#5f8eb5"
  yellow: "#c49b32"
  red: "#b84a3c"
  gold: "#eab540"
  silver: "#b0a898"
  bronze: "#9a7142"
  muted-gray: "#56524a"
typography:
  display:
    fontFamily: "Inter Display, Inter, system-ui, -apple-system, sans-serif"
    fontSize: "clamp(2rem, 5vw, 3rem)"
    fontWeight: 600
    lineHeight: 1.15
    letterSpacing: "-0.02em"
  headline:
    fontFamily: "Inter, system-ui, -apple-system, sans-serif"
    fontSize: "1.25rem"
    fontWeight: 600
    lineHeight: 1.3
  body:
    fontFamily: "Inter, system-ui, -apple-system, sans-serif"
    fontSize: "0.875rem"
    fontWeight: 400
    lineHeight: 1.6
  label:
    fontFamily: "Inter, system-ui, -apple-system, sans-serif"
    fontSize: "0.7rem"
    fontWeight: 600
    letterSpacing: "0.04em"
    textTransform: "uppercase"
rounded:
  sm: "4px"
  md: "8px"
  lg: "12px"
spacing:
  xs: "4px"
  sm: "8px"
  md: "16px"
  lg: "24px"
  xl: "32px"
components:
  button-primary:
    backgroundColor: "{colors.primary}"
    textColor: "#191613"
    rounded: "{rounded.md}"
    padding: "8px 20px"
  button-primary-hover:
    backgroundColor: "{colors.primary-hover}"
    textColor: "#191613"
    rounded: "{rounded.md}"
    padding: "8px 20px"
  button-ghost:
    backgroundColor: "transparent"
    textColor: "{colors.ink-secondary}"
    rounded: "{rounded.md}"
    padding: "8px 20px"
  badge-strong:
    backgroundColor: "oklch(60% 0.11 150 / 0.18)"
    textColor: "{colors.green}"
    rounded: "12px"
  badge-promising:
    backgroundColor: "oklch(58% 0.07 235 / 0.18)"
    textColor: "{colors.blue}"
    rounded: "12px"
  badge-weak:
    backgroundColor: "oklch(65% 0.1 85 / 0.18)"
    textColor: "{colors.yellow}"
    rounded: "12px"
  badge-tarpit:
    backgroundColor: "oklch(50% 0.13 25 / 0.18)"
    textColor: "{colors.red}"
    rounded: "12px"
  card-stat:
    backgroundColor: "{colors.surface}"
    rounded: "{rounded.md}"
    padding: "12px 20px"
  table-row-hover:
    backgroundColor: "oklch(26% 0.006 70)"
---

# Design System: Scout — The Expedition Log

## 1. Overview

**Creative North Star: "The Expedition Log"**

Scout is an explorer's instrument — a field journal and star chart for startup ideas. The interface evokes a late-night study: lamplight pooling on a leather-bound journal, warmth against the dark, the quiet thrill of prospecting. Each idea is a discovered landmark, not a database row.

The system is built on a warm dark palette anchored by amber gold — the color of lamplight on a desk. It rejects the cold blue-gray severity of developer tools (the current GitHub-dark baseline) and the generic SaaS dashboard template entirely. Surfaces are deep and warm, typography is precise but human, and motion is restrained to state transitions — the user is in flow, not watching a show.

This is a product surface (design SERVES the task), so consistency and density are virtues. But it's also a personal instrument — it should feel crafted and alive, not sterile. Delight lives in the warmth of the palette and the precision of the typography, not in decorative motion or novel affordances.

**Key Characteristics:**
- Warm dark: deep brown-black base with amber lamplight accent
- Product-first: system sans-serif stack, consistent component vocabulary, WCAG AA
- Restrained motion: 150–200ms state transitions only, no choreographed sequences
- Flat-by-default elevation: tonal layering over shadow stacks
- Opinionated, not configurable: this is one founder's instrument

## 2. Colors

**Warm Hearth.** The palette anchors on deep warm darks (leather, shadowed wood) illuminated by amber gold (lamplight). Every color is warmed relative to its conventional counterpart — greens pull sage, blues pull steel, reds pull brick. Nothing blue-cast. Nothing cold.

### Primary
- **Amber Gold** (`#e3a83b`, canonical `oklch(72% 0.15 80)`): Primary actions, selected states, active indicators. The color of lamplight. Used for the main CTA button, active nav items, and score highlights. On dark backgrounds it reads as luminous without glowing.

- **Amber Hover** (`#f0b84a`, canonical `oklch(78% 0.15 80)`): Hover and focus states for primary elements. Brighter, more energetic — the lamp flares slightly on interaction.

- **Amber Muted** (`#8a6d2c`, canonical `oklch(50% 0.08 80)`): Subtle amber highlights — table row selection glow, decorative rules under 1px, focus ring inner glow. Never used for text; too muted to hold readable contrast.

### Secondary
- **Warm Teal** (`#5a9e8c`, canonical `oklch(58% 0.08 190)`): Secondary accent. Links, info badges, subtle highlights that need to read as distinct from amber. The cool counterpoint — like oxidized copper on a leather journal — without going clinical.

### Neutral
- **Expedition Black** (`#191613`, canonical `oklch(16% 0.006 70)`): Page background. Deep brown-black — the color of a leather journal cover in low light. Never pure black; carries a trace of amber warmth.

- **Journal Surface** (`#221e1a`, canonical `oklch(20% 0.006 70)`): Cards, panels, filter bars. Slightly lifted from the background, same warm undertone.

- **Raised Surface** (`#2b2722`, canonical `oklch(24% 0.006 70)`): Hover states, active panels, detail views. The highest resting surface before borders take over.

- **Warm Border** (`#3a352e`, canonical `oklch(30% 0.005 70)`): Dividers, table borders, card edges. Present but recessive — structural, not decorative.

- **Lamplight Ink** (`#ece7df`, canonical `oklch(92% 0.005 80)`): Primary body text. Warm cream-white — the color of paper under lamplight. ≥10:1 contrast against the background.

- **Faded Ink** (`#a09888`, canonical `oklch(65% 0.006 80)`): Secondary text, placeholders, metadata. Dimmer but still ≥5:1 against the background.

- **Quiet Ink** (`#6b6559`, canonical `oklch(48% 0.004 80)`): Tertiary text, disabled states, timestamps. ≥4:1 against raised surfaces, sufficient for non-critical labels.

### Semantic
- **Success Green** (`#4d9e5c`, canonical `oklch(60% 0.11 150)`): STRONG verdict badges, positive indicators, connection status. A warm sage green — alive but muted, not neon.

- **Info Blue** (`#5f8eb5`, canonical `oklch(58% 0.07 235)`): PROMISING verdict badges, links (when teal feels too cool). Warmed steel blue.

- **Caution Ochre** (`#c49b32`, canonical `oklch(65% 0.1 85)`): WEAK verdict badges, warning indicators. Pulled from the amber family but yellower, less precious.

- **Alert Brick** (`#b84a3c`, canonical `oklch(50% 0.13 25)`): TARPIT verdict, REJECT, errors, destructive actions. A warm brick red — urgent but not synthetic.

- **Tier Gold** (`#eab540`, canonical `oklch(72% 0.15 85)`): Tier 1 source badge. Distinct from primary amber — slightly yellower, more precious.

- **Tier Silver** (`#b0a898`, canonical `oklch(68% 0.02 80)`): Tier 2 source badge. Warm silver, not cool gray.

- **Tier Bronze** (`#9a7142`, canonical `oklch(54% 0.08 50)`): Tier 3 source badge. Earthy copper-bronze.

### Named Rules
**The Lamplight Rule.** The amber primary accent carries ≤15% of any screen's surface area. Its rarity is what makes it luminous. If amber appears everywhere — every button, every highlight, every border — it stops being lamplight and becomes wallpaper.

**The No Cold Blue Rule.** No color on the screen may have hue ≤210° (true blue through violet). The coldest permitted hue is warm teal (190°). The current GitHub-dark palette's `#58a6ff` blue accent is prohibited.

**The Semantic Warmth Rule.** Every semantic color pulls warmer than its conventional hex. Green pulls toward sage (150° not 140°). Blue pulls toward steel (235° not 220°). Red pulls toward brick (25° not 10°). The result: status colors that feel like they belong to the same journal, not imported from a different palette.

## 3. Typography

**Primary Font:** Inter (with Inter Display for large headings)
**Fallback Stack:** system-ui, -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif
**Mono (for data):** 'JetBrains Mono', 'Fira Code', ui-monospace, monospace

**Character:** Inter's humanist touches — open apertures, slightly angled terminals, generous x-height — bring warmth to a product sans-serif. It reads as approachable without sacrificing precision. Inter Display tightens the spacing for headings where impact matters.

### Hierarchy
- **Display** (600, `clamp(2rem, 5vw, 3rem)`, 1.15, -0.02em): Idea detail titles, empty state headlines. Used sparingly — no more than once per view. `text-wrap: balance`.

- **Headline** (600, `1.25rem`, 1.3): Section headers, detail panel titles, stat card labels. The workhorse heading weight. `text-wrap: balance`.

- **Body** (400, `0.875rem`, 1.6): Primary content, descriptions, justifications. Capped at 70ch for prose blocks. Tighter in table cells (inherently constrained).

- **Label** (600, `0.7rem`, 1.4, 0.04em, uppercase): Table headers, badge text, stat labels, filter labels. Small but legible. Never used as decorative eyebrows above unrelated sections.

- **Mono** (450, `0.8rem`, 1.5): Score values in table cells, IDs, timestamps. Tabular figures for alignment (`font-variant-numeric: tabular-nums`).

### Named Rules
**The One Family Rule.** One sans-serif family for everything. Inter carries headings, body, labels, and UI chrome. No display/body pairing. Product UI doesn't need font contrast; it needs font consistency.

**The No Eyebrow Rule.** Labels appear only where they label something functional (table columns, form fields, stat cards). They never appear as standalone decorative kickers above sections. No "DISCOVER" / "EXPLORE" / "ANALYZE" eyebrows.

## 4. Elevation

The system is flat by default. Depth is conveyed through tonal layering (lighter surfaces on darker backgrounds) rather than shadow stacks. This keeps the interface feeling like a flat journal page rather than a 3D desktop application.

### Shadow Vocabulary
Shadows are reserved for state, not rest:
- **Hover Glow** (`0 0 0 1px oklch(72% 0.15 80 / 0.3)`): Applied to interactive elements on hover — table rows, filter buttons, clickable cards. A subtle amber ring, not a drop shadow.
- **Focus Ring** (`0 0 0 2px oklch(16% 0.006 70), 0 0 0 4px oklch(72% 0.15 80 / 0.5)`): Standard focus-visible indicator. Double ring: dark gap + amber outer.
- **Toast Float** (`0 4px 24px oklch(0% 0 0 / 0.4)`): The toast notification is the only element that casts a genuine shadow — it floats above the page.

### Named Rules
**The Flat-At-Rest Rule.** No surface casts a shadow in its default state. Shadows appear only as interaction feedback (hover, focus) or for floating elements (toast). If a shadow is always visible, it's wrong.

## 5. Components

### Buttons
- **Shape:** Rounded-rectangle, 8px radius. Clean but not pill-soft.
- **Primary:** Amber Gold background (`oklch(72% 0.15 80)`), deep brown-black text (`#191613`). 8px vertical × 20px horizontal padding. `font-weight: 600`. Used for the single most important action on screen — Filter, Score, Refresh.
- **Primary Hover:** `oklch(78% 0.15 80)` background. 150ms ease transition on background-color. No transform, no shadow — just the lamp flares brighter.
- **Primary Focus:** Standard focus ring (see Elevation).
- **Ghost:** Transparent background, Faded Ink text (`#a09888`). 8px vertical × 20px horizontal padding. Hover shifts text to Lamplight Ink and adds a Warm Border outline. Used for secondary actions — Refresh when Filter is primary, Close detail panel.
- **Loading:** Ghost state with spinner replacing text. Primary button shows spinner inline with dimmed text. Never disabled; always shows the loading state.

### Badges & Chips
- **Verdict Badges:** Pill shape (12px radius). Translucent background at 18% opacity over verdict color, solid verdict color text. 2px vertical × 10px horizontal padding. Uppercase, 600 weight, 0.7rem. Five variants: STRONG (green), PROMISING (blue), WEAK (yellow), TARPIT (red), REJECT (muted).
- **Tier Badges:** Same pill shape. Distinct from verdict badges by their metal-named colors: Gold (T1), Silver (T2), Bronze (T3), Muted Gray (T4-5). Smaller text (0.65rem).

### Cards
- **Stat Cards:** Journal Surface background (`#221e1a`), 8px radius, 1px Warm Border. 12px vertical × 20px horizontal padding. Contains a label (uppercase, Faded Ink) and a value (1.4rem, 700 weight, Lamplight Ink). Min-width 100px. Used in the stats bar.
- **Detail Cards:** Expedition Black background (`#191613`), 8px radius, 1px Warm Border. 14px padding. Contains a label (uppercase, Faded Ink), a large score (1.8rem, 700 weight), and metadata (Faded Ink, 0.8rem). Used in the detail panel grid.
- **Justification Card:** Same structure as detail card but with prose body text. Expedition Black background, no border accent. Used for LLM-generated justifications.

### Data Table
- **Header:** Uppercase labels (0.7rem, 600 weight), Faded Ink. 2px Warm Border bottom.
- **Rows:** 1px Warm Border bottom between rows. 10px vertical × 12px horizontal cell padding.
- **Hover:** Row background shifts to `oklch(26% 0.006 70)` — a subtle warm lift. 150ms transition on background-color. Cursor: pointer.
- **Empty state:** Centered, Faded Ink text, 60px padding. Teaches the interface: "No ideas scored yet. Start the pipeline to begin discovering."

### Filters Bar
- **Container:** Journal Surface background, 8px radius, 1px Warm Border, 12px padding.
- **Select inputs:** Expedition Black background, Lamplight Ink text, 1px Warm Border, 4px radius. Min-width 120px.
- **Range input:** Standard HTML range, styled with amber track and thumb. Expedition Black background.

### Toast Notification
- **Container:** Fixed bottom-right, Journal Surface background, 1px Success Green left border (NOT a side-stripe — a full border with the left edge colored), 8px radius. 12px vertical × 20px horizontal padding.
- **Animation:** Fade in + slide up (opacity 0→1, translateY 10px→0). 300ms ease-out. After 3s, reverse and remove.
- **Reduced motion:** Fade only, no translation.

### Detail Panel
- **Container:** Journal Surface background, 8px radius, 1px Warm Border, 20px padding. Hidden by default (`display: none`), shown on row click.
- **Header:** Headline (1.2rem, 600 weight) with close button (×, Faded Ink, 1.5rem).
- **Grid:** `repeat(auto-fit, minmax(240px, 1fr))` for responsive detail cards.
- **Tarpit Warning:** Detail card variant with 1px Alert Brick border and Alert Brick heading. Pre-formatted JSON in mono font.

### Spinner
- 24px circle, 2px Warm Border track, 2px Amber Gold top border. `animation: spin 0.8s linear infinite`.
- **Reduced motion:** Hidden. Show static "Loading…" text instead.

## 6. Do's and Don'ts

### Do:
- **Do** use the amber primary accent on ≤15% of any screen. One primary button, selected states, and the focus ring. That's it.
- **Do** use tonal layering (Expedition Black → Journal Surface → Raised Surface) to convey hierarchy instead of shadows.
- **Do** keep body text at ≥0.875rem and ≥4.5:1 contrast against its background.
- **Do** use `text-wrap: balance` on headings and `text-wrap: pretty` on prose justification blocks.
- **Do** warm every semantic color — green toward sage, blue toward steel, red toward brick. No clinical hex values.
- **Do** use the mono font stack for scores, IDs, and timestamps in table cells. Tabular figures.
- **Do** show a loading spinner for async operations, never a blank screen or disabled button.
- **Do** include `@media (prefers-reduced-motion: reduce)` alternatives for every animation and transition.

### Don't:
- **Don't** use cold blue-gray (`#58a6ff`, GitHub's blue accent) or any hue ≤210°. The coldest permitted hue is warm teal (190°).
- **Don't** use generic SaaS dashboard patterns: blue sidebar, white cards, chart widgets, hero-metric templates.
- **Don't** use glassmorphism, gradient text, or decorative blur effects.
- **Don't** use side-stripe borders (`border-left: 3px solid`) as colored accents on cards or list items.
- **Don't** use tiny uppercase tracked eyebrows above sections ("DISCOVER", "ANALYZE", "RESULTS").
- **Don't** put shadows on elements at rest. Shadows are interaction feedback only.
- **Don't** use more than one font family. Inter (with system fallbacks) for everything; mono for data.
- **Don't** use modal dialogs for content that can live inline. The detail panel expands in place.
- **Don't** animate layout properties (width, height, top, left). Use `transform` and `opacity` only.
- **Don't** ship motion without a reduced-motion fallback. Every transition, every animation.
- **Don't** let heading text overflow at tablet/mobile breakpoints. If a clamp max produces overflow, reduce it or rewrite the copy.
