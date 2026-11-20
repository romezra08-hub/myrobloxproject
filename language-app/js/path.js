// Learning path: a winding trail of lesson nodes, one unit per topic, plus Lisa the fox mascot.
(function (root) {
  const { h } = root.LSUI;
  const { pick } = root.LSI18n;
  const ST = root.LSStore;
  const C = root.LSContent;
  const SP = root.LSSpeech;
  const D = () => root.LS_DATA || {};
  const PER_NODE = 6;

  const TX = {
    unit: { he: "יחידה", en: "Unit", ru: "Раздел" },
    start: { he: "התחלה", en: "START", ru: "СТАРТ" },
    again: { he: "חזרה", en: "PRACTICE", ru: "ПОВТОР" },
    locked: { he: "סיימו את השיעור הקודם קודם 🔒", en: "Finish the previous lesson first 🔒", ru: "Сначала пройдите предыдущий урок 🔒" },
    path: { he: "המסלול שלי", en: "My path", ru: "Мой путь" },
  };
  const LINES = {
    he: ["יאללה! עוד שיעור קטן ואנחנו בדרך 🦊", "כל יום קצת — ככה זוכרים לתמיד!", "טעויות זה טוב, ככה המוח לומד 💪", "אני גאה בך! ממשיכים?", "5 דקות עכשיו שוות שעה בעוד שבוע ⏱️"],
    en: ["Let's go! One small lesson and we're on our way 🦊", "A little every day — that's how words stick!", "Mistakes are great, that's how brains learn 💪", "I'm proud of you! Shall we continue?", "5 minutes now beats an hour next week ⏱️"],
    ru: ["Вперёд! Один маленький урок — и мы в пути 🦊", "Понемногу каждый день — так слова запоминаются!", "Ошибки — это хорошо, так мозг учится 💪", "Я горжусь тобой! Продолжим?", "5 минут сейчас лучше часа через неделю ⏱️"],
  };

  function mascot(text, mood) {
    return h("div.mascot" + (mood ? "." + mood : ""), h("div.fox", { "aria-hidden": "true" }, "🦊"), h("div.bubble-say", text));
  }
  function mascotLine() {
    const l = LINES[root.LSI18n.getLang()] || LINES.en;
    return l[Math.floor(Date.now() / 36e5) % l.length]; // changes every hour
  }

  const UNIT_COLORS = ["#58b80a", "#1c9cf0", "#ce82ff", "#ff9600", "#ff4b4b", "#00b8a9", "#7048e8", "#f0428c"];

  function units(prog) {
    const topics = (D().topics || []).filter((tp) => C.vocab().some((v) => v.topic === tp.id));
    let foundCurrent = false;
    return topics.map((tp, ui) => {
      const words = C.vocab().filter((v) => v.topic === tp.id);
      const nodes = [];
      for (let i = 0; i < words.length; i += PER_NODE) {
        const slice = words.slice(i, i + PER_NODE);
        const seen = slice.filter((w) => prog.cards[w.id]).length;
        const done = seen === slice.length;
        let state = done ? "done" : "locked";
        if (!done && !foundCurrent) { state = "current"; foundCurrent = true; }
        nodes.push({ state, slice, seen });
      }
      return { tp, ui, nodes, color: UNIT_COLORS[ui % UNIT_COLORS.length] };
    });
  }

  function render(app) {
    const p = app.profile();
    const prog = ST.progress(p.id);
    const list = units(prog);
    const wrap = h("div.path");
    let n = 0;
    list.forEach((u) => {
      const doneAll = u.nodes.every((x) => x.state === "done");
      wrap.appendChild(h("div.unit-banner", { style: { "--uc": u.color } },
        h("div", h("div.unit-kicker", pick(TX.unit) + " " + (u.ui + 1)), h("div.unit-title", pick(u.tp))),
        h("a.unit-book", { href: "#/topic/" + u.tp.id, "aria-label": pick(u.tp) }, doneAll ? "👑" : u.tp.emoji)));
      const trail = h("div.trail");
      u.nodes.forEach((node, i) => {
        const x = Math.round(Math.sin((n++) * 0.9) * 70);
        const icon = node.state === "done" ? "👑" : i === u.nodes.length - 1 ? "🏆" : node.state === "current" ? "⭐" : "🔒";
        const btn = h("button.node." + node.state, { type: "button", style: { "--x": x + "px", "--uc": u.color }, "aria-label": pick(u.tp) + " " + (i + 1) }, h("span.node-icon", icon),
          node.state === "current" ? h("span.node-tip", pick(TX.start)) : null,
          node.state !== "locked" && node.seen && node.state !== "done" ? h("span.node-ring", { style: { "--p": Math.round((node.seen / node.slice.length) * 100) } }) : null);
        btn.addEventListener("click", () => {
          if (node.state === "locked") { root.LSUI.toast(pick(TX.locked)); root.LSUI.sfx("wrong"); return; }
          root.LSUI.sfx("tap");
          const plan = C.buildTopic(p, prog, u.tp.id, { canListen: SP.canListen(), newCount: PER_NODE });
          root.LSSession.run({ steps: plan.steps, back: "#/home" });
        });
        trail.appendChild(btn);
      });
      wrap.appendChild(trail);
    });
    setTimeout(() => { const cur = wrap.querySelector(".node.current"); if (cur && cur.getBoundingClientRect().top > window.innerHeight) cur.scrollIntoView({ block: "center", behavior: "smooth" }); }, 400);
    return h("section.path-section", h("h2.section-title", "🛤️ " + pick(TX.path)), wrap);
  }

  root.LSPath = { render, mascot, mascotLine };
})(window);
