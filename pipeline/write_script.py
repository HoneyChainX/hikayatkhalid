#!/usr/bin/env python3
"""
Stage 1 (local) — turn a sheikh-APPROVED backlog.source_text into the episode's
Arabic script + shotlist, mirroring n8n Workflow A/B's writer. Output lands in
`episodes` with script_status='shari_review' — it is a DRAFT for the human
shariah gate, never auto-approved.

HARD RULES enforced in the prompt:
  • religious content comes ONLY from source_text (no hadith/Qur'an from the
    model's own knowledge); quote it faithfully.
  • respect depiction_safety — if a prophet is involved, the prophet is NEVER
    described/voiced/shown (light / voice / off-camera); visual heroes are the
    non-prophet elements.
  • simplified Arabic for ages 4-10; gentle, no fear.

    export GEMINI_API_KEY=...   SUPABASE_URL=...   SUPABASE_SERVICE_ROLE_KEY=...
    EPISODE=ep02 python3 pipeline/write_script.py
Then: review the draft (Telegram/admin shariah gate) → mark approved → produce_episode.py
"""
import json
import os
import sys

import requests

EP = os.environ.get("EPISODE", "ep02")
GEMINI = os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY")
SURL = os.environ.get("SUPABASE_URL", "https://dvxmgtelcismjumgxwkw.supabase.co").rstrip("/")
SKEY = os.environ.get("SUPABASE_SERVICE_ROLE_KEY")
MODEL = os.environ.get("GEMINI_TEXT_MODEL", "gemini-2.5-flash")

WRITER_RULES = """أنت كاتب سيناريو لقناة أطفال إسلامية «حكايات خالد» (أعمار ٤–١٠، عربية مبسّطة).
الشخصيات: خالد (ولد ٧ سنوات)، نور (أخته الصغيرة)، تيتا (الجدّة الراوية)، وفانوس الحكايات (أداة الجسر)، وراوٍ للنشيد.
اكتب السيناريو بهذا الهيكل وبالعلامات نفسها:
【الخطّاف】 ، 【المشهد العصري】 ، 【الجسر — فانوس الحكايات】 ، 【القصة】 ، 【العودة والعبرة】 ، 【الخاتمة】 (دعاء + نشيد) ، 【التشويقة】.
ثم أضف قسم: 🛡️ المراجعة الذاتية (للتحقّق الشرعي) يذكر مصدر كل معلومة دينية، وسطراً: ✅ فحص الإخراج.

قواعد صارمة لا تُخالَف:
- المحتوى الديني (الحديث/الآيات/القصة) يُؤخذ **حرفياً وفقط** من «النص المصدري المعتمد» المرفق، ولا تُضِف من معرفتك شيئاً.
- التزم بـ«ضابط التصوير»: إن وُجد نبيّ فلا يُوصف ولا يُصوّر ولا يُجسَّد صوتُه أو وجهُه أو جسده إطلاقاً (نور/صوت/خارج الكادر)، والأبطال البصريون هي العناصر غير النبويّة.
- درّب الدرس عبر «السيناريو العصري» المرفق (موقف من حياة خالد)، وتيتا تروي القصة من النص المصدري.
- لغة بسيطة، رحيمة، دون ترويع، وبنشيد خفيف بلا آلات.
أخرج نصّ السيناريو كاملاً فقط."""

SHOTLIST_RULES = """حوّل السيناريو التالي إلى shotlist بصيغة JSON: مصفوفة من اللقطات.
كل لقطة كائن: {"scene_id": int تسلسلي يبدأ 1, "speaker": اسم المتحدّث بالعربية (خالد/نور/تيتا/راوٍ أو "خالد ونور" إلخ),
"line": الجملة المنطوقة بالعربية فقط دون توجيهات إخراج, "visual_prompt": وصف اللقطة بالإنجليزية يبدأ بـ "[STYLE] " (وللقطات القصة إن كان فيها نبيّ اجعله بلا وجه/خارج الكادر/ظلّ),
"duration_est": ثوانٍ int, "is_story_shot": true داخل قسم 【القصة】 فقط}.
أخرج JSON صالحاً فقط دون أي نصّ آخر."""


def gemini(system, user, as_json=False):
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{MODEL}:generateContent?key={GEMINI}"
    body = {
        "system_instruction": {"parts": [{"text": system}]},
        "contents": [{"parts": [{"text": user}]}],
        "generationConfig": {"temperature": 0.7,
                             **({"response_mime_type": "application/json"} if as_json else {})},
    }
    r = requests.post(url, json=body, timeout=120)
    if r.status_code != 200:
        sys.exit(f"Gemini {r.status_code}: {r.text[:200]}")
    return r.json()["candidates"][0]["content"]["parts"][0]["text"]


def sb(method, path, **kw):
    h = {"apikey": SKEY, "Authorization": f"Bearer {SKEY}", "Content-Type": "application/json"}
    return requests.request(method, f"{SURL}/rest/v1/{path}", headers={**h, **kw.pop("headers", {})}, **kw)


def main():
    if not (GEMINI and SKEY):
        sys.exit("set GEMINI_API_KEY and SUPABASE_SERVICE_ROLE_KEY in the environment.")
    row = sb("GET", f"backlog?story_id=eq.{EP}&select=*").json()
    if not row:
        sys.exit(f"no backlog row for {EP}")
    b = row[0]
    if not (b.get("source_text") or "").strip():
        sys.exit(f"⛔ {EP} has no approved source_text — sheikh approval required first "
                 f"(see docs/SHARIAH_REVIEW_ep02-ep10.md). No generation before the gate.")

    brief = (f"العنوان: {b['title']}\nالمصدر: {b.get('source_ref')} ({b.get('source_grade')})\n"
             f"الدرس: {b.get('lesson')}\nالسيناريو العصري: {b.get('modern_scenario')}\n"
             f"ضابط التصوير: {b.get('depiction_safety')}\n\n"
             f"النص المصدري المعتمد (المصدر الوحيد للمحتوى الديني):\n{b['source_text']}")

    print(f"==> writing script for {EP} …", flush=True)
    script = gemini(WRITER_RULES, brief)
    print(f"==> writing shotlist …", flush=True)
    shotlist_raw = gemini(SHOTLIST_RULES, script, as_json=True)
    try:
        shots = json.loads(shotlist_raw)
    except Exception:
        shots = json.loads(shotlist_raw[shotlist_raw.find("["):shotlist_raw.rfind("]") + 1])

    payload = {
        "story_id": EP, "title": b["title"], "lesson": b.get("lesson"),
        "modern_scenario": b.get("modern_scenario"), "story_source": b.get("source_ref"),
        "script_text": script, "shotlist_json": json.dumps(shots, ensure_ascii=False),
        "script_status": "shari_review",        # ← human shariah gate required next
        "depiction_safety_check": b.get("depiction_safety"),
    }
    # upsert by story_id (episode_id is IDENTITY ALWAYS — never set it)
    existing = sb("GET", f"episodes?story_id=eq.{EP}&select=episode_id").json()
    if existing:
        sb("PATCH", f"episodes?story_id=eq.{EP}",
           headers={"Prefer": "return=minimal"}, data=json.dumps(payload))
    else:
        sb("POST", "episodes", headers={"Prefer": "return=minimal"}, data=json.dumps(payload))

    print(f"\n✅ {EP}: script ({len(script)} chars) + {len(shots)} shots written, "
          f"status=shari_review.\n   Review at the Telegram/admin shariah gate; once approved → "
          f"EPISODE={EP} python3 pipeline/produce_episode.py")
    print("\n----- DRAFT SCRIPT (for review) -----\n" + script[:1500] + "\n…")


if __name__ == "__main__":
    main()
