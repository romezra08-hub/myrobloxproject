// App shell: router, layout, profile handling.
(function (root) {
  const { h } = root.LSUI;
  const I = root.LSI18n;
  const { t } = I;
  const ST = root.LSStore;

  const appEl = () => document.getElementById("app");
  let leaveHandlers = [];
  let currentProfile = null;

  const App = {
    profile() { return currentProfile; },
    setProfile(p) {
      currentProfile = p;
      if (p) ST.setActive(p.id);
      applyLang();
    },
    refreshProfile() { if (currentProfile) currentProfile = ST.profiles().find((p) => p.id === currentProfile.id) || null; applyLang(); },
    ttsRate() { return (currentProfile && currentProfile.ttsRate) || 0.9; },
    go(hash) { if (location.hash === hash) route(); else location.hash = hash; },
    onLeave(fn) { leaveHandlers.push(fn); },
    mount(el, opts) {
      opts = opts || {};
      const root2 = appEl();
      root2.innerHTML = "";
      root2.className = opts.session ? "in-session" : opts.full ? "in-full" : "";
      root2.appendChild(el);
      if (!opts.session && !opts.full && currentProfile) root2.appendChild(nav());
      window.scrollTo(0, 0);
    },
    header(title, backHash, extra) {
      return h("header.page-head",
        backHash ? h("button.icon-btn.back", { type: "button", "aria-label": t("back"), onclick: () => App.go(backHash) }, I.getLang() === "he" ? "→" : "←") : null,
        h("h1", title), extra || null);
    },
  };

  function applyLang() {
    const ui = (currentProfile && currentProfile.ui) || guessLang();
    I.setLang(ui);
    document.documentElement.lang = ui;
    document.documentElement.dir = ui === "he" ? "rtl" : "ltr";
    document.documentElement.classList.toggle("large-text", !!(currentProfile && currentProfile.large));
    document.title = t("appName");
  }

  function guessLang() {
    const n = (navigator.language || "he").slice(0, 2);
    return ["he", "ru", "en"].includes(n) ? n : "he";
  }

  function nav() {
    const cur = (location.hash || "#/home").split("/")[1] || "home";
    const item = (hash, icon, key) => h("a.nav-item" + (cur === hash ? ".on" : ""), { href: "#/" + hash }, h("span.nav-icon", icon), h("span.nav-lbl", t(key)));
    return h("nav.bottom-nav", item("home", "🏠", "home"), item("learn", "📚", "learn"), item("reels", "🎬", "reelsNav"), item("progress", "📈", "progress"), item("settings", "⚙️", "settings"));
  }
  I.strings.reelsNav = { he: "רילס", en: "Reels", ru: "Рилсы" };

  function route() {
    leaveHandlers.forEach((f) => { try { f(); } catch (e) { console.error(e); } });
    leaveHandlers = [];
    const parts = (location.hash || "#/home").replace(/^#\/?/, "").split("/").map(decodeURIComponent);
    if (!currentProfile) {
      const p = ST.active();
      if (p) App.setProfile(p);
    }
    applyLang();
    if (!currentProfile && parts[0] !== "setup") return root.LSScreens.profiles(App);
    const S = root.LSScreens;
    const name = parts[0] || "home";
    const handler = S.routes[name] || S.routes.home;
    try {
      handler(App, parts.slice(1));
    } catch (e) {
      console.error(e);
      App.mount(h("div.page", h("p", "⚠️ " + e.message), h("button.btn", { onclick: () => App.go("#/home") }, t("backHome"))));
    }
  }

  window.addEventListener("hashchange", route);
  window.addEventListener("beforeunload", () => { if (currentProfile) ST.flush(currentProfile.id); });
  document.addEventListener("visibilitychange", () => { if (document.hidden && currentProfile) ST.flush(currentProfile.id); });

  root.LSApp = App;
  root.addEventListener("DOMContentLoaded", route);
})(window);
