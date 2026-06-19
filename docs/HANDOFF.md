# Hikayat Khalid (حكايات خالد) — Full Project Handoff

> Hand this whole file to a fresh Claude (Claude Code in the terminal, or a new Claude.ai chat). It is self-contained: it describes the project, the exact current state (what is verified-working vs not), every ID/endpoint, the remaining work, and the hard-won gotchas so you don't repeat dead-ends. **Last updated: 2026-06-04.**

---

## 0. What this project is

An automated Islamic children's-story channel ("Hikayat Khalid", ages 4–10, simplified Arabic) for YouTube/Instagram/TikTok. It's an **n8n assembly line** on a **Supabase** backend with **two mandatory human approval gates** (shariah, then technical) via Telegram. Hero = Khalid (7-yr-old boy, black gold-embroidered thobe + olive/gold kufi); plus Noor (sister), Teta (grandmother narrator), and the Lantern of Tales (bridge device).

**Pipeline:** Workflow A (write script → shariah gate) → Workflow B (generate per-shot images + voice → assemble video → technical gate) → Workflow C (publish to YouTube/IG/TikTok, madeForKids=true) → Workflow D (analytics → self-feed backlog).

### NON-NEGOTIABLE hard rules (never violate):
1. **No depiction of any prophet** — ever (light/voice/off-camera only).
2. **No image/audio generation before the script passes the shariah gate.**
3. **Never publish without `madeForKids = true`** on YouTube (COPPA/legal).
4. **AI dramatizes, never invents religion** — religious content comes ONLY from the approved `source_text` field (RAG), never the model's own knowledge. The sheikh must approve `source_text` for each episode.
5. **Secrets rule:** never write service_role keys / API keys / tokens into any file or chat. They live only in n8n credentials or a local `.env`. The user pastes them directly into those UIs.

---

## 1. Infrastructure & IDs (all tool-verified, safe to reuse)

- **Supabase project:** `dvxmgtelcismjumgxwkw` · URL `https://dvxmgtelcismjumgxwkw.supabase.co` · region eu-central-1 · org "Smart Empire"
- **n8n:** `smartcody.app.n8n.cloud` · personal project `rfoIsJux91Gf6pym`
- **Workflows:** A `XuDYMLBdWa5PLtmv` · B `n0w1l2SqEL1NPlY3` · C `BbuEo9UVrAm3azLk` · D `6yKGTazKerzCy5LE`
- **Telegram approval-gate chat:** `-1003752068592`
- **n8n credentials (IDs):** Supabase Hikayat `jcdgqFI7YRZbKfZP` (supabaseApi) · Gemini `RqIwWDik07VLVAiV` (googlePalmApi) · Telegram `Yq5UmUVSkkSt8JfG` · ElevenLabs `7L0sB6q2644rZcKQ` (httpHeaderAuth, header `xi-api-key`) · Cloudflare Workers AI (httpHeaderAuth, header `Authorization: Bearer <token>`) — id rotated, was `SLIqT79YgUl7bLtR` · Shotstack (httpHeaderAuth, header `x-api-key`, SANDBOX key)
- **Khalid voice (ElevenLabs):** `rzNH3PV43Tk38jg31TS6`
- **Khalid reference image:** `episode-media/khalid_v1.png` (public, locked in `characters.khalid`)
- **Cloudflare account id:** `712bdb1154cfda8d3f8dea37b6930e6b`

### Supabase schema (public)
- **backlog** (PK `story_id` text): launch_order, title*, source_ref, source_grade, lesson, modern_scenario, depiction_safety, source_text, priority int, status ∈ {planned,in_production,done}, timestamps. Only **ep01 «رحمة قطرة ماء»** has approved `source_text`; ep02–ep10 await the sheikh.
- **episodes** (PK `episode_id` bigint **IDENTITY ALWAYS — never insert/update it**): story_id (FK), title, story_source, lesson, modern_scenario, script_text, script_status ∈ {draft,shari_review,approved,rejected}, shari_reviewer, shari_notes, self_review jsonb, depiction_safety_check, shotlist_json jsonb, image_urls[], audio_urls[], video_draft_url, … tech_status ∈ {null,assembling,tech_review,approved,rejected}, publish_status ∈ {in_pipeline,ready,publishing,published,ready_to_publish,failed}, yt_url/ig_url/tiktok_url, metrics cols, timestamps.
- **characters** (PK `char_id`): name*, role, fixed_description*, signature_color, style_prompt*, negative_prompt, model_sheet_prompt, reference_url, expression_url, seed, locked, notes, voice_id, language. 4 rows: khalid, noor, teta, lantern.
- **episode_assets** (NEW 2026-06-04, PK id bigint identity): episode_id (FK), scene_id, speaker, line, image_url, audio_url, is_story_shot, created_at. One row per shot. An **AFTER INSERT trigger `rollup_episode_assets`** auto-aggregates image_url/audio_url into episodes.image_urls[]/audio_urls[] ordered by scene_id.
- **activity_log**, **app_config** (keys: voice_map, languages, n8n_webhooks) — used by the admin panel.
- DB function `finalize_episode_assets(ep bigint)` also exists (manual rollup; the trigger makes it optional).

---

## 2. CURRENT STATE — what is proven vs not (be precise; this was hard-won)

### ✅ VERIFIED WORKING (tool-confirmed with real data)
- **Workflow A** end-to-end: picks top planned story → writes Arabic script with Gemini (Basic LLM Chain, not Agent — see gotchas) → saves episodes row → Telegram **shariah gate** → on approve, marks approved + triggers B.
- **Workflow B** through the whole asset loop: Gemini shotlist → per shot [**Cloudflare flux image** → decode base64 → **upload to Supabase Storage** → **ElevenLabs voice** → upload → **record episode_assets row**] → reached **technical gate**. A full episode (ep01 = ~31–38 shots, varies per Gemini run) generated all images + audio, saved to storage, arrays auto-rolled up, and hit the gate — all verified (exec 61, storage showed 38 jpg + 38 mp3, episode_assets=38).
- **Both human gates** work, including the post-approval branch (Mark Ready to Publish / Mark Tech Rejected). Earlier a DB check-constraint vs workflow-vocabulary mismatch 400'd the approve branch — FIXED via migration `align_status_check_constraints_to_workflow_vocab` (constraints now accept ready/publishing/rejected).
- **Asset persistence** (episode_assets + storage uploads + rollup trigger): built and verified.
- **Admin panel** (Next.js): fully built in `./hikayat-admin/` — see `HANDOFF_admin_panel_CLAUDE_CODE.md`. Not yet `npm install`+built (do that locally; the cloud sandbox lacked RAM).

### ⚠️ BUILT BUT NOT YET PROVEN END-TO-END
- **Video assembly (Shotstack)**: 7 nodes wired into Workflow B's tail (Build Timeline → Assemble JSON → Render Video → Render Wait → Poll Render → Render Done? loop → Save Video URL → then tech gate). Credentials attached. **Never completed a clean run** because repeated same-day testing exhausted free rate limits (Cloudflare flux 429, Gemini 429). The assembly code itself is correct; it just needs ONE clean run on fresh quota. See §3.

### ❌ NOT BUILT YET
- **Workflow C publish credentials**: YouTube OAuth (Google Cloud client; n8n redirect `https://smartcody.app.n8n.cloud/rest/oauth2-credential/callback`), Instagram Graph token, TikTok login. Workflow C nodes exist with placeholders.
- **Noor/Teta/Narrator voices**: not cloned. Workflow B's "Resolve Voice ID" currently maps ALL speakers → Khalid's voice as a temporary placeholder. Clone them in ElevenLabs, then restore the per-speaker map.
- **Workflow D**: built, never run (needs published episodes + YouTube Analytics cred).

---

## 3. THE IMMEDIATE NEXT STEP — finish the first video (Workflow B → MP4)

Goal: one clean Workflow B run that generates assets AND produces an MP4 in `episodes.video_draft_url`, reaching the technical gate.

**Why it's been blocked:** free-tier rate limits (Cloudflare Workers AI 429 + Gemini 429) hit because the workflow was run ~15× in one day during testing. These reset in hours. The fix is reliability, not redesign.

**Do this (in order):**
1. **Add Retry-On-Fail to the rate-limited nodes** — IMPORTANT GOTCHA: in n8n these are **node-level settings**, set in the n8n UI (open node → Settings tab → toggle "Retry On Fail", set Max Tries 5, Wait Between Tries 5000ms). Do this on **Generate Image (Cloudflare)** and **Generate Shotlist**. (Attempts to set these via the MCP `update_workflow` kept landing them inside `parameters{}` where n8n ignores them — must be UI or verified at node top-level.)
2. Optionally enable Cloudflare paid Workers AI (pennies) to remove the 429 ceiling entirely, OR set the "Rate Limit Wait" node to ~3–5s to space requests.
3. Reset ep01 for a clean run (SQL): `DELETE FROM episode_assets WHERE episode_id=<id>; UPDATE episodes SET tech_status=NULL, image_urls=NULL, audio_urls=NULL, video_draft_url=NULL WHERE episode_id=<id>;` (current test episode is episode_id=9, story ep01).
4. Run Workflow B (manual trigger). Watch executions; the asset loop takes ~1 min for ~38 shots with short waits.
5. Verify: storage has shotN.jpg/shotN.mp3, episode_assets rows = shot count, and `episodes.video_draft_url` is a Shotstack MP4 URL. Open the URL — it'll be watermarked (sandbox) but proves assembly. Switch Shotstack to the Production key + add credits for an unwatermarked final.

**Shotstack facts:** SANDBOX endpoint `https://api.shotstack.io/edit/stage/render` (POST to render, GET `/{id}` to poll); auth header `x-api-key` (raw key, NO Bearer); status flow queued→fetching→rendering→saving→done, then `response.url`. Sandbox is free, watermarked, and consumes ZERO credits when only compositing your own assets. The Assemble JSON code builds a 2-track timeline (images track + audio track), fixed 5s/shot — refine later to use real per-shot audio durations so narration isn't cut.

---

## 4. GOTCHAS / lessons (each cost real time — don't relearn them)

- **n8n Agent + Structured Output Parser + Gemini = broken** ("Cannot read properties of undefined (reading 'parts')", GitHub #15563/#25449). FIX used: replace the AI Agent node with a **Basic LLM Chain** (`@n8n/n8n-nodes-langchain.chainLlm` v1.9), systemMessage → messages.messageValues[0], hasOutputParser true, reconnect the Gemini model + JSON parser subnodes. Done in both A ("Write Script") and B ("Generate Shotlist").
- **Telegram sendAndWait fails if message > 4096 chars.** The shariah gate truncates the script to ~2800 chars + "full in Supabase".
- **n8n MCP cannot attach/detach a credential on an httpRequest node** (errors "httpRequest does not accept credential X"). HTTP nodes CAN reuse a credential via `predefinedCredentialType` (Supabase) or `genericCredentialType`+`httpHeaderAuth`, but the credential link itself is **UI-only**. If a stale/duplicate credential gets stuck on a node, the clean fix is to **delete the node and rebuild it** (a fresh node has no stale links).
- **Header Auth value must be Fixed text** `Bearer <token>` (for Cloudflare) — not Expression mode, and the `Bearer ` prefix is required. Cloudflare's secret-scanning auto-revokes tokens pasted into chat — keep tokens out of chat; rotate if exposed.
- **n8n Cloud has a 5-min per-execution hard timeout** (not API-raisable). A full episode now runs well under it after removing per-shot waits and using Cloudflare steps=4; if future episodes are longer, batch the loop into a sub-workflow.
- **Native Supabase node is row-only** (no storage). Storage upload must be an httpRequest POST to `/storage/v1/object/<bucket>/<path>` with header `x-upsert:true`; reuse the supabaseApi credential via predefinedCredentialType.
- **Cloudflare flux returns base64 in `result.image`** (not raw bytes) → needs a convertToFile (toBinary, sourceProperty `result.image`) before upload.
- **Pollinations keyless image API is unusable from n8n Cloud** (per-IP concurrency=1 on a shared egress IP → persistent 402). That's why we switched to Cloudflare Workers AI (free tier, token-auth). Don't go back to keyless Pollinations.
- **episodes.episode_id is IDENTITY ALWAYS** — never write it. Storage rows can't be DELETEd via SQL (use the Storage API or rely on x-upsert overwrite).
- **Khalid face is NOT consistent shot-to-shot** — Cloudflare flux-1-schnell is text-only (ignores reference image). Consistency rides on the textual character descriptors in each visual_prompt. To truly fix, use a reference-capable model (Gemini Nano Banana edit-op with billing, or a local ComfyUI + IP-Adapter on an NVIDIA GPU — ComfyUI would replace the image step, it can't do video assembly).

---

## 5. How to continue in Claude Code (recommended)

1. `cd` into `C:\Users\user\Downloads\coworkhalid` (this folder; has the admin panel + all handoff docs + khalid_v1.png).
2. Paste this file's path to Claude Code, or `/add` it as context.
3. For n8n work, Claude Code won't have the n8n MCP — but you can drive n8n via its **public REST API** (`https://smartcody.app.n8n.cloud/api/v1/...`, header `X-N8N-API-KEY`) for read/monitor, and trigger runs via the manual UI or a Webhook node. (Note: the n8n public API can read/update workflows + read executions, but **cannot start a run** — use the UI "Test workflow" or a Webhook trigger.)
4. For Supabase, use the Supabase MCP or the REST/SQL API with the service_role key (in your env, never in a file).
5. Build + run the admin panel locally: `cd hikayat-admin && npm install && npm run dev` (fill `.env.local` first — see its README; needs Supabase URL+service_role, n8n key, Gemini key, ElevenLabs key, Cloudflare token, bucket name).

### Priority order to finish the project
1. **Finish the first video** (§3) — one clean Workflow B run → MP4. Highest value, nearly done.
2. **Wire Workflow C publish creds** (YouTube OAuth first) → publish ep01 as unlisted/private test → confirm madeForKids.
3. **Clone Noor/Teta/Narrator voices** → restore per-speaker voice map.
4. **Sheikh source_text for ep02–ep10** → run the line for real episodes.
5. **Refine**: real per-shot durations in the Shotstack timeline; consider a reference-capable image model for Khalid consistency; run Workflow D after ~3–5 published episodes.

---

## 6. Companion files in this folder
- `HANDOFF_admin_panel_CLAUDE_CODE.md` — the admin panel build/run/audit guide.
- `hikayat-admin/` — the Next.js control-panel source (Stories, Episodes, Characters, Workflows, Integrations, Logs, Settings).
- `خطة_إطلاق_حكايات_خالد.md`, `Hikayat_Khalid_PunchList.md`, `حكايات_خالد_WorkflowBCD_تمّ_البناء.md` — earlier Arabic planning/status docs (some predate the latest fixes; THIS file is the most current).
- `khalid_v1.png` — locked Khalid reference image.
