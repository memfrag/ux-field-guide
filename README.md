# The UX Field Manual

An opinionated, self-contained reference for mobile-first UX/UI design — the working principles behind every critique and recommendation, and a process for taking an app idea to designs that feel native on **both iOS and Android**.

**Read it here: https://memfrag.github.io/ux-field-guide/**

## What's inside

**Part I — Foundations** · how people perceive, decide, and touch

| # | Chapter | |
|---|---------|---|
| 01 | Working Posture | the default stance behind every decision |
| 02 | Laws of Interaction | Fitts, Hick, Jakob, Miller, Tesler, peak–end |
| 03 | Nielsen's Ten | the evaluation checklist, condensed |
| 04 | Gestalt Principles | how the eye groups before the mind reads |
| 05 | Visual Hierarchy | the five levers, with worked examples |
| 06 | Mobile Instincts | thumb zones, touch targets, interruptions |
| 07 | Accessibility | contrast, type scaling, screen readers, focus |

**Part II — Method** · from idea to iteration

| # | Chapter | |
|---|---------|---|
| 08 | The Process | app idea → shipped design, in order |
| 09 | Four Modes of Work | critique · diagnose · reason · produce |
| 10 | Research & Testing | tasks not opinions, five users, severity |

**Part III — Platforms** · one design, expressed natively twice

| # | Chapter | |
|---|---------|---|
| 11 | One Design, Two Dialects | shared core vs. HIG / Material 3 layers |
| 12 | Navigation | back semantics, tabs, modality, deep links |
| 15 | SwiftUI ↔ Compose | the dialect table as it compiles |

**Part IV — Systems & Craft** · the details that decide whether it ships well

| # | Chapter | |
|---|---------|---|
| 16 | Design Systems | decisions made once |
| 17 | Design Tokens | name the decision, not the value |
| 18 | Forms & Input | where most apps actually lose people |
| 19 | UX Writing | buttons, errors, empty states, platform casing |
| 20 | Empty & Loading States | blank and waiting are where trust is won |
| 21 | Motion & Feedback | animation is information — or it's in the way |

**Part V — Judgment** · what to avoid, what to weigh, how to check

| # | Chapter | |
|---|---------|---|
| 26 | What Not To Do | universal, iOS, and Android anti-patterns |
| 27 | The Honest Trade-offs | where the pin sits, and what moves it |
| 28 | The Screen Audit | a 12-point interactive checklist |
| 29 | A Worked Example | one app idea, the whole process, both dialects |

Grounded in Apple's Human Interface Guidelines (Liquid Glass era) and Google's Material 3 (Expressive).

## Notes

- **One file.** `index.html` is fully self-contained: no build step, no external fonts, scripts, or images — all illustrations are inline SVG themed by CSS variables.
- **Deep links.** Every numbered entry is linkable (e.g. [§7.4](https://memfrag.github.io/ux-field-guide/#s7-4)).
- **Printable.** A print stylesheet converts it to a light, paginated document.
- **The checklist remembers.** Screen-audit ticks persist in `localStorage`.

To work on it: open `index.html` in a browser. That's the whole toolchain.
