// Exercise renderers. Each takes (step, ctx) and returns an element.
// ctx: { profile, T, H, prog, finish(result), setCheck(enabled, fn), canListen }
// result: { correct: bool|null, close, answer: string, answerLang, why, skipped, intro }
(function (root) {
  const { h, L, speakerBtn, keyboard } = root.LSUI;
  const { t, pick } = root.LSI18n;
  const U = root.LSUtil;
  const C = root.LSContent;
  const SP = root.LSSpeech;

  const langName = (l) => t("lang_" + l);
  const tgt = (it, ctx) => it[ctx.T];
  const hlp = (it, ctx) => it[ctx.H] || it.en || it.he;

  function autoplay(text, lang, ctx, delay) {
    if (ctx.muted) return;
    setTimeout(() => SP.speak(text, lang, { rate: ctx.rate }), delay || 250);
  }

  function prompt(title) { return h("div.ex-title", title); }

  function transliterationLine(it, ctx) {
    if (ctx.T !== "ru" || !ctx.profile.translit) return null;
    return h("div.translit", { dir: "ltr" }, "[" + C.translitStress(tgt(it, ctx)) + "]");
  }

  // ---------- intro (presentation card) ----------
  function intro(step, ctx) {
    const it = step.item;
    const T = ctx.T, H = ctx.H;
    const isPhrase = it._type === "phrase";
    const info = [];
    if (T === "ru" && it.g) info.push(h("span.chip", t("gender") + ": " + t("g_" + it.g)));
    if (T === "ru" && it.ruPf) info.push(h("span.chip", h("span", t("perfective") + ": "), L(it.ruPf, "ru")));
    if (T === "ru" && it.ruPres) info.push(h("span.chip", h("span", t("present") + ": "), L(it.ruPres, "ru")));
    if (T === "en" && it.enPast) info.push(h("span.chip", h("span", t("pastForm") + ": "), L(it.enPast, "en")));

    const exT = it[T + "Ex"], exH = it[H + "Ex"];
    const notes = ctx.prog.notes || (ctx.prog.notes = {});
    const hook = h("textarea.hook", { rows: 2, placeholder: hookPlaceholder(), dir: "auto" });
    hook.value = notes[it.id] || "";
    hook.addEventListener("input", () => { notes[it.id] = hook.value; root.LSStore.saveProgress(ctx.profile.id); });

    const el = h("div.ex.intro",
      h("div.badge-new", step.review ? "🔁 " + t("reviewTopic") : "✨ " + t(isPhrase ? "newPhrase" : "newWord")),
      it.emoji ? h("div.big-emoji", { "aria-hidden": "true" }, it.emoji) : null,
      h("div.target-word" + (isPhrase ? ".phrase" : ""), L(tgt(it, ctx), T), speakerBtn(tgt(it, ctx), T, { withSlow: true })),
      transliterationLine(it, ctx),
      h("div.help-word", L(hlp(it, ctx), H)),
      info.length ? h("div.chips", info) : null,
      exT ? h("div.example",
        h("div.ex-t", L(exT, T), speakerBtn(exT, T)),
        exH ? h("div.ex-h", L(exH, H)) : null) : null,
      T === "ru" && /́/.test(tgt(it, ctx)) ? h("div.small.muted", t("stressNote")) : null,
      isPhrase ? null : h("details.hook-box", h("summary", "💡 " + hookTitle()), hook)
    );
    autoplay(tgt(it, ctx), T, ctx);
    ctx.setCheck(true, () => ctx.finish({ intro: true, correct: null }), t("gotIt"));
    return el;
  }
  function hookTitle() { return { he: "טריק לזכירה (לא חובה)", en: "Memory hook (optional)", ru: "Подсказка для памяти (по желанию)" }[root.LSI18n.getLang()]; }
  function hookPlaceholder() { return { he: "למשל: מילה שנשמעת דומה, תמונה מצחיקה בראש…", en: "e.g. a similar-sounding word, a funny mental picture…", ru: "например: похожее по звучанию слово, смешная картинка…" }[root.LSI18n.getLang()]; }

  // ---------- multiple choice ----------
  function mc(step, ctx) {
    const it = step.item;
    const T = ctx.T, H = ctx.H;
    const dir = step.dir;
    const optField = dir === "t2h" ? H : T;
    const opts = U.shuffle([it].concat(C.distractors(it, optField, 3)));
    let promptEl, title;
    if (dir === "t2h") {
      title = t("q_meaning");
      promptEl = h("div.target-word", L(tgt(it, ctx), T), speakerBtn(tgt(it, ctx), T));
      autoplay(tgt(it, ctx), T, ctx);
    } else if (dir === "h2t") {
      title = t("q_translate", { lang: langName(T) });
      promptEl = h("div.help-prompt", it.emoji ? h("span.emoji", it.emoji) : null, L(hlp(it, ctx), H));
    } else {
      title = t("q_listen");
      promptEl = h("div.listen-prompt", speakerBtn(tgt(it, ctx), T, { big: true, withSlow: true }));
      autoplay(tgt(it, ctx), T, ctx);
    }
    let answered = false;
    const list = h("div.options");
    opts.forEach((o) => {
      const text = o[optField] || "";
      const btn = h("button.option", { type: "button" }, L(text, optField));
      btn.addEventListener("click", () => {
        if (answered) return;
        answered = true;
        const ok = o.id === it.id;
        btn.classList.add(ok ? "right" : "wrong");
        if (!ok) [...list.children].forEach((b, i) => { if (opts[i].id === it.id) b.classList.add("right"); });
        ctx.finish({ correct: ok, answer: tgt(it, ctx), answerLang: T, sub: hlp(it, ctx) });
      });
      list.appendChild(btn);
    });
    ctx.setCheck(false);
    return h("div.ex.mc", prompt(title), promptEl, list);
  }

  // ---------- typing (production / spelling) ----------
  function typeInput(ctx, onEnter) {
    const input = h("input.answer", { type: "text", autocomplete: "off", autocapitalize: "off", spellcheck: "false", lang: ctx.T, dir: "ltr", placeholder: t("typeHere") });
    input.addEventListener("keydown", (e) => { if (e.key === "Enter") { e.preventDefault(); e.stopPropagation(); onEnter(); } });
    const wantKb = ctx.T === "ru" ? ctx.profile.kb !== false : !!ctx.profile.kb;
    const kb = keyboard(input, ctx.T);
    const kbWrap = h("div.kb-wrap", kb);
    if (!wantKb) kbWrap.hidden = true;
    else input.setAttribute("inputmode", "none");
    const toggle = h("button.link-btn", { type: "button", onclick: () => {
      kbWrap.hidden = !kbWrap.hidden;
      if (kbWrap.hidden) input.removeAttribute("inputmode"); else input.setAttribute("inputmode", "none");
      root.LSStore.updateProfile(ctx.profile.id, { kb: !kbWrap.hidden });
      ctx.profile.kb = !kbWrap.hidden;
      input.focus();
    } }, "⌨️ " + t("keyboard"));
    return { input, extra: h("div", toggle, kbWrap) };
  }

  function type(step, ctx) {
    const it = step.item;
    const T = ctx.T, H = ctx.H;
    const check = () => {
      if (!ti.input.value.trim()) return;
      const r = U.checkAnswer(ti.input.value, tgt(it, ctx), { lang: T, loose: true, splitAlternatives: true, acceptTypos: true });
      ti.input.disabled = true;
      ctx.finish({ correct: r.ok, close: r.close && r.ok && U.normalize(ti.input.value, { lang: T, loose: true }) !== U.normalize(r.best, { lang: T, loose: true }), answer: tgt(it, ctx), answerLang: T, sub: hlp(it, ctx), typed: ti.input.value });
    };
    const ti = typeInput(ctx, check);
    ti.input.addEventListener("input", () => ctx.setCheck(!!ti.input.value.trim(), check));
    ctx.setCheck(false, check);
    setTimeout(() => ti.input.focus({ preventScroll: true }), 50);
    return h("div.ex.type",
      prompt(t("q_type", { lang: langName(T) })),
      h("div.help-prompt", it.emoji ? h("span.emoji", it.emoji) : null, L(hlp(it, ctx), H)),
      ti.input, ti.extra,
      h("button.link-btn", { type: "button", onclick: () => ctx.finish({ correct: false, answer: tgt(it, ctx), answerLang: T, sub: hlp(it, ctx), gaveUp: true }) }, t("dontKnow")));
  }

  // ---------- dictation (listen and write) ----------
  function dictation(step, ctx) {
    const it = step.item;
    const T = ctx.T;
    const answer = tgt(it, ctx);
    const check = () => {
      if (!ti.input.value.trim()) return;
      let ok, close = false;
      if (it._type === "phrase") {
        const cmp = U.compareWords(ti.input.value, answer, T);
        const r = U.checkAnswer(ti.input.value, answer, { lang: T, acceptTypos: true });
        ok = r.ok || cmp.score >= 0.999;
        close = ok && U.normalize(ti.input.value) !== U.normalize(answer);
      } else {
        const r = U.checkAnswer(ti.input.value, answer, { lang: T, loose: true, splitAlternatives: true, acceptTypos: true });
        ok = r.ok; close = r.ok && U.normalize(ti.input.value, { lang: T, loose: true }) !== U.normalize(r.best, { lang: T, loose: true });
      }
      ti.input.disabled = true;
      ctx.finish({ correct: ok, close, answer, answerLang: T, sub: hlp(it, ctx), typed: ti.input.value });
    };
    const ti = typeInput(ctx, check);
    ti.input.addEventListener("input", () => ctx.setCheck(!!ti.input.value.trim(), check));
    ctx.setCheck(false, check);
    autoplay(answer, T, ctx, 300);
    return h("div.ex.dictation",
      prompt(t("q_dictation")),
      h("div.listen-prompt", speakerBtn(answer, T, { big: true, withSlow: true })),
      ti.input, ti.extra,
      h("button.link-btn", { type: "button", onclick: () => ctx.finish({ correct: false, answer, answerLang: T, sub: hlp(it, ctx), gaveUp: true }) }, t("dontKnow")));
  }

  // ---------- speaking (speech recognition) ----------
  function micWidget(expected, lang, ctx, onResult) {
    const out = h("div.mic-result", { "aria-live": "polite" });
    const btn = h("button.mic-btn", { type: "button", "aria-label": t("tapToSpeak") }, h("span.mic-icon", "🎤"), h("span.mic-label", t("tapToSpeak")));
    let busy = false;
    btn.addEventListener("click", async () => {
      if (busy) return;
      if (!SP.canListen()) { out.textContent = t("noSpeech"); onResult(null); return; }
      busy = true;
      btn.classList.add("listening");
      btn.querySelector(".mic-label").textContent = t("listening");
      const res = await SP.listen(lang);
      busy = false;
      btn.classList.remove("listening");
      btn.querySelector(".mic-label").textContent = t("tryAgain");
      out.innerHTML = "";
      if (!res.ok) {
        out.appendChild(h("div.muted", res.error === "not-allowed" || res.error === "service-not-allowed" ? t("micDenied") : t("notHeard")));
        onResult({ score: 0, error: res.error });
        return;
      }
      const m = SP.bestMatch(res.alternatives, expected, lang);
      out.appendChild(h("div.heard", h("span.muted", t("youSaid") + " "), L(m.heard, lang)));
      out.appendChild(h("div.word-marks", { dir: "ltr" }, m.words.map((w) => h("span." + (w.ok ? "ok" : "miss"), w.w))));
      onResult(m);
    });
    return { btn, out };
  }

  function speak(step, ctx) {
    const it = step.item;
    const T = ctx.T;
    const expected = tgt(it, ctx);
    let tries = 0;
    const msg = h("div.speak-msg");
    const w = micWidget(expected, T, ctx, (m) => {
      if (m === null) { ctx.setCheck(true, () => ctx.finish({ correct: null, skipped: true }), t("skip")); return; }
      tries++;
      if (m.score >= 0.8) {
        msg.textContent = m.score >= 0.99 ? t("perfect") : t("great");
        msg.className = "speak-msg good";
        ctx.finish({ correct: true, answer: expected, answerLang: T, sub: hlp(it, ctx), silentAnswer: true });
      } else {
        msg.textContent = t("keepTrying");
        msg.className = "speak-msg meh";
        if (tries >= 3) ctx.setCheck(true, () => ctx.finish({ correct: null, skipped: true, answer: expected, answerLang: T }), t("next"));
      }
    });
    ctx.setCheck(true, () => ctx.finish({ correct: null, skipped: true }), t("skip"));
    return h("div.ex.speak",
      prompt(t("q_speak")),
      h("div.target-word" + (it._type === "phrase" ? ".phrase" : ""), L(expected, T), speakerBtn(expected, T, { withSlow: true })),
      transliterationLine(it, ctx),
      h("div.help-word", L(hlp(it, ctx), ctx.H)),
      SP.canListen() ? w.btn : h("div.notice", t("noSpeech")),
      w.out, msg);
  }

  // ---------- match pairs ----------
  function match(step, ctx) {
    const items = step.items.slice(0, 5);
    const T = ctx.T, H = ctx.H;
    const left = U.shuffle(items), right = U.shuffle(items);
    let sel = null, mistakes = 0, matched = 0;
    const grid = h("div.match-grid");
    const colL = h("div.match-col"), colR = h("div.match-col");
    const mk = (it, side) => {
      const text = side === "L" ? tgt(it, ctx) : hlp(it, ctx);
      const b = h("button.option.match-item", { type: "button", "data-id": it.id, "data-side": side }, L(text, side === "L" ? T : H));
      b.addEventListener("click", () => {
        if (b.classList.contains("done")) return;
        if (side === "L") SP.speak(tgt(it, ctx), T, { rate: ctx.rate });
        if (!sel || sel.dataset.side === side) {
          if (sel) sel.classList.remove("sel");
          sel = b; b.classList.add("sel");
          return;
        }
        if (sel.dataset.id === b.dataset.id) {
          sel.classList.remove("sel");
          sel.classList.add("done"); b.classList.add("done");
          matched++;
          sel = null;
          if (matched === items.length) {
            ctx.finish({ correct: mistakes <= 1, matchIds: items.map((x) => x.id), mistakes, silentAnswer: true });
          }
        } else {
          mistakes++;
          const other = sel;
          b.classList.add("wrong"); other.classList.add("wrong");
          setTimeout(() => { b.classList.remove("wrong"); other.classList.remove("wrong", "sel"); }, 500);
          sel = null;
        }
      });
      return b;
    };
    left.forEach((it) => colL.appendChild(mk(it, "L")));
    right.forEach((it) => colR.appendChild(mk(it, "R")));
    grid.append(colL, colR);
    ctx.setCheck(false);
    return h("div.ex.match", prompt(t("q_match")), grid);
  }

  // ---------- sentence builder (word tiles) ----------
  function tilesWidget(answer, lang, distractorPool, onChange) {
    const tokens = U.tokenize(answer);
    const extra = U.sample((distractorPool || []).filter((w) => !tokens.map((x) => U.normalize(x)).includes(U.normalize(w))), tokens.length > 6 ? 1 : 2);
    const bank = U.shuffle(tokens.concat(extra));
    const placed = [];
    const line = h("div.tiles-line", { dir: lang === "he" ? "rtl" : "ltr" });
    const bankEl = h("div.tiles-bank", { dir: lang === "he" ? "rtl" : "ltr" });
    const render = () => {
      line.innerHTML = ""; bankEl.innerHTML = "";
      placed.forEach((idx, pos) => line.appendChild(h("button.tile", { type: "button", lang, onclick: () => { placed.splice(pos, 1); render(); } }, bank[idx])));
      bank.forEach((w, idx) => {
        const used = placed.includes(idx);
        bankEl.appendChild(h("button.tile" + (used ? ".used" : ""), { type: "button", lang, disabled: used, onclick: () => { placed.push(idx); render(); SP.speak(w, lang, { rate: 1 }); } }, w));
      });
      onChange(placed.map((i) => bank[i]).join(" "));
    };
    render();
    return { el: h("div.tiles", line, bankEl), value: () => placed.map((i) => bank[i]).join(" "), lock: () => { line.classList.add("locked"); bankEl.classList.add("locked"); [...line.children, ...bankEl.children].forEach((b) => (b.disabled = true)); } };
  }

  function wordPool(it, ctx) {
    const pool = [];
    C.phrases().filter((p) => p.id !== it.id && p[ctx.T]).slice(0, 400).forEach((p) => pool.push(...U.tokenize(p[ctx.T])));
    return U.sample(pool, 30);
  }

  function build(step, ctx, listenMode) {
    const it = step.item;
    const T = ctx.T, H = ctx.H;
    const answer = tgt(it, ctx);
    let tw;
    const check = () => {
      const ok = U.tilesKey(tw.value()) === U.tilesKey(answer);
      tw.lock();
      ctx.finish({ correct: ok, answer, answerLang: T, sub: hlp(it, ctx) });
    };
    tw = tilesWidget(answer, T, wordPool(it, ctx), (v) => ctx.setCheck(!!v, check));
    ctx.setCheck(false, check);
    if (listenMode) autoplay(answer, T, ctx, 300);
    return h("div.ex.build",
      prompt(t(listenMode ? "q_buildListen" : "q_build")),
      listenMode ? h("div.listen-prompt", speakerBtn(answer, T, { big: true, withSlow: true })) : h("div.help-prompt", L(hlp(it, ctx), H)),
      tw.el);
  }

  // ---------- letters ----------
  function letterIntro(step, ctx) {
    const l = step.letter;
    const T = ctx.T, H = ctx.H;
    const ex = l.example || {};
    const say = () => SP.speak(l.lower + "… " + (ex.word || ""), T, { rate: 0.75 });
    const el = h("div.ex.letter-intro",
      h("div.badge-new", "🔤 " + t("letters")),
      h("div.letter-big", { lang: T, dir: "ltr" }, h("span", l.upper), h("span.lower", l.lower), h("span.cursive", l.upper + l.lower)),
      h("div.row.center", speakerBtn(() => l.lower + "… " + (ex.word || ""), T, { withSlow: true })),
      l.name ? h("div.muted.center", h("span", t("name") + ": "), L(l.name, T)) : null,
      h("div.card.soft", h("b", t("sound") + ": "), L(pick(l.sound, [H]), H === "en" ? "en" : H)),
      ex.word ? h("div.card.soft.example-word", ex.emoji ? h("span.emoji", ex.emoji) : null, L(ex.word, T), " — ", L(pick(ex, [H]) || "", H), speakerBtn(ex.word, T)) : null,
      l.note ? h("div.small.muted", "✍️ ", L(pick(l.note, [H]), H)) : null);
    setTimeout(say, 300);
    ctx.setCheck(true, () => ctx.finish({ intro: true, correct: null, letter: l.upper }), t("gotIt"));
    return el;
  }

  function letterQuiz(step, ctx) {
    const l = step.letter;
    const T = ctx.T;
    const all = C.alphabet(T);
    const others = U.sample(all.filter((x) => x.upper !== l.upper), 3);
    const opts = U.shuffle([l].concat(others));
    const ex = l.example || {};
    let promptEl, title;
    if (step.mode === "word" && ex.word) {
      title = t("q_letterWord");
      promptEl = h("div.help-prompt", ex.emoji ? h("span.emoji", ex.emoji) : null, speakerBtn(ex.word, T, { big: true }), h("div.muted", L(pick(ex, [ctx.H]) || "", ctx.H)));
      autoplay(ex.word, T, ctx);
    } else {
      title = t("q_letterSound");
      promptEl = h("div.listen-prompt", speakerBtn(() => l.lower + "… " + (ex.word || ""), T, { big: true, withSlow: true }));
      autoplay(l.lower + "… " + (ex.word || ""), T, ctx);
    }
    let answered = false;
    const list = h("div.options.letters-opts");
    opts.forEach((o) => {
      const b = h("button.option.letter-opt", { type: "button", lang: T, dir: "ltr" }, o.upper + " " + o.lower);
      b.addEventListener("click", () => {
        if (answered) return;
        answered = true;
        const ok = o.upper === l.upper;
        b.classList.add(ok ? "right" : "wrong");
        if (!ok) [...list.children].forEach((x, i) => { if (opts[i].upper === l.upper) x.classList.add("right"); });
        ctx.finish({ correct: ok, letter: l.upper, answer: l.upper + " " + l.lower + (ex.word ? " — " + ex.word : ""), answerLang: T });
      });
      list.appendChild(b);
    });
    ctx.setCheck(false);
    return h("div.ex.letter-quiz", prompt(title), promptEl, list);
  }

  // ---------- grammar ----------
  function gExplainLang(ctx) { return ctx.H; }
  function qWithBlank(q, lang) {
    const parts = String(q).split("___");
    return h("div.gq", { lang, dir: "ltr" }, parts[0], parts.length > 1 ? h("span.blank", "____") : null, parts.slice(1).join("___"));
  }

  function gchoice(step, ctx) {
    const ex = step.ex;
    const T = ctx.T;
    let answered = false;
    const list = h("div.options");
    const correctText = ex.q.includes("___") ? ex.q.replace("___", ex.options[ex.answer]) : ex.options[ex.answer];
    ex.options.forEach((o, i) => {
      const b = h("button.option", { type: "button" }, L(o, T));
      b.addEventListener("click", () => {
        if (answered) return;
        answered = true;
        const ok = i === ex.answer;
        b.classList.add(ok ? "right" : "wrong");
        if (!ok) list.children[ex.answer].classList.add("right");
        ctx.finish({ correct: ok, answer: correctText, answerLang: T, why: pick(ex.why, [gExplainLang(ctx)]), sub: pick(ex.tr, [ctx.H]) });
      });
      list.appendChild(b);
    });
    ctx.setCheck(false);
    return h("div.ex.gchoice", prompt(t("q_choose")), qWithBlank(ex.q, T), ex.tr ? h("div.muted.small", L(pick(ex.tr, [ctx.H]), ctx.H)) : null, list);
  }

  function gfill(step, ctx, fixMode) {
    const ex = step.ex;
    const T = ctx.T;
    const answers = Array.isArray(ex.answer) ? ex.answer : [ex.answer];
    const fullAnswer = fixMode ? answers[0] : ex.q.replace("___", answers[0]);
    const check = () => {
      if (!ti.input.value.trim()) return;
      const r = U.checkAnswer(ti.input.value, answers, { lang: T, acceptTypos: fixMode });
      ti.input.disabled = true;
      ctx.finish({ correct: r.ok, close: r.ok && U.normalize(ti.input.value) !== U.normalize(r.best), answer: fullAnswer, answerLang: T, why: pick(ex.why, [gExplainLang(ctx)]), sub: pick(ex.tr, [ctx.H]), typed: ti.input.value });
    };
    const ti = typeInput(ctx, check);
    if (fixMode) ti.input.value = ex.q;
    ti.input.addEventListener("input", () => ctx.setCheck(!!ti.input.value.trim(), check));
    ctx.setCheck(!!ti.input.value, check);
    return h("div.ex.gfill",
      prompt(t(fixMode ? "q_fix" : "q_fill")),
      fixMode ? h("div.gq.wrong-sentence", { lang: T, dir: "ltr" }, "❌ " + ex.q) : qWithBlank(ex.q, T),
      ex.tr ? h("div.muted.small", L(pick(ex.tr, [ctx.H]), ctx.H)) : null,
      ti.input, ti.extra,
      h("button.link-btn", { type: "button", onclick: () => ctx.finish({ correct: false, answer: fullAnswer, answerLang: T, why: pick(ex.why, [gExplainLang(ctx)]), gaveUp: true }) }, t("dontKnow")));
  }

  function gorder(step, ctx) {
    const ex = step.ex;
    const T = ctx.T;
    let tw;
    const check = () => {
      const ok = U.tilesKey(tw.value()) === U.tilesKey(ex.answer);
      tw.lock();
      ctx.finish({ correct: ok, answer: ex.answer, answerLang: T, why: pick(ex.why, [gExplainLang(ctx)]), sub: pick(ex.tr, [ctx.H]) });
    };
    tw = tilesWidget(ex.answer, T, [], (v) => ctx.setCheck(!!v, check));
    ctx.setCheck(false, check);
    return h("div.ex.gorder", prompt(t("q_build")), ex.tr ? h("div.help-prompt", L(pick(ex.tr, [ctx.H]), ctx.H)) : null, tw.el);
  }

  const R = {
    intro, mc, type, dictation, speak, match, letterIntro, letterQuiz,
    build: (s, c) => build(s, c, false),
    buildListen: (s, c) => build(s, c, true),
    gchoice, gfill: (s, c) => gfill(s, c, false), gfix: (s, c) => gfill(s, c, true), gorder,
  };

  function render(step, ctx) {
    const fn = R[step.kind];
    if (!fn) throw new Error("unknown exercise " + step.kind);
    return fn(step, ctx);
  }

  root.LSEx = { render, micWidget, tilesWidget };
})(window);
