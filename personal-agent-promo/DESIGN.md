# Design System

## Overview

Personal Agent is a dark, operational product UI for execution, reflection, and deterministic multi-agent orchestration. The interface uses an obsidian cockpit layout: bordered modules, purple brand energy, green success states, and compact data panels. Visual density comes from KPI grids, history cards, queue replay timelines, and inspectable audit payloads rather than decorative marketing blocks.

## Colors

- **Primary Background**: `#0f1119` - full-canvas dark base.
- **Primary Surface**: `#181b2b` - main panel surface.
- **Soft Surface**: `#1e2235` - nested controls and cards.
- **Primary Text**: `#e9ecff` - headings and high-emphasis copy.
- **Muted Text**: `#a4afcc` - descriptions and secondary metadata.
- **Border**: `#2d3350` - card and panel boundaries.
- **Brand Accent**: `#a68aff` - labels, highlights, and glows.
- **Brand Strong**: `#7f62ff` - active states and CTA energy.
- **Success**: `#66d2ab` - healthy queue and success signals.
- **Error**: `#ff7b8a` - failed/canceled state and risk warnings.

## Typography

- **Primary Sans**: Avenir Next, Segoe UI, Sora, sans-serif. Used for all product UI, headings, labels, and cards.
- **Label Style**: uppercase micro-labels with moderate tracking for execution states and audit categories.
- **Number Style**: tabular numerals for metrics, queue attempts, duration, and conversion data.
- **Video Scale**: hero headings 76-104px, card headings 28-44px, body 22-30px, labels 18-22px.

## Elevation

Depth is built with thin borders, translucent surfaces, and localized purple glow rather than heavy drop shadows. Cards sit on a dark workspace with soft radial lighting and faint grid motion. Product surfaces should feel inspectable and layered, like a command center where every state can be audited.

## Components

- **Obsidian Hero Workspace**: dark hero section with copy on the left and a glass-layer stack on the right.
- **KPI Grid**: compact metric cards for plans, reflections, analyses, orchestration runs, partial success, revenue, paid runs, and duration.
- **Orchestration Step Cards**: deterministic `conclusion/evidence/risk/next_action` blocks with status labels.
- **Queue Timeline Replay**: event cards showing queued, running, succeeded, failed, and canceled states.
- **Tier Boundary Controls**: free, pro, and power segmented options guarded by signed entitlement.
- **Route Transition Grid**: purple grid and sweep visual used for navigation momentum.

## Do's and Don'ts

### Do's

- Use exact product colors from the CSS variables.
- Keep modules dense, bordered, and easy to scan.
- Show audit evidence, risk, and next action as structured outputs.
- Use purple for brand focus and green/red for lifecycle truth.
- Make queue and replay states visibly deterministic.

### Don'ts

- Do not turn the promo into a generic SaaS landing page.
- Do not use bright white canvases or pastel marketing palettes.
- Do not hide orchestration outputs behind vague AI phrasing.
- Do not over-round cards beyond the product feel.
- Do not use unrelated illustrations when product UI can tell the story.
