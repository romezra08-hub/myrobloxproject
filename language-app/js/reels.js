// "Reels": a TikTok-style vertical feed. One topic per feed (no random jumping),
// auto-playing audio, dual captions with the key word highlighted, a quick quiz every
// few cards (active retrieval), and a finite end with a recap.
(function (root) {
  const { h, L } = root.LSUI;
  const { t, pick } = root.LSI18n;
  const U = root.LSUtil;
  const C = root.LSContent;
  const SRS = root.LSSrs;
  const ST = root.LSStore;
  const SP = root.LSSpeech;

  const TXT = {
    title: { he: "רילס", en: "Reels", ru: "Рилсы" },
    sub: { he: "גוללים למעלה כמו בטיקטוק — ולומדים. כל פיד על נושא אחד, עם חידון קטן כל כמה סרטונים.", en: "Swipe up like TikTok — and learn. Each feed sticks to one topic, with a mini-quiz every few cards.", ru: "Листайте вверх, как в ТикТоке, — и учитесь. Каждая лента — одна тема, с мини-тестом через несколько карточек." },
    swipe: { he: "החליקו למעלה", en: "Swipe up", ru: "Листайте вверх" },
    quiz: { he: "חידון מהיר!", en: "Quick quiz!", ru: "Быстрый тест!" },
    know: { he: "יודע/ת", en: "Know it", ru: "Знаю" },
    again: { he: "שוב", en: "Again", ru: "Ещё" },
    end: { he: "סוף הפיד! עכשיו תנו למוח לנוח 😊", en: "End of feed! Now let your brain rest 😊", ru: "Конец ленты! Теперь дайте мозгу отдохнуть 😊" },
    recap: { he: "המילים של הפיד:", en: "Words in this feed:", ru: "Слова из этой ленты:" },
    another: { he: "פיד נוסף", en: "Another feed", ru: "Ещё лента" },
    pickTopic: { he: "בחרו נושא לפיד", en: "Pick a topic for your feed", ru: "Выберите тему ленты" },
    words: { he: "מילים", en: "Words", ru: "Слова" },
    phrases: { he: "משפטים", en: "Phrases", ru: "Фразы" },
    surprise: { he: "תפתיעו אותי", en: "Surprise me", ru: "Удивите меня" },
    tapSound: { he: "הקישו כדי להפעיל צליל 🔊", en: "Tap to turn on sound 🔊", ru: "Нажмите, чтобы включить звук 🔊" },
    quizScore: { he: "חידונים נכונים", en: "Quizzes right", ru: "Верных ответов" },
  };
  const tx = (k) => pick(TXT[k]);

  // Highlight the target word inside an example sentence (textual enhancement).
  function highlight(sentence, word, lang) {
    const w = U.normalize(word, { lang, loose: true });
    const tokens = String(sentence).split(/(\s+)/);
    if (!w || w.includes(" ")) {
      return L(sentence, lang);
    }
    const stem = w.length > 4 ? w.slice(0, Math.max(3, w.length - 2)) : w;
    let done = false;
    const span = h("span", { lang, dir: lang === "he" ? "rtl" : "ltr" });
    tokens.forEach((tok) => {
      const n = U.normalize(tok, { lang });
      if (!done && n && (n === w || (n.startsWith(stem) && n.length <= w.length + 4))) {
        span.appendChild(h("mark", tok));
        done = true;
      } else span.appendChild(document.createTextNode(tok));
    });
    return span;
  }

  function pickFeedItems(profile, prog, source) {
    let list;
    if (source.type === "sit") list = C.phrases().filter((p) => p.sit === source.id).map((p) => C.item(p.id));
    else list = C.vocab().filter((v) => v.topic === source.id).map((v) => C.item(v.id));
    // ~60% unseen (next in order), ~40% known (weakest first) — keeps it fresh but connected
    const unseen = list.filter((x) => !prog.cards[x.id]).slice(0, 8);
    const known = list.filter((x) => prog.cards[x.id]).sort((a, b) => SRS.strength(prog.cards[a.id]) - SRS.strength(prog.cards[b.id])).slice(0, 12 - unseen.length);
    return U.shuffle(known).concat(unseen).slice(0, 12);
  }

  function chooser(app) {
    const profile = app.profile();
    const prog = ST.progress(profile.id);
    const topics = (root.LS_DATA.topics || []).filter((tp) => C.vocab().some((v) => v.topic === tp.id));
    const sits = (root.LS_DATA.situations || []).filter((s) => C.phrases().some((p) => p.sit === s.id));
    const tile = (src, label, emoji, count, total) => h("button.reel-topic", { type: "button", onclick: () => app.go(`#/reels/${src.type}/${src.id}`) },
      h("span.emoji", emoji), h("span.lbl", label), h("span.small.muted", `${count}/${total}`));
    const surprise = () => {
      const pool = topics.map((tp) => ({ type: "topic", id: tp.id, left: C.vocab().filter((v) => v.topic === tp.id && !prog.cards[v.id]).length }));
      const best = U.shuffle(pool).sort((a, b) => (b.left > 0) - (a.left > 0))[0];
      app.go(`#/reels/${best.type}/${best.id}`);
    };
    return h("div.page.reels-chooser",
      app.header(tx("title"), "#/home"),
      h("p.muted", tx("sub")),
      h("button.btn.primary.wide", { type: "button", onclick: surprise }, "🎲 " + tx("surprise")),
      h("h3", tx("words")),
      h("div.reel-topics", topics.map((tp) => {
        const all = C.vocab().filter((v) => v.topic === tp.id);
        return tile({ type: "topic", id: tp.id }, pick(tp), tp.emoji, all.filter((v) => prog.cards[v.id]).length, all.length);
      })),
      sits.length ? h("h3", tx("phrases")) : null,
      h("div.reel-topics", sits.map((s) => {
        const all = C.phrases().filter((p) => p.sit === s.id);
        return tile({ type: "sit", id: s.id }, pick(s), s.emoji, all.filter((p) => prog.cards[p.id]).length, all.length);
      })));
  }

  function feed(app, type, id) {
    const profile = app.profile();
    const prog = ST.progress(profile.id);
    const T = profile.target, H = profile.help;
    const items = pickFeedItems(profile, prog, { type, id });
    const started = Date.now();
    let quizRight = 0, quizTotal = 0;

    // Build card list: content cards with a quiz after every 3rd card.
    const cards = [];
    items.forEach((it, i) => {
      cards.push({ kind: "item", item: it });
      if (i % 3 === 2) {
        const recent = items.slice(Math.max(0, i - 2), i + 1);
        cards.push({ kind: "quiz", item: U.sample(recent, 1)[0] });
      }
    });
    cards.push({ kind: "end" });

    const scroller = h("div.reels", { tabindex: "0" });
    const closeBtn = h("button.icon-btn.reels-close", { type: "button", "aria-label": t("quit"), onclick: () => app.go("#/reels") }, "✕");
    const dots = h("div.reels-dots", { "aria-hidden": "true" }, cards.map(() => h("i")));
    // Browsers only allow audio after the user interacted with the page; in-app navigation counts.
    let soundOk = !!(navigator.userActivation && navigator.userActivation.hasBeenActive);
    const soundHint = h("button.reels-sound", { type: "button", onclick: () => { soundOk = true; soundHint.remove(); playCurrent(); } }, tx("tapSound"));
    if (soundOk) soundHint.hidden = true;

    function grade(it, correct) {
      const before = prog.cards[it.id] || SRS.newCard();
      prog.cards[it.id] = SRS.review(before, correct ? 3 : 1, Date.now());
      ST.addXp(profile.id, correct ? 5 : 1);
      ST.saveProgress(profile.id);
    }

    function itemCard(c) {
      const it = c.item;
      const word = it[T];
      const exT = it[T + "Ex"], exH = it[H + "Ex"];
      const isPhrase = it._type === "phrase";
      const know = h("button.rail-btn", { type: "button", onclick: (e) => { e.stopPropagation(); know.classList.add("on"); again.classList.remove("on"); grade(it, true); } }, h("span", "❤️"), h("small", tx("know")));
      const again = h("button.rail-btn", { type: "button", onclick: (e) => { e.stopPropagation(); again.classList.add("on"); know.classList.remove("on"); grade(it, false); } }, h("span", "🔁"), h("small", tx("again")));
      const slow = h("button.rail-btn", { type: "button", onclick: (e) => { e.stopPropagation(); SP.speak(isPhrase ? word : (exT || word), T, { rate: 0.55 }); } }, h("span", "🐢"), h("small", t("slow")));
      const el = h("section.reel", { "data-kind": "item" },
        h("div.reel-bg", { "aria-hidden": "true" }, it.emoji || "💬"),
        h("div.reel-main",
          it.emoji ? h("div.reel-emoji", it.emoji) : null,
          h("div.reel-word" + (isPhrase ? ".phrase" : ""), L(word, T)),
          T === "ru" && profile.translit ? h("div.translit", "[" + C.translitStress(word) + "]") : null,
          h("div.reel-trans", L(it[H] || "", H))),
        !isPhrase && exT ? h("div.reel-captions",
          h("div.cap-t", highlight(exT, word, T)),
          exH ? h("div.cap-h", L(exH, H)) : null) : null,
        h("div.reel-rail", know, again, slow));
      el.addEventListener("click", () => { soundOk = true; soundHint.remove(); play(c); });
      c.play = () => SP.speak(isPhrase || !exT ? word : word + ". " + exT, T, { rate: app.ttsRate() });
      // the card counts as "seen": create the SRS card if new
      c.onShow = () => {
        if (!prog.cards[it.id]) {
          prog.cards[it.id] = SRS.newCard();
          const k = U.dayKey();
          prog.newToday[k] = (prog.newToday[k] || 0) + 1;
          ST.saveProgress(profile.id);
        }
      };
      return el;
    }

    function quizCard(c) {
      const it = c.item;
      const field = H;
      const opts = U.shuffle([it].concat(C.distractors(it, field, 1)));
      let done = false;
      const res = h("div.reel-quiz-res");
      const el = h("section.reel.quiz", { "data-kind": "quiz" },
        h("div.reel-main",
          h("div.quiz-badge", "⚡ " + tx("quiz")),
          h("div.reel-word" + (it._type === "phrase" ? ".phrase" : ""), L(it[T], T)),
          h("div.quiz-opts", opts.map((o) => {
            const b = h("button.quiz-opt", { type: "button" }, L(o[field] || "", field));
            b.addEventListener("click", (e) => {
              e.stopPropagation();
              if (done) return;
              done = true;
              const ok = o.id === it.id;
              quizTotal++; if (ok) quizRight++;
              b.classList.add(ok ? "right" : "wrong");
              if (!ok) [...b.parentNode.children].forEach((x, i) => { if (opts[i].id === it.id) x.classList.add("right"); });
              res.textContent = ok ? "✅ " + t("great") : "💡 " + t("wrong");
              grade(it, ok);
              setTimeout(() => goTo(cards.indexOf(c) + 1), 900);
            });
            return b;
          })),
          res));
      c.play = () => SP.speak(it[T], T, { rate: app.ttsRate() });
      return el;
    }

    function endCard(c) {
      const el = h("section.reel.end", { "data-kind": "end" }, h("div.reel-main"));
      c.onShow = () => {
        const main = el.querySelector(".reel-main");
        main.innerHTML = "";
        ST.addSeconds(profile.id, Math.min(1800, Math.round((Date.now() - started) / 1000)));
        ST.flush(profile.id);
        main.append(...[
          h("div.big-emoji", "🎬"),
          h("h2", tx("end")),
          quizTotal ? h("div.stat-row", h("div.stat", h("div.stat-num", quizRight + "/" + quizTotal), h("div.stat-lbl", tx("quizScore")))) : null,
          h("div.small.muted", tx("recap")),
          h("div.recap", items.map((it) => h("button.recap-item", { type: "button", onclick: () => SP.speak(it[T], T, { rate: app.ttsRate() }) }, it.emoji ? it.emoji + " " : "", L(it[T], T), h("span.muted", " — "), L(it[H] || "", H)))),
          h("div.row.center",
            h("button.btn.primary", { type: "button", onclick: () => { app.go("#/reels"); } }, "🎬 " + tx("another")),
            h("button.btn.ghost", { type: "button", onclick: () => app.go("#/home") }, t("backHome")))].filter(Boolean));
      };
      return el;
    }

    cards.forEach((c) => {
      c.el = c.kind === "item" ? itemCard(c) : c.kind === "quiz" ? quizCard(c) : endCard(c);
      scroller.appendChild(c.el);
    });
    scroller.firstChild && scroller.firstChild.appendChild(h("div.swipe-hint", "⬆️ " + tx("swipe")));

    let current = -1;
    function play(c) { if (c && c.play) c.play(); }
    function playCurrent() { play(cards[current]); }
    function goTo(i) {
      const c = cards[i];
      if (c) c.el.scrollIntoView({ behavior: "smooth", block: "start" });
    }
    const io = new IntersectionObserver((entries) => {
      entries.forEach((e) => {
        if (e.isIntersecting && e.intersectionRatio > 0.6) {
          const i = cards.findIndex((c) => c.el === e.target);
          if (i === current) return;
          current = i;
          [...dots.children].forEach((d, j) => d.classList.toggle("on", j === i));
          const c = cards[i];
          if (c.onShow) c.onShow();
          if (soundOk) setTimeout(() => { if (current === i) play(c); }, 250);
        }
      });
    }, { root: scroller, threshold: [0.6] });
    cards.forEach((c) => io.observe(c.el));

    scroller.addEventListener("keydown", (e) => {
      if (e.key === "ArrowDown" || e.key === "PageDown" || e.key === " ") { e.preventDefault(); goTo(Math.min(cards.length - 1, current + 1)); }
      if (e.key === "ArrowUp" || e.key === "PageUp") { e.preventDefault(); goTo(Math.max(0, current - 1)); }
    });
    app.onLeave(() => { io.disconnect(); SP.stop(); });

    const wrap = h("div.reels-wrap", scroller, closeBtn, dots, soundHint);
    setTimeout(() => scroller.focus({ preventScroll: true }), 50);
    return wrap;
  }

  root.LSReels = { chooser, feed, highlight, TXT };
})(window);
