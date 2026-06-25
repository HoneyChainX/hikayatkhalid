# Hikayat Khalid — Hybrid production pipeline (chosen approach)

**Decision (2026-06-25):** **Adobe Character Animator (rigged puppets)** for the recurring cast
in modern-frame/narration scenes **+ Alibaba Wan 2.2-S2V/i2v** (DashScope) for the story-world
scenes. This wins on the two axes that matter most for a recurring kids' series: **perfect
character consistency** and **~$0 marginal cost per episode** for the bulk of shots.

## 1. Why this split

| | Character Animator (puppet) | Wan 2.2 (DashScope cloud) |
|---|---|---|
| Used for | modern-frame cast dialogue (Khalid/Noor/Teta) | story-world scenes, lip-synced story characters, faceless-light prophet shots |
| Consistency | **perfect** (same rig every frame/episode) | keyframe-anchored |
| Cost | **~$0/ep** after one-time rig (CC sub) | ~$0.10–0.15 / 5 s clip (Apache-2.0, commercial-safe) |
| Lip-sync | built-in (auto, from audio) | Wan-S2V (built-in) / i2v = no lip-sync |

## 2. Shot routing (auto — `pipeline/route_shots.py`)

Every shot is classified from `is_story_shot` + `speaker` + `visual_prompt`, **compliance-aware**:

| Engine | Meaning | Total shots |
|---|---|---|
| `puppet` | modern-frame cast dialogue → **Character Animator** | **199** |
| `wan_s2v` | story shot, on-screen **non-prophet** speaker → **Wan-S2V lip-sync** | **20** |
| `wan_i2v` | story-world motion / narrator VO / **faceless-light prophet** → **Wan i2v** (no lip-sync) | **93** |

Per episode (run `python3 pipeline/route_shots.py --all`):

```
ep01 31  puppet=24 s2v=0  i2v=7
ep02 48  puppet=32 s2v=8  i2v=8
ep03 28  puppet=18 s2v=0  i2v=10  (prophet 6 — Yunus)
ep04 31  puppet=21 s2v=0  i2v=10
ep05 25  puppet=13 s2v=4  i2v=8   (prophet 4 — Sulayman)
ep06 26  puppet=15 s2v=1  i2v=10
ep07 32  puppet=18 s2v=0  i2v=14  (prophet 5 — Nuh)
ep08 27  puppet=15 s2v=3  i2v=9
ep09 32  puppet=23 s2v=4  i2v=5
ep10 32  puppet=20 s2v=0  i2v=12  (prophet 5 — Ibrahim)
TOTAL    puppet=199 s2v=20 i2v=93  (prophet shots 20)
```

**Compliance:** all **20 prophet shots** are forced to `wan_i2v` with `prophet=true` — animated as
**faceless light / off-screen**, the off-screen voice laid over at assembly, **never lip-synced or
embodied** (see `docs/COMPLIANCE_REVIEW.md`). The router was validated: 0 prophet shots are
narration-only false positives.

## 3. Engine A — Adobe Character Animator (the puppet backbone)

**One-time rig per recurring character — Khalid, Noor, Teta** (and optionally the Lantern/فانوس).
Build each from layered art (Photoshop/Illustrator) in our style bible (`pipeline/characters.json`),
front-facing, neutral, symmetrical, transparent background. Required named layers (Sensei auto-maps):

```
+ Khalid (puppet)
  + Head            (origin handle at neck)
    + Mouth         ← visemes: Neutral, Ah, D, Ee, F, L, M, Oh, R, S, Uh, W-Oo, Smile, Surprised
    + Eyes
      + Blink
      + Pupils      (optional eye tracking)
    + Eyebrows
  + Body
  + Arm Left / Arm Right   (dangle/triggers for gestures)
  + (Background: keep empty — composited separately)
```

**Drive it from our existing audio:** import each shot's `build/<ep>/audio/shotNN.mp3` (the
ElevenLabs Arabic voice) → **Compute Lip Sync from Take Audio** → Sensei assigns visemes to
phonemes automatically (mouth shapes are language-agnostic; Arabic maps cleanly). Add idle
behaviors (auto-blink, breathing, subtle head sway). Export each puppet shot as
`build/<ep>/clips_anim/shotNN.mp4` (the slot the assembler reads).

> Re-used every episode at **zero extra cost** — the rig is the asset; only new audio per shot.

## 4. Engine B — Wan 2.2 on DashScope (`pipeline/animate_wan.py`)

Handles only the `wan_s2v` + `wan_i2v` shots (reads `routing.json`):

- **`wan_s2v`** — `image_url`=keyframe + `audio_url`=the shot's mp3 → **lip-synced** story character
  (the three men, the ant, the hoopoe, the buyer/seller, …).
- **`wan_i2v`** — keyframe → motion (story-world scenes **and** faceless-light prophet shots); the
  voice is laid over at assembly, never lip-synced.

```bash
export DASHSCOPE_KEY=...                              # Alibaba Cloud Model Studio
export WAN_ASSET_BASE=https://<host>/build           # DashScope fetches inputs by URL
EPISODE=ep05 python3 pipeline/route_shots.py
EPISODE=ep05 python3 pipeline/animate_wan.py          # -> clips_anim/shotNN.mp4
```

Wan = **Apache-2.0** → full commercial rights, no watermark. Model IDs/endpoint are env-overridable
(`WAN_I2V_MODEL`, `WAN_S2V_MODEL`, `WAN_BASE`) — verify against current Model Studio docs.

## 5. Assembly (unchanged)

All three engines write `build/<ep>/clips_anim/shotNN.mp4`. Then:

```bash
EPISODE=ep05 python3 pipeline/produce_episode.py     # routes + Wan + assemble (+ persist)
```

`produce_episode.py` runs `route_shots.py`, then Wan (if `DASHSCOPE_KEY`), then `build_ep01.py`
(fits each clip to its voice, music bed, titles) → `build/<ep>/ep01.mp4`. Finish in **DaVinci
Resolve** (free): color-match puppet vs Wan shots to one grade, Arabic animated subtitles, 4K,
loudness −14 LUFS, export 16:9 + 9:16. Prophet shots: lay the off-screen voice over the faceless
i2v clip here.

## 6. What's needed to start

| Need | For | Status |
|---|---|---|
| Character Animator (Creative Cloud) | puppet shots (64% of all shots) | ⬜ subscription |
| **Rigged Khalid / Noor / Teta puppets** | puppet shots | ⬜ build once (art → layers → triggers) |
| `DASHSCOPE_KEY` + public `WAN_ASSET_BASE` | story shots (36%) | ⬜ key + host |
| Keyframes `build/<ep>/img/shotNN.jpg` | Wan inputs + puppet art reference | ✅ ep01; ⬜ ep02–10 (free via Vheer/Flux Kontext) |
| Voices `build/<ep>/audio/shotNN.mp3` | both engines | ✅ ep01; ⬜ ep02–10 (ElevenLabs) |

## 7. Cost (per ~30-shot episode)

- Puppet shots (~20): **$0** (rig amortized).
- Wan shots (~10): ~10 × $0.12 ≈ **$1.2**.
- Voices: ~$0.1 · Music/finish: free (DaVinci).
- **≈ $1–2 / episode**, commercial-safe, no watermark, perfect cast consistency.

First-episode setup (rigging Khalid/Noor/Teta) is the one-time cost; every episode after is ~$1–2.
