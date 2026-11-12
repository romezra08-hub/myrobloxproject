// Runs a list of exercise steps: progress bar, feedback, SRS updates, re-queues mistakes, summary.
(function (root) {
  const { h, L, speakerBtn, confirmBox, confetti } = root.LSUI;
  const { t } = root.LSI18n;
  const SRS = root.LSSrs;
  const ST = root.LSStore;
  const SP = root.LSSpeech;
  const U = root.LSUtil;

  const I = () => root.LSI18n.getLang();
  function run(opts) {
    const app = root.LSApp;
    const profile = app.profile();
    const prog = ST.progress(profile.id);
    const steps = opts.steps.slice();
    const started = Date.now();
    let idx = 0, right = 0, wrong = 0, xp = 0, ended = false, combo = 0, bestCombo = 0;
    let checkFn = null;
    const results = [];

    const bar = h("div.pbar-fill");
    const quitBtn = h("button.icon-btn", { type: "button", "aria-label": t("quit"), onclick: () => quit() }, "✕");
    const counter = h("span.counter");
    const top = h("div.session-top", quitBtn, h("div.pbar", bar), counter);
    const body = h("div.session-body");
    const fb = h("div.feedback", { "aria-live": "polite" });
    const mainBtn = h("button.btn.primary.main-btn", { type: "button" }, t("check"));
    mainBtn.addEventListener("click", () => { if (!mainBtn.disabled && checkFn) checkFn(); });
    const foot = h("div.session-foot", fb, mainBtn);
    const screen = h("div.session", top, body, foot);
    app.mount(screen, { session: true });

    const onKey = (e) => {
      if (e.key === "Enter" && !mainBtn.disabled && checkFn && !(e.target && e.target.tagName === "TEXTAREA")) {
        if (e.target && e.target.tagName === "INPUT" && mainBtn.dataset.mode === "check") return; // input handles its own Enter
        if (e.target === mainBtn) return; // the focused main button gets a native click
        e.preventDefault();
        checkFn();
      }
    };
    document.addEventListener("keydown", onKey);
    app.onLeave(() => { document.removeEventListener("keydown", onKey); saveTime(); SP.stop(); SP.cancelListen(); });

    let timeSaved = false;
    function saveTime() {
      if (timeSaved) return;
      timeSaved = true;
      ST.addSeconds(profile.id, Math.min(3600, Math.round((Date.now() - started) / 1000)));
      ST.flush(profile.id);
    }

    function setCheck(enabled, fn, label) {
      checkFn = fn || checkFn;
      mainBtn.disabled = !enabled;
      mainBtn.textContent = label || t("check");
      mainBtn.dataset.mode = "check";
    }

    function updateBar() {
      bar.style.width = Math.round((idx / Math.max(1, steps.length)) * 100) + "%";
      counter.textContent = Math.min(idx + 1, steps.length) + "/" + steps.length;
    }

    function gradeItem(id, correct, res) {
      const before = prog.cards[id] || SRS.newCard();
      const grade = SRS.gradeFrom(correct, { close: res.close });
      prog.cards[id] = SRS.review(before, grade, Date.now());
      if (!correct) {
        prog.log.unshift({ id, t: Date.now() });
        prog.log = prog.log.slice(0, 200);
      }
    }

    function finish(res) {
      if (ended) return;
      const step = steps[idx];
      if (step._done) return;
      step._done = true;
      res = res || {};

      if (res.intro) {
        if (step.item && !prog.cards[step.item.id]) {
          prog.cards[step.item.id] = SRS.newCard();
          const k = U.dayKey();
          prog.newToday[k] = (prog.newToday[k] || 0) + 1;
        }
        if (res.letter) {
          const ls = prog.letters[res.letter] || (prog.letters[res.letter] = { seen: 0, right: 0, wrong: 0 });
          ls.seen = (ls.seen || 0) + 1;
        }
        xp += 2;
        ST.saveProgress(profile.id);
        return next();
      }
      if (res.correct === null || res.skipped) {
        results.push({ step, skipped: true });
        return next();
      }

      if (step.pretest) {
        xp += 3;
        root.LSUI.sfx(res.correct ? "right" : "tap");
        fb.innerHTML = "";
        fb.className = "feedback show good";
        fb.appendChild(h("div.fb-title", res.correct ? "🎯 " + { he: "ניחוש מעולה!", en: "Great guess!", ru: "Отличная догадка!" }[I()] : "💡 " + { he: "עכשיו את/ה יודע/ת — ככה זוכרים טוב יותר!", en: "Now you know — guessing first helps you remember!", ru: "Теперь вы знаете — догадка помогает запомнить!" }[I()]));
        mainBtn.disabled = false; mainBtn.textContent = t("next"); mainBtn.dataset.mode = "next"; checkFn = next;
        return;
      }
      const correct = !!res.correct;
      if (correct) right++; else wrong++;
      combo = correct ? combo + 1 : 0;
      bestCombo = Math.max(bestCombo, combo);
      if (correct && combo >= 3 && combo % (combo >= 10 ? 5 : 3) === 0) {
        root.LSUI.sfx("combo");
        xp += 5;
        const c = h("div.combo", "🔥 " + combo + " " + { he: "ברצף! +5", en: "in a row! +5", ru: "подряд! +5" }[root.LSI18n.getLang()]);
        screen.appendChild(c); setTimeout(() => c.remove(), 1000);
      } else root.LSUI.sfx(correct ? "right" : "wrong");
      xp += correct ? 10 : 2;
      results.push({ step, correct });

      if (step.item) gradeItem(step.item.id, correct, res);
      if (res.matchIds) res.matchIds.forEach((id) => gradeItem(id, true, res));
      if (res.letter) {
        const ls = prog.letters[res.letter] || (prog.letters[res.letter] = { seen: 1, right: 0, wrong: 0 });
        if (correct) ls.right = (ls.right || 0) + 1; else ls.wrong = (ls.wrong || 0) + 1;
      }
      if (opts.onResult) opts.onResult(step, correct);
      if (step.grammarReview && !step.requeued) {
        const gr = prog.grammar[step.grammarReview] || {};
        gr.rv = (gr.rv || 0) + 1; gr.rvOk = (gr.rvOk || 0) + (correct ? 1 : 0);
        if (gr.rv % 3 === 0) {
          const ok = gr.rvOk >= 2; gr.done = (gr.done || 1) + (ok ? 1 : 0);
          gr.due = Date.now() + (ok ? [3, 7, 14, 30, 60][Math.min(gr.done - 1, 4)] : 1) * 864e5; gr.rvOk = 0;
        }
        prog.grammar[step.grammarReview] = gr;
      }
      ST.saveProgress(profile.id);

      // Mistake? Ask again a little later (immediate re-retrieval), in an easier form.
      if (!correct && !step.requeued && opts.requeue !== false) {
        const again = step.item ? root.LSContent.easier(step) : Object.assign({}, step);
        again.requeued = true;
        delete again._done;
        steps.splice(Math.min(steps.length, idx + 3), 0, again);
      }

      showFeedback(correct, res, step);
    }

    function showFeedback(correct, res, step) {
      fb.innerHTML = "";
      fb.className = "feedback show " + (correct ? (res.close ? "close" : "good") : "bad");
      const lines = [];
      if (correct) {
        lines.push(h("div.fb-title", res.close ? "👍 " + t("almost") : "✅ " + praise()));
      } else {
        lines.push(h("div.fb-title", "💡 " + t("wrong")));
      }
      if (res.answer && (!correct || res.close) && !res.silentAnswer) {
        lines.push(h("div.fb-answer", !correct ? h("span.muted", t("correctAnswer") + " ") : null, L(res.answer, res.answerLang || "en", "strong"), speakerBtn(res.answer, res.answerLang || "en")));
      }
      if (res.sub && (!correct || res.close)) lines.push(h("div.fb-sub", L(res.sub, app.profile().help)));
      if (res.why && !correct) lines.push(h("div.fb-why", L(res.why, app.profile().help)));
      lines.forEach((l) => fb.appendChild(l));
      if (!correct && res.answer && res.answerLang && !res.silentAnswer) SP.speak(res.answer, res.answerLang, { rate: app.ttsRate() });
      mainBtn.disabled = false;
      mainBtn.textContent = t("next");
      mainBtn.dataset.mode = "next";
      checkFn = next;
      setTimeout(() => mainBtn.focus({ preventScroll: true }), 30);
    }

    function praise() {
      const p = [t("correct"), t("great"), t("good")];
      return p[Math.floor(Math.random() * p.length)];
    }

    function next() {
      idx++;
      if (idx >= steps.length) return end();
      show();
    }

    function show() {
      fb.className = "feedback";
      fb.innerHTML = "";
      updateBar();
      body.innerHTML = "";
      const step = steps[idx];
      const ctx = {
        profile: app.profile(), T: profile.target, H: profile.help, prog,
        rate: app.ttsRate(), canListen: SP.canListen(),
        finish, setCheck,
      };
      setCheck(false, null);
      try {
        const el = root.LSEx.render(step, ctx);
        body.appendChild(el);
        body.scrollTop = 0;
      } catch (e) {
        console.error(e);
        next();
      }
    }

    async function quit() {
      if (idx > 0 && !(await confirmBox(t("quitConfirm")))) return;
      ended = true;
      saveTime();
      app.go(opts.back || "#/home");
    }

    function end() {
      ended = true;
      xp += 10;
      ST.addXp(profile.id, xp);
      saveTime();
      if (opts.onComplete) opts.onComplete({ right, wrong, xp, results });
      const total = right + wrong;
      const acc = total ? Math.round((right / total) * 100) : 100;
      const streak = ST.streak(profile.id);
      body.innerHTML = "";
      fb.className = "feedback";
      updateBar();
      bar.style.width = "100%";
      body.appendChild(h("div.summary",
        h("div.big-emoji", acc >= 90 ? "🏆" : acc >= 70 ? "🌟" : "💪"),
        h("h2", t("lessonDone")),
        h("div.stat-row",
          h("div.stat", h("div.stat-num", "+" + xp), h("div.stat-lbl", t("xp"))),
          h("div.stat", h("div.stat-num", acc + "%"), h("div.stat-lbl", t("accuracy"))),
          h("div.stat", h("div.stat-num", "🔥 " + streak), h("div.stat-lbl", t("streak"))),
          bestCombo >= 3 ? h("div.stat", h("div.stat-num", "⚡ " + bestCombo), h("div.stat-lbl", { he: "רצף הכי ארוך", en: "best combo", ru: "лучшая серия" }[root.LSI18n.getLang()])) : null),
        opts.summaryExtra ? opts.summaryExtra({ right, wrong, xp }) : null,
        root.LSHabits ? root.LSHabits.mysteryBonus(profile) : null));
      confetti();
      root.LSUI.sfx("done");
      mainBtn.disabled = false;
      mainBtn.textContent = t(opts.back && opts.back !== "#/home" ? "back" : "backHome");
      mainBtn.dataset.mode = "next";
      checkFn = () => app.go(opts.back || "#/home");
    }

    if (!steps.length) {
      body.appendChild(h("div.summary", h("div.big-emoji", "🎉"), h("p", t("allDone"))));
      setCheck(true, () => app.go(opts.back || "#/home"), t("back"));
      return;
    }
    show();
  }

  root.LSSession = { run };
})(window);
