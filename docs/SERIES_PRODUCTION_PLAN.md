# Hikayat Khalid — Animated Series Production Plan

*A practical bible for producing an **excellent, animated** (3D/cinematic) Islamic
children's series at a **~$5/episode ceiling**, reusing the pipeline already in
this repo. Last updated: 2026-06-19.*

---

## 0. Target & constraints

- **Look:** "3D-or-better" — real motion, Pixar-style/cinematic, not Ken-Burns on stills.
- **Budget:** ≤ $5 / episode, sustainable for a recurring series.
- **Format:** **2.5–3.5 min shorts** — best for YouTube/Shorts/Reels/TikTok discovery *and* keeps per-episode cost in budget. Master in **9:16 vertical** (primary for Shorts/Reels/TikTok) + a **16:9** reframe for YouTube main (DaVinci does the reframe).
- **Per episode:** ~18–24 shots, mostly **5–8 s** clips (≈150–200 s of generated video).
- **Non-negotiables unchanged:** shariah gate before any generation; no prophet depiction; `madeForKids`; religion only from approved `source_text`; no secrets in repo.

---

## 0.5 ✅ Proven end-to-end (2026-06-25)

Stage 3 (animate) is **no longer theoretical** — it has been run on a real ep01
keyframe with a live backend:

- **What:** `build/ep01/img/shot01.jpg` (the existing consistent keyframe) → animated
  → `build/ep01/clips_anim/shot01.mp4` (5.0 s, 1280×720, 24 fps), then muxed with the
  real ElevenLabs Arabic voice → `clips_anim/shot01_voiced_demo.mp4`.
- **How:** **higgsfield** image-to-video, model **`kling3_0_turbo`**, `start_image` = the
  keyframe, gentle motion prompt. Driven directly through the connected higgsfield MCP
  (upload keyframe → `media_confirm` → `generate_video` → download the result mp4).
- **Result:** character stayed perfectly on-model (boy raises hand to wipe his brow —
  exactly the prompted motion); fully safe content; the assembler (`build_ep01.py`) picks
  up `clips_anim/shotNN.mp4` over the stills automatically.
- **Measured cost:** **7.5 credits / 5 s clip** at 720p (kling turbo). Seedance 2.0 Fast
  via higgsfield measured at 14–17.5 credits/clip (better identity, ~2× the price).

So the only remaining gate to produce the **full animated season** is funding a video
backend — not engineering. See the path table below for the cheapest route to the $5/ep ceiling.

---

## 1. The pipeline (6 stages)

```
[1] Script + shotlist        n8n Workflow A → shariah gate            (DONE)
        ↓
[2] Style-locked keyframes    Flux Kontext / nano-banana, 3D style,    (BUILT: rerender_balancer.py)
        ↓                     one start-frame per shot, character-locked
[3] Animate → clips           image-to-video (start_image = keyframe)  ← the new step
        ↓
[4] Lip-sync (dialogue)       LivePortrait, driven by the line's audio
        ↓
[5] Voice + music             ElevenLabs (BUILT) + Suno nasheed + SFX
        ↓
[6] Finish                    DaVinci Resolve: edit, color, Arabic
                              titles/subtitles, mix, 4K upscale, export
```

Stages **1, 2, 5** already exist in this repo. The animated series adds **3, 4, 6**. The image-to-video step (3) slots in exactly where `build_ep01.py` currently makes Ken-Burns clips.

---

## 2. Three execution paths

| | **A · Cloud API** | **B · Rented RTX** ⭐ | **C · Owned RTX** |
|---|---|---|---|
| Video engine | Seedance 2.0 Fast (fal.ai) | LTX-2 / Wan 2.2 in ComfyUI | LTX-2 / Wan 2.2 in ComfyUI |
| Compute | none | RunPod/Vast ~$0.4–0.6/hr | your RTX (≥16 GB ideal) |
| **$/episode** | **~$4–5** | **~$0.5–1.5** | **~$0 (power)** |
| Resolution | 720p–1080p | up to **4K** | up to **4K** |
| Setup | minutes | a few hours (one-time graph) | a few hours + GPU |
| Best when | start **today**, no HW | a **recurring series**, no HW buy | you already have an RTX |

**Path D · higgsfield (MCP — connected RIGHT NOW).** No new key needed; already
authenticated in this session. `kling3_0_turbo` i2v measured at **7.5 cr / 5 s clip**
(≈ **$0.36/clip** at the $95/2 000-cr top-up). A ~20-shot episode ≈ **150 cr ≈ $7**;
animating only the ~14 hero shots (Ken-Burns stills for the rest) lands **≈ $5/ep**.
Best for: the proof (done), hero shots, and fast iterations without provisioning anything.
Seedance via higgsfield is ~2× (better identity).

**Recommendation:** the proof is done on **D** (higgsfield, today, no setup). For the
**full 10-episode season at the $5/ep ceiling**, **Path A (fal.ai Seedance Fast, ~$4–5/ep
for every shot animated)** is the cheapest turnkey route — `animate_fal.py` is already
wired into `produce_episode.py`; it just needs a `FAL_KEY`. If you'd rather not add a key,
fund higgsfield credits and I drive the whole season straight through the MCP. Path **B**
(rented RTX) still wins on a long recurring series: **~$1/ep at 4K, unlimited**.

---

## 3. Per-episode cost breakdown (3-min short, ~20 shots)

| Stage | Path A (cloud) | Path B (rented RTX) | Path C (owned) |
|---|---|---|---|
| Keyframes (~20 imgs) | nano-banana ~$0.6 | free (local Kontext) | free |
| Video (~180 s) | Seedance Fast $0.022/s ≈ **$3.96** | GPU time ≈ **$0.5–1.0** | ≈ $0 |
| Lip-sync (dialogue) | in-model / Hedra ~$0.3 | LivePortrait free | free |
| Voice (ElevenLabs) | ~$0.10 | ~$0.10 | ~$0.10 |
| Music (Suno/free) | ~$0–0.3 | ~$0–0.3 | ~$0–0.3 |
| **Total** | **~$4.5–5.0** | **~$0.7–1.5** | **~$0.1** |

Reference rates: [fal.ai i2v pricing](https://fal.ai/learn/tools/ai-image-to-video-generators), [2026 API pricing](https://devtk.ai/en/blog/ai-video-generation-pricing-2026/), [local RTX/LTX-2](https://blogs.nvidia.com/blog/rtx-ai-garage-ces-2026-open-models-video-generation/).

---

## 4. Character consistency — the hard part, and how we beat it

Moving clips drift far more than stills. Strategy:

1. **Locked reference sheets** per character. Khalid exists (`khalid_v1.png`). **Create Noor, Teta, Lantern sheets** the same way (front/¾/side, neutral pose) and lock them in `characters`.
2. **Per-shot keyframe** (stage 2): edit the locked reference into the shot with **Flux Kontext / nano-banana** (already built in `rerender_balancer.py`). This is the identity anchor.
3. **Animate from the keyframe** (stage 3): always pass the keyframe as **`start_image`** so motion *starts from* the locked identity. Use **reference-driven** engines (Seedance 2.0 is identity-aware; **Wan 2.2 Animate** transfers motion onto a character image).
4. **Style bible** in `characters.json`: a single "3D Pixar, soft global illumination, warm palette" style string applied everywhere; per-character descriptors; negatives.
5. **QA gate**: cheap per-shot identity check; regenerate any shot that drifts (idempotent pipeline already supports this).
6. **Short clips** (5–8 s) reduce drift vs long takes; cut on action.

---

## 5. Stage-by-stage tooling & settings

- **[2] Keyframes** — `rerender_balancer.py` (Kontext/nano-banana). Style: 3D Pixar. 1 keyframe/shot @ the master aspect (9:16). Free on owned/rented GPU; ~$0.03/img on nano-banana cloud.
- **[3] Video** —
  - *Cloud:* **Seedance 2.0 Fast** (`fal-ai/bytedance/seedance/...`), 720p, 5–8 s, `start_image`=keyframe, motion prompt from the shot's action. ~$0.022/s.
  - *Local/rented:* **LTX-2** (fast, up to 4K, 20 s) or **Wan 2.2 / Wan-Animate** in **ComfyUI**; RTX ≥16 GB; NVFP4/FP8 for speed.
- **[4] Lip-sync** — **LivePortrait** (open, free) for dialogue shots: drive Khalid/Noor/Teta keyframe with the matching ElevenLabs audio. Non-dialogue shots skip this.
- **[5] Audio** — **ElevenLabs** voices (committed map in `characters.json`); **Suno/Udio** for the nasheed; free SFX (BBC/Freesound).
- **[6] Finish** — **DaVinci Resolve** (free; Studio one-time ~$295 adds Super Scale 4K, AI animated subtitles, Flux NIM): assemble, color-match clips, transitions, **Arabic title cards + animated subtitles**, audio ducking/mix, **loudness −14 LUFS**, upscale, export **9:16 + 16:9**. [Resolve AI features](https://www.kunalganglani.com/blog/davinci-resolve-21-ai-features-review).

---

## 6. DaVinci Resolve finishing checklist

- [ ] Import clips + audio; order by `scene_id`.
- [ ] Color-match shots (different gen seeds drift in tone) → one LUT/grade.
- [ ] Gentle transitions (cross-dissolve 6–10 frames), no jarring cuts.
- [ ] **Arabic title card** (open) + **end card** (subscribe/next-episode).
- [ ] **Animated Arabic subtitles** (AI, voice-synced) — accessibility + retention.
- [ ] Music bed (nasheed) ducked under narration; SFX (water, footsteps).
- [ ] Loudness normalize −14 LUFS; de-noise voices.
- [ ] **Super Scale** → 4K (Studio) or Real-ESRGAN (free).
- [ ] Export: YouTube 16:9 (H.264/4K) + Shorts/Reels/TikTok 9:16.

---

## 7. What's already built (reuse map)

| Need | Already in repo |
|---|---|
| Shotlist (per-shot lines + visual prompts) | `pipeline/ep01_shotlist.json` |
| Consistent keyframes (multi-backend, free) | `pipeline/rerender_balancer.py`, `rerender_khalid_*.py` |
| Character/style bible + voice map | `pipeline/characters.json` |
| Real ElevenLabs Arabic voices | `pipeline/revoice_elevenlabs.py` |
| Assembly + manifest | `pipeline/build_ep01.py` |
| Supabase persistence (assets/DB) | `pipeline/upload_to_supabase.py` |

The series build inserts **stage 3 (animate)** between keyframes and assembly, and routes the final cut through **DaVinci** instead of ffmpeg for broadcast polish.

---

## 8. Keys / accounts needed per path

- **Path A:** `FAL_KEY` (or Replicate) for Seedance; `GEMINI` *with billing* for nano-banana keyframes (or free Kontext); `ELEVENLABS` (have).
- **Path B:** RunPod/Vast account (hourly GPU); `ELEVENLABS`. No image/video API keys (open models, local).
- **Path C:** RTX GPU (≥16 GB); `ELEVENLABS`. Everything else local/free.
- **All:** DaVinci Resolve (free download). All keys via env — never committed.

---

## 9. Rollout plan

1. **Proof (1 day):** animate 2–3 existing consistent Khalid keyframes on Path A (Seedance Fast) → judge "3D-or-better" quality. ~$0.30.
2. **Pilot (ep01):** full 3-min animated cut on the chosen path; finish in DaVinci; publish unlisted; confirm `madeForKids`.
3. **Standardize:** lock style bible + character sheets (Noor/Teta/Lantern); template the ComfyUI graph (Path B) or fal scripts (Path A).
4. **Scale:** sheikh-approve `source_text` for ep02–ep10 → batch-produce; run Workflow D analytics after ~3–5 episodes.

---

## 10. Bottom line

- **Excellent + animated + ~$5/ep is achievable** via cloud **Seedance 2.0 Fast** today.
- **For a series, rented/owned RTX + ComfyUI (LTX-2 / Wan 2.2) is dramatically cheaper (~$0–1.5/ep) at 4K** and reuses everything we built.
- **DaVinci Resolve (free)** is the finishing layer that lifts any path to broadcast quality (color, Arabic subtitles, audio, 4K).
- Hardest risk is **character consistency in motion** — mitigated by locked reference sheets + keyframe-as-start-frame + reference-driven engines + a QA regenerate gate.
