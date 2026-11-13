---
name: logical-leap-signal
version: 1.0.0
description: Logical Leap's branded beLine Max Podcast / Amplified video editing preset. Use for Logical Leap founders, client education, AI automation, web design, SEO, CRM, B2B marketing and agency commentary. Retain beLine's speaker-first edit, synchronized bold white captions, sequential insight cards and restrained movement; re-skin with Logical Leap purple/lime and Inter typography. "Logical Leap Signal Editorial" is the optional restrained Instrument Serif title-only variant.
---

# Logical Leap Signal — Video Editing Skill
**Status:** Brand-aligned production preset, v1.0, created November 12, 2026.
**Activators:** "Logical Leap style", "Logical Leap Signal", "Logical Leap branded beLine", "Signal Editorial".
**Parent skill:** `beline-max-podcast` / **beLine Max Podcast — Amplified**. This is a brand adaptation, NOT a redesign of editorial grammar.

## Sources and confidence
- Live site: https://logicalleap.tech
- Site source: `Logical-Leap/logicalleap-replica`, `src/index.css`, `tailwind.config.ts`, `index.html` on main (reviewed Nov 12, 2026).
- beLine original skill: https://drive.google.com/file/d/1xxSQJ8_vJy0JIp3v2nD4H4T_FUFrR0U-/view
- beLine edited-video reference: https://drive.google.com/drive/folders/1hzoVWoWBOHJUXQjE4RAbafjZWbaLI48M
- Visual identity supplied by user: circular white astronaut and "Logical Leap" wordmark over dark violet-to-blue gradient. The supplied image is a screenshot, NOT an export-quality transparent master.
- Color numbers below are derived from website HSL variables and rounded to hexadecimal. They are implementation tokens, not a separately verified official brand-guidelines PDF.
- The website uses `Inter` for body and `Instrument Serif` for headings; the user prefers predominantly sans-serif in video.

## Non-negotiable visual identity
Use **one active highlight color per frame**. No competing green/yellow/blue accents in the same caption or card. Be consistent across a whole batch.

| Role | Hex | Rule |
|---|---|---|
| Primary / structural purple | `#190731` | Backgrounds, card fills, brand dividers |
| Dark canvas | `#0E051A` | Full-frame graphics, lower scrims |
| Single active highlight, Leap Lime | `#99CD32` | Important caption word, card edge, numeric callout, CTA |
| White | `#F5F5F5` | Default captions, diagram labels |
| Optional dark card surface | `#180E25` | Internal contrast with purple canvas |
| Website yellow token | `#F9D51F` | Observed in site code; **not used in default Signal video** |
| Legacy brand blue | asset-only | Allowed ONLY as part of approved existing astronaut-logo gradient; do not introduce arbitrary blue highlights |

**Palette usage:** default approximately 70% existing footage/dark surfaces, 25% white, 5% lime accents. No multi-tone lime palette. No yellow/gold beLine accent and no saturated blue UI ornaments in the default preset. Website brand colors and the screenshot-logo gradient differ; do not invent a unified formal brand kit from this evidence.

## Typography and two selectable variants
### Default: Signal Sans
- Headline captions: `Inter Tight ExtraBold` (or `Inter Black` if Inter Tight not available), **ALL CAPS**, solid white.
- Highlight one short word or key phrase in `#99CD32`, synchronized to actual spoken words.
- Diagrams/cards: `Inter Bold` for labels, `Inter Medium` for explanatory text, `Inter Black` for numerals.
- Wordmark: always use original approved logo art; never approximate its letterforms using a typed font.
- No serif in subtitles, lower thirds, data, lists or CTA.

### Optional: Signal Editorial
- Identical edit decisions, framing, transitions, color palette and caption system as Signal Sans.
- Permit `Instrument Serif` ONLY for a standalone opening title, quote pull, or section-header card (generally <=15% of screen-time). Never use serif for synchronized subtitles or small moving text.
- Pair serif headings with sans captions and diagram labels; do not use multiple serif font families.
- Default to Sans unless user explicitly selects Editorial.

## Preserve the beLine edit grammar
1. **Speaker-first.** Show tightly framed real face-cam/A-roll as the dominant visual; use original footage. Prefer 9:16 `1080x1920` or higher for Shorts/Reels, native frame rate (24fps if specifically matching the source beLine clips). Also support 16:9 without shrinking captions awkwardly.
2. **Dialogue first.** Find the strongest true quote within the first ~0-3 seconds. Build a self-contained argument with a payoff. Remove fillers/false starts only when speech continuity remains natural. Do not chop final words/phonemes, re-order to distort meaning or fabricate lines.
3. **Top captions.** Keep readable 2-6-word chunks in top safe area (roughly 8-18% frame height). White text with ONE lime emphasis beat. Solid filled text, never thin outlines. Hold captions long enough to read. Captions must reflect the spoken transcript exactly.
4. **Mid/lower semantic cards.** Use deep-purple near-opaque rectangular cards, small corner radius, a single 1-2px lime divider or border, white copy, optional lime number. Reveal adjacent rows/steps as speakers mention them. Show one main graphic system at a time; never cover mouth, face, subtitles or existing lower thirds.
5. **Illustrate specific spoken concepts.** Good treatments: `LEAD -> CRM -> FOLLOW-UP`, `3 MANUAL HANDOFFS` vs `ONE CONNECTED WORKFLOW` when actually discussed; honest anonymized dashboards; clean process arrows; simple side-by-side comparisons. Never invent customer figures, savings, approval rates or testimonials.
6. **Motion.** Primarily clean hard cuts. On intentional reframing, use an occasional single-direction eased camera move around 3-6% over ~0.4-0.7 s, followed by a stable hold; these are initial tuning targets, not measured reference specs. Avoid automatic pulses on each cut, zoom snapbacks, fast simultaneous scales, abrupt reframe resets and gratuitous spin/glow effects. Card reveals should be short (~4-10 frames at 24fps), eased and then held steady.
7. **Visual rhythm.** Alternate portrait-led exposition with occasional explanation panels where semantics justify them; do not fill every second with graphics. Hold the shot when dense type needs reading. Avoid unrelated montage/B-roll unless explicitly directed by the project.
8. **Sound.** Original speech is authoritative and remains dry and intelligible. Do not duplicate audio, add artificial reverb, overcompress, clip, time-stretch speech without permission or make sound effects overpower spoken words. Music is off by default; if requested, use licensed/approved track, mixed under dialogue.
9. **Logo and ending.** Optional short logo lockup at the end with original approved artwork, on `#190731` or `#0E051A`, subtle fade, no reinterpretation of the astronaut. Screenshot of logo is a visual reference only, not production logo art. CTA only where source supports the offer, e.g. "LEARN MORE AT LOGICALLEAP.TECH"; avoid unverified urgency or claims.
10. **Batch identity.** Exact same lime, purple, font weights, border widths, radii and motion timings across the batch. Avoid previously rejected inconsistent greens/yellows and abrupt pushes.

## Layout presets
**Portrait interview / 9:16**
- Face is primary; safe caption band at top; one explanatory system in lower half, placed to avoid occlusion.
- Caption size baseline ~64-90px at 1080-wide; adjust to phrase length, face position and platform safe zones; do not force single-line width beyond safe area.
- Card labels typically 42-60px; numerals can be larger. Usable safe margin at least 7% of frame width, adjusted for platform UI.

**No-face explainer**
- Only when source lacks usable camera footage: build from factual screenshots, charts, process diagrams, authentic UI recordings and meaningful animation. No fabricated interface data.
- Purple canvas, single lime focus, white text, strong hierarchy. Animation demonstrates a process, not merely decorative motion.

**16:9**
- Preserve A-roll resolution, use lower-third cards or side panels as safe; do not blindly scale a vertical layout. Keep full-resolution logos and avoid tiny type.

## Example 30-45s structure
- 0-3s: real spoken hook, clean face crop, synced white/lime caption.
- 3-11s: define problem, show one purple/lime labeled card.
- 11-25s: reveal a 2-3-step process diagram in the order described.
- 25-37s: speaker takeaway, simplify composition to face + caption.
- 37-45s: organic conclusion and optional quiet website/logo end card if source and message justify it.
Timing is illustrative, never a mandatory template or reason to truncate the idea.

## Source/editing workflow
1. Locate highest-quality source recording, transcript, permission boundaries and approved original logo file.
2. Select self-contained accurate clip; mark hook, claim, proof and closing line. Do not invent a proof point.
3. Lock clean dialogue edits before any motion/captions. Keep lips/speech in sync and final sentence intact.
4. Generate accurate word-level timings; proofread names, nouns, numbers, products and URLs.
5. Create beat sheet mapping exact quote/timecode -> caption phrase/highlight -> graphic -> entry/hold/exit.
6. Render Sans by default; Editorial when specifically requested. Export as H.264/H.265 MP4 + AAC, >=1080p.
7. Review full export visually and audibly: no truncated words, doubled dialogue, strange reverb, jittery camera, caption overflow, clipped logo, conflicting accent shades, unsupported facts or unreadable information.
8. Deliver MP4, optionally SRT, edit beat sheet, source manifest and editable FCPXML/timeline as supported. Only claim uploaded or published files after verification.

## Exclusions and lineage
- Not `nor-ad-glass`, not bright glossy conversion advertising, not music-first Kino, not an unrelated Sly minimalist cut.
- Do not overwrite or change the parent `beline-max-podcast` skill. This is an independent child profile.
- Distinguish **documented** palette/font choices from **provisional** camera timings and caption sizes.
- An Agent Skills `SKILL.md` file committed to a repository is *not* automatically an installed, account-wide ChatGPT skill; a compatible editor must load this path or be instructed to use it.

## Sample invocation
"Use `logical-leap-signal` in Sans mode for a 9:16 Logical Leap clip. Keep the beLine speaker-led pacing and white word-synced captions, replacing beLine gold with ONE Leap Lime #99CD32. Use Inter, deep-purple explainer cards, restrained eased pushes, dry original speech, no fake metrics, no reverb and no unrelated montage. Review the final render."
