# Election Process Education Assistant — Design Context

## Users

**Primary:** First-time voters (18–35, primarily) during election periods who are nervous about understanding complex voting rules and deadlines. They visit with anxiety, confusion, and a need for clarity.

**Secondary:** Confused voters returning after a gap (missed elections, moved to new state, changed voting method). Same emotional state: uncertainty seeking reassurance.

**Use Case:** User lands with a specific question: "When do I need to register?" "Where do I vote?" "Can I vote by mail?" Our assistant guides them through a 4-step wizard, generates a personalized timeline, then offers "Ask Why?" contextual explanations for confusing terms.

**Context:** Desktop and mobile, typically visited during evenings/weekends (after work or research time). May be interrupted and return later (session persistence matters).

---

## Brand Personality

**3 Words:** Warm, Demystifying, Trustworthy

**Voice:** Friendly but not patronizing. We explain without oversimplifying. We celebrate voting as a right, not a burden. We answer the "why" behind confusing rules so users feel empowered, not talked-down-to.

**Emotional Goals:**
- Transform anxiety → clarity
- Replace jargon → plain language
- Shift "voting is confusing" → "I know exactly what to do"

**What We Are NOT:** Robotic, legal/official, dry bureaucratic, corporate, generic.

---

## Aesthetic Direction

### Theme
**Both Light & Dark** with automatic detection (`prefers-color-scheme`) and manual toggle in header.

**Light Mode:** Primary for daytime research. Inviting, open, educational. Borrowed from CivicLens hero aesthetic.

**Dark Mode:** For evening/late-night users. Reduces eye strain, maintains warmth through carefully tinted neutrals and accessible contrast.

### Color Palette

**Foundation (Light Mode):**
- `--civic-deep: #0F172A` — Deep slate headings, nav, primary buttons (semantic weight)
- `--civic-accent: #2563EB` — Interactive blue for links, hover states, focus rings (confident, civic)
- `--civic-light: #F8FAFC` — Page background (off-white, slightly warm)
- `--civic-white: #FFFFFF` — Card backgrounds, form inputs
- `--civic-gray: #64748B` — Secondary text, disabled states
- `--civic-border: #E2E8F0` — Subtle dividers

**Confidence Indicators:**
- `--civic-success: #006837` — HIGH confidence (dark green, strong)
- `--civic-warn: #a66100` — MEDIUM confidence (amber, cautious)
- `--civic-danger: #b30000` — LOW confidence (red, warning)

**Dark Mode Inversion:**
- Swap `--civic-deep` ↔ `--civic-light`
- Keep accent hue (blue) but adjust lightness for contrast
- Tint neutrals toward `--civic-accent` for cohesion

### Typography

**Display Font:** `Literata` (serif, 500–700 weight)
- **Usage:** H1, H2, page titles, brand name
- **Personality:** Editorial, grounded, quietly authoritative
- **Rationale:** Feels like a well-edited civic handbook rather than a generic marketing site

**Body Font:** `Work Sans` (sans-serif, 400–700 weight)
- **Usage:** Paragraphs, labels, buttons, form text
- **Personality:** Clear, practical, reassuring
- **Rationale:** Keeps the interface readable and calm while still feeling distinct

**Type Scale:**
- **H1:** 2.25rem (36px), 1.3 line-height → Hero, page title
- **H2:** 1.875rem (30px), 1.3 line-height → Section heading
- **H3:** 1.5rem (24px), 1.4 line-height → Subsection, card title
- **Body:** 1rem (16px), 1.6 line-height → Paragraphs, default
- **Small:** 0.875rem (14px), 1.5 line-height → Labels, secondary text
- **Tiny:** 0.75rem (12px), 1.4 line-height → Metadata, timestamps

### Spacing & Layout

**4pt Scale:** 4, 8, 12, 16, 24, 32, 48, 64, 96px

**Semantic Tokens:**
- `--space-xs: 4px` — Micro spacing between related items
- `--space-sm: 8px` — Tight grouping (icon + text, form groups)
- `--space-md: 16px` — Standard component padding
- `--space-lg: 24px` — Section breaks, card margins
- `--space-xl: 32px` — Page sections
- `--space-2xl: 48px` — Major sections, hero spacing

**Container:** `max-width: 1100px` with `padding: 0 24px`

**Responsive Breakpoints:**
- Mobile (< 640px): Single column, `padding: 0 16px`, `gap: 12px`
- Tablet (640–1024px): 2 columns where relevant, `gap: 16px`
- Desktop (> 1024px): Full layout, `gap: 24px`

### Motion & Interaction

**Guiding Principle:** Motion should clarify state changes, never distract.

**Transitions:**
- **Quick interactions** (hover, focus): `0.15s ease-out` (snappy feedback)
- **Page loads:** Staggered 0.2s intervals for card reveals
- **Form errors:** `0.3s ease-out` (attention-grabbing but not jarring)
- **Dark mode toggle:** `0.3s ease-out` (smooth theme swap)

**Easing:** Prefer `ease-out` (exponential deceleration). Avoid `bounce`, `elastic` (dated).

**Reduced Motion:** Always respect `prefers-reduced-motion: reduce`. Disable all animations for these users.

---

## Design Principles

1. **Clarity First:** Every element has a purpose. Jargon gets explained, not hidden. Visual hierarchy guides the eye.

2. **Accessibility by Default:** WCAG 2.2 AAA is non-negotiable. 7:1+ contrast, keyboard navigation, semantic HTML, ARIA labels, skip links, focus indicators.

3. **Trust Through Validation:** Show confidence scores, cite sources, warn when uncertain. Users should never wonder if this info is correct.

4. **Mobile-First Simplicity:** Start with single-column mobile, expand responsively. No hidden features on small screens.

5. **Warmth Over Minimalism:** We're explaining voting to nervous people. Friendly tone, generous spacing, encouraging language. Don't strip it bare.

---

## Anti-References

- ❌ **CivicLens Anti-Patterns:** Hub-and-spoke with scattered calls-to-action (feels chaotic). Freeform chat encourages hallucination.
- ❌ **Generic Government Sites:** Dense legal text, poor information hierarchy, outdated aesthetics. We simplify.
- ❌ **Overly Playful:** Emoji overload, cutesy language. We're serious about voting rights, just friendly about explaining.
- ❌ **Dark Mode by Default:** Not appropriate for civic education; feels "cool" but reduces accessibility for some users.

---

## Implementation Notes

### Dark Mode Strategy
Use CSS `@media (prefers-color-scheme: dark)` with a manual toggle button in the header:

```html
<button id="theme-toggle" aria-label="Toggle dark mode">🌙</button>
```

Store user preference in `localStorage` so it persists across sessions.

### Component Library (Reusable)
- **Buttons:** Primary (blue bg), secondary (white bg, blue border), ghost (text only)
- **Cards:** Standard (white bg, shadow), timeline-step (with confidence badge)
- **Forms:** Radio groups (wizard steps), text inputs (state/ZIP), select dropdowns
- **Alerts:** Success (green, checkmark), warning (amber, triangle), danger (red, X)
- **Badges:** Confidence levels (HIGH/MEDIUM/LOW with color coding)

### Accessibility Tokens
- **Focus Ring:** 3px solid `var(--civic-accent)` with 2px offset
- **Contrast Ratio:** All text ≥ 7:1 (AAA standard)
- **Font Size:** Minimum 16px on body, 14px on labels
- **Touch Targets:** Minimum 48px × 48px for interactive elements
- **Landmarks:** `<nav>`, `<main>`, `<aside>`, `<section>` with ARIA labels

---

## File Structure

```
templates/
├── base.html              # Shared layout: nav, skip link, footer, design tokens
├── index.html             # Homepage: hero + feature cards + quick-start form
├── timeline.html          # Output: SVG timeline + accordion + Ask-Why sidebar
├── wizard/
│   ├── step1.html         # Country selection
│   ├── step2.html         # State/region
│   ├── step3.html         # Registration status
│   └── step4.html         # Voting method + conditional questions

static/
├── css/
│   ├── design-tokens.css  # OKLCH color palette, theme toggle
│   ├── components.css     # Buttons, cards, forms, alerts
│   └── motion.css         # Transitions, animations
└── js/
    └── theme-toggle.js    # Dark mode toggle with localStorage
```

---

**Document Version:** 1.0  
**Last Updated:** 2026-05-01  
**Design Lead:** Impeccable Skill  
