# Hyperframes Composition Brief: vasp_triage (v3 — bug-fix + expansion pass)

## Objective
Fix three concrete rendering bugs found in a frame-by-frame review of the v2 (~43s) render, and add six new scenes the review asked for, bringing the video to ~54s. This is a revision pass on an EXISTING working composition — extend and fix it, don't rebuild from scratch.

## Output
- Composition directory: `brag-output/composition/`
- Rendered video: `brag-output/brag.mp4`
- Format: landscape — 1920x1080
- Duration: ~54 seconds (intentionally longer than v2's 43s — the new proof scenes, especially the submit money shot, need real room; do not compress by cutting them)

## BUGS TO FIX FIRST (found in the v2 render, must not recur)

1. **Clipped text at the terminal card edge.** Three shots cut off mid-word: `--status "not su` (Scene 8, edit command), `energy(sigma→` (Scene 12, progress.txt reveal), and the ZBRENT message (also Scene 12). Root cause is almost certainly the terminal card being sized without checking the actual longest line of copy against it. Fix: measure the longest line in EACH scene (see the "widest lines" list below) and size that scene's terminal card so every line has at least 48px of clear padding on both sides at 1920px width, or reduce the command/output font-size for that card. Verify by reading rendered frames, not just the source — a `hyperframes snapshot` check at each scene's mid-point should show no line touching or crossing the card edge.

   Widest lines to check explicitly:
   - Scene 8: `$ vtriage edit --set ENCUT=400 --status "not submitted"`
   - Scene 9: `  /scratch/BCC/W10_1  (CONTCAR to POSCAR)` (and the other 4 folder lines)
   - Scene 9: `Type yes to save each run and submit:`
   - Scene 12: `Run 2 | Job 316703 | Result: converged | energy(sigma->0): -696.30022286 eV`
   - Scene 12: the ZBRENT message line from Run 1
   - Scene 7: `POTCAR order Re W differs from POSCAR W Re`

2. **Empty terminal panels.** The old `submit` and `history` scenes typed a command and showed no output beneath it. This is fixed by fully specifying real output for both scenes below (Scene 9 and Scene 11) — the fix must be verified by actually seeing the output text render, not just present in the source markup (check for a CSS/timing bug that could leave content in the DOM but not visible — e.g. an animation that never fires, opacity stuck at 0, or a timeline gap).

3. **Frozen mid-type text.** One shot showed `vtriage sub` frozen, i.e. the typing animation was cut or advanced before completing. Fix: every typed command across every scene must run its full typing animation to completion and hold complete for at least 0.3s before the scene does anything else (adds output, cuts away, etc.). Audit all six command scenes (status, menu-adjacent none, report, edit, submit, history) for this specifically.

## Source Material
- Project root: `/Users/gauravarora/Desktop/Git_project/personal_github/vasp_triage`
- Files consulted for this revision's new verbatim copy: `resubmit.py` (submit output format, queue count, warning messages — lines ~207, ~249, ~254, ~265, ~288, ~298), `classify.py` (POTCAR check message — line ~168), `menu.py` (the real ASCII banner — lines ~21-26 — and the main menu's numbered choices — lines ~391-398), `config.py` (`QUEUE_LIMIT = 15`), plus the existing `why_vasp_triage.md` narrative already in the video.
- Repository URL for the install/link scenes: `git@github.com:Gaurav-Arora-MatSci/vasp_triage.git` (git remote). Display the SSH clone form in the install scene's command; display the plain web form `github.com/Gaurav-Arora-MatSci/vasp_triage` under the closing banner as the readable link.

## New copy that must appear verbatim (in addition to everything already in the v2 brief, which stays)

- Scene 4 (menu): "1) status summary" / "2) list folders by status" / "3) write report" / "4) archive finished runs" / "5) submit jobs" / "6) edit INCAR or KPOINTS" / "7) change the root folder" — caption: "Or skip the commands. Same tool, a menu."
- Scene 7 (POTCAR, upgraded to real code output): `POTCAR order Re W differs from POSCAR W Re` — this exact string, verbatim, is what `classify.py`'s `potcar_check()` produces. Caption: "Runs to completion. Gives a number. Nothing warns you."
- Scene 9 (submit, the money shot) — full real output block, in order:
  ```
  $ vtriage submit --status "not submitted"
  Jobs in queue: 3 of limit 15

  Folders to submit: 5
    /scratch/BCC/W10_1  (CONTCAR to POSCAR)
    /scratch/BCC/W10_2
    /scratch/BCC/W10_3
    /scratch/BCC/W10_4  (CONTCAR to POSCAR)
    /scratch/BCC/W10_5
  Type yes to save each run and submit:
  ```
  The queue line and prompt line are the real, exact strings from `resubmit.py`. The five folder paths are representative filler in the tool's real style (one path per line, `(CONTCAR to POSCAR)` appended only where a restart is needed) — keep exactly 5 lines so the card doesn't need to scroll. After the block renders, the cursor blinks at the final prompt line for ~1s with no SFX before the scene cuts.
- Scene 10 (warning, NEW scene): `Warning: same error as previous run (zbrent). Change settings first.` — this exact string is what `resubmit.py` prints (with a folder path appended in the real tool; omit the path here for a cleaner card, or include a short illustrative one, either is fine). Render this line in a reserved warning color (e.g. #f87171), used nowhere else in the video. Optional caption beneath: "It remembers what you already tried."
- Scene 11 (history, fixed to include real output): "INCAR, KPOINTS, POSCAR, CONTCAR, OUTCAR, OSZICAR archived as -N" / "and a line appended to progress.txt."
- Scene 13 (scale, NEW scene): "247 directories. 4 seconds." / "A real scan, not a demo folder with three calculations in it."
- Scene 15 (install, NEW scene): `git clone git@github.com:Gaurav-Arora-MatSci/vasp_triage.git` / "No pip. No conda. No database."
- Scene 16 (outro, replacing the old plain logo card): the real ASCII banner, drawn line by line:
  ```
   ================================================================
    __     ___    ____  ____    _____ ____  ___    _    ____ _____
    \ \   / / \  / ___||  _ \  |_   _|  _ \|_ _|  / \  / ___| ____|
     \ \ / / _ \ \___ \| |_) |   | | | |_) || |  / _ \| |  _|  _|
      \ V / ___ \ ___) |  __/    | | |  _ < | | / ___ \ |_| | |___
       \_/_/   \_\____/|_|       |_| |_| \_\___/_/   \_\____|_____|
   ================================================================
  ```
  Bars (`=` lines) in terminal green, the letter-art lines in white — matching the terminal palette already used everywhere else. Draw top to bottom, ~0.15s per line/bar. After the draw completes and a brief hold, fade in beneath it: `github.com/Gaurav-Arora-MatSci/vasp_triage`.

## Creative Direction
- Tone preset: polished — unchanged.
- Structural fix: the old cut spent ~10.5s (hook + 3 separate scenes) on "what other tools do" before showing anything of vasp_triage's own. Compress this to one combined ~4.5s beat (Scene 2 below) covering all four lines (tool names, "own the run", "walks in after", "reads/writes/asks") in quick, still-readable succession, so the total intro is ~7s instead of ~10.5s. Recovered time goes to the submit scene (now 6s, the longest scene in the video) and the POTCAR catch (now 4.5s with real code output).
- Avoid (unchanged, now also covering the new scenes): generic SaaS language, abstract filler visuals, any claim/command/output not grounded in the actual codebase or explicitly marked as illustrative filler (the submit scene's 5 folder paths).

## Visual Identity
- Background: near-black terminal (#0d1117-style)
- Text: off-white monospace (#e6edf3) for terminal/log content; white for the ending banner's letter-art
- Accent: terminal green (#4ade80) — status words, command prompts, the ending banner's `=` bars
- NEW: a reserved warning color (e.g. #f87171, a clear but not garish red) used ONLY on the Scene 10 warning line — nowhere else in the video, so it reads as a distinct, meaningful signal
- Display font: technical monospace (unchanged)
- Body font: clean sans (unchanged)
- Terminal card sizing rule (fixes bug #1): size each scene's card to its own longest line plus ≥48px padding per side at 1920px width; do not reuse one fixed card width across all scenes if the content varies this much in length (the submit scene's folder-list lines and the progress.txt energy value are the two widest cases)

## Storyboard
Use the storyboard in `brag-output/brag-plan.md` (v3) as the full creative contract — 16 scenes, ~54s total. Scene summary:

1. The confession — 2.5s — typed hook line
2. Contrast + reversal, combined — 4.5s — tool names → "own the run" → "walks in after" → "reads/writes/asks" — all four beats in one tightened scene
3. Feature: status — 3.5s — `$ vtriage status` → six-item ordered status list as one block
4. Feature: menu (NEW) — 2.5s — real banner + real numbered menu list
5. Feature: parse — 2s — two caption lines, no command
6. Feature: report — 3.5s — `$ vtriage report` → report.md/CSV + consistency-check output
7. The POTCAR catch (real code output) — 4.5s — `POTCAR order Re W differs from POSCAR W Re` → caption
8. Feature: edit — 4s — full command typed and HELD complete → preview diff → y/n → "y" (fix: no more clipping, no more mid-type freeze)
9. Feature: submit — THE MONEY SHOT — 6s — full real output block, ends on a blinking cursor at the confirmation prompt (fix: no more empty panel)
10. The warning (NEW) — 2.5s — red `Warning: same error as previous run (zbrent)...` line
11. Feature: history — 3.5s — full real output (fix: no more empty panel)
12. The progress.txt reveal — 4.5s — unchanged content, fixed card width so nothing clips
13. Scale (NEW) — 2.5s — "247 directories. 4 seconds."
14. The rules — 2.5s — unchanged
15. Install (NEW) — 2.5s — `git clone ...` / "No pip. No conda. No database."
16. Outro: real ASCII banner + link (NEW, replaces old plain logo card) — 3s — drawn line by line, then the repo link fades in

Sum: 54.0s. Small per-scene adjustments (±0.3-0.5s) for natural transitions are fine; keep the total in the 50-58s range.

## Audio
- Audio role and general philosophy: unchanged from v2 — sparse, dry, reused SFX family; steady low music bed.
- NEW: Scene 10's warning line gets one distinct, calm, low alert tone (not alarming) — the one intentional exception to "reuse the same family," since this is the one moment the video wants to feel meaningfully different from a routine command echo.
- NEW: Scene 9's blinking-cursor hold (last ~1s of the scene) gets NO SFX and the music should duck toward near-silence for that specific second — this silence is the point, it visually and sonically demonstrates "waiting for your yes."
- NEW: Scene 16's banner draw-on gets one soft tick per line as it draws (8 lines/bars ≈ 8 soft ticks at ~0.15s spacing) or a single sustained soft tone under the whole draw — Hyperframes should pick whichever reads cleaner once the visual exists; no impact/bell sound on the final link fade-in, keep that silent.
- Music treatment: extend the existing fade envelope to ~54s — near-silent under Scene 1, fade-in through Scene 2, flat ~0.25-0.3 through Scenes 3-6, slight lift (~0.3-0.35) under Scene 7 (POTCAR) and Scene 9 (submit, except the final blinking-cursor second which drops to near-silent), flat through Scenes 10-11, another slight lift under Scene 12 (progress.txt), flat through 13-15, fade to silence during Scene 16's banner draw.
- Music cue guidance: same bundled preset as v2 (109.96 BPM). At ~54s, use at most 2-3 strong-cue locks total (e.g. near the POTCAR catch and the progress.txt reveal); do not force cues onto the new scenes if it would rush their reading time — natural timing is fine for scenes beyond the preset's ~25s analysis window.
- Reuse existing SFX assets already in `composition/assets/` (keyboard ticks, drop accent, impact hit); add one new "alert" SFX for Scene 10 if a suitable file exists in the Hyperframes SFX library the composition already has access to (check `sfx-analysis.md` for a low-key negative/alert-type sound — something restrained, not a harsh buzzer), otherwise reuse the existing drop accent at a slightly different pitch/volume treatment if the runtime supports it, or a plain visual-only warning (no unique SFX) if no suitable asset exists — document whichever choice is made.

## Hyperframes Instructions
Load the same domain skill/reference docs as before (composition contract, animation, keyframes, audio, CLI). This is a revision pass:

1. **Fix the three bugs first**, verified by rendering and inspecting frames (e.g. `hyperframes snapshot`), not just by reading the source.
2. **Insert the six new scenes** (menu, warning, scale, install, and the upgraded POTCAR + upgraded ending) at the positions specified above, reusing the existing terminal-prompt component built for v2's feature scenes for menu/warning/scale/install where it fits, and building the new ASCII-banner draw-on as its own component.
3. Keep the reused terminal aesthetic consistent — same colors/fonts as before, with the one new reserved warning color used only on Scene 10.
4. Re-run `npx hyperframes check` and treat it as the gate before re-rendering.
5. Re-render to `brag-output/brag.mp4` (overwrite), confirm duration lands ~50-58s.
6. Re-pick a poster frame — the submit money shot (Scene 9, the folder list + prompt fully visible) or the progress.txt reveal are both strong candidates; pick whichever reads better as a single still frame, produce `brag-output/brag.jpg`, and bake it as frame 0 of `brag.mp4`.
7. Update `brag-output/share-copy.txt` if the new content changes what's worth saying in one sentence (a version mentioning the POTCAR catch and "no pip, no conda, no database" is a reasonable direction, but keep it one sentence).

Requirements carried over from v2, still in force: show real product content (now several real outputs, not just the progress.txt block), respect reading-time floors, use only local assets already in `composition/assets/` (add one new SFX file only if genuinely needed for the warning tone, from the same bundled library), run the check gate before render.
