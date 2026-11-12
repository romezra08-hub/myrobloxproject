// Content access for the active profile + lesson (session) builders.
(function (root) {
  const U = root.LSUtil;
  const SRS = root.LSSrs;
  const D = () => root.LS_DATA || {};

  const TRANSLIT = { а: "a", б: "b", в: "v", г: "g", д: "d", е: "e", ё: "yo", ж: "zh", з: "z", и: "i", й: "y", к: "k", л: "l", м: "m", н: "n", о: "o", п: "p", р: "r", с: "s", т: "t", у: "u", ф: "f", х: "kh", ц: "ts", ч: "ch", ш: "sh", щ: "shch", ъ: "", ы: "y", ь: "'", э: "e", ю: "yu", я: "ya" };
  function translit(s) {
    return [...U.stripStress(s)].map((c) => {
      const low = c.toLowerCase();
      if (!(low in TRANSLIT)) return c;
      const r = TRANSLIT[low];
      return c === low ? r : r.charAt(0).toUpperCase() + r.slice(1);
    }).join("");
  }
  // Latin transliteration keeping the stressed vowel in CAPS-free accent: "moloko´" style -> we use an acute on the latin vowel
  function translitStress(s) {
    let out = "";
    const chars = [...String(s)];
    for (let i = 0; i < chars.length; i++) {
      const c = chars[i];
      if (c === "́") { out += "́"; continue; }
      const low = c.toLowerCase();
      if (low in TRANSLIT) {
        let r = TRANSLIT[low];
        if (c !== low) r = r.charAt(0).toUpperCase() + r.slice(1);
        // put accent after the vowel letter of multi-letter outputs (ya -> yá)
        if (chars[i + 1] === "́" && r.length > 1) { out += r + "́"; i++; continue; }
        out += r;
      } else out += c;
    }
    return out.normalize("NFC");
  }

  const topicOrder = () => (D().topics || []).map((t) => t.id);

  function vocab() { return D().vocab || []; }
  function phrases() { return D().phrases || []; }

  let byId = null;
  function item(id) {
    if (!byId) {
      byId = {};
      vocab().forEach((v) => (byId[v.id] = Object.assign({ _type: "word" }, v)));
      phrases().forEach((p) => (byId[p.id] = Object.assign({ _type: "phrase" }, p)));
    }
    return byId[id];
  }
  function resetIndex() { byId = null; }

  // Curriculum order: level first, then topic order, then file order.
  function curriculum() {
    const order = topicOrder();
    return vocab()
      .map((v, i) => ({ v, i }))
      .sort((a, b) => (a.v.level || 2) - (b.v.level || 2) || order.indexOf(a.v.topic) - order.indexOf(b.v.topic) || a.i - b.i)
      .map((x) => x.v);
  }

  function phraseCurriculum() {
    const sits = (D().situations || []).map((s) => s.id);
    return phrases()
      .map((p, i) => ({ p, i }))
      .sort((a, b) => (a.p.level || 2) - (b.p.level || 2) || sits.indexOf(a.p.sit) - sits.indexOf(b.p.sit) || a.i - b.i)
      .map((x) => x.p);
  }

  // ---- distractors for multiple choice ----
  function distractors(it, field, n) {
    // never offer an option that shares a translation with the answer in ANY language (avoids two "right" answers)
    const same = (v) => ["en", "ru", "he"].some((l) => v[l] && it[l] && U.normalize(v[l]) === U.normalize(it[l]));
    const pool = (it._type === "phrase" ? phrases() : vocab()).filter((v) => v.id !== it.id && v[field] && !same(v));
    const near = pool.filter((v) => v.topic === it.topic || (it.sit && v.sit === it.sit));
    const picks = U.sample(near, n);
    if (picks.length < n) picks.push(...U.sample(pool.filter((v) => !picks.includes(v)), n - picks.length));
    // avoid duplicate visible texts
    const seen = new Set([U.normalize(it[field])]);
    return picks.filter((p) => { const k = U.normalize(p[field]); if (seen.has(k)) return false; seen.add(k); return true; });
  }

  // ---- exercise selection by strength ----
  function exerciseFor(it, card, ctx) {
    const s = SRS.strength(card);
    const canListen = ctx.canListen;
    const r = Math.random();
    if (it._type === "phrase") {
      if (s <= 1) return { kind: "build", item: it };
      if (s === 2) return { kind: r < 0.5 ? "buildListen" : "build", item: it };
      if (canListen && r < 0.35) return { kind: "speak", item: it };
      return { kind: r < 0.7 ? "buildListen" : "dictation", item: it };
    }
    if (s === 0) return { kind: "mc", dir: "t2h", item: it };
    if (s === 1) return { kind: "mc", dir: r < 0.5 ? "h2t" : "listen", item: it };
    if (s === 2) return r < 0.5 ? { kind: "type", item: it } : { kind: "mc", dir: r < 0.75 ? "listen" : "h2t", item: it };
    if (canListen && r < 0.2) return { kind: "speak", item: it };
    if (r < 0.55) return { kind: "type", item: it };
    if (r < 0.8) return { kind: "dictation", item: it };
    return { kind: "mc", dir: "listen", item: it };
  }

  function easier(step) {
    if (step.kind === "type" || step.kind === "dictation" || step.kind === "speak") {
      return step.item._type === "phrase" ? { kind: "build", item: step.item } : { kind: "mc", dir: "h2t", item: step.item };
    }
    if (step.kind === "buildListen") return { kind: "build", item: step.item };
    return Object.assign({}, step, { retry: true });
  }

  function dueCards(prog, now) {
    now = now || Date.now();
    return Object.keys(prog.cards)
      .filter((id) => item(id) && SRS.isDue(prog.cards[id], now))
      .sort((a, b) => prog.cards[a].due - prog.cards[b].due);
  }

  function unseen(prog, list) {
    return list.filter((v) => !prog.cards[v.id]);
  }

  // Letters progress helpers
  function alphabet(target) { return ((D().alphabet || {})[target]) || []; }
  function lettersLearned(prog, target) {
    const al = alphabet(target);
    return al.filter((l) => (prog.letters[l.upper] || {}).right >= 2).length;
  }
  function nextLetterGroup(prog, target) {
    const groups = ((D().alphabetLessons || {})[target]) || [];
    for (const g of groups) {
      if (g.some((u) => !((prog.letters[u] || {}).right >= 2))) return g;
    }
    return null;
  }

  // Build the daily mixed lesson.
  // Order: alphabet warm-up (while learning letters) -> due reviews (interleaved) -> new words
  // (present, then immediately retrieve) -> new phrase -> speaking -> a final mixed recap.
  function buildDaily(profile, prog, opts) {
    opts = opts || {};
    const ctx = { canListen: !!opts.canListen };
    const steps = [];
    const T = profile.target;

    // 1) Alphabet warm-up for early learners
    const al = alphabet(T);
    if (al.length && lettersLearned(prog, T) < al.length) {
      const g = nextLetterGroup(prog, T);
      if (g) {
        const letters = g.map((u) => al.find((l) => l.upper === u)).filter(Boolean);
        letters.filter((l) => !(prog.letters[l.upper] || {}).seen).forEach((l) => steps.push({ kind: "letterIntro", letter: l }));
        U.shuffle(letters).forEach((l, i) => steps.push({ kind: "letterQuiz", letter: l, mode: i % 2 ? "word" : "sound" }));
      }
    }

    // 2) Reviews
    const due = dueCards(prog).slice(0, opts.maxReviews || 20);
    const reviewSteps = due.map((id) => exerciseFor(item(id), prog.cards[id], ctx));

    // 3) New words
    const today = U.dayKey();
    // Don't let reviews snowball: the bigger the review pile, the fewer new words today.
    const dueCount = dueCards(prog).length;
    const base = opts.newCount != null ? opts.newCount : (profile.newPerDay || 8);
    const newLimit = dueCount > 30 ? Math.max(2, base - Math.floor((dueCount - 30) / 8)) : base;
    const fresh = unseen(prog, curriculum()).slice(0, newLimit).map((v) => item(v.id));
    const newSteps = [];
    for (let i = 0; i < fresh.length; i += 4) {
      const batch = fresh.slice(i, i + 4);
      // Pretesting effect: guess first (no penalty), then see the answer, then retrieve.
      batch.forEach((it) => { newSteps.push({ kind: "mc", dir: "t2h", item: it, pretest: true }); newSteps.push({ kind: "intro", item: it }); });
      U.shuffle(batch).forEach((it) => newSteps.push({ kind: "mc", dir: Math.random() < 0.5 ? "h2t" : "listen", item: it, learning: true }));
      if (batch.length >= 3) newSteps.push({ kind: "match", items: batch, learning: true });
    }

    // 4) New phrase once the learner knows some words
    const knownCount = Object.keys(prog.cards).length;
    const phraseSteps = [];
    if (knownCount >= 12) {
      const freshP = unseen(prog, phraseCurriculum()).slice(0, 2).map((p) => item(p.id));
      freshP.forEach((p) => { phraseSteps.push({ kind: "intro", item: p }); phraseSteps.push({ kind: "build", item: p, learning: true }); });
    }

    // Interleave reviews with new material so the lesson doesn't feel blocked.
    const mixed = [];
    const r = reviewSteps.slice();
    const half = Math.ceil(r.length / 2);
    mixed.push(...r.splice(0, half));
    mixed.push(...newSteps);
    mixed.push(...r);
    mixed.push(...phraseSteps);

    // 5) recap new words with a harder direction (spaced within the session)
    if (fresh.length) U.sample(fresh, Math.min(4, fresh.length)).forEach((it) => mixed.push({ kind: "mc", dir: Math.random() < 0.5 ? "h2t" : "listen", item: it, learning: true }));
    if (ctx.canListen && fresh.length) mixed.push({ kind: "speak", item: fresh[0], learning: true });

    steps.push(...mixed);
    return { steps, newIds: fresh.map((f) => f.id).concat(phraseSteps.filter((s) => s.kind === "intro").map((s) => s.item.id)), day: today };
  }

  // Lesson on one vocabulary topic: new words from the topic + reviews from the topic.
  function buildTopic(profile, prog, topicId, opts) {
    opts = opts || {};
    const ctx = { canListen: !!opts.canListen };
    const list = vocab().filter((v) => v.topic === topicId).map((v) => item(v.id));
    const fresh = unseen(prog, list).slice(0, opts.newCount || 6);
    const old = U.shuffle(list.filter((v) => prog.cards[v.id])).slice(0, 10);
    const steps = [];
    for (let i = 0; i < fresh.length; i += 3) {
      const b = fresh.slice(i, i + 3);
      b.forEach((it) => steps.push({ kind: "intro", item: it }));
      U.shuffle(b).forEach((it) => steps.push({ kind: "mc", dir: "t2h", item: it, learning: true }));
    }
    if (fresh.length >= 3) steps.push({ kind: "match", items: U.sample(fresh, Math.min(5, fresh.length)), learning: true });
    old.forEach((it) => steps.push(exerciseFor(it, prog.cards[it.id], ctx)));
    fresh.forEach((it) => steps.push({ kind: "mc", dir: "h2t", item: it, learning: true }));
    if (!steps.length) list.slice(0, 8).forEach((it) => steps.push(exerciseFor(it, prog.cards[it.id], ctx)));
    return { steps: interleaveTail(steps), newIds: fresh.map((f) => f.id) };
  }

  function buildSituation(profile, prog, sitId, opts) {
    opts = opts || {};
    const ctx = { canListen: !!opts.canListen };
    const list = phrases().filter((p) => p.sit === sitId).map((p) => item(p.id));
    const fresh = unseen(prog, list).slice(0, 4);
    const old = U.shuffle(list.filter((p) => prog.cards[p.id])).slice(0, 6);
    const steps = [];
    fresh.forEach((p) => { steps.push({ kind: "intro", item: p }); steps.push({ kind: "build", item: p, learning: true }); });
    old.forEach((p) => steps.push(exerciseFor(p, prog.cards[p.id], ctx)));
    fresh.forEach((p) => steps.push({ kind: "buildListen", item: p, learning: true }));
    if (ctx.canListen && fresh[0]) steps.push({ kind: "speak", item: fresh[0], learning: true });
    return { steps, newIds: fresh.map((f) => f.id) };
  }

  // Hardest items: most lapses / wrong answers.
  function hardest(prog, n) {
    return Object.keys(prog.cards)
      .filter((id) => item(id))
      .map((id) => ({ id, c: prog.cards[id] }))
      .filter((x) => x.c.wrong > 0)
      .sort((a, b) => (b.c.wrong - b.c.right * 0.3) - (a.c.wrong - a.c.right * 0.3))
      .slice(0, n || 20)
      .map((x) => x.id);
  }

  function buildMistakes(profile, prog, opts) {
    const ctx = { canListen: !!(opts && opts.canListen) };
    const ids = hardest(prog, 12);
    const steps = [];
    ids.forEach((id) => { const it = item(id); if (it._type === "word") steps.push({ kind: "intro", item: it, review: true }); });
    U.shuffle(ids).forEach((id) => steps.push(exerciseFor(item(id), prog.cards[id], ctx)));
    return { steps, newIds: [] };
  }

  function interleaveTail(steps) { return steps; }

  function stats(prog) {
    const ids = Object.keys(prog.cards).filter((id) => item(id));
    let mastered = 0, learning = 0;
    ids.forEach((id) => (SRS.isMastered(prog.cards[id]) ? mastered++ : learning++));
    return { seen: ids.length, mastered, learning, due: dueCards(prog).length };
  }

  function forecast(prog, days) {
    const out = new Array(days).fill(0);
    const start = new Date(); start.setHours(0, 0, 0, 0);
    Object.keys(prog.cards).forEach((id) => {
      const c = prog.cards[id];
      if (!item(id) || c.state === "new") return;
      const d = Math.floor((c.due - start.getTime()) / SRS.DAY);
      out[Math.max(0, Math.min(days - 1, d))] += d < days ? 1 : 0;
    });
    return out;
  }

  root.LSContent = { translit, translitStress, vocab, phrases, item, resetIndex, curriculum, phraseCurriculum, distractors, exerciseFor, easier, dueCards, unseen, alphabet, lettersLearned, nextLetterGroup, buildDaily, buildTopic, buildSituation, buildMistakes, hardest, stats, forecast };
})(window);
