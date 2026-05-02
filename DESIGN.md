---
name: Election Process Guide
description: Personalized step-by-step voting deadline and education assistant
colors:
  primary: "#2563EB"
  civic-deep: "#0F172A"
  civic-white: "#FFFFFF"
  civic-light: "#F8FAFC"
  civic-gray: "#64748B"
  civic-success: "#059669"
  civic-warn: "#D97706"
  civic-danger: "#DC2626"
typography:
  display:
    fontFamily: "'Literata', serif"
    fontWeight: 700
  body:
    fontFamily: "'Work Sans', sans-serif"
    fontWeight: 400
rounded:
  sm: "8px"
  default: "12px"
spacing:
  xs: "4px"
  sm: "8px"
  md: "16px"
  lg: "24px"
  xl: "32px"
  2xl: "48px"
  3xl: "64px"
components:
  btn-primary:
    backgroundColor: "{colors.primary}"
    textColor: "{colors.civic-white}"
    rounded: "{rounded.sm}"
    padding: "16px 32px"
  hero-action-card:
    backgroundColor: "{colors.civic-white}"
    rounded: "{rounded.default}"
    padding: "{spacing.2xl}"
---

# Design System: Election Process Guide

## 1. Overview

**Creative North Star: "The Civic Authority"**

The Election Process Guide is built to instill trust, clarity, and competence. Voting can be an overwhelming, deadline-driven process. The aesthetic philosophy here relies on structured typography, high-contrast readability, and generous whitespace. We explicitly reject bureaucratic clutter, confusing walls of text, and overly colorful decorative noise. 

**Key Characteristics:**
- **Clarity over cleverness:** Information is progressively disclosed.
- **Hierarchical precision:** Size and weight contrast immediately draw the eye to actions and deadlines.
- **Sturdy and trustworthy:** Serif display headings ground the system in institutional authority, while sans-serif body copy ensures high legibility.

## 2. Colors

The palette is restrained, using high-contrast neutrals with a single, clear primary accent for interaction.

### Primary
- **Civic Accent Blue** (#2563EB): The absolute indicator of interaction. Used for primary buttons, focus rings, and active states. 

### Semantic
- **Civic Success** (#059669): Used for "Ready" statuses and correct quiz answers.
- **Civic Warn** (#D97706): Used for looming deadlines and "Needs Review" states.
- **Civic Danger** (#DC2626): Used for passed deadlines and critical errors.

### Neutral
- **Civic Deep Slate** (#0F172A): Primary text color. Dark enough for high contrast, softer than pure black.
- **Civic Gray** (#64748B): Secondary text, descriptions, and passive metadata.
- **Civic White** (#FFFFFF): Core surface color for cards and interactive panels.
- **Civic Light** (#F8FAFC): Page background. Provides subtle contrast against pure white cards.

### Named Rules
**The One Action Rule.** The Civic Accent Blue (#2563EB) is reserved strictly for interactive elements (links, buttons, active focus states). Do not use it for passive text or decorative background fills.

## 3. Typography

**Display Font:** Literata (serif)
**Body Font:** Work Sans (sans-serif)

**Character:** Literata brings a sense of editorial authority and institutional trust, while Work Sans provides friendly, accessible legibility for dense instructional text.

### Hierarchy
- **Display** (700, clamp(2rem, 5vw, 2.4rem)): Hero headers and page titles.
- **Headline** (600, 1.5rem): Section titles and card headers.
- **Body** (400, 1.05rem, 1.6): Standard paragraph text. Capped at 70ch for readability.
- **Label** (700, 0.8rem, uppercase, 0.05em tracking): Small metadata, step counters, and category tags.

### Named Rules
**The Strict Serif Rule.** Literata is reserved exclusively for major headings (`h1`, `h2`) and prominent numbers (like stage counters). It is never used for body paragraphs or UI controls.

## 4. Elevation

The system relies on structural drop shadows to lift interactive surfaces off the background.

### Shadow Vocabulary
- **Ambient Shadow** (`0 4px 6px -1px rgb(0 0 0 / 0.07)`): Base elevation for standard cards and inputs.
- **Hover/Focus Lift** (`0 10px 15px -3px rgb(0 0 0 / 0.08)`): Used when a card or button is interacted with, physically moving it closer to the user.

### Named Rules
**The Flat Background Rule.** The app background is always flat. Shadows are only applied to white surfaces (cards, buttons, modals) to denote interactivity and hierarchy.

## 5. Components

### Buttons
- **Shape:** Softly rounded (8px).
- **Primary:** Civic Accent background, white text, bold.
- **Hover / Focus:** Translates up slightly (`translateY(-2px)`) and gains a stronger shadow to feel tactile.
- **Secondary:** Transparent background, subtle border, gray text.

### Hero Action Card
- **Corner Style:** 12px radius.
- **Background:** Civic White.
- **Shadow Strategy:** Deep ambient shadow.
- **Internal Padding:** Generous (32px - 48px). Used to center the primary user task (e.g., finding polling places, starting the wizard).

### Inputs / Selects
- **Style:** 2px solid border (Civic Border), Civic Light background, 8px radius.
- **Focus:** The border turns Civic Accent, the background shifts to Civic White, and a 3px transparent Civic Accent outline appears to guarantee accessibility.

## 6. Do's and Don'ts

### Do:
- **Do** use the 4pt spacing scale (`var(--space-md)`, `var(--space-xl)`) consistently to maintain rhythm.
- **Do** wrap primary tasks in the Hero Action Card pattern to command focus.
- **Do** use progressive disclosure (like accordions or step-by-step wizards) for complex legal requirements.

### Don't:
- **Don't** use `border-left` or `border-right` greater than 1px as a colored stripe on cards. Use full borders or background tints.
- **Don't** use gradient text anywhere in the interface.
- **Don't** use generic shadow values. Stick to the predefined `--shadow` and `--shadow-lg` tokens.
