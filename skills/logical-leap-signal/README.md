# Logical Leap Signal — Branded beLine Editing Skill

This folder packages the `logical-leap-signal` reusable video-editing preset.

- **[SKILL.md](./SKILL.md):** production rules, source lineage, typography variants, caption placement, timing, animation, audio QA, logo constraints, and example usage.
- **[brand-tokens.json](./brand-tokens.json):** reusable design values for programmatic editors and templates.

## Two modes

- **Signal Sans (default):** all-sans Inter/Inter Tight, purple structure and a single lime highlight.
- **Signal Editorial (opt-in):** same beLine-style edit grammar, with selective Instrument Serif display titles only.

## Using it

In a skills-capable agent, register/load this folder according to that agent's skills configuration. In ChatGPT or an editing workflow without automatic skill discovery, point the editor to this `SKILL.md` file or quote its activation name `logical-leap-signal`.

This repository commit does **not** independently install an account-wide ChatGPT plugin/skill. The original `beline-max-podcast` reference remains separate.

Source of website-aligned color and font tokens: [logicalleap.tech](https://logicalleap.tech) and the site repository's `src/index.css` / `tailwind.config.ts`. Astronaut mark in user-provided screenshot is for design analysis, not a transparent production logo file.
