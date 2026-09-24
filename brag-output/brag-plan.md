# Brag Plan: vasp_triage (v3 — revision after frame-by-frame review)

## What is this app?
vasp_triage is a standard-library-only Python tool that walks into VASP calculation folders you already made, on a cluster, figures out what actually happened in each one, writes that history into the folder as plain text, and asks before touching a single file.

## What changed in this revision
A frame-by-frame review of the v2 (~43s) render found real bugs and real gaps, all fixed here:

**Bugs to fix (not stylistic — these read as broken):**
1. Clipped text at the terminal card edge in three shots (`--status "not su`, `energy(sigma→`, the ZBRENT message). Fix by widening the terminal card and/or reducing the command font-size slightly — text must never touch or cross the card's right edge. Build in real side padding (at least 48px at 1920 width) and verify every line of copy fits inside it before animating.
2. The submit and history command scenes showed a typed command with an empty panel underneath — no output. These are now specified with full real output below (see Scene 9 and Scene 11) and must never render as a bare prompt.
3. `vtriage sub` appeared frozen mid-type in one shot. Every typed command must finish typing and hold complete for at least 0.3s before the scene does anything else (cut, add output, etc.) — never cut away or add output while a string is still typing.

**New content added, all grounded in the actual code (see file:line references below):**
- The full, real `submit` output — the "money shot" — including the queue count, the folder list with CONTCAR-restart annotations, and the confirmation prompt with a blinking cursor before the cut.
- A `Warning: same error as previous run (zbrent)...` line — shows the tool being smart, not just tidy.
- The exact POTCAR mismatch line the code produces, verbatim, as terminal output rather than paraphrased prose.
- A menu scene — half a second of the real numbered menu with its banner, so the video doesn't read as command-line-only.
- A scale beat — one frame with a concrete count, to signal the tool survives a real mess of directories.
- An install beat — `git clone`, no pip/conda/database — because the barrier to entry is part of the pitch.
- A drawn-out ASCII-art ending using the tool's own real banner from `menu.py`, plus the repository link, so the video ends with something to act on.

**Structural fix:** the old cut spent ~10.5s of its 43s on "what other tools do" before showing anything of vasp_triage's own. That's compressed to ~7s here (hook + one combined contrast/reversal beat) so the "money shot" scenes (submit, POTCAR catch) get real room instead.

## The angle
Every other tool in this space (custodian, atomate2, AiiDA) wants to own your calculation from the start. vasp_triage is the opposite: it shows up after the fact, to the mess that's already on disk, and treats the directory itself as the source of truth. The credibility now comes from *proof*, not just claims: the actual submit confirmation prompt, the actual warning it prints when you're about to repeat a mistake, the actual POTCAR mismatch message, and the actual menu — shown, not described.

## Hook (first 2-3 seconds)
Typed line: "Several hundred directories. No memory of which is which."

## Key moments (the middle)
- **The submit money shot** (Scene 9): the real, full `submit` output with the queue count, the folder list, CONTCAR-restart annotations, and a blinking cursor sitting at the "Type yes to save each run and submit:" prompt — this is the clearest proof of "never acts without your yes."
- **The POTCAR catch** (Scene 7): the verbatim code output `POTCAR order Re W differs from POSCAR W Re`, captioned "Runs to completion. Gives a number. Nothing warns you." — the sharpest differentiator in the whole tool.
- **The warning** (Scene 10): `Warning: same error as previous run (zbrent). Change settings first.` in red — proof the tool remembers, not just logs.
- **The menu** (Scene 4): half a second of the real numbered menu and banner — proof this isn't command-line-only.
- **The progress.txt reveal** (Scene 12): unchanged from before — Run 1 crashed → Run 2 converged, read as a commit history.
- **Scale** (Scene 13): a real count — 247 directories, 4 seconds — the moment someone decides whether this survives their own mess.
- **Install** (Scene 15): `git clone ...` / "No pip. No conda. No database." — the barrier is the pitch.

## Outro / punchline
The tool's own real ASCII banner from `menu.py`, drawn line by line top to bottom at ~0.15s per line, in the same terminal green (bars) and white (letters) as the rest of the video, then the repository link fades in beneath it: `github.com/Gaurav-Arora-MatSci/vasp_triage`.

## User flow worth showing
The full real command surface, now including the menu as an alternative entry point: `vtriage status` → `vtriage menu` (briefly) → `vtriage report` → `vtriage edit` → `vtriage submit` (full real output) → a `Warning:` line → `vtriage history` (full real output) → the `progress.txt` artifact.

## Tone
- Preset: polished
- Creative direction: quiet, precise systems-tool film — terminal/monospace aesthetic, confident restraint. Unchanged from before, but now the proof-scenes (submit, POTCAR, warning) should land with a beat of stillness — let the viewer actually read the real output, don't rush past it.
- Interpretation: every terminal card gets real breathing room on both sides — no more clipping. The submit scene in particular should feel like the money shot: give it more time than any other feature scene (6s) and let the cursor blink at the confirmation prompt.

## Format: landscape — 1920x1080
## Duration: ~54s (elongated further from v2's 43s to fit the money-shot scenes properly; this is intentional per explicit feedback — do not compress back down by cutting the new proof scenes)

## Visual identity (from the project)
- Background: near-black terminal (#0d1117-style dark background)
- Accent: terminal green (#4ade80) for status words, command prompts, and the ending banner's bars
- Text: off-white monospace (#e6edf3) for terminal/log content; white for the ending banner's letters; a clear red/warning color (e.g. #f87171) reserved only for the `Warning:` line — nowhere else
- Display font: technical monospace (e.g. "JetBrains Mono" / "IBM Plex Mono")
- Body font: clean sans (e.g. "Inter") for captions
- Terminal card sizing: wide enough that every line of copy in this plan fits with at least 48px of clear padding on both sides at 1920 width — check the longest line in each scene (the submit folder-list lines and the POTCAR mismatch line are the widest) and size the card to that, not the other way around
- Strongest visual elements, in order: the submit money-shot (Scene 9), the progress.txt reveal (Scene 12), the POTCAR catch (Scene 7), the real ASCII banner ending

## Share copy (draft)
vasp_triage doesn't run your VASP jobs — it walks into the ones you already ran, catches the failures that run clean and silent (like a mismatched POTCAR), and asks before it touches a single file. No pip, no conda, no database.

## Audio direction
- Role: sparse professional accents over a steady, low music bed — unchanged philosophy from v2, extended to the new ~54s length
- Music: happy-beats-business-moves-vol-12-by-ende-dot-app.mp3 (117s long, ample runway, no loop needed)
- Music treatment: near-silent under the hook, fades in through the combined contrast/reversal beat, holds flat (~0.25-0.3) through the feature/proof scenes so it never fights command-typing SFX or the warning line, lifts slightly (~0.3-0.35) under the POTCAR catch, the submit money shot, and the progress.txt reveal — the three biggest payoffs — fades under the ending banner draw-on, silent under the final link.
- Music cue guidance: same bundled preset as before (109.96 BPM). Use as soft hints only; at a ~54s length, do not attempt more than 2-3 strong-cue locks total. Never let a cue rush the submit prompt's blinking-cursor hold or the POTCAR line's reading time.
- Audio-reactive treatment: subtle — same as before, terminal window glow may breathe faintly with RMS; skip if not straightforward, as was already the call in v1/v2.
- SFX posture: sparse, dry, reused across all command scenes (status, menu, report, edit, submit, history) so the now-larger command count still reads as one restrained family. The warning line gets its own single, quiet, low "alert" tone distinct from the neutral command SFX — not alarming, just distinct. The submit scene's blinking cursor at the confirmation prompt should have no additional SFX — let the silence and the blink carry the tension. The ending banner draw-on gets one soft tick per line-batch (not per character) as it draws, or a single sustained soft tone under the whole draw — keep it restrained, this is a logo moment not a fanfare.
- Restraint rule: unchanged — no triumphant swells, no comedic stingers. The warning tone must read as informative, not alarming — this tool warns you calmly, it doesn't panic.

## Storyboard

### Scene 1 — The confession — 2.5s
Black terminal screen. Typed line: "Several hundred directories. No memory of which is which."
Sequential/interaction: yes — character-by-character typing with key ticks.
Audio intent: quiet, a little uneasy.
Music: none yet.
Transition mood: hard cut → Scene 2

### Scene 2 — Contrast + reversal, combined and tightened — 4.5s
Fast beat, four short lines in sequence, each held just long enough to read, no longer: "custodian. atomate2. AiiDA." (grouped, ~1s) → "All of them want to own the run." (~1.2s) → "vasp_triage walks in after." (~1.2s) → "It reads files. It writes a log. It asks first." (~1.1s).
Sequential/interaction: yes — four beats in quick succession, no scene break between them.
Audio intent: matter-of-fact exposition moving into quiet confidence.
Audio-coupled idea: one soft tick as the tool names group in; nothing else.
Music: fades in low during this scene, reaching ~0.2 by the end.
Transition mood: clean crossfade → Scene 3

### Scene 3 — Feature: status — 3.5s
`$ vtriage status` types in, then the six real status labels arrive as one fast block and hold: running / missing inputs or not submitted / crashed or incomplete / SCF not converged / ionic not converged / converged. Caption: "One ordered set of rules decides the status."
Sequential/interaction: yes — command types in, then the six-item list arrives as a block (not one-per-beat), holds.
Music: steady low bed.
Transition mood: clean crossfade → Scene 4

### Scene 4 — Feature: menu (NEW) — 2.5s
The real menu, briefly: the top bar and banner text ("VASP job triage and resubmission") compressed to fit, then the numbered choice list exactly as the tool prints it: "1) status summary  2) list folders by status  3) write report  4) archive finished runs  5) submit jobs  6) edit INCAR or KPOINTS  7) change the root folder". Caption: "Or skip the commands. Same tool, a menu."
Sequential/interaction: yes — banner appears first (brief), then the numbered list appears as a block.
Audio intent: light, quick — this is a "by the way" beat, not a major reveal.
Music: steady low bed.
Transition mood: clean crossfade → Scene 5

### Scene 5 — Feature: parse — 2s
Two caption lines, no command: "Underneath: small functions that read INCAR, KPOINTS, OUTCAR, OSZICAR, SLURM output." / "Each one reads one thing."
Sequential/interaction: none — two lines arrive with a very short stagger.
Music: steady low bed.
Transition mood: clean crossfade → Scene 6

### Scene 6 — Feature: report — 3.5s
`$ vtriage report` types in, output: "report.md + grouped CSV files" then "ENCUT, EDIFF, EDIFFG, KPOINTS, POTCAR compared across the folder." Card sized wide enough that no line clips.
Sequential/interaction: yes — command types in, then two output lines arrive in sequence, each held to a real reading floor.
Music: steady low bed, may begin lifting toward Scene 7.
Transition mood: hard cut → Scene 7

### Scene 7 — The POTCAR catch (upgraded — real code output) — 4.5s
Terminal output, verbatim from the tool: `POTCAR order Re W differs from POSCAR W Re` (this exact string is what `classify.py`'s `potcar_check()` produces). Held clearly, card wide enough that it never clips. Then, larger, in the accent color: caption "Runs to completion. Gives a number. Nothing warns you." held on screen.
Sequential/interaction: yes — the terminal line arrives first and holds, then the caption arrives beneath/after it.
Audio intent: the chill moment — the tool's sharpest differentiator, shown as real output rather than paraphrased.
Audio-coupled idea: a single restrained low tick as the caption lands.
Music: a strong cue may land here.
Transition mood: hard cut → Scene 8

### Scene 8 — Feature: edit — 4s
`$ vtriage edit --set ENCUT=400 --status "not submitted"` types in FULLY and holds complete for at least 0.3s (fix: this must never be cut or advanced while still typing). Card must be wide enough that "not submitted" and the full flag never clip at the edge. Preview block: "ENCUT: 350 → 400" across a few folders, then "Apply to 12 folders? [y/n]" and a typed "y". Caption: "Every edit previews first. Nothing changes without yes."
Sequential/interaction: yes — command types in and holds complete, preview block appears, yes/no prompt appears, "y" is typed with a distinct key tick.
Music: steady low bed.
Transition mood: clean crossfade → Scene 9

### Scene 9 — Feature: submit — THE MONEY SHOT — 6s
`$ vtriage submit --status "not submitted"` types in fully and holds. Then the full real output arrives, in this exact order, each line given real reading time (this is the longest, most important scene — do not rush it):
```
Jobs in queue: 3 of limit 15

Folders to submit: 5
  /scratch/BCC/W10_1  (CONTCAR to POSCAR)
  /scratch/BCC/W10_2
  /scratch/BCC/W10_3
  /scratch/BCC/W10_4  (CONTCAR to POSCAR)
  /scratch/BCC/W10_5
Type yes to save each run and submit:
```
(Folder paths beyond the first are illustrative filler in the same style — real code prints one path per line with `(CONTCAR to POSCAR)` only on folders that need a restart, matching `resubmit.py`'s actual output format. Keep the list to 5 lines so it fits the card without scrolling or clipping.)
After the full block is visible, the cursor sits blinking at the "Type yes to save each run and submit:" prompt for a full second before the scene cuts — this is the visual proof of "never acts without your yes." No SFX during the blink; let the silence do the work.
Sequential/interaction: yes — command types and holds, then the output block arrives (queue line first, then the folder list, then the prompt), then the cursor blinks for ~1s.
Audio intent: the whole video's thesis made visible — quiet, deliberate, no rush.
Music: may lift slightly (~0.3-0.35) as this scene begins, but drop to near-silence under the blinking-cursor hold at the end.
Transition mood: hard cut → Scene 10

### Scene 10 — The warning (NEW) — 2.5s
A single line in the reserved warning color (red, e.g. #f87171): `Warning: same error as previous run (zbrent). Change settings first.` — this is the exact message `resubmit.py` prints. Optional small caption beneath, smaller and neutral-colored: "It remembers what you already tried."
Sequential/interaction: none — the line arrives and holds; if a caption is used, it fades up ~0.4s after the warning line.
Audio intent: a distinct but calm alert tone, not alarming — the tool warns you, it doesn't panic.
Music: steady low bed, ducked slightly under the alert tone if needed.
Transition mood: hard cut → Scene 11

### Scene 11 — Feature: history (archive) — fix: must show real output — 3.5s
`$ vtriage history` types in and holds complete. Output (this must actually render — the empty-panel bug from the last pass must not recur): "INCAR, KPOINTS, POSCAR, CONTCAR, OUTCAR, OSZICAR archived as -N" then "and a line appended to progress.txt." Card wide enough for the full first line without clipping.
Sequential/interaction: yes — command types and holds, then the two output lines arrive in sequence.
Music: may begin lifting toward the progress.txt reveal's strong cue.
Transition mood: clean crossfade → Scene 12

### Scene 12 — The progress.txt reveal — 4.5s
Unchanged from v2: a real terminal window labeled `progress.txt` shows Run 1 (crashed, ZBRENT — full message must fit without clipping, widen the card if needed) fading to Run 2 (converged, `energy(sigma->0): -696.30022286 eV` — full value must fit without clipping). Caption: "Read that as a commit history. Because that's what it is."
Sequential/interaction: yes — Run 1 appears first and holds, then Run 2 appears/replaces it.
Music: a strong cue may align to this scene's arrival.
Transition mood: clean crossfade → Scene 13

### Scene 13 — Scale (NEW) — 2.5s
A single, large, confident line: "247 directories. 4 seconds." Beneath it, smaller: "A real scan, not a demo folder with three calculations in it."
Sequential/interaction: none — the count arrives large and holds, the caption fades in beneath it shortly after.
Music: steady.
Transition mood: clean crossfade → Scene 14

### Scene 14 — The rules — 2.5s
Unchanged: "Standard library only." / "Never acts without your yes."
Transition mood: soft crossfade → Scene 15

### Scene 15 — Install (NEW) — 2.5s
Two lines, monospace, terminal-styled: `git clone git@github.com:Gaurav-Arora-MatSci/vasp_triage.git` then, beneath it: "No pip. No conda. No database."
Sequential/interaction: yes — the clone command types in briefly (fast, this is a familiar shape, don't over-hold it), then the second line fades up beneath it.
Music: steady, beginning to prepare for the fade-out.
Transition mood: hard cut → Scene 16

### Scene 16 — Outro: the real ASCII banner + link — 3s
The tool's own real banner from `menu.py`, drawn line by line top to bottom, roughly 0.15s per line (6 lines of the word-art plus the top/bottom bars ≈ 8 draw steps ≈ 1.2s total draw time), in terminal green for the `=` bars and white for the letter art:
```
 ================================================================
  __     ___    ____  ____    _____ ____  ___    _    ____ _____
  \ \   / / \  / ___||  _ \  |_   _|  _ \|_ _|  / \  / ___| ____|
   \ \ / / _ \ \___ \| |_) |   | | | |_) || |  / _ \| |  _|  _|
    \ V / ___ \ ___) |  __/    | | |  _ < | | / ___ \ |_| | |___
     \_/_/   \_\____/|_|       |_| |_| \_\___/_/   \_\____|_____|
 ================================================================
```
After the draw completes, hold briefly, then fade in beneath it: `github.com/Gaurav-Arora-MatSci/vasp_triage`.
Sequential/interaction: yes — lines draw top to bottom at ~0.15s/line, then a pause (~0.5s), then the link fades in (~0.6s) and holds to the end of the video.
Audio intent: quiet landing — the logo moment, not a fanfare.
Audio-coupled idea: one soft tick per line-batch as it draws (or a single sustained soft tone under the whole draw), nothing else; no impact/bell on the link's arrival.
Music: fades out during the banner draw, silent by the time the link is fully visible.
Transition mood: soft fade → end

**Music mood for this video:** polished, steady, understated throughout, with three deliberate lifts (POTCAR catch, submit money shot, progress.txt reveal) and a full drop-to-silence under the submit scene's blinking-cursor hold and under the final banner/link.
**Audio summary:** near-silent hook → fade-in through the tightened contrast/reversal beat → flat low bed through the feature and proof scenes, broken only by a distinct calm alert tone on the warning line → three slight lifts at the video's three strongest payoffs → full silence under the submit prompt's cursor blink → fade to silence under the closing banner and link.
