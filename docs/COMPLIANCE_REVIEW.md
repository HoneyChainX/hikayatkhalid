# Hard-rule compliance review — all 10 approved shotlists & scripts

Automated sweep (2026-06-25) of `pipeline/epNN_shotlist.json` + `scripts/epNN_script.md`
against the project's non-negotiable rules. Re-run any time:
`grep` for prophet speaker tokens / out-of-source religious attributions (see method below).

## Result summary

| Check | Result |
|---|---|
| Any **prophet visually depicted** (face/body) | **None** — all prophets rendered as faint light / shadow / off-screen, faceless |
| **Out-of-source** hadith/āyah inserted | **None found** (ep02's earlier `أدِّ الأمانة` insertion was removed; current text clean) |
| Religious attribution in scripts | only `ep08` (`رواه البخاري`) — **in-source** (the episode's `source_ref` is Bukhari) |
| **Prophet given a distinct off-screen voice** | **2 episodes — needs sheikh confirmation** (see below) |

## ⚠️ For the sheikh to confirm before those specific shots are generated

Both items already satisfy the **visual** rule (prophet = faceless light, off-screen) and the
**source** rule (lines are verbatim Qur'an from the approved `source_text`). The only open
question is whether a **distinct off-screen prophet voice** is permitted, or whether the
prophet's Qur'anic words should be delivered by the **narrator (Teta)** with the prophet
represented by light only.

| Episode | Shot(s) | Speaker label | Line (verbatim Qur'an) | Visual |
|---|---|---|---|---|
| **ep03** (Yunus) | 14 | `تيتا ويونس` | `لَّا إِلَٰهَ إِلَّا أَنتَ سُبْحَانَكَ إِنِّي كُنتُ مِنَ الظَّالِمِينَ` (الأنبياء ٨٧) | faint light, faceless, off-screen voice w/ echo |
| **ep05** (Sulayman & the ant) | 14, 15 | `صوت سليمان` | `رَبِّ أَوْزِعْنِي أَنْ أَشْكُرَ نِعْمَتَكَ…` (النمل ١٩) ، `…مَا لِيَ لَا أَرَى الْهُدْهُدَ…` (النمل ٢٠) | luminous halo / back only / off-screen voice |

**Recommended safe default (pending the sheikh's ruling):** at production time, deliver the
prophet's Qur'anic words via the **narrator (Teta)** or on-screen text + a neutral reciter,
keep the prophet as **light only**, and **do not cast a distinct "voice of the prophet."**
If the sheikh explicitly permits an off-screen prophet voice, the shotlists already support it.
Either way, **no prophet face/body is ever shown.**

## Other (softer) notes — not hard-rule blockers

- **ep04** has a speaker `عمر` (a companion, not a prophet). Companions are outside the prophet
  rule; confirm with the sheikh only if your editorial policy avoids depicting specific companions.
- **ep06** features Jurayj and the infant who spoke (righteous people / a miracle, not prophets) — within bounds.
- **ep08** features the leper/​bald/​blind men and the angel (Bukhari) — within bounds; `رواه البخاري` is in-source.
- **ep02** shotlist is **48 shots** (written before the 24–32 cap). Optional: re-shotlist to 24–32 to cut cost; the script itself is fine.

## Method (for re-running)

- Prophet-as-speaker: scan each shotlist's `speaker` for prophet tokens
  (`النبي`, `رسول الله`, `موسى`, `عيسى`, `يونس`, `سليمان`, `إبراهيم`, …).
- Out-of-source religious text: diff each script's hadith/āyah against the episode's approved
  `source_text` (in `backlog.source_text`); flag anything not present there.
- Visual depiction: confirm every prophet `visual_prompt` uses light/shadow/off-screen/faceless.

> The two gates remain authoritative: the sheikh approves the `source_text`, then the drafted
> script. This sweep is an automated aid to that human review, not a replacement for it.
