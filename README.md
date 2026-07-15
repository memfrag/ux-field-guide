# The UX/UI Field Manual

An opinionated, self-contained reference for mobile-first UX/UI design — the working principles behind every critique and recommendation, interaction and visual craft both, and a process for taking an app idea to designs that feel native on **both iOS and Android**.

**Read it here: https://memfrag.github.io/ux-field-guide/**

## What's inside

**Part I — Foundations** · How people perceive, decide, and touch

| # | Chapter | |
|---|---------|---|
| 01 | Working Posture | the default stance behind every decision |
| 02 | Laws of Interaction | Fitts, Hick, Jakob, Miller, Tesler, peak–end |
| 03 | Nielsen’s Ten | the evaluation checklist, condensed |
| 04 | Gestalt Principles | how the eye groups before the mind reads |
| 05 | Visual Hierarchy | the five levers, with worked examples |
| 06 | Grid Systems | the invisible structure behind consistent hierarchy |
| 07 | Mobile Instincts | thumb zones, touch targets, interruptions |
| 08 | Accessibility | contrast, type scaling, screen readers, focus |

**Part II — Method** · From idea to iteration — how the work gets done

| # | Chapter | |
|---|---------|---|
| 09 | The Process | app idea → shipped design, in order |
| 10 | Mapping Methods | empathy maps, journey maps, experience maps, blueprints |
| 11 | Four Modes of Work | critique · diagnose · reason · produce |
| 12 | Research & Testing | tasks not opinions, five users, severity |

**Part III — Platforms** · One design, expressed natively twice

| # | Chapter | |
|---|---------|---|
| 13 | One Design, Two Dialects | shared core vs. HIG / Material 3 layers |
| 14 | Navigation | back semantics, tabs, modality, deep links |
| 15 | Adaptive Layout | size classes, list-detail, foldables |
| 16 | Iconography & Imagery | SF Symbols vs Material Symbols, app icons |
| 17 | SwiftUI ↔ Compose | the dialect table as it compiles |
| 18 | Widgets & Live Surfaces | WidgetKit, Live Activities, Live Updates |

**Part IV — Systems &amp; Craft** · The details that decide whether it ships well

| # | Chapter | |
|---|---------|---|
| 19 | Design Systems | decisions made once |
| 20 | Design Tokens | name the decision, not the value |
| 21 | Forms & Input | where most apps actually lose people |
| 22 | UX Writing | buttons, errors, tone of voice, platform casing |
| 23 | Empty & Loading States | blank and waiting are where trust is won |
| 24 | Motion & Feedback | animation is information — or it's in the way |
| 25 | Onboarding & First-Run | the shortest path to the first win |
| 26 | Notifications & Interruptions | the trust economy of the lock screen |
| 27 | Internationalization | text expansion, RTL, locale formats |
| 28 | AI Interface Patterns | the autonomy ladder, streaming, uncertainty |

**Part V — Visual Craft** · Type, color, depth, data, and image — the layer under the interaction

| # | Chapter | |
|---|---------|---|
| 29 | Typography Systems | modular scales, pairing, optical sizing |
| 30 | Color Systems | one seed hue to a full role-based palette |
| 31 | Elevation & Depth | tonal vs. directional, shadow as a spatial claim |
| 32 | Data Visualization | form first, color last, validated not eyeballed |
| 33 | Illustration & Empty-State Art | one consistent style, earned not decorative |

**Part VI — Judgment** · What to avoid, what to weigh, how to check

| # | Chapter | |
|---|---------|---|
| 34 | What Not To Do | universal, iOS, and Android anti-patterns |
| 35 | The Honest Trade-offs | where the pin sits, and what moves it |
| 36 | The Screen Audit | a 12-point interactive checklist |
| 37 | A Worked Example | one app idea, the whole process, both dialects |
| A | Sources & Further Reading | HIG, Material 3, WCAG, NN/g, the books |

Grounded in Apple's Human Interface Guidelines (Liquid Glass era) and Google's Material 3 (Expressive).

## Notes

- **One file.** `index.html` is fully self-contained: no build step, no external fonts, scripts, or images — all illustrations are inline SVG themed by CSS variables.
- **Deep links.** Every numbered entry is linkable (e.g. [§8.4](https://memfrag.github.io/ux-field-guide/#s8-4)).
- **Printable.** A print stylesheet converts it to a light, paginated document.
- **The checklist remembers.** Screen-audit ticks persist in `localStorage`.
- **Cheat sheet.** [`cheatsheet.html`](https://memfrag.github.io/ux-field-guide/cheatsheet.html) is a print-first one-pager: laws, audit, numbers, dialect table.
- **Auto-versioned.** The Pages deploy stamps the footer with the git date, revision count, and SHA.

To work on it: open `index.html` in a browser. That's the whole toolchain.
