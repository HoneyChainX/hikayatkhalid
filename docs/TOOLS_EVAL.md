# Tools evaluation — external repos & "free AI video" tools (2026-06-25)

Evaluated against Hikayat Khalid's real constraints: a **monetized, `madeForKids`**
Arabic series needing **character consistency**, **image-to-video**, **commercial-use rights**,
the **no-prophet-depiction / source-only** hard rules, and **≤ ~$5/episode**.

> The decisive filter most "free AI video" lists ignore: **commercial use + no watermark.**
> A monetized channel can't ship clips from a tier that forbids commercial use or stamps a watermark.

## A. The two GitHub repos

| Repo | What it is | Maturity | Verdict for us |
|---|---|---|---|
| **anil-matcha/open-generative-ai** | Next.js/Electron studio: image, image-to-video (60+ models), **lip-sync**, up to 14 ref images. Cloud via **Muapi.ai** gateway; **local** via bundled `sd.cpp` + `Wan2GP`. | Mature — 20.8k★, 234 commits, v2.0.0 (May 2026), MIT | **Useful**, as (a) a cheaper cloud gateway [Muapi ≈ 30% under official APIs] and (b) a **ready UI for local Wan 2.2 on a GPU** (= our Path B). Lip-sync is a bonus for dialogue shots. **GUI-first → operator console, not a headless automation backend.** |
| **Anil-matcha/Open-AI-Design-Agent** | Brief→design-deliverables agent: posters, logos, **thumbnails**, brand kits. Same Muapi backend. | Immature — 243★, **7 commits**, "studio code being added" | **Skip for episodes** (wrong focus + incomplete). Revisit later only for **channel branding / thumbnails**. |

**Caveats for both:** "free/open-source" = the **code**; generation still costs **Muapi credits** unless you
run local models on a capable GPU. They add **no** TTS, scriptwriting, assembly, or **shariah enforcement** —
our `write_script.py`, ElevenLabs, ffmpeg, and `COMPLIANCE_REVIEW.md`/gates stay essential. Single-vendor
dependency on Muapi.

## B. The video's genre — "4 FREE & UNLIMITED video generators" (sponsored by Higgsfield)

The honest reality behind the "free + unlimited" framing, filtered for a **monetized** channel:

| Tool | Free? | Watermark | **Commercial use** | i2v | Needs GPU | Fit for us |
|---|---|---|---|---|---|---|
| **Wan 2.2** (Alibaba, Apache-2.0) | **Truly unlimited** | No | **Yes** | Yes + char-animation | **Yes** (RTX 4090) | ⭐ **Best free path** = our Path B engine |
| **LTX-Video** (Lightricks, open) | Unlimited | No | **Yes** | Yes, up to 4K/50fps | Yes | ⭐ Already in our plan (LTX-2) |
| **CogVideoX** (THUDM, Apache-2.0) | Unlimited | No | **Yes** | Yes | Yes (modest) | ✅ Open-source backup |
| **Veo 3.1** (Google) | Free = **manual** AI-Studio UI, rate-limited | No (invisible SynthID) | Check ToS (API = paid) | Yes | No | ✅ Top quality; **paid Gemini API** for automation, free only for manual tests |
| Kling / Hailuo / Luma / Pika / Runway / Sora **free tiers** | Daily creditlets or one-time dump | **Usually yes** | **No on free tier** | Mixed | No | ❌ Test-only — not shippable on a monetized channel |
| **Seedance 2.0** free tier | Limited, new | Unconfirmed | Unconfirmed | — | No | ➖ We already reach Seedance via higgsfield/fal/Muapi |
| **Higgsfield** (the video's sponsor) | $15/mo, 15+ models | No | Yes | Yes | No | ✅ **Already using & proven** (ep01 shot01) |

**Bottom line:** "free **and** unlimited **and** commercially usable" is true **only for open-source models on
your own/rented GPU** — i.e. exactly our **Path B (rented RTX)**. Every *free cloud* tier either forbids
commercial use, watermarks, or depletes. The video, ironically, **validates the plan we already built.**

## C. What this changes for Hikayat Khalid

1. **Path B gets concrete engines + a license guarantee:** run **Wan 2.2** (or LTX-Video) in ComfyUI on a
   rented RTX → **no watermark, full commercial rights, ~$1/ep at 4K, "unlimited."** `open-generative-ai`
   can serve as the operator UI for this if we don't want pure ComfyUI.
2. **Cheaper cloud option:** wire **Muapi** as a `MUAPI_KEY` backend beside `animate_fal.py` (~30% under fal)
   for the same Kling/Seedance models — good if we want cloud without managing a GPU.
3. **Veo 3.1** is a strong **paid-API** cloud option (great realism, no visible watermark) — worth a manual
   AI-Studio test on one shot before committing.
4. **None of these touch the hard rules.** Character consistency still relies on our keyframe-first
   (`start_image`) approach; no-prophet / source-only enforcement stays in our prompts + QA + gates.

## D. Recommendation (unchanged in shape, better-informed)

- **Lowest cost + clean rights:** **Path B** — rented RTX running **Wan 2.2 / LTX**. ~$1/ep, 4K, no watermark,
  commercial-safe. The "free unlimited" tools from the video *are* these models.
- **Zero-setup, start now:** **higgsfield** (already connected/proven) or **Muapi** (cheaper gateway).
- Free *cloud* tiers (Kling/Hailuo/Luma/etc.) = **test-only**; don't ship monetized clips from them.

Sources: aivideobootcamp.com free-tools guide; higgsfield.ai 2026 model comparisons; muapi.ai docs/credits;
repo READMEs (open-generative-ai, Open-AI-Design-Agent).
