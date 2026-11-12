// Main screens: profiles, home, learn hub, progress, settings, family.
(function (root) {
  const { h, L, toast, confirmBox, speakerBtn } = root.LSUI;
  const I = root.LSI18n;
  const { t, pick } = I;
  const ST = root.LSStore;
  const C = root.LSContent;
  const U = root.LSUtil;
  const SRS = root.LSSrs;
  const SP = root.LSSpeech;

  const X = {
    alphabetFirst: { he: "מתחילים מהאותיות", en: "Start with the letters", ru: "Начнём с букв" },
    alphabetFirstSub: { he: "קודם לומדים לקרוא — זה הבסיס להכול. האותיות משולבות גם בשיעור היומי.", en: "First learn to read — it's the base for everything. Letters are also mixed into the daily lesson.", ru: "Сначала научимся читать — это основа всего. Буквы также входят в урок дня." },
    reelsCard: { he: "רילס — לומדים בגלילה", en: "Reels — learn by swiping", ru: "Рилсы — учимся листая" },
    reelsCardSub: { he: "כמו טיקטוק, אבל כל סרטון מלמד מילה", en: "Like TikTok, but every card teaches a word", ru: "Как ТикТок, но каждая карточка учит слову" },
    bedtime: { he: "חזרה לפני השינה 🌙", en: "Bedtime review 🌙", ru: "Повторение перед сном 🌙" },
    bedtimeSub: { he: "מחקרים מראים: חזרה קצרה לפני השינה עוזרת לזכור.", en: "Research shows a short review before sleep helps memory.", ru: "Исследования: короткое повторение перед сном помогает запомнить." },
    family: { he: "המשפחה", en: "Family", ru: "Семья" },
    familySub: { he: "בודקים אחד את השני — אמא יודעת רוסית, ואתה יודע אנגלית!", en: "Quiz each other — Mom knows Russian, and you know English!", ru: "Проверяйте друг друга — мама знает русский, а сын — английский!" },
    quizEachOther: { he: "בוחנים אחד את השני", en: "Quiz each other", ru: "Проверьте друг друга" },
    whoIsAsked: { he: "מי נבחן/ת?", en: "Who is being quizzed?", ru: "Кого проверяем?" },
    askerReads: { he: "הבוחן/ת שואל/ת בקול:", en: "The quizzer asks out loud:", ru: "Проверяющий спрашивает вслух:" },
    howSay: { he: "איך אומרים ב{lang}:", en: "How do you say in {lang}:", ru: "Как сказать ({lang}):" },
    showAns: { he: "הצגת התשובה (רק לבוחן/ת!)", en: "Show answer (quizzer only!)", ru: "Показать ответ (только проверяющему!)" },
    gotRight: { he: "ענה/תה נכון", en: "Got it right", ru: "Ответил(а) верно" },
    gotWrong: { he: "עוד לא", en: "Not yet", ru: "Пока нет" },
    needWords: { he: "צריך קודם ללמוד כמה מילים כדי שיהיה מה לבחון.", en: "Learn some words first so there's something to quiz.", ru: "Сначала выучите несколько слов, чтобы было что проверять." },
    needTwo: { he: "הוסיפו עוד לומד/ת כדי לבחון אחד את השני.", en: "Add another learner to quiz each other.", ru: "Добавьте ещё одного ученика, чтобы проверять друг друга." },
    welcome: { he: "ברוכים הבאים!", en: "Welcome!", ru: "Добро пожаловать!" },
    chooseUi: { he: "בחרו שפה:", en: "Choose a language:", ru: "Выберите язык:" },
    translit: { he: "להראות תעתיק לטיני למילים ברוסית", en: "Show Latin transliteration for Russian words", ru: "Показывать латинскую транслитерацию" },
    largeText: { he: "טקסט גדול", en: "Large text", ru: "Крупный текст" },
    onScreenKb: { he: "מקלדת על המסך בתרגילי כתיבה", en: "On-screen keyboard for typing", ru: "Экранная клавиатура" },
    sessionDone: { he: "שיעורים היום", en: "Lessons today", ru: "Уроков сегодня" },
    lettersProgress: { he: "אותיות", en: "Letters", ru: "Буквы" },
    grammarDone: { he: "שיעורי דקדוק", en: "Grammar lessons", ru: "Уроки грамматики" },
    about: { he: "על האפליקציה", en: "About", ru: "О приложении" },
    voices: { he: "קולות במכשיר", en: "Voices on this device", ru: "Голоса на устройстве" },
    yes: { he: "יש", en: "yes", ru: "есть" },
    no: { he: "אין", en: "none", ru: "нет" },
    mic: { he: "זיהוי דיבור", en: "Speech recognition", ru: "Распознавание речи" },
  };
  const x = (k, v) => { let s = pick(X[k]); if (v) Object.keys(v).forEach((kk) => (s = s.split("{" + kk + "}").join(v[kk]))); return s; };

  const AVATARS = ["👩", "👩‍🦰", "👵", "👨", "🧑", "👦", "👧", "🧔", "🦊", "🐱", "🌻", "⭐"];

  // ---------- profiles ----------
  function profiles(app) {
    const list = ST.profiles();
    const langBtns = h("div.row.center.wrap", ["he", "ru", "en"].map((l) => h("button.chip-btn" + (I.getLang() === l ? ".on" : ""), { type: "button", onclick: () => { I.setLang(l); document.documentElement.dir = l === "he" ? "rtl" : "ltr"; app.mount(profiles(app), { full: true }); } }, { he: "עברית", ru: "Русский", en: "English" }[l])));
    const preset = (p) => () => { const prof = ST.createProfile(p); app.setProfile(prof); app.go("#/home"); };
    const el = h("div.page.welcome",
      h("div.logo", "🗣️"),
      h("h1.center", t("appName")),
      h("p.center.muted", t("tagline")),
      langBtns,
      list.length ? h("h2", t("whoLearns")) : null,
      h("div.profile-list", list.map((p) => h("button.profile-card", { type: "button", onclick: () => { app.setProfile(p); app.go("#/home"); } },
        h("span.avatar", p.avatar), h("span.pname", p.name), h("span.ptarget", (p.target === "en" ? "🇬🇧 " : "🇷🇺 ") + t("lang_" + p.target)), h("span.pstreak", "🔥 " + ST.streak(p.id))))),
      !list.length ? h("div",
        h("h2", t("quickSetup")),
        h("button.preset", { type: "button", onclick: preset({ name: I.getLang() === "ru" ? "Мама" : I.getLang() === "en" ? "Mom" : "אמא", avatar: "👩", target: "en", ui: I.getLang() === "en" ? "he" : I.getLang(), help: I.getLang() === "ru" ? "ru" : "he", large: true }) }, h("span.avatar", "👩"), h("span", t("presetMom")), h("span.small.muted", "🇮🇱🇷🇺 → 🇬🇧")),
        h("button.preset", { type: "button", onclick: preset({ name: I.getLang() === "ru" ? "Я" : I.getLang() === "en" ? "Me" : "אני", avatar: "🧑", target: "ru", ui: I.getLang() === "ru" ? "he" : I.getLang(), help: I.getLang() === "en" ? "en" : "he", translit: true }) }, h("span.avatar", "🧑"), h("span", t("presetMe")), h("span.small.muted", "🇮🇱🇬🇧 → 🇷🇺"))) : null,
      h("button.btn.ghost.wide", { type: "button", onclick: () => app.go("#/setup") }, "➕ " + t("addLearner")));
    app.mount(el, { full: true });
  }

  function profileForm(app, existing) {
    const p = Object.assign({ name: "", avatar: "🙂", target: "en", ui: I.getLang(), help: "he", translit: false }, existing || {});
    const name = h("input.text-in", { type: "text", value: p.name, placeholder: t("name"), dir: "auto", maxlength: 24 });
    const avatarRow = h("div.row.wrap");
    const renderAv = () => { avatarRow.innerHTML = ""; AVATARS.forEach((a) => avatarRow.appendChild(h("button.av-btn" + (p.avatar === a ? ".on" : ""), { type: "button", onclick: () => { p.avatar = a; renderAv(); } }, a))); };
    renderAv();
    const seg = (key, opts, onChange) => {
      const row = h("div.seg");
      const render = () => { row.innerHTML = ""; opts().forEach((o) => row.appendChild(h("button.seg-btn" + (p[key] === o.v ? ".on" : ""), { type: "button", onclick: () => { p[key] = o.v; render(); onChange && onChange(); } }, o.label))); };
      render();
      row.rerender = render;
      return row;
    };
    let helpSeg;
    const fixHelp = () => {
      if (p.help === p.target) p.help = "he";
      helpSeg && helpSeg.rerender();
      translitRow.hidden = p.target !== "ru";
    };
    const targetSeg = seg("target", () => [{ v: "en", label: "🇬🇧 " + t("lang_en") }, { v: "ru", label: "🇷🇺 " + t("lang_ru") }], fixHelp);
    const uiSeg = seg("ui", () => [{ v: "he", label: "עברית" }, { v: "ru", label: "Русский" }, { v: "en", label: "English" }]);
    helpSeg = seg("help", () => ["he", "ru", "en"].filter((l) => l !== p.target).map((l) => ({ v: l, label: t("lang_" + l) })));
    const translitBox = h("input", { type: "checkbox" });
    translitBox.checked = !!p.translit;
    const translitRow = h("label.check-row", translitBox, " ", x("translit"));
    translitRow.hidden = p.target !== "ru";
    const save = () => {
      p.name = name.value.trim() || p.avatar;
      p.translit = translitBox.checked;
      let prof;
      if (existing) prof = ST.updateProfile(existing.id, p);
      else prof = ST.createProfile(p);
      app.setProfile(prof);
      app.go("#/home");
    };
    return h("div.page.form",
      app.header(existing ? t("edit") : t("addLearner"), existing ? "#/settings" : "#/who"),
      h("label.field", h("span", t("name")), name),
      h("div.field", h("span", t("avatar")), avatarRow),
      h("div.field", h("span", t("learnWhat")), targetSeg),
      h("div.field", h("span", t("uiLang")), uiSeg),
      h("div.field", h("span", t("helpLang")), helpSeg),
      translitRow,
      h("button.btn.primary.wide", { type: "button", onclick: save }, existing ? t("save") : t("start")));
  }

  // ---------- home ----------
  function home(app) {
    const p = app.profile();
    const prog = ST.progress(p.id);
    const st = C.stats(prog);
    const today = U.dayKey();
    const xpToday = prog.xp[today] || 0;
    const goal = p.dailyGoal || 50;
    const pct = Math.min(100, Math.round((xpToday / goal) * 100));
    const streak = ST.streak(p.id);
    const al = C.alphabet(p.target);
    const lettersKnown = C.lettersLearned(prog, p.target);
    const hour = new Date().getHours();
    const others = ST.profiles().filter((o) => o.id !== p.id);
    const newLeft = C.unseen(prog, C.curriculum()).length;

    const startDaily = () => {
      const plan = C.buildDaily(p, prog, { canListen: SP.canListen() });
      root.LSSession.run({ steps: plan.steps });
    };
    const startBedtime = () => {
      const due = C.dueCards(prog).slice(0, 12);
      const ids = due.length ? due : Object.keys(prog.cards).filter((id) => C.item(id)).sort((a, b) => prog.cards[b].last - prog.cards[a].last).slice(0, 10);
      const steps = U.shuffle(ids).map((id) => C.exerciseFor(C.item(id), prog.cards[id], { canListen: false }));
      root.LSSession.run({ steps });
    };

    const ring = h("div.ring", { style: { "--p": pct }, role: "img", "aria-label": `${t("goal")} ${pct}%` }, h("span", pct >= 100 ? "✓" : pct + "%"));
    const el = h("div.page.home",
      h("header.home-head",
        h("button.avatar-btn", { type: "button", onclick: () => app.go("#/who"), "aria-label": t("switchLearner") }, p.avatar),
        h("div", h("h1", t("hello", { name: "\u2068" + p.name + "\u2069" })), h("div.muted.small", (p.target === "en" ? "🇬🇧 " : "🇷🇺 ") + t("lang_" + p.target), " ", root.LSHabits.levelChip(p.id))),
        h("div.streak-pill" + (streak > 0 ? ".hot" : ""), { title: t("streak") }, "🔥 ", h("b", String(streak)))),
      h("div.goal-card.card",
        ring,
        h("div", h("div.small.muted", t("goal")), h("div.goal-num", `${xpToday} / ${goal} ${t("xp")}`), pct >= 100 ? h("div.small.good", t("goalDone")) : null),
        h("div.mini-stats", h("div", h("b", st.seen), h("small", t("wordsKnown"))), h("div", h("b", st.due), h("small", t("toReview"))))),
      root.LSHabits.journeyCard(p),
      p.plan ? h("div.plan-line", "📌 ", h("span", { dir: "auto" }, p.plan)) : null,
      h("button.hero-card", { type: "button", onclick: startDaily },
        h("div.hero-emoji", "🎯"),
        h("div.hero-text",
          h("div.hero-title", t("dailyLesson")),
          h("div.hero-sub", t("dailyLessonSub")),
          h("div.hero-chips", h("span.chip", "🔁 " + st.due + " " + t("toReview")), h("span.chip", "✨ " + Math.min(p.newPerDay || 8, newLeft) + " " + t("newWords")))),
        h("div.hero-go", xpToday > 0 ? t("anotherLesson") : t("startLesson"))),
      al.length && lettersKnown < al.length ? h("button.card.action-card", { type: "button", onclick: () => app.go("#/alphabet") },
        h("span.ac-emoji", p.target === "ru" ? "🔤" : "🔠"),
        h("div", h("b", x("alphabetFirst")), h("div.small.muted", x("alphabetFirstSub")),
          h("div.mini-bar", h("i", { style: { width: Math.round((lettersKnown / al.length) * 100) + "%" } })), h("div.small", `${lettersKnown}/${al.length} ${t("letters")}`))) : null,
      h("button.card.action-card.reels-cta", { type: "button", onclick: () => app.go("#/reels") },
        h("span.ac-emoji", "🎬"), h("div", h("b", x("reelsCard")), h("div.small.muted", x("reelsCardSub")))),
      hour >= 19 || hour < 3 ? h("button.card.action-card.night", { type: "button", onclick: startBedtime },
        h("span.ac-emoji", "🌙"), h("div", h("b", x("bedtime")), h("div.small.muted", x("bedtimeSub")))) : null,
      h("h2.section-title", t("learn")),
      sectionGrid(app, p),
      h("button.card.action-card", { type: "button", onclick: () => app.go("#/family") },
        h("span.ac-emoji", "👨‍👩‍👦"),
        h("div", h("b", x("family")), h("div.small.muted", x("familySub")),
          others.length ? h("div.row.wrap.small", others.map((o) => h("span.chip", `${o.avatar} ${o.name} 🔥${ST.streak(o.id)}`))) : null)));
    app.mount(el);
  }

  function sections(p) {
    return [
      { hash: "alphabet", icon: p.target === "ru" ? "🔤" : "🔠", key: "alphabet" },
      { hash: "writing", icon: "✍️", key: "writing" },
      { hash: "words", icon: "📖", key: "words" },
      { hash: "phrases", icon: "💬", key: "phrases" },
      { hash: "grammar", icon: "🧩", key: "grammar" },
      { hash: "sounds", icon: "👄", key: "sounds" },
      { hash: "dialogues", icon: "🎭", key: "dialogues" },
      { hash: "mistakes", icon: "🩹", key: "review" },
    ];
  }

  function sectionGrid(app, p) {
    return h("div.section-grid", sections(p).map((s) => h("a.section-tile", { href: "#/" + s.hash },
      h("span.st-icon", s.icon), h("span.st-title", t("sec_" + s.key)), h("span.st-sub", t("sec_" + s.key + "_sub")))));
  }

  function learn(app) {
    const p = app.profile();
    app.mount(h("div.page", app.header(t("learn")), sectionGrid(app, p),
      h("a.card.action-card", { href: "#/reels" }, h("span.ac-emoji", "🎬"), h("div", h("b", x("reelsCard")), h("div.small.muted", x("reelsCardSub")))),
      h("a.card.action-card", { href: "#/family" }, h("span.ac-emoji", "👨‍👩‍👦"), h("div", h("b", x("family")), h("div.small.muted", x("familySub"))))));
  }

  // ---------- progress ----------
  function progress(app) {
    const p = app.profile();
    const prog = ST.progress(p.id);
    const st = C.stats(prog);
    const days = [];
    let k = U.dayKey();
    for (let i = 0; i < 30; i++) { days.unshift(k); k = U.addDays(k, -1); }
    const maxXp = Math.max(10, ...days.map((d) => prog.xp[d] || 0));
    const fc = C.forecast(prog, 7);
    const maxFc = Math.max(1, ...fc);
    const topics = (root.LS_DATA.topics || []).map((tp) => {
      const all = C.vocab().filter((v) => v.topic === tp.id);
      const seen = all.filter((v) => prog.cards[v.id]).length;
      const mastered = all.filter((v) => SRS.isMastered(prog.cards[v.id])).length;
      return { tp, all: all.length, seen, mastered };
    }).filter((x2) => x2.all);
    const hard = C.hardest(prog, 10);
    const al = C.alphabet(p.target);
    const gl = (root.LS_DATA.grammar || []).filter((g) => g.target === p.target);
    const gDone = gl.filter((g) => (prog.grammar[g.id] || {}).best >= 0.7).length;
    const mins = Math.round((prog.minutes[U.dayKey()] || 0) / 60);

    app.mount(h("div.page.progress",
      app.header(t("progress")),
      h("div.stat-grid",
        stat("🔥", ST.streak(p.id), t("streak")),
        stat("📖", st.seen, t("wordsKnown")),
        stat("🏆", st.mastered, t("mastered")),
        stat("⏱️", mins, t("minutesToday")),
        stat("🔤", `${C.lettersLearned(prog, p.target)}/${al.length}`, x("lettersProgress")),
        stat("🧩", `${gDone}/${gl.length}`, x("grammarDone"))),
      h("div.card",
        h("h3", t("last30")),
        h("div.bars", days.map((d) => h("div.bar", { title: `${d}: ${prog.xp[d] || 0}` }, h("i", { style: { height: Math.round(((prog.xp[d] || 0) / maxXp) * 100) + "%" } }))))),
      h("div.card",
        h("h3", t("forecast")),
        h("div.bars.fc", fc.map((n, i) => h("div.bar", h("i", { style: { height: Math.round((n / maxFc) * 100) + "%" } }), h("small", i === 0 ? t("today") : i === 1 ? t("tomorrow") : "+" + i), h("b.small", String(n)))))),
      h("div.card",
        h("h3", t("byTopic")),
        topics.map((x2) => h("a.topic-row", { href: "#/topic/" + x2.tp.id },
          h("span", x2.tp.emoji + " " + pick(x2.tp)),
          h("div.mini-bar.two", h("i.m", { style: { width: (x2.mastered / x2.all) * 100 + "%" } }), h("i.s", { style: { width: ((x2.seen - x2.mastered) / x2.all) * 100 + "%" } })),
          h("small.muted", `${x2.seen}/${x2.all}`)))),
      hard.length ? h("div.card",
        h("h3", t("hardest")),
        hard.map((id) => { const it = C.item(id); return h("div.word-row", it.emoji ? h("span", it.emoji) : null, L(it[p.target], p.target, "strong"), speakerBtn(it[p.target], p.target), h("span.muted", L(it[p.help] || "", p.help))); }),
        h("button.btn.primary", { type: "button", onclick: () => app.go("#/mistakes") }, t("sec_review"))) : null));
  }
  function stat(icon, num, lbl) { return h("div.stat-card", h("div.stat-icon", icon), h("div.stat-num", String(num)), h("div.stat-lbl", lbl)); }

  // ---------- settings ----------
  function settings(app) {
    const p = app.profile();
    const range = (key, min, max, step, fmt) => {
      const val = h("span.range-val", fmt(p[key]));
      const r = h("input", { type: "range", min, max, step, value: p[key] });
      r.addEventListener("input", () => { val.textContent = fmt(Number(r.value)); });
      r.addEventListener("change", () => { ST.updateProfile(p.id, { [key]: Number(r.value) }); app.refreshProfile(); });
      return h("div.range-row", r, val);
    };
    const toggle = (key, label, def) => {
      const c = h("input", { type: "checkbox" });
      c.checked = p[key] == null ? !!def : !!p[key];
      c.addEventListener("change", () => { ST.updateProfile(p.id, { [key]: c.checked }); app.refreshProfile(); if (key === "large") app.go("#/settings"); });
      return h("label.check-row", c, " ", label);
    };
    const fileIn = h("input", { type: "file", accept: "application/json,.json", hidden: true });
    fileIn.addEventListener("change", async () => {
      const f = fileIn.files[0];
      if (!f) return;
      try { ST.importAll(await f.text()); app.refreshProfile(); toast(t("imported")); app.go("#/home"); } catch (e) { toast(t("importFailed")); }
    });
    const exportData = () => {
      root.LSUI.saveFile(`learn-together-backup-${U.dayKey()}.json`, ST.exportAll(), "application/json");
    };
    const voiceInfo = () => {
      const has = (l) => !!SP.voiceFor(l);
      return h("div.small.muted", `${x("voices")}: 🇬🇧 ${has("en") ? x("yes") : x("no")} · 🇷🇺 ${has("ru") ? x("yes") : x("no")} · 🇮🇱 ${has("he") ? x("yes") : x("no")} — ${x("mic")}: ${SP.canListen() ? x("yes") : x("no")}`);
    };
    app.mount(h("div.page.settings",
      app.header(t("settings")),
      h("div.card.profile-summary",
        h("span.avatar", p.avatar), h("div", h("b", p.name), h("div.small.muted", t("lang_" + p.target))),
        h("button.btn.ghost", { type: "button", onclick: () => app.go("#/edit") }, t("edit")),
        h("button.btn.ghost", { type: "button", onclick: () => app.go("#/who") }, t("switchLearner"))),
      h("div.card",
        h("div.field", h("span", t("speechRate")), range("ttsRate", 0.5, 1.2, 0.05, (v) => (v || 0.9).toFixed(2) + "×")),
        h("div.row", h("button.btn.ghost", { type: "button", onclick: () => SP.speak(p.target === "en" ? "Hello! How are you today?" : "Приве́т! Как дела́?", p.target, { rate: app.ttsRate() }) }, "🔊 " + t("testVoice"))),
        voiceInfo(),
        h("div.small.muted", t("needVoiceHelp")),
        h("div.field", h("span", t("newPerDay")), range("newPerDay", 3, 20, 1, (v) => String(v || 8))),
        h("div.field", h("span", t("dailyGoalXp")), range("dailyGoal", 20, 300, 10, (v) => String(v || 50))),
        toggle("sfx", { he: "צלילי משחק ורטט", en: "Game sounds & vibration", ru: "Игровые звуки и вибрация" }[I.getLang()], true),
        toggle("large", x("largeText")),
        toggle("kb", x("onScreenKb"), p.target === "ru"),
        p.target === "ru" ? toggle("translit", x("translit")) : null),
      root.LSHabits.settingsCard(app),
      h("div.card",
        h("h3", t("howItWorks")),
        h("p", { html: t("howItWorksText") }),
        h("p.small.muted", t("install"))),
      h("div.card",
        h("button.btn.ghost.wide", { type: "button", onclick: exportData }, "💾 " + t("exportData")),
        h("button.btn.ghost.wide", { type: "button", onclick: () => fileIn.click() }, "📂 " + t("importData")), fileIn,
        h("button.btn.danger-ghost.wide", { type: "button", onclick: async () => { if (await confirmBox(t("confirmReset"))) { ST.resetProgress(p.id); app.go("#/home"); } } }, "♻️ " + t("resetData")),
        h("button.btn.danger-ghost.wide", { type: "button", onclick: async () => { if (await confirmBox(t("confirmReset"))) { ST.deleteProfile(p.id); app.setProfile(null); app.go("#/who"); } } }, "🗑️ " + t("deleteLearner")))));
  }

  // ---------- family ----------
  function family(app, args) {
    const me = app.profile();
    const all = ST.profiles();
    const today = U.dayKey();
    const board = h("div.family-board", all.map((p) => {
      const pr = ST.progress(p.id);
      const st = C.stats(pr);
      return h("div.family-card" + (p.id === me.id ? ".me" : ""),
        h("div.avatar", p.avatar), h("b", p.name),
        h("div.small", (p.target === "en" ? "🇬🇧" : "🇷🇺") + " " + t("lang_" + p.target)),
        h("div", "🔥 " + ST.streak(p.id)),
        h("div.small.muted", `${pr.xp[today] || 0} ${t("xp")} · ${st.seen} ${t("wordsKnown")}`));
    }));
    const quizArea = h("div");
    const startQuiz = (learner) => {
      const lp = ST.progress(learner.id);
      const ids = U.shuffle(Object.keys(lp.cards).filter((id) => C.item(id))).slice(0, 10);
      quizArea.innerHTML = "";
      if (!ids.length) { quizArea.appendChild(h("p.notice", x("needWords"))); return; }
      let i = 0, right = 0;
      const showOne = () => {
        quizArea.innerHTML = "";
        if (i >= ids.length) {
          ST.addXp(learner.id, right * 5);
          quizArea.appendChild(h("div.card.center", h("div.big-emoji", "🎉"), h("h3", `${learner.avatar} ${learner.name}: ${right}/${ids.length}`)));
          return;
        }
        const it = C.item(ids[i]);
        // prompt in a language both know: learner's help language
        const promptLang = learner.help;
        const ans = h("div.quiz-answer", { hidden: true }, it.emoji ? h("span.emoji", it.emoji) : null, L(it[learner.target], learner.target, "strong"), speakerBtn(it[learner.target], learner.target));
        const grade = (ok) => {
          lp.cards[it.id] = SRS.review(lp.cards[it.id] || SRS.newCard(), ok ? 3 : 1, Date.now());
          ST.saveProgress(learner.id);
          if (ok) right++;
          i++; showOne();
        };
        quizArea.appendChild(h("div.card.quiz-card",
          h("div.small.muted", `${i + 1}/${ids.length} · ${x("askerReads")}`),
          h("div.quiz-q", x("howSay", { lang: t("lang_" + learner.target) })),
          h("div.quiz-word", L(it[promptLang] || it.he, promptLang)),
          h("button.btn.ghost", { type: "button", onclick: (e) => { ans.hidden = false; e.target.remove(); } }, "👀 " + x("showAns")),
          ans,
          h("div.row.center", h("button.btn.good", { type: "button", onclick: () => grade(true) }, "✅ " + x("gotRight")), h("button.btn.ghost", { type: "button", onclick: () => grade(false) }, "🔁 " + x("gotWrong")))));
      };
      showOne();
    };
    app.mount(h("div.page.family",
      app.header(x("family"), "#/home"),
      h("p.muted", x("familySub")),
      board,
      h("h2", x("quizEachOther")),
      all.length < 2 ? h("p.notice", x("needTwo"), " ", h("a", { href: "#/setup" }, t("addLearner"))) : h("div",
        h("p", x("whoIsAsked")),
        h("div.row.wrap", all.map((p) => h("button.btn.ghost", { type: "button", onclick: () => startQuiz(p) }, `${p.avatar} ${p.name}`)))),
      quizArea));
  }

  function mistakes(app) {
    const p = app.profile();
    const prog = ST.progress(p.id);
    const plan = C.buildMistakes(p, prog, { canListen: SP.canListen() });
    if (!plan.steps.length) {
      app.mount(h("div.page", app.header(t("sec_review"), "#/home"), h("div.card.center", h("div.big-emoji", "🌟"), h("p", t("noMistakes")))));
      return;
    }
    root.LSSession.run({ steps: plan.steps });
  }

  const routes = {
    home: (app) => home(app),
    learn: (app) => learn(app),
    progress: (app) => progress(app),
    settings: (app) => settings(app),
    family: (app, a) => family(app, a),
    mistakes: (app) => mistakes(app),
    setup: (app) => app.mount(profileForm(app, null), { full: true }),
    edit: (app) => app.mount(profileForm(app, app.profile()), { full: true }),
    who: (app) => profiles(app),
    reels: (app, a) => {
      if (a[0] && a[1]) app.mount(root.LSReels.feed(app, a[0], a[1]), { full: true });
      else app.mount(root.LSReels.chooser(app));
    },
  };

  root.LSScreens = { routes, profiles, x, X };
})(window);
