// "Talk with Lisa": a conversation partner powered by Claude (the artifact "sample" capability).
// The AI replies in the target language at the learner's level, corrects every learner message
// (a recast + a short explanation in the learner's own language), offers a translation and a hint.
(function (root) {
  const { h, L, karaoke, keyboard, sfx } = root.LSUI;
  const { t, pick } = root.LSI18n;
  const ST = root.LSStore;
  const SP = root.LSSpeech;
  const C = root.LSContent;
  const NAMES = { en: "English", ru: "Russian", he: "Hebrew" };

  const SCENES = [
    { id: "free", emoji: "💬", he: "שיחה חופשית", en: "Free chat", ru: "Свободный разговор", brief: "a friendly chat about the learner's day, family, hobbies and plans" },
    { id: "cafe", emoji: "☕", he: "בבית קפה", en: "At a café", ru: "В кафе", brief: "you are a waiter in a café; the learner orders" },
    { id: "shop", emoji: "🛍️", he: "בחנות בגדים", en: "Clothes shop", ru: "В магазине одежды", brief: "you are a shop assistant; the learner is buying clothes" },
    { id: "doctor", emoji: "🩺", he: "אצל הרופא", en: "At the doctor", ru: "У врача", brief: "you are a doctor; the learner describes how they feel" },
    { id: "directions", emoji: "🧭", he: "שואלים דרך", en: "Asking directions", ru: "Как пройти", brief: "you are a local in the street; the learner asks for directions" },
    { id: "hotel", emoji: "🏨", he: "במלון", en: "At a hotel", ru: "В гостинице", brief: "you are a hotel receptionist; the learner checks in" },
    { id: "job", emoji: "💼", he: "ראיון עבודה", en: "Job interview", ru: "Собеседование", brief: "you are a friendly interviewer; ask simple questions about the learner's work and skills" },
    { id: "family", emoji: "👨‍👩‍👦", he: "מדברים על המשפחה", en: "Talking about family", ru: "О семье", brief: "a warm chat about the learner's family and home" },
  ];
  const TX = {
    title: { he: "מדברים עם ליסה", en: "Talk with Lisa", ru: "Разговор с Лисой" },
    sub: { he: "שיחה אמיתית עם בינה מלאכותית בשפה שאתם לומדים. ליסה מתקנת כל טעות ומסבירה — בלי לחץ.", en: "A real conversation with AI in the language you're learning. Lisa fixes every mistake and explains — no pressure.", ru: "Настоящий разговор с ИИ на изучаемом языке. Лиса исправляет каждую ошибку и объясняет — без стресса." },
    pick: { he: "על מה נדבר?", en: "What shall we talk about?", ru: "О чём поговорим?" },
    write: { he: "כתבו או דברו…", en: "Type or speak…", ru: "Пишите или говорите…" },
    send: { he: "שליחה", en: "Send", ru: "Отправить" },
    better: { he: "עדיף לומר:", en: "Better:", ru: "Лучше сказать:" },
    perfect: { he: "מושלם! 👏", en: "Perfect! 👏", ru: "Идеально! 👏" },
    hint: { he: "רמז לתשובה", en: "Answer hint", ru: "Подсказка" },
    translate: { he: "תרגום", en: "Translate", ru: "Перевод" },
    thinking: { he: "ליסה חושבת…", en: "Lisa is thinking…", ru: "Лиса думает…" },
    unavailable: { he: "השיחה עם הבינה המלאכותית עובדת כשפותחים את האפליקציה בתוך claude.ai.", en: "AI conversation works when the app is opened inside claude.ai.", ru: "Разговор с ИИ работает, когда приложение открыто в claude.ai." },
    denied: { he: "הגישה לבינה המלאכותית לא אושרה. אפשר לאשר בתפריט ההרשאות של הדף.", en: "AI access wasn't allowed. You can allow it in the page's permissions menu.", ru: "Доступ к ИИ не разрешён. Его можно включить в меню разрешений страницы." },
    error: { he: "משהו השתבש. נסו שוב בעוד רגע.", en: "Something went wrong. Try again in a moment.", ru: "Что-то пошло не так. Попробуйте ещё раз." },
    newChat: { he: "שיחה חדשה", en: "New chat", ru: "Новый разговор" },
  };
  const x = (k) => pick(TX[k]);

  function level(prog) {
    const n = Object.keys(prog.cards).length;
    return n < 120 ? "A1 (complete beginner: very short, simple present-tense sentences, the most common words)" : n < 450 ? "A2 (elementary: short simple sentences, common past and future)" : "B1 (intermediate: natural everyday sentences)";
  }

  function prompt(p, prog, scene, history, learnerText) {
    const T = NAMES[p.target], H = NAMES[p.help];
    return [
      `You are Lisa, a warm, patient, funny conversation partner (a friendly fox) helping a learner practice ${T}. The learner's own language is ${H}.`,
      `Scenario: ${scene.brief}. Learner level: ${level(prog)}.`,
      `Rules: Reply ONLY in ${T}, 1-3 short sentences, matched to the level, and usually end with a simple question to keep the conversation going. Stay in the scenario. Be encouraging.` +
        (p.target === "ru" ? " Write Russian with stress marks (the combining acute accent U+0301 right after the stressed vowel of every multi-syllable word)." : ""),
      `Correct the learner's LAST message: fix grammar, word choice, word order, spelling and wrong forms. Ignore capitalization, punctuation, and missing Russian stress marks or ё. If the learner wrote in another language, set "corrected" to how to say it in ${T}. If the message is already correct and natural, set correction to null.`,
      `Return ONLY JSON: {"correction": null or {"corrected": "<the learner's message, corrected, in ${T}>", "explanation": "<one short friendly sentence in ${H} explaining the mistake>"}, "reply": "<your reply in ${T}>", "translation": "<your reply translated to ${H}>", "hint": "<a short example answer the learner could give, in ${T}>"}`,
      "",
      "Conversation so far:",
      history.length ? history.map((m) => (m.role === "ai" ? "Lisa: " : "Learner: ") + m.text).join("\n") : "(none yet — start the conversation with a greeting and a first question; correction must be null)",
      learnerText ? "Learner (last message): " + learnerText : "",
    ].join("\n");
  }

  function picker(app) {
    app.mount(h("div.page.aichat",
      app.header("🦊 " + x("title"), "#/home"),
      root.LSPath ? root.LSPath.mascot(x("sub")) : h("p.muted", x("sub")),
      h("h3", x("pick")),
      h("div.topic-grid", SCENES.map((s) => h("a.topic-tile", { href: "#/chat/" + s.id }, h("span.tt-emoji", s.emoji), h("span.tt-name", pick(s)))))));
  }

  async function chat(app, args) {
    const p = app.profile();
    const prog = ST.progress(p.id);
    const scene = SCENES.find((s) => s.id === args[0]) || SCENES[0];
    const T = p.target, H = p.help;
    const history = [];
    let busy = false, alive = true;
    app.onLeave(() => { alive = false; SP.stop(); SP.cancelListen(); });

    const log = h("div.chat.ai-log");
    const status = h("div.small.muted.ai-status", { "aria-live": "polite" });
    const input = h("input.answer.ai-input", { type: "text", lang: T, dir: "ltr", placeholder: x("write"), autocomplete: "off", spellcheck: "false" });
    const kb = keyboard(input, T);
    const kbWrap = h("div.kb-wrap", kb);
    kbWrap.hidden = !(T === "ru" ? p.kb !== false : !!p.kb);
    const sendBtn = h("button.btn.primary.ai-send", { type: "button" }, "➤");
    const micBtn = h("button.btn.ghost.ai-mic", { type: "button", "aria-label": t("tapToSpeak") }, "🎤");
    const kbBtn = h("button.btn.ghost.ai-kb", { type: "button", "aria-label": t("keyboard"), onclick: () => { kbWrap.hidden = !kbWrap.hidden; } }, "⌨️");
    const bar = h("div.ai-bar", input, micBtn, kbBtn, sendBtn);

    app.mount(h("div.page.aichat-page",
      app.header(scene.emoji + " " + pick(scene), "#/chat", h("button.btn.ghost.small", { type: "button", onclick: () => app.go("#/chat/" + scene.id) }, x("newChat"))),
      log, status, h("div.ai-compose", bar, kbWrap)));

    const sample = root.claude && root.claude.use ? await root.claude.use("sample").catch(() => null) : null;
    if (!alive) return;
    if (!sample) { status.textContent = x("unavailable"); bar.hidden = true; return; }

    function aiBubble(res) {
      const k = karaoke(res.reply || "", T, "strong");
      const tr = h("div.small.muted", { hidden: true }, L(res.translation || "", H));
      const hintBox = h("div.ai-hint", { hidden: true });
      if (res.hint) hintBox.append(L(res.hint, T), " ", h("button.link-btn.small", { type: "button", onclick: () => { input.value = res.hint; input.focus(); } }, "↩︎"));
      const el = h("div.bubble.bot",
        h("span.who", "🦊"),
        h("div.bubble-body",
          h("div", k.el, " ", h("button.icon-btn.speaker", { type: "button", "aria-label": t("listen"), onclick: () => k.play(app.ttsRate()) }, "🔊")),
          tr, hintBox,
          h("div.ai-tools",
            h("button.link-btn.small", { type: "button", onclick: () => { tr.hidden = !tr.hidden; } }, "👁️ " + x("translate")),
            res.hint ? h("button.link-btn.small", { type: "button", onclick: () => { hintBox.hidden = !hintBox.hidden; } }, "💡 " + x("hint")) : null)));
      log.appendChild(el);
      el.scrollIntoView({ block: "end", behavior: "smooth" });
      k.play(app.ttsRate());
    }

    function meBubble(text) {
      const fix = h("div.ai-fix");
      const el = h("div.bubble.me", h("span.who", p.avatar), h("div.bubble-body", h("div", L(text, T, "strong")), fix));
      log.appendChild(el);
      el.scrollIntoView({ block: "end", behavior: "smooth" });
      return fix;
    }

    function showCorrection(fix, corr) {
      if (!corr || !corr.corrected) { fix.appendChild(h("div.ai-ok", x("perfect"))); return; }
      fix.append(
        h("div.ai-better", "✏️ " + x("better") + " ", L(corr.corrected, T, "strong"), root.LSUI.speakerBtn(corr.corrected, T)),
        corr.explanation ? h("div.small", L(corr.explanation, H)) : null);
    }

    async function turn(learnerText, viaMic) {
      if (busy) return;
      busy = true; sendBtn.disabled = true; micBtn.disabled = true;
      let fix = null;
      if (learnerText) fix = meBubble(learnerText);
      status.textContent = "🦊 " + x("thinking");
      try {
        const res = await sample.json(prompt(p, prog, scene, history, learnerText), { cache: false });
        if (!alive) return;
        status.textContent = "";
        if (learnerText) {
          history.push({ role: "me", text: learnerText });
          showCorrection(fix, res && res.correction);
          sfx(res && res.correction ? "tap" : "right");
          ST.addXp(p.id, 4);
          if (viaMic && root.LSQuests) root.LSQuests.bump(p.id, "spoken");
        }
        if (res && res.reply) { history.push({ role: "ai", text: res.reply }); aiBubble(res); }
        while (history.length > 24) history.shift();
      } catch (e) {
        if (!alive) return;
        status.textContent = e && (e.code === "not_granted" || e.code === "denied") ? x("denied") : x("error");
        if (fix && learnerText) { input.value = learnerText; fix.closest(".bubble").remove(); }
      } finally {
        busy = false; sendBtn.disabled = false; micBtn.disabled = false;
      }
    }

    const send = () => { const v = input.value.trim(); if (!v) return; input.value = ""; turn(v, false); };
    sendBtn.addEventListener("click", send);
    input.addEventListener("keydown", (e) => { if (e.key === "Enter") { e.preventDefault(); send(); } });
    micBtn.addEventListener("click", () => {
      if (busy) return;
      if (!SP.canListen()) { status.textContent = t("noSpeech"); return; }
      micBtn.classList.add("listening"); status.textContent = "🎤 " + t("listening");
      SP.listen(T).then((r) => {
        micBtn.classList.remove("listening"); status.textContent = "";
        if (!alive) return;
        if (r.ok && r.alternatives[0]) turn(r.alternatives[0], true);
        else status.textContent = r.error === "not-allowed" ? t("micDenied") : t("notHeard");
      });
    });

    turn(null, false); // Lisa opens the conversation
  }

  Object.assign(root.LSScreens.routes, { chat: (app, a) => (a[0] ? chat(app, a) : picker(app)) });
  root.LSChat = { SCENES };
})(window);
