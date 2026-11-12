// Spaced-repetition scheduler (SM-2 family with learning steps, like Anki).
// Grades: 1 = Again (wrong), 2 = Hard, 3 = Good, 4 = Easy.
(function (root) {
  const MIN = 60 * 1000;
  const DAY = 24 * 60 * MIN;
  const LEARN_STEPS = [1 * MIN, 10 * MIN];     // re-show soon after first meeting
  const RELEARN_STEPS = [10 * MIN];
  const MAX_IVL = 365;

  function newCard(now) {
    return { state: "new", step: 0, ivl: 0, ease: 2.5, reps: 0, lapses: 0, due: now || Date.now(), last: 0, right: 0, wrong: 0 };
  }

  function fuzz(ivl, rnd) {
    if (ivl < 3) return ivl;
    const r = (rnd || Math.random)();
    const spread = Math.max(1, Math.round(ivl * 0.05));
    return ivl + Math.round((r * 2 - 1) * spread);
  }

  function review(card, grade, now, rnd) {
    now = now || Date.now();
    const c = Object.assign({}, card || newCard(now));
    c.reps += 1;
    c.last = now;
    if (grade >= 3) c.right += 1; else c.wrong += 1;

    if (c.state === "new" || c.state === "learn" || c.state === "relearn") {
      const steps = c.state === "relearn" ? RELEARN_STEPS : LEARN_STEPS;
      if (grade === 1) {
        c.state = c.state === "relearn" ? "relearn" : "learn";
        c.step = 0;
        c.due = now + steps[0];
      } else if (grade === 4) {
        const wasRelearn = c.state === "relearn";
        c.state = "review";
        c.ivl = wasRelearn ? Math.max(1, c.ivl) : 4;
        c.due = now + c.ivl * DAY;
      } else {
        const next = (c.state === "new" ? 0 : c.step) + (grade === 2 ? 0 : 1);
        if (next >= steps.length) {
          const wasRelearn = c.state === "relearn";
          c.state = "review";
          c.ivl = wasRelearn ? Math.max(1, c.ivl) : 1;
          c.due = now + c.ivl * DAY;
        } else {
          c.state = c.state === "new" ? "learn" : c.state;
          c.step = next;
          c.due = now + steps[next];
        }
      }
      return c;
    }

    // review state
    if (grade === 1) {
      c.lapses += 1;
      c.ease = Math.max(1.3, c.ease - 0.2);
      c.ivl = Math.max(1, Math.round(c.ivl * 0.3));
      c.state = "relearn";
      c.step = 0;
      c.due = now + RELEARN_STEPS[0];
      return c;
    }
    // reward reviews that happened late but were still remembered
    const overdueDays = Math.max(0, (now - c.due) / DAY);
    let ivl;
    if (grade === 2) {
      ivl = Math.max(c.ivl + 1, Math.round(c.ivl * 1.2));
      c.ease = Math.max(1.3, c.ease - 0.15);
    } else if (grade === 3) {
      ivl = Math.max(c.ivl + 1, Math.round((c.ivl + overdueDays / 2) * c.ease));
    } else {
      ivl = Math.max(c.ivl + 2, Math.round((c.ivl + overdueDays) * c.ease * 1.3));
      c.ease = Math.min(3.0, c.ease + 0.15);
    }
    c.ivl = Math.min(MAX_IVL, fuzz(ivl, rnd));
    c.due = now + c.ivl * DAY;
    return c;
  }

  // 0..5 strength used to pick harder exercise types as a word gets stronger.
  function strength(card) {
    if (!card || card.state === "new") return 0;
    if (card.state === "learn" || card.state === "relearn") return card.reps >= 3 ? 2 : 1;
    if (card.ivl < 3) return 2;
    if (card.ivl < 8) return 3;
    if (card.ivl < 21) return 4;
    return 5;
  }

  function isDue(card, now) {
    return !!card && card.state !== "new" && card.due <= (now || Date.now());
  }

  function isMastered(card) {
    return !!card && card.state === "review" && card.ivl >= 21;
  }

  // Convert an exercise result to a grade.
  function gradeFrom(correct, opts) {
    opts = opts || {};
    if (!correct) return 1;
    if (opts.close || opts.hinted) return 2;
    if (opts.fast && opts.hard) return 4;
    return 3;
  }

  const api = { newCard, review, strength, isDue, isMastered, gradeFrom, DAY, MIN };
  root.LSSrs = api;
  if (typeof module !== "undefined") module.exports = api;
})(typeof window !== "undefined" ? window : globalThis);
