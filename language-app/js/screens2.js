// Content screens: alphabet, handwriting, vocabulary, phrases, grammar, pronunciation, dialogues.
(function (root) {
  const { h, L, speakerBtn, toast } = root.LSUI;
  const I = root.LSI18n;
  const { t, pick } = I;
  const ST = root.LSStore;
  const C = root.LSContent;
  const U = root.LSUtil;
  const SRS = root.LSSrs;
  const SP = root.LSSpeech;
  const D = () => root.LS_DATA || {};

  const Y = {
    shadow: { he: "חזרה בצל (Shadowing)", en: "Shadowing", ru: "Шэдоуинг (повтор за диктором)" },
    shadowSub: { he: "מקשיבים לשורה ומיד חוזרים עליה בקול, באותו קצב ומנגינה.", en: "Listen to a line and immediately repeat it out loud, with the same rhythm and melody.", ru: "Послушайте фразу и сразу повторите её вслух, в том же ритме и с той же интонацией." },
    youAreB: { he: "את/ה משחק/ת את 🙋 — האפליקציה משחקת את 🤖", en: "You play 🙋 — the app plays 🤖", ru: "Вы играете 🙋 — приложение играет 🤖" },
    start: { he: "התחלה", en: "Start", ru: "Начать" },
    lineOf: { he: "שורה", en: "Line", ru: "Реплика" },
    finished: { he: "סיימתם את השיחה!", en: "Conversation finished!", ru: "Диалог окончен!" },
    pairsQuiz: { he: "בוחן שמיעה: איזו מילה שמעת?", en: "Listening quiz: which word did you hear?", ru: "Тест на слух: какое слово вы услышали?" },
    writeWord: { he: "כתיבת מילה", en: "Write a word", ru: "Написать слово" },
    chooseLetter: { he: "בחרו אות לתרגול", en: "Choose a letter to practice", ru: "Выберите букву" },
    writingTip: { he: "כתבו עם האצבע על האות המטושטשת. אחר כך נסו בלי עזרה.", en: "Write with your finger over the faded letter. Then try without help.", ru: "Пишите пальцем поверх бледной буквы. Потом попробуйте без подсказки." },
    nextLetter: { he: "האות הבאה", en: "Next letter", ru: "Следующая буква" },
    allLetters: { he: "כל האותיות", en: "All letters", ru: "Все буквы" },
    phonics: { he: "צירופי אותיות וכללי קריאה", en: "Letter combinations & reading rules", ru: "Сочетания букв и правила чтения" },
    lettersQuizAll: { he: "בוחן על כל האותיות שלמדתי", en: "Quiz all letters I've met", ru: "Тест по всем изученным буквам" },
    grammarIntro: { he: "כל שיעור: הסבר קצר, דוגמאות עם שמע, ותרגול. 70% ומעלה = הושלם.", en: "Each lesson: short explanation, examples with audio, and practice. 70%+ = completed.", ru: "Каждый урок: короткое объяснение, примеры со звуком и практика. 70%+ = пройдено." },
    best: { he: "הכי טוב", en: "Best", ru: "Лучший" },
    study: { he: "ללמוד", en: "Study", ru: "Учить" },
    sentencesTab: { he: "משפטים", en: "Phrases", ru: "Фразы" },
    trainSounds: { he: "אמרו את המילים — האפליקציה תקשיב", en: "Say the words — the app will listen", ru: "Скажите слова — приложение послушает" },
  };
  const y = (k) => pick(Y[k]);

  // ---------- alphabet ----------
  function alphabet(app) {
    const p = app.profile();
    const prog = ST.progress(p.id);
    const al = C.alphabet(p.target);
    const groups = ((D().alphabetLessons || {})[p.target]) || [];
    const learnGroup = (g) => {
      const letters = g.map((u) => al.find((l) => l.upper === u)).filter(Boolean);
      const steps = [];
      letters.forEach((l) => steps.push({ kind: "letterIntro", letter: l }));
      U.shuffle(letters.concat(letters)).forEach((l, i) => steps.push({ kind: "letterQuiz", letter: l, mode: i % 2 ? "word" : "sound" }));
      root.LSSession.run({ steps, back: "#/alphabet" });
    };
    const quizAll = () => {
      const met = al.filter((l) => (prog.letters[l.upper] || {}).seen);
      const pool = met.length >= 4 ? met : al.slice(0, 8);
      const steps = U.sample(pool, Math.min(12, pool.length)).map((l, i) => ({ kind: "letterQuiz", letter: l, mode: i % 2 ? "word" : "sound" }));
      root.LSSession.run({ steps, back: "#/alphabet" });
    };
    const next = C.nextLetterGroup(prog, p.target);
    const state = (l) => { const s = prog.letters[l.upper] || {}; return s.right >= 2 ? "known" : s.seen ? "seen" : ""; };
    app.mount(h("div.page.alphabet",
      app.header(t("sec_alphabet"), "#/home"),
      next ? h("button.hero-card.small-hero", { type: "button", onclick: () => learnGroup(next) },
        h("div.hero-emoji", "🔤"), h("div.hero-text", h("div.hero-title", t("learnGroup")), h("div.hero-sub", { dir: "ltr", lang: p.target }, next.join("  "))), h("div.hero-go", "▶")) : null,
      h("button.btn.ghost.wide", { type: "button", onclick: quizAll }, "🎯 " + y("lettersQuizAll")),
      h("p.small.muted", t("tapLetter")),
      groups.map((g, gi) => h("div.letter-group",
        h("div.small.muted", t("group") + " " + (gi + 1)),
        h("div.letter-grid", { dir: "ltr" }, g.map((u) => { const l = al.find((z) => z.upper === u); if (!l) return null; return h("a.letter-tile." + (state(l) || "new"), { href: "#/letter/" + encodeURIComponent(u), lang: p.target }, h("span", l.upper + l.lower)); })),
        h("button.link-btn", { type: "button", onclick: () => learnGroup(g) }, "▶ " + t("learnGroup")))),
      phonicsBlock(p)));
  }

  function phonicsBlock(p) {
    const list = ((D().phonics || {})[p.target]) || [];
    if (!list.length) return null;
    return h("details.card.phonics",
      h("summary", h("b", "📏 " + y("phonics"))),
      list.map((ph) => h("div.phonics-row",
        h("b", { dir: "ltr", lang: p.target }, ph.combo),
        ph.example ? h("span", ph.emoji ? ph.emoji + " " : "", L(ph.example, p.target), speakerBtn(ph.example, p.target)) : null,
        h("div.small", L(pick(ph.sound, [p.help]), p.help)))));
  }

  function letterPage(app, args) {
    const p = app.profile();
    const al = C.alphabet(p.target);
    const u = args[0];
    const i = al.findIndex((l) => l.upper === u);
    const l = al[i];
    if (!l) return app.go("#/alphabet");
    const ex = l.example || {};
    app.mount(h("div.page.letter-page",
      app.header(l.upper + " " + l.lower, "#/alphabet"),
      h("div.letter-big", { lang: p.target, dir: "ltr" }, h("span", l.upper), h("span.lower", l.lower), h("span.cursive", l.upper + l.lower)),
      h("div.row.center", speakerBtn(() => l.lower + "… " + (ex.word || ""), p.target, { withSlow: true })),
      l.name ? h("div.center.muted", t("name") + ": ", L(l.name, p.target)) : null,
      h("div.card.soft", h("b", t("sound") + ": "), L(pick(l.sound, [p.help]), p.help)),
      ex.word ? h("div.card.soft.example-word", ex.emoji ? h("span.emoji", ex.emoji) : null, L(ex.word, p.target), " — ", L(pick(ex, [p.help]) || "", p.help), speakerBtn(ex.word, p.target)) : null,
      l.note ? h("div.card.soft", "✍️ ", L(pick(l.note, [p.help]), p.help)) : null,
      h("div.row.center",
        h("a.btn.primary", { href: "#/writing/" + encodeURIComponent(u) }, "✍️ " + t("trace")),
        al[i + 1] ? h("a.btn.ghost", { href: "#/letter/" + encodeURIComponent(al[i + 1].upper) }, y("nextLetter") + " " + al[i + 1].upper) : null)));
  }

  // ---------- handwriting ----------
  function writing(app, args) {
    const p = app.profile();
    const prog = ST.progress(p.id);
    const al = C.alphabet(p.target);
    if (!args[0]) {
      app.mount(h("div.page.writing",
        app.header(t("sec_writing"), "#/home"),
        h("p.muted", y("writingTip")),
        h("h3", y("chooseLetter")),
        h("div.letter-grid", { dir: "ltr" }, al.map((l) => {
          const best = (prog.letters[l.upper] || {}).best || 0;
          return h("a.letter-tile" + (best >= 70 ? ".known" : best ? ".seen" : ".new"), { href: "#/writing/" + encodeURIComponent(l.upper), lang: p.target }, h("span", l.upper + l.lower), best ? h("small", best + "") : null);
        })),
        h("h3", y("writeWord")),
        h("div.row.wrap", U.sample(C.vocab().filter((v) => v[p.target] && !/\s/.test(v[p.target]) && U.stripStress(v[p.target]).length <= 6 && v.emoji), 8).map((v) => h("a.chip-btn", { href: "#/writing/word:" + encodeURIComponent(v.id) }, v.emoji + " " + U.stripStress(v[p.target]))))));
      return;
    }
    let mode = "trace", style = "print";
    let text, label, sayText, idx = -1, wordItem = null;
    if (args[0].startsWith("word:")) {
      wordItem = C.item(args[0].slice(5));
      if (!wordItem) return app.go("#/writing");
      text = U.stripStress(wordItem[p.target]);
      label = (wordItem.emoji || "") + " " + (wordItem[p.help] || "");
      sayText = wordItem[p.target];
    } else {
      idx = al.findIndex((l) => l.upper === args[0]);
      const l = al[idx];
      if (!l) return app.go("#/writing");
      text = l.upper + l.lower;
      label = (l.example && l.example.emoji ? l.example.emoji + " " : "") + ((l.example && l.example.word) || "");
      sayText = l.lower + "… " + ((l.example && l.example.word) || "");
    }
    const size = Math.min(340, window.innerWidth - 40);
    const pad = root.LSWriting.tracePad({ text, size, style });
    const model = h("div.model-text", { dir: "ltr", lang: p.target }, text);
    model.hidden = true;
    const scoreEl = h("div.trace-score", { "aria-live": "polite" });
    const modeLbl = h("div.ex-title", t("trace"));
    const setStyle = (s) => { style = s; pad.setStyle(s); model.style.fontFamily = root.LSWriting.FONTS[s]; styleBtns.forEach((b) => b.classList.toggle("on", b.dataset.s === s)); };
    const styleBtns = [["print", t("printed")], ["cursive", t("cursive")]].map(([s, lbl]) => h("button.seg-btn" + (s === style ? ".on" : ""), { type: "button", "data-s": s, onclick: () => setStyle(s) }, lbl));
    const done = () => {
      if (!pad.hasInk()) return;
      const sc = pad.score();
      scoreEl.textContent = `${t("score")}: ${sc}/100 ` + (sc >= 80 ? "🌟" : sc >= 60 ? "👍" : "✏️");
      if (idx >= 0) {
        const ls = prog.letters[al[idx].upper] || (prog.letters[al[idx].upper] = { seen: 1, right: 0, wrong: 0 });
        ls.traced = (ls.traced || 0) + 1;
        ls.best = Math.max(ls.best || 0, mode === "write" ? sc : Math.round(sc * 0.8));
        ST.saveProgress(p.id);
      }
      ST.addXp(p.id, sc >= 60 ? 5 : 2);
      if (mode === "trace" && sc >= 55) {
        setTimeout(() => {
          mode = "write"; modeLbl.textContent = t("traceWrite"); pad.setGuide(false); pad.clear(); model.hidden = false;
        }, 900);
      }
    };
    app.mount(h("div.page.trace-page",
      app.header(text, "#/writing"),
      h("div.row.center", h("div.seg", styleBtns), speakerBtn(sayText, p.target)),
      modeLbl,
      h("div.small.muted.center", label),
      model,
      h("div.trace-wrap", pad.el),
      scoreEl,
      h("div.row.center",
        h("button.btn.ghost", { type: "button", onclick: () => { pad.clear(); scoreEl.textContent = ""; } }, "🧽 " + t("clear")),
        h("button.btn.primary", { type: "button", onclick: done }, "✓ " + t("done")),
        idx >= 0 && al[idx + 1] ? h("a.btn.ghost", { href: "#/writing/" + encodeURIComponent(al[idx + 1].upper) }, y("nextLetter") + " →") : null),
      h("button.link-btn", { type: "button", onclick: () => { mode = "trace"; modeLbl.textContent = t("trace"); pad.setGuide(true); pad.clear(); model.hidden = true; } }, "↺ " + t("trace"))));
    // re-render once web fonts have loaded so the guide uses the right shape
    if (document.fonts && document.fonts.ready) document.fonts.ready.then(() => pad.redraw());
    if (document.fonts && document.fonts.load) document.fonts.load('40px "Marck Script"').then(() => pad.redraw()).catch(() => {});
  }

  // ---------- vocabulary ----------
  function words(app) {
    const p = app.profile();
    const prog = ST.progress(p.id);
    const topics = (D().topics || []).filter((tp) => C.vocab().some((v) => v.topic === tp.id));
    app.mount(h("div.page.words",
      app.header(t("sec_words"), "#/home"),
      h("div.topic-grid", topics.map((tp) => {
        const all = C.vocab().filter((v) => v.topic === tp.id);
        const seen = all.filter((v) => prog.cards[v.id]).length;
        const mastered = all.filter((v) => SRS.isMastered(prog.cards[v.id])).length;
        return h("a.topic-tile", { href: "#/topic/" + tp.id },
          h("span.tt-emoji", tp.emoji), h("span.tt-name", pick(tp)),
          h("div.mini-bar.two", h("i.m", { style: { width: (mastered / all.length) * 100 + "%" } }), h("i.s", { style: { width: ((seen - mastered) / all.length) * 100 + "%" } })),
          h("small.muted", `${seen}/${all.length}`));
      }))));
  }

  function topic(app, args) {
    const p = app.profile();
    const prog = ST.progress(p.id);
    const tp = (D().topics || []).find((z) => z.id === args[0]);
    if (!tp) return app.go("#/words");
    const list = C.vocab().filter((v) => v.topic === tp.id).map((v) => C.item(v.id));
    const start = () => { const plan = C.buildTopic(p, prog, tp.id, { canListen: SP.canListen() }); root.LSSession.run({ steps: plan.steps, back: "#/topic/" + tp.id }); };
    const status = (it) => { const c = prog.cards[it.id]; return SRS.isMastered(c) ? "mastered" : c ? "learning" : "new"; };
    app.mount(h("div.page.topic",
      app.header(tp.emoji + " " + pick(tp), "#/words"),
      h("div.row",
        h("button.btn.primary", { type: "button", onclick: start }, "▶ " + t("learnTopic")),
        h("a.btn.ghost", { href: `#/reels/topic/${tp.id}` }, "🎬 Reels")),
      h("h3", t("allWords")),
      h("div.word-list", list.map((it) => h("div.word-row." + status(it),
        h("span.wr-emoji", it.emoji || "•"),
        h("div.wr-main",
          h("div", L(it[p.target], p.target, "strong"), p.target === "ru" && it.g ? h("small.muted", " (" + t("g_" + it.g) + ")") : null),
          p.target === "ru" && p.translit ? h("div.translit.small", "[" + C.translitStress(it[p.target]) + "]") : null,
          h("div.muted.small", L(it[p.help] || "", p.help))),
        speakerBtn(it[p.target], p.target),
        h("span.status-dot", { title: t(status(it) === "mastered" ? "mastered" : status(it) === "learning" ? "learning" : "notStarted") }))))));
  }

  // ---------- phrases ----------
  function phrases(app) {
    const p = app.profile();
    const prog = ST.progress(p.id);
    const sits = (D().situations || []).filter((s) => C.phrases().some((ph) => ph.sit === s.id));
    app.mount(h("div.page.phrases",
      app.header(t("sec_phrases"), "#/home"),
      h("div.topic-grid", sits.map((s) => {
        const all = C.phrases().filter((ph) => ph.sit === s.id);
        const seen = all.filter((ph) => prog.cards[ph.id]).length;
        return h("a.topic-tile", { href: "#/situation/" + s.id }, h("span.tt-emoji", s.emoji), h("span.tt-name", pick(s)),
          h("div.mini-bar", h("i", { style: { width: (seen / all.length) * 100 + "%" } })), h("small.muted", `${seen}/${all.length}`));
      }))));
  }

  function situation(app, args) {
    const p = app.profile();
    const prog = ST.progress(p.id);
    const s = (D().situations || []).find((z) => z.id === args[0]);
    if (!s) return app.go("#/phrases");
    const list = C.phrases().filter((ph) => ph.sit === s.id);
    const start = () => { const plan = C.buildSituation(p, prog, s.id, { canListen: SP.canListen() }); root.LSSession.run({ steps: plan.steps, back: "#/situation/" + s.id }); };
    app.mount(h("div.page",
      app.header(s.emoji + " " + pick(s), "#/phrases"),
      h("div.row", h("button.btn.primary", { type: "button", onclick: start }, "▶ " + t("practice")), h("a.btn.ghost", { href: `#/reels/sit/${s.id}` }, "🎬 Reels")),
      h("div.word-list", list.map((ph) => h("div.word-row.phrase-row" + (prog.cards[ph.id] ? ".learning" : ".new"),
        h("div.wr-main", h("div", L(ph[p.target], p.target, "strong")), h("div.muted.small", L(ph[p.help] || "", p.help))),
        speakerBtn(ph[p.target], p.target, { withSlow: true }))))));
  }

  // ---------- grammar ----------
  function grammarList(app) {
    const p = app.profile();
    const prog = ST.progress(p.id);
    const list = (D().grammar || []).filter((g) => g.target === p.target).sort((a, b) => (a.order || 0) - (b.order || 0));
    app.mount(h("div.page.grammar",
      app.header(t("sec_grammar"), "#/home"),
      h("p.small.muted", y("grammarIntro")),
      h("div.lesson-list", list.map((g, i) => {
        const r = prog.grammar[g.id] || {};
        const done = r.best >= 0.7;
        return h("a.lesson-row" + (done ? ".done" : ""), { href: "#/grammar/" + g.id },
          h("span.lesson-num", done ? "✓" : String(i + 1)),
          h("div", h("b", pick(g.title, [p.ui, p.help])), r.best != null ? h("div.small.muted", `${y("best")}: ${Math.round(r.best * 100)}%`) : null));
      }))));
  }

  function grammarLesson(app, args) {
    const p = app.profile();
    const prog = ST.progress(p.id);
    const g = (D().grammar || []).find((z) => z.id === args[0]);
    if (!g) return app.go("#/grammar");
    const exLang = g.explain[p.help] ? p.help : g.explain[p.ui] ? p.ui : Object.keys(g.explain)[0];
    const practice = () => {
      const exs = U.shuffle(g.exercises || []);
      const steps = exs.map((ex) => ({ kind: { choice: "gchoice", fill: "gfill", order: "gorder", fix: "gfix" }[ex.type] || "gchoice", ex }));
      let right = 0, total = 0;
      root.LSSession.run({
        steps, back: "#/grammar/" + g.id,
        onResult: (step, ok) => { if (!step.requeued) { total++; if (ok) right++; } },
        onComplete: () => {
          const score = total ? right / total : 0;
          const r = prog.grammar[g.id] || {};
          prog.grammar[g.id] = { best: Math.max(r.best || 0, score), done: (r.done || 0) + 1, last: Date.now() };
          ST.saveProgress(p.id);
        },
      });
    };
    app.mount(h("div.page.grammar-lesson",
      app.header(pick(g.title, [p.ui, p.help]), "#/grammar"),
      h("div.card.explain", { lang: exLang, dir: exLang === "he" ? "rtl" : "ltr" }, h("h3", t("explanation")), h("div", { html: g.explain[exLang] || "" })),
      g.examples && g.examples.length ? h("div.card",
        h("h3", t("examples")),
        g.examples.map((e) => h("div.example-row",
          h("div", L(e.t, p.target, "strong"), speakerBtn(e.t, p.target)),
          h("div.muted.small", L(pick(e, [p.help]) || "", p.help))))) : null,
      h("button.btn.primary.wide", { type: "button", onclick: practice }, "✏️ " + t("practice") + ` (${(g.exercises || []).length})`)));
  }

  // ---------- pronunciation ----------
  function soundsList(app) {
    const p = app.profile();
    const prog = ST.progress(p.id);
    const list = ((D().sounds || {})[p.target]) || [];
    app.mount(h("div.page.sounds",
      app.header(t("sec_sounds"), "#/home"),
      h("div.lesson-list", list.map((s) => h("a.lesson-row" + ((prog.sounds[s.id] || {}).done ? ".done" : ""), { href: "#/sound/" + s.id },
        h("span.lesson-num", "👄"), h("div", h("b", pick(s.title, [p.help])))))),
      h("div.card",
        h("h3", "🎙️ " + y("shadow")),
        h("p.small", y("shadowSub")),
        h("a.btn.ghost", { href: "#/dialogues" }, t("sec_dialogues")))));
  }

  function soundPage(app, args) {
    const p = app.profile();
    const prog = ST.progress(p.id);
    const s = (((D().sounds || {})[p.target]) || []).find((z) => z.id === args[0]);
    if (!s) return app.go("#/sounds");
    const T = p.target;
    const markDone = () => { prog.sounds[s.id] = Object.assign({}, prog.sounds[s.id], { done: true }); ST.saveProgress(p.id); };
    // minimal-pair listening quiz
    const quizBox = h("div");
    const pairQuiz = () => {
      const pairs = U.shuffle(s.pairs || []);
      let i = 0, right = 0;
      const one = () => {
        quizBox.innerHTML = "";
        if (i >= pairs.length) { quizBox.appendChild(h("div.notice", `${right}/${pairs.length} ${right === pairs.length ? "🌟" : "👍"}`)); markDone(); ST.addXp(p.id, right * 3); return; }
        const pair = pairs[i];
        const target = pair[Math.random() < 0.5 ? 0 : 1];
        SP.speak(target, T, { rate: app.ttsRate(), vary: true });
        let answered = false;
        quizBox.appendChild(h("div.card",
          h("div.small.muted", `${i + 1}/${pairs.length} · ${t("whichDidYouHear")}`),
          h("div.row.center", speakerBtn(target, T, { withSlow: true })),
          h("div.options.two", pair.map((w) => h("button.option", { type: "button", onclick: (e) => {
            if (answered) return; answered = true;
            const ok = w === target; if (ok) right++;
            e.currentTarget.classList.add(ok ? "right" : "wrong");
            setTimeout(() => { i++; one(); }, ok ? 700 : 1500);
          } }, L(w, T))))));
      };
      one();
    };
    app.mount(h("div.page.sound-page",
      app.header(pick(s.title, [p.help]), "#/sounds"),
      h("div.card.soft", h("b", "💡 " + t("tip") + ": "), L(pick(s.tip, [p.help]), p.help)),
      s.pairs && s.pairs.length ? h("div.card",
        h("h3", t("minimalPairs")),
        s.pairs.map((pair) => h("div.pair-row", pair.map((w) => h("span.pair-word", L(w, T, "strong"), speakerBtn(w, T, { withSlow: true }))))),
        h("button.btn.primary", { type: "button", onclick: pairQuiz }, "🎧 " + y("pairsQuiz")),
        quizBox) : null,
      h("div.card",
        h("h3", t("practiceWords")),
        h("p.small.muted", y("trainSounds")),
        (s.words || []).map((w) => {
          const mw = root.LSEx.micWidget(w, T, {}, (m) => { if (m && m.score >= 0.8) { markDone(); ST.addXp(p.id, 3); } });
          mw.btn.classList.add("small-mic");
          return h("div.practice-row", h("div.row", L(w, T, "strong"), speakerBtn(w, T, { withSlow: true }), SP.canListen() ? mw.btn : null), mw.out);
        }))));
  }

  // ---------- dialogues ----------
  function dialoguesList(app) {
    const p = app.profile();
    const prog = ST.progress(p.id);
    const list = (D().dialogues || []).slice().sort((a, b) => (a.level || 1) - (b.level || 1));
    app.mount(h("div.page.dialogues",
      app.header(t("sec_dialogues"), "#/home"),
      h("p.small.muted", y("shadowSub")),
      h("div.lesson-list", list.map((d) => h("a.lesson-row" + ((prog.dialogues[d.id] || {}).done ? ".done" : ""), { href: "#/dialogue/" + d.id },
        h("span.lesson-num", d.emoji || "💬"),
        h("div", h("b", pick(d.title, [p.ui, p.help])), h("div.small.muted", L(d.title[p.target] || "", p.target)), h("div.small.muted", t("level") + " " + (d.level || 1))))))));
  }

  function dialoguePage(app, args) {
    const p = app.profile();
    const prog = ST.progress(p.id);
    const d = (D().dialogues || []).find((z) => z.id === args[0]);
    if (!d) return app.go("#/dialogues");
    const T = p.target, H = p.help;
    let showTr = true, hide = false, stopFlag = false;
    const linesBox = h("div.chat");
    const renderLines = (active) => {
      linesBox.innerHTML = "";
      d.lines.forEach((ln, i) => {
        linesBox.appendChild(h("div.bubble." + (ln.who === "B" ? "me" : "bot") + (i === active ? ".active" : ""),
          h("span.who", ln.who === "B" ? "🙋" : "🤖"),
          h("div.bubble-body",
            h("div", hide && ln.who === "B" && i >= (active == null ? 0 : active) ? h("span.hidden-text", "• • •") : L(ln[T], T, "strong"), speakerBtn(ln[T], T, { withSlow: true })),
            showTr ? h("div.small.muted", L(ln[H] || "", H)) : null)));
      });
    };
    renderLines(null);
    const playAll = async () => {
      stopFlag = false;
      for (let i = 0; i < d.lines.length && !stopFlag; i++) {
        renderLines(i);
        await SP.speak(d.lines[i][T], T, { rate: app.ttsRate() });
        await new Promise((r) => setTimeout(r, 400));
      }
      renderLines(null);
    };
    const stage = h("div");
    const roleplay = () => {
      stopFlag = true; SP.stop();
      let i = 0, scoreSum = 0, count = 0;
      const step = async () => {
        stage.innerHTML = "";
        if (i >= d.lines.length) {
          renderLines(null);
          const avg = count ? scoreSum / count : 1;
          prog.dialogues[d.id] = { done: true, best: Math.max((prog.dialogues[d.id] || {}).best || 0, avg) };
          ST.saveProgress(p.id); ST.addXp(p.id, 15);
          stage.appendChild(h("div.card.center", h("div.big-emoji", "🎭"), h("h3", y("finished")), count ? h("div", t("score") + ": " + Math.round(avg * 100) + "%") : null));
          root.LSUI.confetti();
          return;
        }
        const ln = d.lines[i];
        renderLines(i);
        const el = [...linesBox.children][i];
        if (el) el.scrollIntoView({ block: "center", behavior: "smooth" });
        if (ln.who === "A") {
          await SP.speak(ln[T], T, { rate: app.ttsRate() });
          i++; setTimeout(step, 350);
          return;
        }
        const nextBtn = h("button.btn.ghost", { type: "button", onclick: () => { i++; step(); } }, t("next") + " ⏭");
        const mw = root.LSEx.micWidget(ln[T], T, {}, (m) => {
          if (m === null) return;
          if (m.score >= 0.7) { scoreSum += m.score; count++; setTimeout(() => { i++; step(); }, 1100); }
        });
        stage.appendChild(h("div.card.your-turn",
          h("b", t("yourTurn")),
          h("div.big-line", L(ln[T], T), speakerBtn(ln[T], T, { withSlow: true })),
          showTr ? h("div.small.muted", L(ln[H] || "", H)) : null,
          SP.canListen() ? mw.btn : h("div.notice", t("noSpeech")), mw.out, nextBtn));
      };
      step();
    };
    const trBox = h("input", { type: "checkbox", checked: true });
    trBox.addEventListener("change", () => { showTr = trBox.checked; renderLines(null); });
    const hideBox = h("input", { type: "checkbox" });
    hideBox.addEventListener("change", () => { hide = hideBox.checked; renderLines(null); });
    app.onLeave(() => { stopFlag = true; SP.stop(); SP.cancelListen(); });
    app.mount(h("div.page.dialogue",
      app.header((d.emoji || "") + " " + pick(d.title, [p.ui, p.help]), "#/dialogues"),
      h("div.row.wrap",
        h("button.btn.ghost", { type: "button", onclick: playAll }, "▶ " + t("playAll")),
        h("button.btn.primary", { type: "button", onclick: roleplay }, "🎭 " + t("roleplay"))),
      h("div.small.muted", y("youAreB")),
      h("div.row.wrap.small", h("label.check-row", trBox, " ", t("showTranslation")), h("label.check-row", hideBox, " ", t("hideText"))),
      linesBox, stage));
  }

  Object.assign(root.LSScreens.routes, {
    alphabet: (app) => alphabet(app),
    letter: (app, a) => letterPage(app, a),
    writing: (app, a) => writing(app, a),
    words: (app) => words(app),
    topic: (app, a) => topic(app, a),
    phrases: (app) => phrases(app),
    situation: (app, a) => situation(app, a),
    grammar: (app, a) => (a[0] ? grammarLesson(app, a) : grammarList(app)),
    sounds: (app) => soundsList(app),
    sound: (app, a) => soundPage(app, a),
    dialogues: (app) => dialoguesList(app),
    dialogue: (app, a) => dialoguePage(app, a),
  });
})(window);
