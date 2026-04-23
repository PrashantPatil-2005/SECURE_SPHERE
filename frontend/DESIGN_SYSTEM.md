# SecuriSphere Frontend — Design System Rules

Guidance for integrating Figma designs (via the Figma MCP) into the SecuriSphere React dashboard. The Figma MCP returns React + Tailwind reference code; **always adapt it to the primitives, tokens, and conventions listed below** rather than pasting the raw output.

---

## 1. Token Definitions

### Source of truth: CSS variables in `frontend/src/index.css`, mapped by `frontend/tailwind.config.js`

Tokens are defined as **CSS custom properties** and consumed by Tailwind through `var(--…)` expressions. There is no `tokens.json` or Style Dictionary — Tailwind is the transformation layer.

```css
/* frontend/src/index.css */
:root { /* light — white-based */
  --base-50:  #0a0a0a;  --base-100: #171717;  --base-200: #262626;
  --base-300: #404040;  --base-400: #525252;  --base-500: #737373;
  --base-600: #a3a3a3;  --base-700: #d4d4d4;  --base-800: #e5e7eb;
  --base-900: #f9fafb;  --base-950: #ffffff;
  --accent: #0a0a0a;  --accent-hover: #171717;
  --accent-muted: rgba(10,10,10,0.06);  --line: #e5e7eb;
}
.dark { /* dark — black-based */
  --base-50:  #fafafa;  --base-100: #f5f5f5;  --base-200: #e5e5e5;
  --base-300: #d4d4d4;  --base-400: #a3a3a3;  --base-500: #737373;
  --base-600: #525252;  --base-700: #404040;  --base-800: #222222;
  --base-900: #111111;  --base-950: #0a0a0a;
  --accent: #fafafa;  --accent-hover: #ffffff;
  --accent-muted: rgba(255,255,255,0.06);  --line: #222222;
}
```

```js
// frontend/tailwind.config.js
colors: {
  base:   { DEFAULT: 'var(--base-900)', 50…950: 'var(--base-*)' },
  accent: { DEFAULT: 'var(--accent)', hover: 'var(--accent-hover)', muted: 'var(--accent-muted)' },
  severity: { critical: '#ef4444', high: 'var(--base-400)', medium: 'var(--base-500)', low: 'var(--base-600)', info: 'var(--base-500)' },
}
```

Rules:

- **Monochrome baseline.** The palette is black/white. Light mode is white-based, dark mode is black-based. Do not introduce brand hues into the surface/chrome layer.
- **The `accent` token is also monochrome** (`#0a0a0a` in light, `#fafafa` in dark). When a Figma design uses a brand blue/green accent on buttons or links, map it to `text-accent` / `bg-accent` — do not reintroduce a steel-blue.
- **Surfaces use `bg-base-*`**: `bg-base-950` for body, `bg-base-900` for cards, `bg-base-800` for borders/dividers or elevated rows. Always via the `base` scale — never hardcode hex.
- **Severity coloring has two layers that intentionally diverge**:
  - In `tailwind.config.js`, `severity.high/medium/low/info` are gray shades — use these when severity is an ambient label that shouldn't dominate the UI.
  - The `severityClass()` / `severityColor()` helpers in `lib/utils.js` emit the **saturated Tailwind palette** (`red-400`, `orange-400`, `amber-400`, `cyan-400`). Use these when severity is the primary signal (badges, row accents, chart series).
  - `Badge.jsx` variants use the saturated palette directly (`bg-red-500/15 text-red-300 border-red-500/40`, etc.). See §2.
- **No glow shadows on cards.** The only approved `shadow-[…]` glows are on `Badge` variants (`critical`, `active`, `escalated`) and on the `animate-glow-ring` keyframe used for hero elements. Cards are flat.
- **No translucent-white backdrop-blur panels for primary surfaces.** `Card` is opaque. Use `bg-white/[0.02–0.08]` (and `bg-black/[…]` in light mode) only for row hover states and subtle fills.

### Typography tokens

```js
fontFamily: {
  sans: ['Inter', 'system-ui', '-apple-system', 'sans-serif'],
  mono: ['JetBrains Mono', 'Fira Code', 'monospace'],
}
fontSize: { '2xs': ['10px', '14px'] }
```

- `html { font-size: 14px }` — Tailwind `text-sm` resolves to ~14px. A Figma spec of "14px body" is `text-sm`.
- **Use `font-mono` for all timestamps, IPs, counts, IDs, and metric values.** Pair with `tabular-nums` for aligned digits.
- Inter + JetBrains Mono load from Google Fonts in `index.html`. Do not add a third family.

### Radii, motion, shadows

- Card radius is non-standard: `rounded-[10px]` (not `rounded-lg`). Matched by `Card`, `StatCard`.
- Buttons/inputs: `rounded-lg` (8px). Pills/badges: `rounded` (4px) or `rounded-full`.
- Tailwind animation tokens (see `tailwind.config.js`): `animate-pulse-glow`, `animate-fade-in` (200ms), `animate-slide-up` (250ms), `animate-flash-row` (1.4s), `animate-float-soft` (3s loop), `animate-gradient-shift` (8s loop), `animate-scale-in` (220ms spring), `animate-glow-ring` (2.4s loop). Use these before writing new keyframes.
- For elevated emphasis, prefer a colored 1px border (`border-severity-critical/40`, `border-red-500/40`) over a blurred shadow.

---

## 2. Component Library

Location: `frontend/src/components/`. Seven subdirectories plus a few feature components at the root:

```
components/
├── ui/           # primitives — Button, Card, Badge, Input, StatCard, Spinner
├── layout/       # app chrome — Header, Sidebar, StatusBar (legacy sidebar layout)
├── nav/          # nav shells — SidebarNav, TopNav, AppNavTabs, CommandPalette, navConfig
├── shell/        # AuthenticatedApp (router + shell switcher), TweaksPanel
├── charts/       # Recharts wrappers (EventsAreaChart, RiskGauge, SparkLine, ThreatDonutChart,
│                 #                    TopServicesBar, MitrePanel, …)
├── dashboard/    # Dashboard-mode feature blocks — KPI cards, feeds, mode switcher,
│                 #   TriageDashboard / GridDashboard / StoryDashboard, DemoBanner, …
├── events/       # Events-page blocks
├── incidents/    # Incidents-page blocks
├── topology/     # Topology-page blocks (beside TopologyGraph.jsx at the root)
├── intro/        # Intro / landing blocks
├── design/       # design-system surface snippets used inside the app
├── KillChainTimeline.jsx
├── TopologyGraph.jsx
├── TopologyChecklist.jsx
└── IncidentActions.jsx
```

**Before generating new components from a Figma design, check `ui/` for an existing primitive.**

| If the Figma element is…                   | Use…                                     |
|--------------------------------------------|------------------------------------------|
| A contained panel with header + body       | `<Card>` + `<CardHeader>` + `<CardContent>` |
| A KPI / metric tile                        | `<StatCard>` (don't build your own)     |
| A colored pill (severity, status)          | `<Badge variant="…">`                    |
| Any interactive button                     | `<Button variant="…" size="…">`          |
| A text or search field                     | `<Input>` / `<Select>`                   |
| A loading state                            | `<Spinner>` / `<PageLoader>` / `<Skeleton>` |
| A nav shell (sidebar/top/minimal)          | Pick via `useAppStore().nav` — see §7    |
| ⌘K / command palette                       | `<CommandPalette>` from `components/nav` |
| Any chart                                  | Existing `charts/*` component, or Recharts with the tooltip pattern below |

### Variant API (class-variance-authority)

Primitives use `cva` (see `ui/button.jsx`, `ui/Badge.jsx`). When you add a variant:

1. Extend the `cva` block — do **not** pass bespoke class overrides at the call site.
2. Variant names must match the semantic domain (`critical`, `high`, `medium`, `low`, `info`, `open`, `investigating`, `resolved`, `acknowledged`, `escalated`, `suppressed`, `active`, `accent`, `default`). Don't invent a `warning` when `medium` already exists.

Current `Badge` variants (for reference):

```jsx
// components/ui/Badge.jsx
critical | high | medium | low | info | accent | default |
active | acknowledged | escalated | suppressed |
open | investigating | resolved
```

### Storybook / docs

There is no Storybook. Primitives are small and self-documenting — read the file directly.

---

## 3. Frameworks & Libraries

| Concern              | Choice                                                                 |
|----------------------|------------------------------------------------------------------------|
| UI framework         | React 18 (`react` + `react-dom`), function components + hooks only     |
| Build / bundler      | Vite 5 (`vite.config.js`), `@vitejs/plugin-react`                      |
| Routing              | `react-router-dom` v6 (`BrowserRouter` / `Routes` / `Route`)           |
| Global state         | `zustand` (with `persist` middleware) at `src/stores/useAppStore.js`   |
| Styling              | Tailwind CSS 3.4 + PostCSS + Autoprefixer                              |
| Variants             | `class-variance-authority` (`cva`)                                     |
| Class merging        | `clsx` + `tailwind-merge` → re-exported as `cn()` in `lib/utils.js`    |
| Motion               | `framer-motion` — page transitions, card entry, hero                   |
| Charts               | `recharts` (primary), `d3` / `d3-force` (TopologyGraph only)           |
| Icons                | `lucide-react`                                                         |
| Dates                | `date-fns`                                                             |
| Realtime             | `socket.io-client` (fallback: HTTP polling via `lib/api.js`)           |

Path alias: `@` → `frontend/src` (see `vite.config.js`). **Always use `@/…` imports, never relative `../../`.**

No TypeScript — the project is JSX. Don't introduce `.ts` / `.tsx` files. JSDoc typedefs are used in a few `nav/` and `lib/` files and are welcome where useful.

Dev server runs on `:3000` and proxies `/api` + `/socket.io` to the backend on `:8000`.

---

## 4. Asset Management

- There is **no `/public/` or `/src/assets/` image directory**. The app ships with zero raster assets.
- Favicon is an inline SVG data-URI in `index.html` (🛡 glyph) — if a Figma design specifies a new favicon, inline it the same way.
- Fonts load from Google Fonts CDN via `<link>` in `index.html`. Preconnect tags are already present; don't duplicate them.
- No CDN for images, no image pipeline, no `vite-imagetools`. If you need an image, prefer an SVG written inline in JSX (topology nodes, login-screen grid, intro page hero) or an icon from `lucide-react`.

---

## 5. Icon System

- **Single source: `lucide-react`.** Every icon in the app comes from there.
- Import named: `import { Shield, AlertTriangle, Radio } from 'lucide-react';`
- Size via `className` (`w-3.5 h-3.5`, `w-4 h-4`, `w-[18px] h-[18px]`) or the `size` prop — match the surrounding pattern. Header uses `w-3.5 h-3.5`; SidebarNav uses `w-[18px] h-[18px]`.
- Color inherits from `text-*` classes — set color on the parent, not via a `color` prop.
- When Figma shows a non-Lucide icon, find the closest Lucide equivalent before introducing a new icon system. Lucide naming is semantic (`Shield`, `Zap`, `Server`) — pick by meaning.

---

## 6. Styling Approach

### Methodology: Tailwind utility-first + `cn()` merging

- Global CSS lives only in `frontend/src/index.css` (CSS variables, base resets, scrollbar, selection).
- **No CSS Modules, no styled-components, no Emotion.** All component styling is Tailwind classes.
- Compose classes with `cn(...)` from `@/lib/utils`:
  ```jsx
  import { cn } from '@/lib/utils';
  <div className={cn('rounded-lg border', active && 'border-accent', className)} />
  ```

### Theming: class-based dark mode (`darkMode: 'class'`)

- `<html>` carries (or drops) the `.dark` class. Toggling is done through `useAppStore().setTheme('light' | 'dark')` which calls `applyThemeToDocument()` from `lib/themeDom.js`.
- `hydrateDocumentThemeFromStorage()` runs before the login screen renders (see `App.jsx`) and after Zustand rehydrates (`onRehydrateStorage` in `useAppStore`) so there's no flash.
- **Both modes are first-class citizens.** Because tokens live in CSS vars, most components automatically swap — the rule for new surface classes is: use the `base.*` scale and `accent.*` tokens, and both modes will work without extra overrides.
- Translucent layering convention: in dark mode, layer subtle tints with `bg-white/[0.02–0.08]` and `border-white/[0.05–0.10]`. In light mode, prefer `bg-black/[0.02–0.06]` and `border-black/[0.05–0.10]`.

### Responsive design

- Tailwind breakpoints, mobile-first. Common pattern:
  ```jsx
  <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
  ```
- The app assumes a desktop analyst workstation. There is no hamburger menu. The **nav shell** (not the sidebar) is the adaptive unit — see §7.

### Animation

- Use the named keyframes from `tailwind.config.js` first: `animate-pulse-glow` for live dots, `animate-flash-row` for newly arrived rows, `animate-fade-in` / `animate-slide-up` for entry, `animate-scale-in` for modal/panel entry, `animate-glow-ring` for hero attention, `animate-float-soft` for idle affordances, `animate-gradient-shift` for ambient hero gradients.
- For page/tab transitions, use `framer-motion` with the standard preset:
  ```jsx
  const anim = { initial: { opacity: 0, y: 10 }, animate: { opacity: 1, y: 0 }, transition: { duration: 0.25 } };
  ```
  Do not invent new motion timings — 150–250ms ease-out is the site's vocabulary.

### Semantic helpers in `lib/utils.js`

When Figma shows color-coded severity, threat-level, or layer UI, **always route through these helpers** instead of writing a switch in the component:

```js
severityColor(sev)    → '#ef4444' | '#f97316' | '#eab308' | '#22d3ee' | var(--base-500)
severityClass(sev)    → Tailwind class string (text+bg+border, saturated palette)
threatLevelColor(lvl) → '#ef4444' critical, '#f97316' threatening, '#eab308' suspicious, '#10b981' normal
layerColor(layer)     → network=#22d3ee, api=#a855f7, auth=#f59e0b, browser=#34d399
```

`safeString()` and `getSeverityString()` are guards: backend payloads sometimes arrive as `{ level: 'high' }` instead of `'high'`. Use them whenever a severity/status field comes from the API.

Time helpers: `formatTimestamp`, `formatTimestampFull`, `relativeTime`. All three internally fix the "backend emits naive ISO" bug by appending `Z` when no timezone is present — **use them; do not call `new Date(iso)` directly**.

---

## 7. Project Structure

```
frontend/src/
├── main.jsx               # ReactDOM root, imports index.css
├── App.jsx                # BrowserRouter: /attacker standalone + /* → Shell → AuthenticatedApp
├── index.css              # CSS vars (light / .dark), base resets, scrollbar
│
├── pages/                 # one file per top-level route
│   ├── Login.jsx
│   ├── Attacker.jsx       # standalone red-team view (no auth shell)
│   ├── Intro.jsx
│   ├── Dashboard.jsx
│   ├── Events.jsx
│   ├── Incidents.jsx
│   ├── Topology.jsx
│   ├── RiskScores.jsx
│   ├── Mitre.jsx
│   └── System.jsx
│
├── components/
│   ├── ui/                # primitives — use these before making new ones
│   ├── layout/            # Header, Sidebar, StatusBar
│   ├── nav/               # SidebarNav, TopNav, AppNavTabs, CommandPalette, navConfig
│   ├── shell/             # AuthenticatedApp (router + nav-shell switcher), TweaksPanel
│   ├── charts/            # Recharts wrappers with site-styled tooltips
│   ├── dashboard/         # Dashboard-mode feature blocks (Triage / Grid / Story)
│   ├── events/ incidents/ topology/ intro/ design/
│   ├── KillChainTimeline.jsx
│   ├── TopologyGraph.jsx
│   ├── TopologyChecklist.jsx
│   └── IncidentActions.jsx
│
├── contexts/
│   └── CommandPaletteBridge.jsx   # wires ⌘K palette to router
│
├── stores/
│   └── useAppStore.js     # zustand: theme, density, ann, kc, nav, tweaksOpen (persisted)
│
├── hooks/
│   ├── use-theme.js
│   ├── use-realtime.js
│   ├── useCommandPalette.js
│   └── useLocalStorage.js
│
└── lib/
    ├── api.js             # HTTP client for /api/*
    ├── websocket.js       # socket.io client
    ├── mock-data.js       # fallback demo data when backend is down
    ├── themeDom.js        # applyThemeToDocument, hydrateDocumentThemeFromStorage
    └── utils.js           # cn(), safeString, severity/threat/layer helpers, time formatters
```

### Routing

`App.jsx` mounts `BrowserRouter`. Two top-level routes:

- `/attacker` → standalone `<Attacker/>` (no auth shell, different layout).
- `*` → `<Shell/>` which gates on auth and renders `<AuthenticatedApp/>`, whose router exposes `/intro`, `/dashboard`, `/events`, `/incidents`, `/topology`, `/risk`, `/mitre`, `/system`.

**`components/nav/navConfig.js` is the single source of truth for nav items.** When adding a route:

1. Add a `NavItem` entry (`id`, `label`, `path`, `section`) to `NAV_ITEMS`.
2. Add the `<Route>` inside `AuthenticatedApp`.
3. Do not duplicate the label anywhere else — consume via `NAV_ITEMS`, `pathForTab(id)`, or `tabIdFromPath(pathname)`.

### Nav shells

Three interchangeable chrome layouts stored in `useAppStore().nav`:

- `sidebar` — left rail (default), legacy `layout/Sidebar.jsx` + `Header.jsx`.
- `top` — horizontal top nav (`nav/TopNav.jsx` + `AppNavTabs.jsx`).
- `minimal` — chrome-light for presentation/demo.

`AuthenticatedApp` picks the shell based on the store. When designing new chrome in Figma, specify which shell the design targets; don't paint it into a single layout.

### State flow

- **Persistent UI prefs** (theme, density, annotations, kill-chain view, nav shell) → `useAppStore`. Persisted to `localStorage` under `securisphere-app-store`.
- **Live data** (events, incidents, metrics, topology) → `useRealtime()` in `hooks/use-realtime.js`. Page components receive them as props from the shell.
- When extending a page, **add the data reducer to `useRealtime`** and pass the new field through the shell rather than calling `api.*` inside the page (Login/Attacker are the exceptions).
- **Command palette**: open with ⌘K / Ctrl-K via `useCommandPalette`. Actions route through `CommandPaletteBridge` which consumes `NAV_ITEMS` — register new commands there, not inline.

### Organizing a new feature

1. **Page shell**: one file under `pages/`, default-exported function component.
2. **Wrap content in `<motion.div {...anim}>`** using the standard `anim` constant for tab-entry consistency.
3. **Layout**: Tailwind `grid grid-cols-*` + `gap-4/6`. KPI rows are `grid-cols-4`, analytics rows are `grid-cols-3` (2-col main + 1-col sidebar), list rows are `grid-cols-2`.
4. **Every panel is a `<Card>`** with `<CardHeader><CardTitle>…</CardTitle></CardHeader><CardContent>…</CardContent>`.
5. **Feed / list rows** follow the Dashboard live-feed pattern: `px-4 py-2 hover:bg-white/[0.02] rounded-xl mx-2 mb-1 border border-transparent hover:border-white/[0.05]`. The first row gets `animate-flash-row` on new-event arrivals.
6. **Tooltips for charts**: build a `CustomTooltip` inside the chart file using `rounded-lg border border-white/10 bg-base-900/95 backdrop-blur-sm px-3 py-2 shadow-lg` — this is the site-wide tooltip shell. See `EventsAreaChart.jsx`, `ThreatDonutChart.jsx`.
7. **Feature blocks** belong under the matching `components/<feature>/` directory, not inline in the page file, once they exceed ~60 lines.

---

## Figma-to-SecuriSphere translation checklist

When applying a Figma design:

1. **Tokens**: map every color to the nearest `base.*`, `accent.*`, or `severity.*` token. Raw hex is a code-smell.
2. **Monochrome chrome**: surface/chrome stays on the `base` scale. Accents stay on `accent` (mono). Only severity / chart series / badges use saturated color.
3. **Primitive first**: scan `components/ui/` before generating HTML. 90% of panels are `<Card>` + `<Badge>` + `<Button>`.
4. **Feature block**: if the Figma frame matches an existing `components/<feature>/` block (KPI bar, live feed, mode switcher, MITRE panel), reuse it instead of regenerating.
5. **Icons**: swap Figma icons for their `lucide-react` equivalent. Don't paste SVGs.
6. **Radius**: card = `rounded-[10px]`, button/input = `rounded-lg`, badge = `rounded` or `rounded-full`.
7. **Type**: mono for any data value (numbers, IPs, IDs, timestamps); sans for everything else; `uppercase tracking-wider` on micro-labels (`text-2xs uppercase tracking-wider`).
8. **Severity/threat/layer coloring**: go through `severityColor`, `severityClass`, `threatLevelColor`, `layerColor` in `lib/utils.js`. Use `Badge variant="critical|high|…"` when rendering a pill.
9. **Motion**: `animate-fade-in` / `animate-slide-up` / `animate-scale-in`, or a `framer-motion` block using the existing `anim` preset.
10. **Theme**: verify the design reads correctly in both modes — flip `.dark` on `<html>` via the Header toggle. If you must add a mode-specific rule, do it with `html:not(.dark) …` or `.dark …` in `index.css`, not with inline conditionals.
11. **Routes**: if the Figma adds a new top-level view, add it to `NAV_ITEMS` in `nav/navConfig.js` and a `<Route>` in `AuthenticatedApp` — nothing else should know the path.
12. **Never**: add new global CSS, new font families, new icon libraries, new styling systems, TypeScript files, or a second state-management library alongside zustand.
