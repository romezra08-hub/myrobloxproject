// Daily quests: 3 small goals a day, all tied to real practice, with a chest when all are done.
(function (root) {
  const { h } = root.LSUI;
  const { pick } = root.LSI18n;
  const ST = root.LSStore;
  const U = root.LSUtil;

  const POOL = {
    xp: { icon: "⚡", goal: 40, he: "צברו {n} נקודות", en: "Earn {n} XP", ru: "Наберите {n} очков" },
    newWords: { icon: "✨", goal: 6, he: "למדו {n} מילים חדשות", en: "Learn {n} new words", ru: "Выучите {n} новых слов" },
    combo: { icon: "🔥", goal: 5, he: "{n} תשובות נכונות ברצף", en: "Get {n} right in a row", ru: "{n} верных ответов подряд" },
    perfect: { icon: "🎯", goal: 1, he: "שיעור עם 90% ומעלה", en: "Finish a lesson with 90%+", ru: "Урок на 90% и выше" },
    story: { icon: "📖", goal: 1, he: "קראו סיפור", en: "Read a story", ru: "Прочитайте историю" },
    spoken: { icon: "🎤", goal: 3, he: "אמרו {n} דברים נכון בקול", en: "Say {n} things correctly out loud", ru: "Скажите правильно {n} раза" },
    reels: { icon: "🎬", goal: 1, he: "סיימו פיד רילס", en: "Finish a Reels feed", ru: "Досмотрите ленту рилсов" },
    lessons: { icon: "📚", goal: 2, he: "סיימו {n} שיעורים", en: "Finish {n} lessons", ru: "Пройдите {n} урока" },
  };
  const TX = {
    title: { he: "משימות יומיות", en: "Daily quests", ru: "Задания дня" },
    chest: { he: "כל המשימות הושלמו! +30 נקודות 🎁", en: "All quests done! +30 XP 🎁", ru: "Все задания выполнены! +30 очков 🎁" },
    left: { he: "התחדשות בחצות", en: "New quests at midnight", ru: "Новые задания в полночь" },
  };

  function day(prog) {
    const k = U.dayKey();
    prog.daily = prog.daily || {};
    // keep only the last 7 days
    Object.keys(prog.daily).forEach((d) => { if (d < U.addDays(k, -7)) delete prog.daily[d]; });
    return (prog.daily[k] = prog.daily[k] || {});
  }

  function hash(s) { let x = 0; for (const c of s) x = (x * 31 + c.charCodeAt(0)) >>> 0; return x; }
  function todays(profile) {
    const keys = Object.keys(POOL).filter((k) => k !== "xp" && (k !== "spoken" || root.LSSpeech.canListen()));
    const seed = hash(U.dayKey() + profile.id);
    const picks = [];
    for (let i = 0; picks.length < 2 && i < 20; i++) { const k = keys[(seed + i * 7) % keys.length]; if (!picks.includes(k)) picks.push(k); }
    return ["xp"].concat(picks);
  }

  function value(prog, key) {
    const k = U.dayKey();
    if (key === "xp") return prog.xp[k] || 0;
    if (key === "newWords") return prog.newToday[k] || 0;
    return day(prog)[key] || 0;
  }

  function bump(profileId, key, n) {
    const prog = ST.progress(profileId);
    const d = day(prog);
    d[key] = key === "combo" ? Math.max(d[key] || 0, n || 0) : (d[key] || 0) + (n || 1);
    ST.saveProgress(profileId);
    checkChest(profileId);
  }

  function checkChest(profileId) {
    const prof = ST.profiles().find((p) => p.id === profileId);
    if (!prof) return;
    const prog = ST.progress(profileId);
    const d = day(prog);
    if (d.chest) return;
    if (todays(prof).every((k) => value(prog, k) >= POOL[k].goal)) {
      d.chest = 1;
      ST.addXp(profileId, 30);
      root.LSUI.toast(pick(TX.chest));
      root.LSUI.sfx("done");
    }
  }

  function card(profile) {
    const prog = ST.progress(profile.id);
    const d = day(prog);
    const rows = todays(profile).map((k) => {
      const q = POOL[k];
      const v = Math.min(q.goal, value(prog, k));
      const done = v >= q.goal;
      return h("div.quest" + (done ? ".done" : ""),
        h("span.quest-icon", done ? "✅" : q.icon),
        h("div.quest-main",
          h("div.quest-text", pick(q).replace("{n}", q.goal)),
          h("div.quest-bar", h("i", { style: { width: Math.round((v / q.goal) * 100) + "%" } }), h("span", v + " / " + q.goal))));
    });
    return h("div.card.quests",
      h("div.quests-head", h("b", "🏅 " + pick(TX.title)), h("span.small.muted", d.chest ? "🎁 ✓" : pick(TX.left))),
      rows);
  }

  root.LSQuests = { card, bump, checkChest, todays, value };
})(window);
