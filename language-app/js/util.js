// Pure helpers. No DOM access here so they can be unit-tested in Node.
(function (root) {
  const STRESS = /́/g;

  function stripStress(s) {
    return String(s || "").replace(STRESS, "");
  }

  // Normalise text for answer comparison.
  // opts.lang: "en" | "ru" | "he"; opts.loose: also drop articles / "to " for vocab answers.
  function normalize(s, opts) {
    opts = opts || {};
    let t = stripStress(s).toLowerCase().normalize("NFC");
    t = t.replace(/ё/g, "е");
    t = t.replace(/[’‘`´]/g, "'");
    // remove parenthetical clarifications: "you (formal)" -> "you"
    t = t.replace(/\([^)]*\)/g, " ");
    t = t.replace(/[.,!?;:"«»„“”¡¿…—–\-]/g, " ");
    t = t.replace(/\s+/g, " ").trim();
    if (opts.loose && opts.lang === "en") {
      t = t.replace(/^(to|a|an|the) /, "");
    }
    return t;
  }

  function levenshtein(a, b) {
    if (a === b) return 0;
    if (!a.length) return b.length;
    if (!b.length) return a.length;
    let prev = new Array(b.length + 1);
    for (let j = 0; j <= b.length; j++) prev[j] = j;
    for (let i = 1; i <= a.length; i++) {
      const cur = [i];
      for (let j = 1; j <= b.length; j++) {
        const cost = a[i - 1] === b[j - 1] ? 0 : 1;
        cur[j] = Math.min(prev[j] + 1, cur[j - 1] + 1, prev[j - 1] + cost);
      }
      prev = cur;
    }
    return prev[b.length];
  }

  // Split a display string into alternative answers: "big / large" or "גדול / גדולה"
  function alternatives(s) {
    return String(s || "")
      .split(/\s*[\/;]\s*|,\s+(?=\S)/)
      .map((x) => x.trim())
      .filter(Boolean);
  }

  // Compare user answer to one or more accepted answers.
  // Returns { ok: bool, close: bool (typo-level), best: accepted string }
  function checkAnswer(input, accepted, opts) {
    opts = opts || {};
    const list = Array.isArray(accepted) ? accepted : [accepted];
    const expanded = [];
    list.forEach((a) => {
      expanded.push(a);
      if (opts.splitAlternatives) alternatives(a).forEach((x) => expanded.push(x));
    });
    const ni = normalize(input, opts);
    if (!ni) return { ok: false, close: false, best: list[0] };
    let bestDist = Infinity, best = list[0];
    for (const a of expanded) {
      const na = normalize(a, opts);
      if (!na) continue;
      if (na === ni) return { ok: true, close: false, best: a };
      const d = levenshtein(ni, na);
      if (d < bestDist) { bestDist = d; best = a; }
    }
    const len = normalize(best, opts).length;
    const tolerance = len >= 8 ? 2 : len >= 4 ? 1 : 0;
    const close = bestDist <= tolerance;
    return { ok: close && !!opts.acceptTypos, close, best };
  }

  // Word-level comparison for speech recognition / sentence feedback.
  // Returns { score: 0..1, words: [{w, ok}] } relative to the expected sentence.
  function compareWords(heard, expected, lang) {
    const hw = normalize(heard, { lang }).split(" ").filter(Boolean);
    const ewDisplay = stripStress(expected).replace(/[.,!?;:"«»„“”…]/g, "").split(/\s+/).filter(Boolean);
    const ew = ewDisplay.map((w) => normalize(w, { lang }));
    const used = new Array(hw.length).fill(false);
    let hits = 0;
    const words = ew.map((w, i) => {
      let ok = false;
      for (let j = 0; j < hw.length; j++) {
        if (used[j]) continue;
        const tol = w.length >= 6 ? 1 : 0;
        if (hw[j] === w || levenshtein(hw[j], w) <= tol) { used[j] = true; ok = true; break; }
      }
      if (ok) hits++;
      return { w: ewDisplay[i], ok };
    });
    const extra = used.filter((u) => !u).length;
    const score = ew.length ? Math.max(0, (hits - extra * 0.25) / ew.length) : 0;
    return { score: Math.min(1, score), words };
  }

  function shuffle(arr, rnd) {
    rnd = rnd || Math.random;
    const a = arr.slice();
    for (let i = a.length - 1; i > 0; i--) {
      const j = Math.floor(rnd() * (i + 1));
      [a[i], a[j]] = [a[j], a[i]];
    }
    return a;
  }

  function sample(arr, n, rnd) {
    return shuffle(arr, rnd).slice(0, n);
  }

  // Split a sentence into word tiles, keeping punctuation attached to words.
  function tokenize(sentence) {
    return String(sentence).trim().split(/\s+/).filter(Boolean);
  }

  function tilesKey(s) {
    return normalize(s).replace(/\s+/g, " ");
  }

  function dayKey(d) {
    d = d || new Date();
    const y = d.getFullYear(), m = String(d.getMonth() + 1).padStart(2, "0"), day = String(d.getDate()).padStart(2, "0");
    return `${y}-${m}-${day}`;
  }

  function addDays(key, n) {
    const [y, m, d] = key.split("-").map(Number);
    const dt = new Date(y, m - 1, d);
    dt.setDate(dt.getDate() + n);
    return dayKey(dt);
  }

  function escapeHtml(s) {
    return String(s == null ? "" : s)
      .replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;").replace(/'/g, "&#39;");
  }

  // Count vowels to decide if a Russian word needs a stress mark.
  function ruVowelCount(w) {
    return (stripStress(w).toLowerCase().match(/[аеёиоуыэюя]/g) || []).length;
  }

  const api = { stripStress, normalize, levenshtein, alternatives, checkAnswer, compareWords, shuffle, sample, tokenize, tilesKey, dayKey, addDays, escapeHtml, ruVowelCount };
  root.LSUtil = api;
  if (typeof module !== "undefined") module.exports = api;
})(typeof window !== "undefined" ? window : globalThis);
