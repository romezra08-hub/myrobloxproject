// Habit loop helpers: levels (investment), mystery bonus (variable reward), reminders + if-then plan (trigger).
(function (root) {
  const { h, L, speakerBtn } = root.LSUI;
  const { pick } = root.LSI18n;
  const ST = root.LSStore;
  const U = root.LSUtil;

  const T = {
    level: { he: "רמה", en: "Level", ru: "Уровень" },
    mystery: { he: "🎁 הפתעה!", en: "🎁 Mystery bonus!", ru: "🎁 Сюрприз!" },
    bonusXp: { he: "בונוס: +{n} נקודות", en: "Bonus: +{n} XP", ru: "Бонус: +{n} очков" },
    sneak: { he: "הצצה למילה של מחר:", en: "Sneak peek at tomorrow's word:", ru: "Слово завтрашнего дня:" },
    funFact: { he: "הידעת?", en: "Did you know?", ru: "А вы знали?" },
    rest: { he: "עמדת ביעד היומי. מנוחה ושינה עוזרות למוח לשמור את מה שלמדת 😴", en: "Daily goal done. Rest and sleep help your brain keep what you learned 😴", ru: "Цель дня выполнена. Отдых и сон помогают мозгу закрепить выученное 😴" },
    plan: { he: "התוכנית שלי: מתי ואיפה אלמד?", en: "My plan: when and where will I study?", ru: "Мой план: когда и где я занимаюсь?" },
    planPh: { he: "למשל: אחרי הקפה של הבוקר, על הספה", en: "e.g. After my morning coffee, on the sofa", ru: "например: после утреннего кофе, на диване" },
    planWhy: { he: "תוכנית \"אם-אז\" מוכחת מחקרית כעוזרת לבנות הרגל.", en: "An \"if-then\" plan is proven to help build habits.", ru: "План «если-то» доказанно помогает выработать привычку." },
    reminder: { he: "תזכורת יומית ביומן", en: "Daily calendar reminder", ru: "Ежедневное напоминание в календаре" },
    reminderBtn: { he: "הוספה ליומן", en: "Add to calendar", ru: "Добавить в календарь" },
  };
  const tx = (k, v) => { let s = pick(T[k]); if (v) Object.keys(v).forEach((kk) => (s = s.split("{" + kk + "}").join(v[kk]))); return s; };

  const FACTS = [
    { he: "ברוסית אין מילה ל-\"a\" או \"the\".", en: "Russian has no words for \"a\" or \"the\".", ru: "В русском нет слов «a» и «the»." },
    { he: "באנגלית כ-1,000 מילים מכסות בערך 80% ממה שאנשים אומרים ביום-יום.", en: "About 1,000 words cover roughly 80% of everyday English speech.", ru: "Около 1000 слов покрывают примерно 80% повседневной английской речи." },
    { he: "האלפבית הרוסי (קירילי) נקרא על שם הנזיר קירילוס.", en: "The Cyrillic alphabet is named after Saint Cyril.", ru: "Кириллица названа в честь святого Кирилла." },
    { he: "ללמוד שפה בכל גיל מחזק את הזיכרון והמוח.", en: "Learning a language at any age strengthens memory and the brain.", ru: "Изучение языка в любом возрасте укрепляет память и мозг." },
    { he: "המילה האנגלית הנפוצה ביותר היא the.", en: "The most common English word is \"the\".", ru: "Самое частое английское слово — «the»." },
    { he: "ברוסית ההטעמה יכולה לשנות משמעות: за́мок (טירה) / замо́к (מנעול).", en: "In Russian, stress can change meaning: за́мок (castle) / замо́к (lock).", ru: "В русском ударение меняет смысл: за́мок / замо́к." },
    { he: "טעויות עוזרות ללמוד: המוח זוכר טוב יותר תשובה שתוקנה.", en: "Mistakes help: the brain remembers corrected answers better.", ru: "Ошибки помогают: исправленный ответ запоминается лучше." },
    { he: "לומדים שהופכים את זה להרגל יומי זוכרים פי כמה יותר מאלו שלומדים פעם בשבוע.", en: "A little every day beats one long session a week for memory.", ru: "Понемногу каждый день лучше для памяти, чем раз в неделю много." },
  ];

  function totalXp(id) {
    const p = ST.progress(id);
    return Object.values(p.xp).reduce((a, b) => a + b, 0);
  }
  function levelOf(xp) {
    const lvl = Math.floor(Math.sqrt(xp / 40)) + 1;
    const cur = 40 * (lvl - 1) * (lvl - 1), nxt = 40 * lvl * lvl;
    return { lvl, pct: Math.round(((xp - cur) / (nxt - cur)) * 100) };
  }
  function levelChip(id) {
    const l = levelOf(totalXp(id));
    return h("span.level-chip", { title: l.pct + "%" }, "⭐ " + tx("level") + " " + l.lvl, h("i", { style: { width: l.pct + "%" } }));
  }

  // Variable reward shown at the end of a lesson.
  function mysteryBonus(profile) {
    const r = Math.random();
    const box = h("div.mystery", h("div.mystery-title", tx("mystery")));
    if (r < 0.45) {
      const n = [5, 5, 10, 10, 15, 20, 30][Math.floor(Math.random() * 7)];
      ST.addXp(profile.id, n);
      box.appendChild(h("div.mystery-body.big", tx("bonusXp", { n })));
    } else if (r < 0.75) {
      const prog = ST.progress(profile.id);
      const next = root.LSContent.unseen(prog, root.LSContent.curriculum())[0];
      if (next) box.appendChild(h("div.mystery-body", h("div.small", tx("sneak")), next.emoji ? h("span.emoji", next.emoji + " ") : null, L(next[profile.target], profile.target, "strong"), speakerBtn(next[profile.target], profile.target), h("div.muted", L(next[profile.help] || "", profile.help))));
      else box.appendChild(h("div.mystery-body.big", tx("bonusXp", { n: 10 })));
    } else {
      box.appendChild(h("div.mystery-body", h("b", tx("funFact") + " "), pick(FACTS[Math.floor(Math.random() * FACTS.length)])));
    }
    if ((ST.progress(profile.id).xp[U.dayKey()] || 0) >= (profile.dailyGoal || 50)) box.appendChild(h("div.small.muted", tx("rest")));
    return box;
  }

  // Calendar file (.ics) with a daily recurring reminder and an alarm.
  function downloadReminder(time, title) {
    const [hh, mm] = (time || "19:00").split(":");
    const d = new Date(); d.setDate(d.getDate() + 1);
    const ymd = U.dayKey(d).replace(/-/g, "");
    const ics = ["BEGIN:VCALENDAR", "VERSION:2.0", "PRODID:-//LearnTogether//EN", "BEGIN:VEVENT",
      "UID:lt-" + Date.now() + "@learn-together", "DTSTAMP:" + new Date().toISOString().replace(/[-:]/g, "").slice(0, 15) + "Z",
      `DTSTART:${ymd}T${hh}${mm}00`, "DURATION:PT10M", "RRULE:FREQ=DAILY", "SUMMARY:" + title,
      "BEGIN:VALARM", "TRIGGER:PT0M", "ACTION:DISPLAY", "DESCRIPTION:" + title, "END:VALARM", "END:VEVENT", "END:VCALENDAR"].join("\r\n");
    const a = h("a", { href: URL.createObjectURL(new Blob([ics], { type: "text/calendar" })), download: "learn-together-reminder.ics" });
    document.body.appendChild(a); a.click(); a.remove();
  }

  function settingsCard(app) {
    const p = app.profile();
    const plan = h("input.text-in", { type: "text", value: p.plan || "", placeholder: tx("planPh"), dir: "auto", maxlength: 80 });
    plan.addEventListener("change", () => { ST.updateProfile(p.id, { plan: plan.value.trim() }); app.refreshProfile(); });
    const time = h("input.text-in", { type: "time", value: p.remindAt || "19:00", style: { maxWidth: "140px" } });
    time.addEventListener("change", () => { ST.updateProfile(p.id, { remindAt: time.value }); app.refreshProfile(); });
    return h("div.card",
      h("div.field", h("span", tx("plan")), plan, h("div.small.muted", tx("planWhy"))),
      h("div.field", h("span", tx("reminder")), h("div.row", time, h("button.btn.ghost", { type: "button", onclick: () => downloadReminder(time.value, "🗣️ " + pick({ he: "לומדים ביחד — 10 דקות", en: "Learn Together — 10 minutes", ru: "Учим вместе — 10 минут" })) }, "📅 " + tx("reminderBtn")))));
  }

  root.LSHabits = { levelChip, levelOf, totalXp, mysteryBonus, settingsCard, downloadReminder };
})(window);
