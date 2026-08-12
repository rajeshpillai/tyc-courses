#!/usr/bin/env python3
"""Generate publish.js with the lesson payload embedded.

browser_run_code_unsafe can load code from a file, which lets us keep the
lesson HTML on disk instead of pushing it through a tool call.

Creates all 7 topics and all 49 lessons under an existing DRAFT course.
"""
import json
from pathlib import Path

HERE = Path(__file__).parent
payload = json.loads((HERE / "payload.json").read_text())

COURSE_ID = 3201  # "Build Your Own AI Agent" — created as a draft

TEMPLATE = """async (page) => {
  const payload = %(payload)s;
  const COURSE_ID = %(course)d;

  await page.goto('https://teachyourselfcoding.com/wp-admin/admin.php?page=create-course&course_id=' + COURSE_ID + '#/curriculum');
  await page.waitForTimeout(6000);

  return await page.evaluate(async (args) => {
    const {payload, COURSE_ID} = args;
    const o = window._tutorobject;
    if (!o) return 'ERROR: _tutorobject missing on page ' + location.href;
    const log = [];
    const sleep = ms => new Promise(r => setTimeout(r, ms));

    const post = async (fields) => {
      const fd = new FormData();
      for (const k of Object.keys(fields)) fd.append(k, fields[k]);
      fd.append(o.nonce_key, o[o.nonce_key]);
      fd.append('_method', 'POST');
      const r = await fetch(o.ajaxurl, {method: 'POST', body: fd, credentials: 'same-origin'});
      let j = null;
      try { j = await r.json(); } catch (e) {}
      return {status: r.status, data: j && j.data, message: j && j.message};
    };

    // 1. Create every topic, in module order.
    const topicIds = [];
    for (const t of payload) {
      const res = await post({action: 'tutor_save_topic', course_id: COURSE_ID,
                              title: t.topic_title, summary: t.topic_summary});
      topicIds.push(res.data);
      log.push('topic ' + res.status + ' id=' + res.data + ' :: ' + t.topic_title);
      await sleep(300);
    }

    // 2. Create every lesson under its topic, in order.
    let made = 0, failed = 0;
    for (let i = 0; i < payload.length; i++) {
      const topicId = topicIds[i];
      if (!topicId) { log.push('SKIP module ' + (i + 1) + ': no topic id'); continue; }
      for (const lsn of payload[i].lessons) {
        const res = await post({
          action: 'tutor_save_lesson',
          topic_id: topicId,
          title: lsn.title,
          description: lsn.html,
          thumbnail_id: 'null',
          'video[runtime][hours]': 0,
          'video[runtime][minutes]': 0,
          'video[runtime][seconds]': 0,
          '_is_preview': 0
        });
        if (res.status === 200 || res.status === 201) {
          made++;
        } else {
          failed++;
          log.push('FAIL ' + res.status + ' :: ' + lsn.title + ' :: ' + (res.message || ''));
        }
        await sleep(300);
      }
      log.push('module ' + (i + 1) + ' :: ' + payload[i].lessons.length + ' lessons under topic ' + topicId);
    }
    log.push('TOTAL lessons created=' + made + ' failed=' + failed);
    return log.join('\\n');
  }, {payload: payload, COURSE_ID: COURSE_ID});
}
"""

js = TEMPLATE % {"payload": json.dumps(payload), "course": COURSE_ID}

out = HERE / "publish.js"
out.write_text(js)
total = sum(len(m["lessons"]) for m in payload)
print(f"wrote {out} ({len(js):,} bytes)")
print(f"  course {COURSE_ID}: {len(payload)} topics, {total} lessons")
