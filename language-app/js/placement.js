// Placement check: a quick quiz across levels; correctly answered words are marked known,
// so returning/partial learners don't have to start from zero.
(function (root) {
  const { h } = root.LSUI;
  const { pick } = root.LSI18n;
  const ST = root.LSStore;
  const C = root.LSContent;
  const SRS = root.LSSrs;
  const U = root.LSUtil;
  const TX = {
    title: { he: "כבר יודעים קצת?", en: "Already know some?", ru: "Уже что-то знаете?" },
    sub: { he: "בדיקה של 2 דקות — מילים שתדעו יסומנו כידועות ותדלגו עליהן.", en: "A 2-minute check: words you know get marked as known and skipped.", ru: "Проверка на 2 минуты: знакомые слова отметятся как выученные." },
    done: { he: "מילים סומנו כידועות", en: "words marked as known", ru: "слов отмечено как известные" },
  };

  function card(app) {
    const p = app.profile();
    const prog = ST.progress(p.id);
    if (prog.placementDone || Object.keys(prog.cards).length > 20) return null;
    return h("button.card.action-card.placement", { type: "button", onclick: () => run(app) },
      h("span.ac-emoji", "🧭"), h("div", h("b", pick(TX.title)), h("div.small.muted", pick(TX.sub))));
  }

  function run(app) {
    const p = app.profile();
    const prog = ST.progress(p.id);
    const cur = C.curriculum().filter((v) => !prog.cards[v.id]);
    // sample evenly across the curriculum (easy → hard)
    const picks = [];
    const n = 16;
    for (let i = 0; i < n; i++) { const v = cur[Math.floor((i / n) * cur.length)]; if (v && !picks.includes(v)) picks.push(v); }
    const known = [];
    const steps = picks.map((v) => ({ kind: "mc", dir: "h2t", item: C.item(v.id), placement: true }));
    root.LSSession.run({
      steps, requeue: false, back: "#/home",
      onResult: (step, ok) => { if (ok) known.push(step.item.id); },
      onComplete: () => {
        const now = Date.now();
        // a right answer here means "already known": schedule it a week out
        known.forEach((id) => { const c = SRS.newCard(now); prog.cards[id] = Object.assign(c, { state: "review", ivl: 7, reps: 1, right: 1, due: now + 7 * SRS.DAY }); });
        // words never answered right stay new; wrongly answered ones are removed so they're taught properly
        picks.forEach((v) => { if (!known.includes(v.id)) delete prog.cards[v.id]; });
        prog.placementDone = true;
        ST.saveProgress(p.id);
      },
      summaryExtra: () => h("div.notice", "🧭 " + known.length + " " + pick(TX.done)),
    });
  }
  root.LSPlacement = { card, run };
})(window);
