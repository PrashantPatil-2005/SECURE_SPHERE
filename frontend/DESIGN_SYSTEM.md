# SecuriSphere Frontend — Design System Rules

Guidance for integrating Figma designs (via the Figma MCP) into the SecuriSphere React dashboard. The Figma MCP returns React + Tailwind reference code; **always adapt it to the primitives, tokens, and conventions listed below** rather than pasting the raw output.

---

## 1. Token Definitions

### Source of truth: `frontend/tailwind.config.js`

All colors, typography, radii, and motion tokens live in the Tailwind theme `extend` block. There is no separate `tokens.json` or Style Dictionary pipeline — Tailwind *is* the transformation layer.

```js
// frontend/tailwind.config.js — "Enterprise Slate" palette
colors: {
  base: {               // warm-cool charcoal scale, dark-first
    DEFAULT:'#161923',  // body bg (950)
    900:'#1a1d29',      // sidebar/header
    800:'#1e2230',      // card surface
    700:'#272b38',      // elevated / hover
    500:'#5f667a',      // muted text
    400:'#868da2', 300:'#abb2c3', 200:'#cbd0dc', 100:'#e3e6ed',
  },
  accent: {             // muted steel blue — deliberately NOT Tailwind's #3b82f6
    DEFAULT:'#6b86b3', hover:'#5a7aa6',
    glow:'rgba(107,134,179,0.15)', muted:'rgba(107,134,179,0.08)',
  },
  severity: {           // desaturated, earth-leaning
    critical:'#c14953', high:'#b8753a', medium:'#b59441',
    low:'#5f8c6e',      info:'#5a87a8',
  },
  // Tailwind's red/orange/yellow/green/cyan palettes are OVERRIDDEN to the
  // same muted tones so `bg-red-500/10`, `text-green-400`, etc. stay on-palette
  // without touching every component. See tailwind.config.js for the full scales.
}
```

Rules:
- **Never hardcode hex values** in components — use `bg-base-800`, `text-accent`, `bg-severity-critical`, or the overridden Tailwind semantic names (`text-red-400` = muted critical, `text-green-400` = sage low, etc.).
- **Tailwind color names are semantic, not visual** in this project: `red-*` means "critical," `green-*` means "healthy/low," `yellow-*` means "medium/warning." They resolve to muted, not saturated, values.
- **No glow shadows** (`shadow-[0_0_20px_...]`). For emphasis, use a colored 1px border (`border-severity-critical/40`) or a colored left accent bar. The pulse-glow keyframe on small live-dots (`w-[7px] h-[7px]`) is the only approved glow use.
- **No translucent-white backdrop-blur panels.** `Card` is opaque `bg-base-800` with a flat border. The `white/[0.02-0.08]` tints used for row hover states and subtle fills are fine — they're the site's layering language.
- **Light-mode is warm paper** (`#fafaf7`) not cool gray-50. Overrides in `src/index.css` remap `bg-base-*` and `text-base-*` to the warm scale, and remap `white/[…]` borders to opaque warm borders.

### Typography tokens

```js
fontFamily: {
  sans: ['Inter', 'system-ui', '-apple-system', 'sans-serif'],
  mono: ['JetBrains Mono', 'Fira Code', 'monospace'],
}
fontSize: { '2xs': ['10px', '14px'] }
```

- `html { font-size: 14px }` in `src/index.css` — Tailwind `text-sm` resolves to ~14px. Keep this in mind when a Figma spec says "14px body."
- **Use `font-mono` for all timestamps, IPs, counts, IDs, and metric values.** Combine with `.tabular-nums` for aligned digits.
- Inter + JetBrains Mono are loaded from Google Fonts in `index.html` — do not add a third family.

### Radii, motion, and shadows

- Card radius is non-standard: `rounded-[10px]` (not `rounded-lg`). Matched by `Card`, `StatCard`.
- Buttons/inputs use `rounded-lg` (8px). Pills/badges use `rounded` (4px) or `rounded-full`.
- Keyframe tokens: `pulse-glow`, `fade-in`, `slide-up`, `flash-row`. Apply via `animate-pulse-glow` etc. — do not write new keyframes for similar effects.
- Ambient glow is done with an arbitrary shadow, e.g. `shadow-[0_0_20px_rgba(59,130,246,0.08)]` — match the **color family** of the element (accent=blue, severity.high=orange, etc.).

---

## 2. Component Library

Location: `frontend/src/components/` with three well-defined tiers:

```
components/
├── ui/           # primitives — Button, Card, Badge, Input, StatCard, Spinner
├── layout/       # app chrome — Header, Sidebar, StatusBar
├── charts/       # data viz — EventsAreaChart, RiskGauge, SparkLine, ThreatDonutChart,
│                             TopServicesBar, MitrePanel
├── KillChainTimeline.jsx     # feature components live at the root of components/
└── TopologyGraph.jsx
```

**Before generating new components from a Figma design, check `ui/` for an existing primitive.** Rule of thumb:

| If the Figma element is…                   | Use…                                     |
|--------------------------------------------|------------------------------------------|
| A contained panel with header + body       | `<Card>` + `<CardHeader>` + `<CardContent>` |
| A KPI / metric tile                        | `<StatCard>` (don't build your own)     |
| A colored pill (severity, status)          | `<Badge variant="…">`                    |
| Any interactive button                     | `<Button variant="…" size="…">`          |
| A text or search field                     | `<Input>` / `<Select>`                   |
| A loading state                            | `<Spinner>` / `<PageLoader>` / `<Skeleton>` |
| Any chart                                  | Existing `charts/*` component, or Recharts with the tooltip pattern below |

### Variant API (class-variance-authority)

Primitives use `cva` for variants (see `ui/button.jsx`, `ui/Badge.jsx`). When you add a variant:
1. Extend the `cva` block — do **not** pass bespoke class overrides at the call site.
2. Variant names must match the semantic domain (`critical`, `high`, `medium`, `low`, `info`, `open`, `investigating`, `resolved`). Don't invent a `warning` when `medium` already exists.

### Storybook / docs

There is no Storybook. Primitives are small and self-documenting — read the file directly.

---

## 3. Frameworks & Libraries

| Concern              | Choice                                                             |
|----------------------|--------------------------------------------------------------------|
| UI framework         | React 18 (`react` + `react-dom`), function components + hooks only |
| Build / bundler      | Vite 5 (`vite.config.js`), `@vitejs/plugin-react`                  |
| Styling              | Tailwind CSS 3.4 + PostCSS + Autoprefixer                          |
| Variants             | `class-variance-authority` (`cva`)                                 |
| Class merging        | `clsx` + `tailwind-merge` → re-exported as `cn()` in `lib/utils.js`|
| Motion               | `framer-motion` — used for page transitions and card entry         |
| Charts               | `recharts` (primary), `d3` / `d3-force` (topology graph only)      |
| Icons                | `lucide-react`                                                     |
| Dates                | `date-fns`                                                         |
| Realtime             | `socket.io-client` (fallback: HTTP polling via `lib/api.js`)       |

Path alias: `@` → `frontend/src` (see `vite.config.js`). **Always use `@/…` imports, never relative `../../`.**

No TypeScript — the project is JSX. Don't introduce `.ts`/`.tsx` files; match the surrounding extension.

Dev server runs on `:3000` and proxies `/api` + `/socket.io` to the backend on `:8000`.

---

## 4. Asset Management

- There is **no `/public/` or `/src/assets/` image directory**. The app ships with zero raster assets.
- Favicon is an inline SVG data-URI in `index.html` (🛡 glyph) — if a Figma design specifies a new favicon, inline it the same way.
- Fonts load from Google Fonts CDN via `<link>` in `index.html`. Preconnect tags are already present; don't duplicate them.
- No CDN for images, no image pipeline, no `vite-imagetools`. If you need an image, prefer an SVG written inline in JSX (e.g. topology nodes, login-screen grid), or an icon from `lucide-react`.

---

## 5. Icon System

- **Single source: `lucide-react`**. Every icon in the app comes from there.
- Import named: `import { Shield, AlertTriangle, Radio } from 'lucide-react';`
- Size via the `className` (`w-3.5 h-3.5`, `w-4 h-4`, `w-[18px] h-[18px]`) or the `size` prop — match the surrounding pattern (Header uses `w-3.5 h-3.5`, Sidebar uses `w-[18px] h-[18px]`).
- Color inherits from `text-*` classes — set color on the parent, not via a `color` prop.
- When Figma shows a non-Lucide icon, find the closest Lucide equivalent before introducing a new icon system. Naming in Lucide is semantic (`Shield`, `Zap`, `Server`) — pick by meaning.

---

## 6. Styling Approach

### Methodology: Tailwind utility-first + `cn()` merging

- Global CSS lives only in `frontend/src/index.css` (base resets, scrollbar, selection, light-mode overrides).
- **No CSS Modules, no styled-components, no Emotion.** All component styling is Tailwind classes.
- Compose classes with `cn(...)` from `@/lib/utils`:
  ```jsx
  import { cn } from '@/lib/utils';
  <div className={cn('rounded-lg border', active && 'border-accent', className)} />
  ```

### Theming: class-based dark mode (`darkMode: 'class'`)

- `<html>` carries the `.dark` class by default (see `index.html`). `useTheme()` in `src/hooks/use-theme.js` toggles it and persists to `localStorage`.
- **Dark mode is the primary design**. Light mode is implemented as overrides in `index.css` that remap `bg-base-800/900/950` and `text-base-100..500`. When adding a new surface class, verify it either uses the `base.*` palette (covered by overrides) or add a matching `html:not(.dark) …` rule.
- The site uses **dark-on-dark with translucent whites** (`bg-white/[0.03]`, `border-white/[0.07]`) for layering — this is why light-mode overrides map `white/[…]` selectors to `black/[…]`.

### Responsive design

- Tailwind breakpoints, mobile-first. Common pattern:
  ```jsx
  <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
  ```
- The app assumes a desktop analyst workstation. There is no hamburger menu; the sidebar collapses to a 64px rail via hover/pin state, not via breakpoint. Match that pattern for new chrome.

### Animation

- Use the named keyframes from `tailwind.config.js` first: `animate-pulse-glow` for "live" dots, `animate-flash-row` for newly arrived rows, `animate-fade-in` / `animate-slide-up` for entry.
- For page/tab transitions, use `framer-motion` with the standard preset (see `App.jsx` lines 120–129 and the `anim` constant at the top of `pages/Dashboard.jsx`):
  ```jsx
  const anim = { initial: { opacity: 0, y: 10 }, animate: { opacity: 1, y: 0 }, transition: { duration: 0.25 } };
  ```
  Do not invent new motion timings — 150–250ms ease-out is the site's vocabulary.

### Semantic helpers in `lib/utils.js`

When Figma shows color-coded severity or threat-level UI, **always route through these helpers** instead of writing a switch in the component:

```js
severityColor(sev)    → '#ef4444' | '#f97316' | ...
severityClass(sev)    → Tailwind class string (text+bg+border)
threatLevelColor(lvl) → '#a855f7' for critical, '#ef4444' threatening, ...
layerColor(layer)     → network/api/auth/browser palette
```

This is also why `safeString()` and `getSeverityString()` exist: backend payloads sometimes arrive as `{ level: 'high' }` instead of `'high'`. Use these guards when a field comes from the API.

---

## 7. Project Structure

```
frontend/src/
├── main.jsx               # ReactDOM root, imports index.css
├── App.jsx                # shell: Sidebar + Header + <main/> + StatusBar; auth + tab routing
├── index.css              # global base, scrollbar, light-mode overrides
│
├── pages/                 # one file per top-level tab — Dashboard, Events, Incidents,
│                          #   Topology, RiskScores, System, Login
├── components/
│   ├── ui/                # primitives (use these before making new ones)
│   ├── layout/            # Header, Sidebar, StatusBar
│   ├── charts/            # Recharts wrappers with site-styled tooltips
│   ├── KillChainTimeline.jsx
│   └── TopologyGraph.jsx
├── hooks/                 # use-theme, use-realtime
└── lib/
    ├── api.js             # HTTP client for /api/*
    ├── websocket.js       # socket.io client
    ├── mock-data.js       # fallback demo data when backend is down
    └── utils.js           # cn(), safeString, severity/threat/layer helpers, time formatters
```

### Organizing a new feature

1. **Page shell**: one file under `pages/`, default-exported function component.
2. **Wrap content in `<motion.div {...anim}>`** using the `anim` constant pattern for tab-entry consistency.
3. **Layout**: use Tailwind `grid grid-cols-*` + `gap-4/6`. KPI rows are `grid-cols-4`, analytics rows are `grid-cols-3` (2-col main + 1-col sidebar), list rows are `grid-cols-2`.
4. **Every panel is a `<Card>`** with `<CardHeader><CardTitle>…</CardTitle></CardHeader><CardContent>…</CardContent>`.
5. **Feed / list rows** follow the Dashboard live-feed pattern: `px-4 py-2 hover:bg-white/[0.02] rounded-xl mx-2 mb-1 border border-transparent hover:border-white/[0.05]`. The first row gets `animate-flash-row` on new-event arrivals.
6. **Tooltips for charts**: build a `CustomTooltip` inside the chart file using `rounded-lg border border-white/10 bg-base-800/95 backdrop-blur-sm px-3 py-2 shadow-lg` — this is the site-wide tooltip shell (see `EventsAreaChart.jsx`, `ThreatDonutChart.jsx`).

### Data flow

- Live data comes from `useRealtime()` in `hooks/use-realtime.js`. Page components receive events/incidents/metrics/etc. as props from `App.jsx` — they don't call `api.*` directly (except `Login.jsx`).
- When extending a page, **add the data reducer to `useRealtime` and pass the new field through `App.jsx`** rather than fetching inside the page.

---

## Figma-to-SecuriSphere translation checklist

When applying a Figma design:

1. **Tokens**: map every color to the nearest `base.*`, `accent.*`, or `severity.*` token. Raw hex is a code-smell.
2. **Primitive first**: scan `components/ui/` before generating HTML. 90% of panels are `<Card>` + `<Badge>` + `<Button>`.
3. **Icons**: swap Figma icons for their `lucide-react` equivalent. Don't paste SVGs.
4. **Radius**: card = `rounded-[10px]`, button/input = `rounded-lg`, badge = `rounded` or `rounded-full`.
5. **Type**: mono for any data value (numbers, IPs, IDs, timestamps); sans for everything else; `tracking-wider`/`uppercase` on micro-labels (`text-[10px] uppercase tracking-[0.06em]`).
6. **Surface**: dark-mode first. Layer translucent whites on top of `bg-base-800/900` — don't introduce new solid surface colors.
7. **Motion**: `animate-fade-in` / `animate-slide-up` or a `framer-motion` block using the existing `anim` preset.
8. **Severity/threat/layer coloring**: go through `severityColor`, `severityClass`, `threatLevelColor`, `layerColor` in `lib/utils.js`.
9. **Light mode**: verify the design still reads correctly with `.dark` removed from `<html>` (test with the theme toggle in `Header`). Add targeted `html:not(.dark)` rules in `index.css` only if truly needed.
10. **Never**: add new global CSS, new font families, new icon libraries, new styling systems, or TypeScript files.
