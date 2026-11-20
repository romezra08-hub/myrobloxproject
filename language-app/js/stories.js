// Graded stories: comprehensible input + reading while listening (karaoke) + comprehension questions.
(function (root) {
  const { h, L, karaoke, confetti, sfx } = root.LSUI;
  const { t, pick } = root.LSI18n;
  const ST = root.LSStore;
  const SP = root.LSSpeech;
  const U = root.LSUtil;
  const D = () => root.LS_DATA || {};

  const TX = {
    title: { he: "סיפורים", en: "Stories", ru: "Истории" },
    sub: { he: "סיפורים קצרים עם קול, תמונות ושאלות. מנסים להבין לפני שמציצים בתרגום!", en: "Short stories with audio, pictures and questions. Try to understand before peeking at the translation!", ru: "Короткие истории со звуком, картинками и вопросами. Попробуйте понять, прежде чем смотреть перевод!" },
    playAll: { he: "הקראת הסיפור", en: "Read it to me", ru: "Прочитать вслух" },
    stop: { he: "עצירה", en: "Stop", ru: "Стоп" },
    tapReveal: { he: "תרגום המשפט (אפשר גם להקיש על מילה)", en: "Sentence translation (or tap a word)", ru: "Перевод фразы (или нажмите на слово)" },
    questions: { he: "הבנת הנקרא", en: "Did you understand?", ru: "Вы поняли?" },
    showAll: { he: "להציג את כל התרגומים", en: "Show all translations", ru: "Показать все переводы" },
    done: { he: "כל הכבוד! סיימת את הסיפור", en: "Well done! You finished the story", ru: "Молодец! История прочитана" },
    level: { he: "רמה", en: "Level", ru: "Уровень" },
    sentences: { he: "משפטים", en: "sentences", ru: "предложений" },
    empty: { he: "הסיפורים בדרך…", en: "Stories are on their way…", ru: "Истории скоро появятся…" },
  };
  const x = (k) => pick(TX[k]);

  function list(app) {
    const p = app.profile();
    const prog = ST.progress(p.id);
    prog.stories = prog.stories || {};
    const stories = (D().stories || []).slice().sort((a, b) => a.level - b.level);
    const byLevel = [1, 2, 3].map((lv) => stories.filter((s) => s.level === lv)).filter((g) => g.length);
    app.mount(h("div.page.stories",
      app.header("📚 " + x("title"), "#/home"),
      h("p.muted", x("sub")),
      !stories.length ? h("div.notice", x("empty")) : null,
      byLevel.map((g) => h("div",
        h("h3", x("level") + " " + g[0].level + " " + "⭐".repeat(g[0].level)),
        h("div.story-grid", g.map((s) => {
          const r = prog.stories[s.id];
          return h("a.story-card" + (r ? ".done" : ""), { href: "#/story/" + s.id },
            h("span.story-emoji", s.emoji || "📖"),
            h("b", L(s.title[p.target] || "", p.target)),
            h("small", L(s.title[p.help] || "", p.help)),
            h("small.story-meta", r ? "✅ " + Math.round(r.best * 100) + "%" : s.sentences.length + " " + x("sentences")));
        }))))));
  }

  // Glosses: tap a word to see its meaning if it's in the word lists (exact form or a close stem).
  let glossIndex = null;
  function gloss(word, T, H) {
    if (!glossIndex) {
      glossIndex = { en: {}, ru: {} };
      root.LSContent.vocab().forEach((v) => ["en", "ru"].forEach((l) => {
        const k = U.normalize(v[l] || "", { lang: l, loose: true });
        if (k && !k.includes(" ") && !glossIndex[l][k]) glossIndex[l][k] = v;
      }));
      // verb forms: Russian present (я/ты/они) and perfective, English past
      root.LSContent.vocab().forEach((v) => {
        [v.ruPres, v.ruPf].filter(Boolean).forEach((f) => String(f).split(/[,\s]+/).forEach((tok) => {
          const k = U.normalize(tok, { lang: "ru" });
          if (k.length > 2 && !["они", "ты"].includes(k) && !glossIndex.ru[k]) glossIndex.ru[k] = v;
        }));
        if (v.enPast) { const k = U.normalize(v.enPast, { lang: "en" }); if (k && !glossIndex.en[k]) glossIndex.en[k] = v; }
      });
    }
    const w = U.normalize(word, { lang: T, loose: true });
    const idx = glossIndex[T] || {};
    if (idx[w]) return idx[w];
    // try trimming common endings (Russian cases / English -s -ed -ing)
    for (let cut = 1; cut <= 3 && w.length - cut >= 3; cut++) {
      const stem = w.slice(0, w.length - cut);
      const hit = Object.keys(idx).find((k) => k.startsWith(stem) && k.length - stem.length <= 3);
      if (hit) return idx[hit];
    }
    return null;
  }

  function story(app, args) {
    const p = app.profile();
    const prog = ST.progress(p.id);
    prog.stories = prog.stories || {};
    const s = (D().stories || []).find((z) => z.id === args[0]);
    if (!s) return app.go("#/stories");
    const T = p.target, H = p.help;
    let stopFlag = false, playing = false;
    const rows = s.sentences.map((sn, i) => {
      const k = karaoke(sn[T], T, "story-t");
      k.el.querySelectorAll(".kw").forEach((w) => w.addEventListener("click", (e) => {
        e.stopPropagation();
        document.querySelectorAll(".gloss-pop").forEach((n) => n.remove());
        const hit = gloss(w.textContent, T, H);
        SP.speak(w.textContent, T, { rate: 0.8 });
        if (!hit) return;
        const pop = h("span.gloss-pop", hit.emoji ? hit.emoji + " " : "", L(hit[H] || "", H));
        w.appendChild(pop);
        setTimeout(() => pop.remove(), 2600);
      }));
      const tr = h("div.story-h", { hidden: true }, L(sn[H] || "", H));
      const reveal = h("button.link-btn.small", { type: "button", onclick: (e) => { e.stopPropagation(); tr.hidden = !tr.hidden; } }, "👁️ " + x("tapReveal"));
      const row = h("div.story-line", { onclick: () => { stopFlag = true; k.play(app.ttsRate()); } },
        h("span.story-pic", sn.emoji || "•"), h("div.story-text", k.el, tr, reveal));
      return { row, k, tr };
    });
    const playBtn = h("button.btn.primary", { type: "button" }, "▶ " + x("playAll"));
    playBtn.addEventListener("click", async () => {
      if (playing) { stopFlag = true; SP.stop(); return; }
      playing = true; stopFlag = false; playBtn.textContent = "⏹ " + x("stop");
      for (let i = 0; i < rows.length && !stopFlag; i++) {
        rows.forEach((r, j) => r.row.classList.toggle("active", j === i));
        rows[i].row.scrollIntoView({ block: "center", behavior: "smooth" });
        await rows[i].k.play(app.ttsRate());
        await new Promise((r) => setTimeout(r, 450));
      }
      rows.forEach((r) => r.row.classList.remove("active"));
      playing = false; playBtn.textContent = "▶ " + x("playAll");
    });
    const showAll = h("button.btn.ghost", { type: "button", onclick: () => rows.forEach((r) => (r.tr.hidden = false)) }, "👁️ " + x("showAll"));

    // comprehension questions (in the target language, with a translation hint)
    let right = 0, answered = 0;
    const qs = (s.questions || []).map((q, qi) => {
      const box = h("div.card.story-q");
      let done = false;
      box.append(
        h("div.story-q-text", h("b", (qi + 1) + ". "), L(q.q[T] || "", T, "strong"), " ", root.LSUI.speakerBtn(q.q[T] || "", T)),
        h("div.small.muted", L(q.q[H] || "", H)),
        h("div.options", q.options.map((o, oi) => {
          const b = h("button.option", { type: "button" }, L(o[T] || "", T));
          b.addEventListener("click", () => {
            if (done) return; done = true; answered++;
            const ok = oi === q.answer; if (ok) right++;
            b.classList.add(ok ? "right" : "wrong");
            if (!ok) b.parentNode.children[q.answer].classList.add("right");
            sfx(ok ? "right" : "wrong");
            if (answered === s.questions.length) finish();
          });
          return b;
        })));
      return box;
    });
    const result = h("div");
    function finish() {
      const score = s.questions.length ? right / s.questions.length : 1;
      const prev = prog.stories[s.id] || {};
      prog.stories[s.id] = { best: Math.max(prev.best || 0, score), done: (prev.done || 0) + 1 };
      ST.addXp(p.id, 10 + right * 5);
      if (root.LSQuests) root.LSQuests.bump(p.id, "story");
      ST.saveProgress(p.id);
      result.appendChild(h("div.card.center", h("div.big-emoji", score === 1 ? "🏆" : "🌟"), h("h3", x("done")), h("div", right + "/" + s.questions.length)));
      confetti(); sfx("done");
    }
    app.onLeave(() => { stopFlag = true; SP.stop(); });
    app.mount(h("div.page.story",
      app.header((s.emoji || "📖") + " " + (s.title[T] || ""), "#/stories"),
      h("div.small.muted", L(s.title[H] || "", H)),
      h("div.row", playBtn, showAll),
      h("div.story-body", rows.map((r) => r.row)),
      qs.length ? h("h2", "🤔 " + x("questions")) : null,
      qs, result));
  }

  Object.assign(root.LSScreens.routes, { stories: (app) => list(app), story: (app, a) => story(app, a) });
  root.LSStories = { TX };
})(window);
