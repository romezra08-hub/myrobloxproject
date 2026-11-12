// Text-to-speech and speech recognition wrappers (Web Speech API).
(function (root) {
  const U = root.LSUtil;
  const LOCALES = { en: "en-US", ru: "ru-RU", he: "he-IL" };
  let voices = [];
  const synth = root.speechSynthesis;

  function loadVoices() {
    if (!synth) return;
    voices = synth.getVoices() || [];
  }
  if (synth) {
    loadVoices();
    if (typeof synth.addEventListener === "function") synth.addEventListener("voiceschanged", loadVoices);
    else synth.onvoiceschanged = loadVoices;
  }

  function voiceFor(lang) {
    const loc = LOCALES[lang] || lang;
    const prefix = loc.slice(0, 2);
    const cands = voices.filter((v) => (v.lang || "").replace("_", "-").toLowerCase().startsWith(prefix));
    if (!cands.length) return null;
    // Prefer exact locale, then natural/online/Google voices which sound better.
    const score = (v) => {
      let s = 0;
      const l = (v.lang || "").replace("_", "-").toLowerCase();
      if (l === loc.toLowerCase()) s += 4;
      if (/natural|neural|online|google|premium|enhanced/i.test(v.name)) s += 3;
      if (/samantha|milena|yuri|daniel|alex/i.test(v.name)) s += 1;
      return s;
    };
    return cands.sort((a, b) => score(b) - score(a))[0];
  }

  function canSpeak(lang) {
    if (!synth) return false;
    if (!voices.length) loadVoices();
    // If voice list is empty some browsers still speak with the default voice.
    return voices.length === 0 ? true : !!voiceFor(lang);
  }

  function speak(text, lang, opts) {
    opts = opts || {};
    return new Promise((resolve) => {
      if (!synth || !text) return resolve(false);
      try {
        synth.cancel();
        const u = new root.SpeechSynthesisUtterance(U.stripStress(text));
        u.lang = LOCALES[lang] || lang;
        const v = voiceFor(lang);
        if (v) u.voice = v;
        u.rate = opts.rate || 0.9;
        u.pitch = 1;
        let done = false;
        const finish = (ok) => { if (!done) { done = true; resolve(ok); } };
        u.onend = () => finish(true);
        u.onerror = () => finish(false);
        // Safety timeout: some engines never fire onend.
        setTimeout(() => finish(true), 1500 + text.length * 120 / (u.rate || 1));
        synth.speak(u);
      } catch (e) { resolve(false); }
    });
  }

  function stop() { try { synth && synth.cancel(); } catch (e) {} }

  const Rec = root.SpeechRecognition || root.webkitSpeechRecognition;
  function canListen() { return !!Rec; }

  // Listen once. Resolves { ok, alternatives: [string], error }
  let current = null;
  function listen(lang, opts) {
    opts = opts || {};
    return new Promise((resolve) => {
      if (!Rec) return resolve({ ok: false, alternatives: [], error: "unsupported" });
      stop();
      try { if (current) current.abort(); } catch (e) {}
      const r = new Rec();
      current = r;
      r.lang = LOCALES[lang] || lang;
      r.interimResults = false;
      r.maxAlternatives = 5;
      r.continuous = false;
      let settled = false;
      const finish = (res) => { if (!settled) { settled = true; current = null; resolve(res); } };
      r.onresult = (e) => {
        const alts = [];
        const res = e.results[0];
        for (let i = 0; i < res.length; i++) alts.push(res[i].transcript);
        finish({ ok: true, alternatives: alts });
      };
      r.onerror = (e) => finish({ ok: false, alternatives: [], error: e.error || "error" });
      r.onend = () => finish({ ok: false, alternatives: [], error: "no-speech" });
      try { r.start(); } catch (e) { finish({ ok: false, alternatives: [], error: "start" }); }
      setTimeout(() => { try { r.stop(); } catch (e) {} }, opts.timeout || 8000);
    });
  }

  function cancelListen() { try { current && current.abort(); } catch (e) {} }

  // Pick the recognition alternative that best matches the expected text.
  function bestMatch(alternatives, expected, lang) {
    let best = { score: 0, words: [], heard: "" };
    (alternatives || []).forEach((a) => {
      const r = U.compareWords(a, expected, lang);
      if (r.score > best.score || !best.heard) best = Object.assign(r, { heard: a });
    });
    return best;
  }

  root.LSSpeech = { speak, stop, canSpeak, canListen, listen, cancelListen, bestMatch, voiceFor, LOCALES };
})(window);
