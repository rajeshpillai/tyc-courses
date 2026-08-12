#!/usr/bin/env python3
"""Generate sync.js — push regenerated titles and lesson HTML to the live draft.

Matches by POSITION, not by title. The provider-neutral rewrite renamed several
lessons and replaced one outright, so title matching would orphan the old ones
and silently skip the new. Structure is unchanged (7 topics x 7 lessons in the
same order), so position is the reliable key.

Lessons were created in module order, so lesson index i maps to id BASE + i.
The script verifies that mapping before writing anything.
"""
import json
from pathlib import Path

HERE = Path(__file__).parent
payload = json.loads((HERE / "payload.json").read_text())

COURSE_ID = 3201
TOPIC_IDS = [3202, 3203, 3204, 3205, 3206, 3207, 3208]
BASE_LESSON_ID = 3209          # first lesson created; ids are sequential

flat = []
for mi, mod in enumerate(payload):
    for li, lsn in enumerate(mod["lessons"]):
        flat.append({
            "id": BASE_LESSON_ID + len(flat),
            "topic_id": TOPIC_IDS[mi],
            "title": lsn["title"],
            "html": lsn["html"],
        })

TEMPLATE = """async (page) => {
  const lessons = %(lessons)s;
  const topics  = %(topics)s;

  await page.goto('https://teachyourselfcoding.com/wp-admin/admin.php?page=create-course&course_id=%(course)d#/basics');
  await page.waitForTimeout(5000);

  return await page.evaluate(async (args) => {
    const {lessons, topics} = args;
    const nonce = window.wpApiSettings.nonce;
    const log = [];
    const sleep = ms => new Promise(r => setTimeout(r, ms));

    const get = (id) => fetch('/wp-json/wp/v2/lesson/' + id + '?context=edit&_fields=id,title,content,parent',
      {credentials: 'same-origin', headers: {'X-WP-Nonce': nonce}}).then(r => r.json());

    // 1. Safety check: every target id must exist and sit under the expected topic.
    let bad = 0;
    for (const l of lessons) {
      const cur = await get(l.id);
      if (!cur || !cur.id) { log.push('MISSING lesson ' + l.id); bad++; continue; }
      if (cur.parent && cur.parent !== l.topic_id) {
        log.push('WRONG TOPIC ' + l.id + ' is under ' + cur.parent + ', expected ' + l.topic_id);
        bad++;
      }
    }
    if (bad) {
      log.push('ABORTED before writing: ' + bad + ' mismatch(es). Nothing changed.');
      return log.join('\\n');
    }
    log.push('preflight ok: ' + lessons.length + ' lessons found in the expected order');

    // 2. Update titles and bodies where they differ.
    let titled = 0, bodied = 0, same = 0, failed = 0;
    for (const l of lessons) {
      const cur = await get(l.id);
      const curTitle = (cur.title && cur.title.raw) || '';
      const curBody  = (cur.content && cur.content.raw) || '';
      const body = {};
      if (curTitle.trim() !== l.title.trim()) body.title = l.title;
      if (curBody.trim() !== l.html.trim())   body.content = l.html;

      if (!Object.keys(body).length) { same++; continue; }

      const r = await fetch('/wp-json/wp/v2/lesson/' + l.id, {
        method: 'POST',
        headers: {'Content-Type': 'application/json', 'X-WP-Nonce': nonce},
        credentials: 'same-origin',
        body: JSON.stringify(body)});
      if (r.status === 200) {
        if (body.title)   { titled++; log.push('retitled ' + l.id + ' -> ' + l.title.slice(0, 58)); }
        if (body.content) bodied++;
      } else {
        failed++; log.push('FAIL ' + r.status + ' on ' + l.id);
      }
      await sleep(250);
    }

    // 3. Topic summaries, in case a module intro changed.
    for (const t of topics) {
      const o = window._tutorobject;
      const fd = new FormData();
      fd.append('action', 'tutor_save_topic');
      fd.append('course_id', %(course)d);
      fd.append('topic_id', t.id);
      fd.append('title', t.title);
      fd.append('summary', t.summary);
      fd.append(o.nonce_key, o[o.nonce_key]);
      fd.append('_method', 'POST');
      const r = await fetch(o.ajaxurl, {method: 'POST', body: fd, credentials: 'same-origin'});
      log.push('topic ' + t.id + ' summary -> ' + r.status);
      await sleep(250);
    }

    log.push('---');
    log.push('titles changed=' + titled + '  bodies changed=' + bodied +
             '  unchanged=' + same + '  failed=' + failed);
    return log.join('\\n');
  }, {lessons: lessons, topics: topics});
}
"""

topics = [{"id": TOPIC_IDS[i], "title": m["topic_title"], "summary": m["topic_summary"]}
          for i, m in enumerate(payload)]

js = TEMPLATE % {"lessons": json.dumps(flat), "topics": json.dumps(topics),
                 "course": COURSE_ID}
out = HERE / "sync.js"
out.write_text(js)
print(f"wrote {out} ({len(js):,} bytes)")
print(f"  {len(flat)} lessons, ids {flat[0]['id']}–{flat[-1]['id']}, {len(topics)} topics")
print("  match strategy: position (titles changed in the rewrite)")
