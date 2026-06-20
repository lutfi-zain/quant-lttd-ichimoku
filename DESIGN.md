---
name: Ichimoku Quant Dashboard
description: High-end corporate dark mode quant backtesting dashboard
colors:
  # Base Dark Mode Theme
  bg-deep: "#0c0d0e"
  bg-surface: "#151617"
  bg-surface-hover: "#1e1f21"
  border-muted: "#242528"
  border-active: "#404247"
  text-primary: "#eceefe"
  text-secondary: "#c7c9d3"
  text-muted: "#9ca3af"
  accent: "#00f0ff"
  success: "#34d399"
  danger: "#f87171"
  warning: "#fbbf24"
  info: "#60a5fa"
  
  # Base Light Mode Theme
  bg-deep-light: "#fbfbfa"
  bg-surface-light: "#ffffff"
  bg-surface-hover-light: "#f7f6f3"
  border-muted-light: "#eaeaea"
  border-active-light: "#cccccc"
  text-primary-light: "#111111"
  text-secondary-light: "#2f3437"
  text-muted-light: "#585e68"
  success-light: "#346538"
  danger-light: "#9f2f2d"
  warning-light: "#956400"
  info-light: "#1f6c9f"
  
  # Badges & Overlays
  badge-success-bg: "#edf3ec"
  badge-success-bg-dark: "rgba(16, 185, 129, 0.12)"
  badge-danger-bg: "#fdebec"
  badge-danger-bg-dark: "rgba(239, 68, 68, 0.12)"
  badge-warning-bg: "#fbf3db"
  badge-warning-bg-dark: "rgba(245, 158, 11, 0.12)"
  badge-info-bg: "#e1f3fe"
  badge-info-bg-dark: "rgba(59, 130, 246, 0.12)"
  
  # Chart Assets & Indicators
  chart-up: "#10b981"
  chart-down: "#ef4444"
  chart-tenkan: "#f87171"
  chart-kijun: "#60a5fa"
  chart-span-a: "rgba(52, 211, 153, 0.25)"
  chart-span-a-light: "rgba(52, 101, 56, 0.25)"
  chart-span-b: "rgba(248, 113, 113, 0.25)"
  chart-span-b-light: "rgba(159, 47, 45, 0.25)"
  chart-chikou: "rgba(168, 85, 247, 0.5)"
  chart-chikou-light: "rgba(107, 33, 168, 0.45)"
  chart-imo: "#fbbf24"
  chart-imo-light: "#d97706"
  chart-thresh: "#9ca3af"
  chart-thresh-light: "#787774"
  chart-entropy: "#a78bfa"
  chart-entropy-light: "#7c3aed"
  chart-chikou-s: "#22d3ee"
  chart-chikou-s-light: "#0891b2"
  chart-market: "#888888"
  chart-alert: "rgba(239, 68, 68, 0.4)"
  chart-alert-light: "rgba(159, 47, 45, 0.4)"
  chart-crosshair: "#6b7280"
  chart-crosshair-light: "#888888"

  # Standard Defaults
  white: "#ffffff"
  black: "#111111"
typography:
  display:
    fontFamily: "Switzer, -apple-system, BlinkMacSystemFont, sans-serif"
    fontSize: "clamp(2rem, 5vw, 3.5rem)"
    fontWeight: 600
    lineHeight: 1.1
    letterSpacing: "-0.03em"
  body:
    fontFamily: "Switzer, -apple-system, BlinkMacSystemFont, sans-serif"
    fontSize: "14px"
    fontWeight: 400
    lineHeight: 1.5
  mono:
    fontFamily: "Geist Mono, monospace"
    fontSize: "13px"
    fontWeight: 400
  serif:
    fontFamily: "Instrument Serif, serif"
    fontWeight: 400
rounded:
  xs: "2px"
  sm: "3px"
  base: "4px"
  md: "6px"
  lg: "8px"
  full: "9999px"
spacing:
  xs: "4px"
  sm: "8px"
  md: "16px"
  lg: "24px"
  xl: "32px"
components:
  card:
    backgroundColor: "{colors.bg-surface}"
    rounded: "{rounded.lg}"
    border: "1px solid {colors.border-muted}"
  button-primary:
    backgroundColor: "{colors.text-primary}"
    textColor: "{colors.bg-surface}"
    rounded: "{rounded.base}"
    padding: "8px 16px"
  button-primary-hover:
    backgroundColor: "{colors.accent}"
    textColor: "{colors.bg-deep}"
  toggle-option:
    backgroundColor: "transparent"
    textColor: "{colors.text-muted}"
  toggle-option-active:
    backgroundColor: "{colors.accent}"
    textColor: "{colors.bg-deep}"
---

# Design System: Ichimoku Quant Dashboard

## 1. Overview

**Creative North Star: "The Obsidian Ledger"**

A sleek, dark, data-dense financial command center. The visual system prioritizes extreme contrast, structural flat layout alignment, and vibrant data-indicative accents (neon cyan and desaturated signal badging). The design is calibrated to convey institutional precision and analytical authority.

### Key Characteristics:
- **High-Density Data**: Information layout uses flat grids and compact borders instead of generous white-space padding.
- **Deep Monochromatic Surface**: Built on absolute dark tones (`#0c0d0e` and `#151617`) to keep visual focus entirely on technical charts and metrics.
- **Utilitarian Details**: Technical readouts, legends, and status indicators are rendered in sharp monospace text.

## 2. Colors

The color palette utilizes deep charcoal surfaces contrasted with crisp primary text, using neon cyan exclusively as a tactical accent to highlight active controls and parameters.

### Primary
- **Neon Cyan** (`#00f0ff`): Tactically highlights active parameters, selected options, and key charting lines. The accent is used on ≤10% of any given screen to preserve its high-impact significance.

### Neutral
- **Deep Background** (`#0c0d0e`): The base background of the dashboard workspace.
- **Surface Card** (`#151617`): Used for containers, sidebars, and control boxes.
- **Muted Border** (`#242528`): Solid 1px separating line dividing the stacked charts and cards.
- **Primary Text** (`#eceefe`): Crisp, highly legible readout color for key headers and values.
- **Secondary Text** (`#c7c9d3`): Standard body text and description labels.
- **Muted Text** (`#6b7280`): Low-priority descriptors and inactive settings.

### Named Rules
**The Accent Rarity Rule.** The neon cyan accent (`#00f0ff`) is strictly reserved for current state highlights and primary target buttons. It is never used for general decorations, large layout lines, or non-interactive headings.

## 3. Typography

**Display Font:** Switzer (with sans-serif fallbacks)
**Body Font:** Switzer (with sans-serif fallbacks)
**Label/Mono Font:** Geist Mono (monospace)

### Hierarchy
- **Display** (600, clamp(2rem, 5vw, 3.5rem), 1.1): Used for main title and core portfolio metrics. Displays a tight `-0.03em` letter spacing.
- **Headline** (500, 18px, 1.3): Used for bento card and chart container headings.
- **Body** (400, 14px, 1.5): Standard prose and parameter descriptions. Body line length is capped at 65–75ch for readable flow.
- **Mono** (400, 13px, 1.4): Reserved for numbers, timestamps, coordinates, trade execution logs, and numeric toggle states.

### Named Rules
**The Monospace Numeric Rule.** Every numeric table cell, chart coordinates coordinate, and trade parameter must use Geist Mono to prevent character-width shift and ensure precise vertical alignment.

## 4. Elevation

The system is strictly **Flat & Layered**. It rejects ambient drop shadows, relying entirely on solid 1px borders (`#242528`) and subtle background shifts (surface hover state `#1e1f21`) to establish layout hierarchy. This ensures a clean, non-fuzzy visual interface.

### Named Rules
**The Flat-By-Default Rule.** Surfaces are flat at rest. Drop shadows and glassmorphic blurs are prohibited. Hierarchy is communicated exclusively by the border boundaries and background value contrast.

## 5. Components

### Buttons
- **Shape:** Rectangular with a minimal corner radius (4px).
- **Primary Button:** Uses a solid primary text background (`#eceefe`) and deep surface color (`#151617`) for high-contrast legibility.
- **Hover state:** Shifts background to neon cyan (`#00f0ff`) and text to deep background (`#0c0d0e`) with an instant transition.

### Cards / Containers
- **Corner Style:** Rounded with an 8px radius.
- **Background:** Flat surface card background (`#151617`).
- **Border:** Solid 1px muted border (`#242528`).
- **Internal Padding:** 16px or 24px depending on visual density.

### Toggles & Toggle Buttons
- **Style:** Segmented linear buttons inside a 1px border frame.
- **Active state:** Background shifts to neon cyan (`#00f0ff`) and text to deep background (`#0c0d0e`).
- **Inactive state:** Transparent background with muted text.

## 6. Do's and Don'ts

### Do:
- **Do** align the three charts (BTC Price, Oscillator, and Cumulative Equity Growth) vertically with only a 1px separator border between them.
- **Do** format all tabular numbers, trading percentages, dates, and metric readouts in Geist Mono.
- **Do** maintain a strict 4.5:1 contrast ratio for all secondary and placeholder labels.

### Don't:
- **Don't** use ambient drop shadows or decorative glassmorphism blurs.
- **Don't** add side-stripe accent borders to the bento cards or log cards.
- **Don't** use saturated background colors for status badges (always use low-saturation pale alerts).
- **Don't** use tiny uppercase tracked eyebrows above sections as general scaffolding.
