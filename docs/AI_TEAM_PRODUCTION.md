# Hikayat Khalid — AI Production Team (Conflux-style)

A pipeline run by **specialized expert agents**, each owning one job, coordinated by a
**Producer** and gated by a **Shariah Officer**. Mirrors the Conflux multi-agent concept:
small, single-responsibility experts + a deterministic orchestrator + a state manifest.

> Scope note: episode **scripts are NOT regenerated** by this team — they are an approved,
> frozen input (`scripts/epNN_script.md`, `pipeline/epNN_shotlist.json`). The team produces
> everything downstream of the script, **for the whole project (ep01–ep10)**.

**Cast (canonical):** خالد Khalid (7yo boy), زينة Zina (5yo girl, formerly Noor), تيتا Teta
(grandmother), جدو Gido (grandfather), عبد الرحمن Abdulrahman (role TBD). Plus **temp/guest
characters per episode** (humans, animals, birds) registered in `characters.json → temp_characters`.

## The team (16 specialists)

### Core production line

| # | Agent | Single responsibility | Key tools / skills |
|---|-------|----------------------|--------------------|
| 0 | **Producer** | Orchestrates the pipeline, routes shots, schedules the GPU pool, holds the state manifest, runs human checkpoints | all; RunPod API; `route_shots.py` |
| 1 | **Shariah & Compliance Officer** 🛑 | HARD GATE. Validates every shot's text/visual against the non‑negotiable rules + approved `source_text`. Approves or blocks. Nothing renders without sign‑off | Read, `docs/COMPLIANCE_REVIEW.md`, source_text |
| 2 | **Art Director** | Character bible + on‑model 3D refs (Khalid, Zina, Teta, Gido, Abdulrahman, lantern) + per‑episode temp guests (humans/animals/birds). Owns visual consistency | ComfyUI Flux Kontext (`comfy_image.py`), higgsfield, Read/Write |
| 3 | **Keyframe / Storyboard Artist** | Per‑shot keyframes — single clean speaker for dialogue, composed scene for story shots | ComfyUI Flux Kontext |
| 4 | **Casting & Voice Director** | Age/gender‑correct voice per character (child Zina, elderly Teta & Gido, young Khalid), TTS, voice QA | ElevenLabs API, higgsfield voices |
| 5 | **Audio Engineer** | Loudness normalize (−14 LUFS), mixing, music/SFX beds | ffmpeg (`audio_normalize.py`) |
| 6 | **Animation Engineer** | Render: S2V lip‑sync (dialogue) + Wan i2v (story). Drives the 2×4090 pool in parallel | ComfyUI (`animate_s2v.py`, `animate_one.py`) |
| 7 | **Post‑Production Engineer** | SeedVR2 upscale → HD, RIFE smoothing | ComfyUI (`upscale_seedvr2.py`) |
| 8 | **Editor** | Assemble shots → episode (timing, transitions, captions) | ffmpeg (`assemble_opening.py`) |
| 9 | **QA / Continuity Reviewer** 🔎 | Adversarially reviews every shot + final cut: lip‑sync, on‑model, **voice age‑fit**, artifacts, compliance. Flags fails → redo loop | Read (frames), ffmpeg |
| 10 | **Publisher** | Thumbnail, title/description, `madeForKids=true`, upload prep | Canva MCP, Gmail |

### Creative & strategy experts (advise/direct the core line)

| # | Agent | Single responsibility |
|---|-------|----------------------|
| 11 | **Creative Director** 🎨 | Creativity within the frozen story — hooks, emotional beats, delight, variety; directs creative intent the keyframe/camera/animation execute |
| 12 | **Global Branding Expert** 🌍 | Brand bible (logo, palette, type, title/end cards, stings), cross‑episode/platform consistency, global appeal |
| 13 | **Cinematographer** 🎥 | Per‑shot camera language — shot size, eye‑level angle, gentle movement, framing, continuity; baked into prompts |
| 14 | **Efficiency & Effectiveness Lead** ⚙️ | Saturate the 2×4090 fleet, validated settings, no rework, cost/ROI, and that output actually achieves engagement/learning |
| 15 | **Child Development Expert** 🧒 | Ages 4–10 fit — pacing, emotional safety, comprehension, positive modeling, engagement psychology (near‑gate with Shariah) |

## Pipeline (per episode)

```
approved script ──▶ [1] Shariah gate + [15] Child-Dev check ──▶ blocked? → stop & escalate
        │
        ├─▶ creative/strategy pass: [11] Creative · [13] Camera · [12] Brand · [14] Efficiency
        │      (per-shot intent + camera notes + brand + GPU run-plan, fed into the line below)
        │
        ├─▶ [2] Art Director: 3D refs ready ─┐
        ├─▶ [4] Voice Director: cast voices ─┤ (parallel)
        ▼                                    ▼
   [3] Keyframes (per shot)        [4]+[5] TTS → normalize
        └──────────────┬─────────────────────┘
                       ▼
            [6] Animation (S2V dialogue / Wan story) ── parallel across GPUs
                       ▼
            [7] Post: SeedVR2 upscale + smooth
                       ▼
            [8] Editor: assemble episode
                       ▼
            [9] QA review ──fail──▶ back to the owning agent (targeted redo)
                       ▼ pass
            [10] Publisher → deliver
```

## Quality gates (the point of the team)

- **G0 Shariah** — no prophet depiction (light/voice/off‑camera only), religious content only from
  approved `source_text`, wholesome, `madeForKids`. Blocks render.
- **G1 Casting** — voice age/gender MUST match the character bible (Noor=child, Teta=elderly,
  Khalid=young boy). This gate is what would have caught the adult‑Noor voice automatically.
- **G2 Continuity** — every character on‑model vs their ref; single clean speaker per dialogue shot.
- **G3 QA** — lip‑sync tracks audio, no hand/limb artifacts, levels at −14 LUFS, no seams.

## State manifest

`build/epNN/production_state.json` — per shot: `{shariah, keyframe, voice, audio, render, upscale,
qa}` each `pending|done|fail`, plus engine, speaker, paths. The Producer reads/writes it; QA flips
stages back to `fail` to trigger targeted redos (never a full re‑render).

## Render fleet

- **2× RTX 4090** pod (`pod_setup_s2v_multi.sh`) — primary; one ComfyUI per GPU (ports 8188 + 19123),
  shots split across both → ~2× throughput, each ~1.8× a 3090.
- **RTX 3090** pod — overflow / prep (refs, keyframes) while the 4090s render.

## Character bible (source of truth for Art Director + Voice Director)

| Character | Age | 3D ref | Voice (ElevenLabs) | Status |
|-----------|-----|--------|--------------------|--------|
| خالد Khalid | 7 boy | `khalid_ref_3d.png` ✅ | Khalid MJ (`rzNH3PV43Tk38jg31TS6`) ar young male | ✅ |
| زينة Zina (was Noor) | 5 girl | `zina_ref_3d.png` ✅ | Gungun (`nfMYisZqs1GOjTFllho3`) kids‑show child | ✅ |
| تيتا Teta | elderly F | `teta_ref_3d.png` ⏳ | Sawsan (`mS4cERRqrNy5Kmlx8Udf`) native ar grandmother | ⏳ ref + user voice pick |
| جدو Gido | elderly M | `gido_ref_3d.png` ⏳ | needs casting (elderly ar male) | ⏳ ref + voice |
| عبد الرحمن Abdulrahman | TBD | `abdulrahman_ref_3d.png` ⏳ | needs casting | ⏳ confirm role + ref + voice |
| Lantern / temp guests | — | per‑episode | — | Art Director per episode |
