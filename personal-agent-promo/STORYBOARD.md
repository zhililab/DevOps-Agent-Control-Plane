# Storyboard

**Format:** 1920x1080  
**Duration:** 20 seconds  
**Audio:** Voiceover-ready script in `SCRIPT.md`; no rendered narration included because TTS requires the HyperFrames CLI.  
**VO direction:** Calm, precise, senior DevOps operator energy. Leave short pauses after each sentence.  
**Style basis:** `DESIGN.md` colors, typography, and components from the local Next.js app.

## Asset Audit

| Asset | Type | Assign to Beat | Role |
| --- | --- | --- | --- |
| `assets/icon.svg` | Brand mark | Beat 1, Beat 5 | Product identity opener and closer |
| CSS-built dashboard panels | Product UI | Beat 1, Beat 2 | Hero workspace and KPI cockpit |
| CSS-built orchestration cards | Product UI | Beat 3 | Deterministic audit surface |
| CSS-built queue timeline | Product UI | Beat 4 | Queue lifecycle and replay proof |
| CSS-built tier controls | Product UI | Beat 4, Beat 5 | Entitlement boundary visual |

## BEAT 1 - BLACK BOX OPEN (0:00-0:04)

**VO:** "Your AI workflow shouldn't be a black box."

**Concept:** The viewer starts inside a dark operational workspace. A sealed black panel opens into the product cockpit, making the invisible workflow visible.

**Visual:** Brand mark glows in the upper-left. A large headline anchors the left side. On the right, layered dashboard cards drift forward: orchestration runs, partial success, average duration, and revenue. Thin grid lines move behind the surface.

**Animation:** Logo breathes in. Headline rises and resolves. Cards cascade in from different depths. Metric numbers count up. A purple sweep transitions to the next beat.

## BEAT 2 - WORKFLOW LOOP (0:04-0:08)

**VO:** "Personal Agent turns daily DevOps work into deterministic orchestration."

**Concept:** The workflow becomes a repeatable loop instead of a scattered day. Three agent lanes form a circuit.

**Visual:** Planner, Analyzer, and Reviewer lanes form around a central run token. Small task chips move through the lanes. A status rail shows `running`, `success`, and `partial_success`.

**Animation:** SVG-like connector lines draw across the scene. Lane cards slide into alignment. The run token travels across the path. Status chips pulse as they activate.

## BEAT 3 - INSPECTABLE STEPS (0:08-0:12.5)

**VO:** "Plan the day. Analyze signals. Review and reflect. Every step leaves evidence, risk, and a next action you can replay."

**Concept:** The product proves that AI output is structured and auditable. Each agent card opens into a deterministic audit payload.

**Visual:** Three step cards fan across the frame. Each card exposes four rows: conclusion, evidence, risk, next_action. A replay scrubber line moves underneath.

**Animation:** Cards enter with staggered depth. Audit rows type on. Risk badges flip from muted to green or red. Replay scrubber glides left to right.

## BEAT 4 - QUEUE CONTROL (0:12.5-0:16.5)

**VO:** "Queue it, retry it, cancel it, and keep tier boundaries auditable."

**Concept:** The system is not just a run button. It has lifecycle control and subscription guardrails.

**Visual:** Queue timeline stages appear: queued, running, succeeded, failed, canceled. A retry button lights, a cancel request locks, and free/pro/power tier chips sit beside a signed entitlement strip.

**Animation:** Timeline nodes activate one by one. Failed state snaps red, retry routes back to queued, cancel becomes idempotent. Entitlement strip scans with a controlled shimmer.

## BEAT 5 - CTA LOCKUP (0:16.5-0:20)

**VO:** "Personal Agent. Execution you can inspect."

**Concept:** The animated control surface settles into a clean product lockup. The product name and promise remain.

**Visual:** Brand mark, product name, and final line on a dark canvas. Mini UI panels orbit quietly behind the lockup without stealing focus.

**Animation:** Background panels decelerate. Logo scales into place. Final line writes on. Scene fades down in the last half second.

## Production Architecture

```text
personal-agent-promo/
├── index.html
├── DESIGN.md
├── SCRIPT.md
├── STORYBOARD.md
└── assets/
    └── icon.svg
```
