# Design System — OMRFlow

Hard UI rules derived from the product requirements. These are non-negotiable and apply to every screen. The agent must follow them.

## Principles

1. **Custom everything.** No native `<select>` dropdowns, no browser `alert()` / `confirm()` / `prompt()`. Every dropdown, menu, picker, dialog, and notification is a custom-styled component.
2. **Modals, not alerts.** Confirmations, errors, and prompts use custom modal dialogs or toast notifications — never native popups.
3. **Concise copy.** Short, precise text. Labels, not paragraphs. No filler, no long explanations in the UI.
4. **Mobile-first & fully responsive.** Design for 320px first, scale up. Every screen must be usable on a phone and on a wide desktop.
5. **Consistent & calm.** One spacing scale, one type scale, a small color palette, consistent component behavior.
6. **Accessible.** Keyboard navigable, visible focus states, adequate contrast, proper roles/aria on custom components.

## Required custom components

Build these once, reuse everywhere:

- **Select / Dropdown** — custom listbox (button + popover + options), keyboard support (↑/↓/Enter/Esc), search for long lists. Replaces native `<select>`.
- **Multi-select** — chips + searchable options.
- **Modal / Dialog** — header, body, actions; focus-trapped; closes on Esc/overlay; used for confirms and forms.
- **Confirm dialog** — a thin wrapper over Modal for yes/no actions (e.g., delete test).
- **Toast / Snackbar** — transient success/error/info messages.
- **Menu / Context menu** — for row actions, overflow menus.
- **Tabs**, **Accordion** — for analytics and settings sections.
- **Data table** — sortable, paginated, responsive (collapses to cards on mobile).
- **Form fields** — text, number, textarea, toggle, radio, checkbox, file upload (for scans) — all custom-styled with inline validation messages.
- **Stepper / Wizard** — for multi-step flows (test creation, sheet generation).
- **Progress** — bar/indeterminate for async scanning.
- **Empty states** — concise, with a single clear action.
- **Charts** — wrap Chart.js for distributions, trends, improvement deltas.

## Layout & responsiveness

- Breakpoints (Tailwind defaults): `sm 640 / md 768 / lg 1024 / xl 1280`.
- Patterns: tables → cards on small screens; sidebar → bottom/hamburger nav on mobile; multi-column forms → single column on mobile.
- Touch targets ≥ 44px. No hover-only interactions (must work on touch).
- Test every screen at 320px, 375px, 768px, 1280px.

## Visual language (starter — refine to taste)

- **Type scale**: e.g., 12 / 14 / 16 / 20 / 24 / 32. Body 14–16. One font family.
- **Spacing scale**: 4 / 8 / 12 / 16 / 24 / 32.
- **Radius**: consistent (e.g., 8px for inputs/cards, 12–16px for modals).
- **Color**: neutral background, one primary accent, semantic success/warning/error/info. Keep it small and consistent. Define as CSS variables / Tailwind theme tokens so it's themeable.
- **Elevation**: subtle shadows for popovers/modals; clear overlay scrim for modals.
- **States**: every interactive element has hover, active, focus, disabled, and loading states.

## Tech notes

- React + Tailwind for tokens + utilities. Build the component library as reusable React components (dropdowns, modals, toasts, etc.) — implement once, import everywhere.
- Use a headless primitive library (e.g., Radix UI or Headless UI) under custom Tailwind styling for accessible dropdowns/modals/menus, so you get keyboard/focus behavior for free while keeping the look fully custom. Charts via Recharts.
- Centralize components in a shared UI folder; screens compose them. Never re-implement a dropdown or modal per screen.
- The same component rules port 1:1 to the mobile app (React Native) later.

## Copy guidelines

- Buttons: verbs ("Create test", "Generate sheets", "Scan").
- Errors: say what happened + what to do, briefly ("Couldn't read QR. Re-upload a clearer photo.").
- Avoid jargon in user-facing text. Keep everything scannable.

## Definition of done (UI)

A screen is done only when: no native dropdown/alert is used; it's responsive at all four test widths; all states exist; it's keyboard-accessible; copy is short and clear.
