# Visual Guidelines (V1)

This guide defines reusable UI tokens and motion rules for the current dark Obsidian-inspired theme.

## Theme Tokens

Core tokens live in `frontend/app/globals.css`:

- `--bg`: application canvas background
- `--surface` / `--surface-soft`: layered card backgrounds
- `--text` / `--muted`: primary and secondary text colors
- `--border`: default border color
- `--brand` / `--brand-strong`: violet interaction accents
- `--error` / `--success`: status colors

## Component Usage Rules

- `PageCard` is the default page shell for top-level pages.
- `status` + `status-error`/`status-success` should be used for transient user feedback.
- `kpi-card`, `chart-card`, `result-block` are reusable dashboard content containers.
- `graph-filter-row` owns graph workflow filter controls and must stay keyboard operable.

## Motion Principles

- Use motion to guide hierarchy and transitions, not to decorate every element.
- Keep enter animation duration between `420ms` and `550ms` (`riseIn` baseline).
- Route transitions (`routeSweep`, `routeFlash`) should remain under `900ms`.
- Respect reduced motion with `@media (prefers-reduced-motion: reduce)`.

## Readability and Accessibility Guardrails

- Preserve strong contrast for labels and muted text on dark surfaces.
- Keep interactive controls focus-visible with clear outlines.
- Mobile first breakpoints: `768px` and `420px`.
- Ensure long content wraps safely in status blocks and `pre` blocks.

## Change Log

- 2026-04-21: Added keyboard graph focus guidance and visual baseline test strategy.
- 2026-04-21: Added `qa-fast`, `qa-visual`, `qa-all` quality gates.
