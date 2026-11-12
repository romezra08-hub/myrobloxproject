// Small DOM toolkit: element builder, toasts, modals, audio buttons, on-screen keyboard.
(function (root) {
  const { t } = root.LSI18n;

  // h("div.card#id", {onclick, dir, html, ...attrs}, children...)
  function h(sel, attrs, ...kids) {
    const m = sel.match(/^([a-z0-9]+)?((?:[.#][\w-]+)*)$/i);
    const el = document.createElement((m && m[1]) || "div");
    if (m && m[2]) {
      m[2].replace(/([.#])([\w-]+)/g, (_, p, n) => { if (p === ".") el.classList.add(n); else el.id = n; });
    }
    if (attrs && (typeof attrs !== "object" || attrs instanceof Node || Array.isArray(attrs))) { kids.unshift(attrs); attrs = null; }
    if (attrs) {
      for (const k in attrs) {
        const v = attrs[k];
        if (v == null || v === false) continue;
        if (k.startsWith("on") && typeof v === "function") el.addEventListener(k.slice(2), v);
        else if (k === "html") el.innerHTML = v;
        else if (k === "text") el.textContent = v;
        else if (k === "class") el.className += " " + v;
        else if (k === "style" && typeof v === "object") Object.keys(v).forEach((sk) => (sk.startsWith("--") ? el.style.setProperty(sk, v[sk]) : (el.style[sk] = v[sk])));
        else el.setAttribute(k, v === true ? "" : v);
      }
    }
    append(el, kids);
    return el;
  }
  function append(el, kids) {
    kids.forEach((k) => {
      if (k == null || k === false) return;
      if (Array.isArray(k)) append(el, k);
      else el.appendChild(k instanceof Node ? k : document.createTextNode(String(k)));
    });
  }

  // Text in a specific language, isolated for correct bidi rendering.
  function L(text, lang, cls) {
    const dir = lang === "he" ? "rtl" : "ltr";
    return h("span" + (cls ? "." + cls.split(" ").join(".") : ""), { lang: lang, dir: dir }, text);
  }

  function toast(msg, ms) {
    const el = h("div.toast", { role: "status" }, msg);
    document.body.appendChild(el);
    requestAnimationFrame(() => el.classList.add("show"));
    setTimeout(() => { el.classList.remove("show"); setTimeout(() => el.remove(), 300); }, ms || 2600);
  }

  function confirmBox(msg) {
    return new Promise((resolve) => {
      const close = (v) => { overlay.remove(); resolve(v); };
      const overlay = h("div.overlay", { onclick: (e) => { if (e.target === overlay) close(false); } },
        h("div.modal", { role: "dialog", "aria-modal": "true" },
          h("p", msg),
          h("div.row.end",
            h("button.btn.ghost", { onclick: () => close(false) }, t("cancel")),
            h("button.btn.danger", { onclick: () => close(true) }, "OK"))));
      document.body.appendChild(overlay);
    });
  }

  function speakerBtn(getText, lang, opts) {
    opts = opts || {};
    const rate = () => (opts.rate || (root.LSApp && root.LSApp.ttsRate()) || 0.9);
    const btn = h("button.icon-btn.speaker" + (opts.big ? ".big" : ""), { type: "button", "aria-label": t("listen"), title: t("listen") }, "🔊");
    btn.addEventListener("click", async (e) => {
      e.stopPropagation();
      btn.classList.add("playing");
      await root.LSSpeech.speak(typeof getText === "function" ? getText() : getText, lang, { rate: rate() });
      btn.classList.remove("playing");
    });
    if (!opts.withSlow) return btn;
    const slow = h("button.icon-btn.speaker.slow", { type: "button", "aria-label": t("slow"), title: t("slow") }, "🐢");
    slow.addEventListener("click", async (e) => {
      e.stopPropagation();
      slow.classList.add("playing");
      await root.LSSpeech.speak(typeof getText === "function" ? getText() : getText, lang, { rate: 0.55 });
      slow.classList.remove("playing");
    });
    return h("span.speakers", btn, slow);
  }

  const LAYOUTS = {
    ru: ["йцукенгшщзхъ", "фывапролджэ", "ячсмитьбюё"],
    en: ["qwertyuiop", "asdfghjkl", "zxcvbnm'"],
  };

  // On-screen keyboard bound to an <input>.
  function keyboard(input, lang) {
    const rows = LAYOUTS[lang];
    if (!rows) return null;
    let upper = false;
    const insert = (ch) => {
      const s = input.selectionStart == null ? input.value.length : input.selectionStart;
      const e = input.selectionEnd == null ? input.value.length : input.selectionEnd;
      input.value = input.value.slice(0, s) + ch + input.value.slice(e);
      const pos = s + ch.length;
      try { input.setSelectionRange(pos, pos); } catch (err) {}
      input.dispatchEvent(new Event("input", { bubbles: true }));
    };
    const kb = h("div.kb", { dir: "ltr", lang: lang });
    const render = () => {
      kb.innerHTML = "";
      rows.forEach((r, i) => {
        const row = h("div.kb-row");
        if (i === rows.length - 1) row.appendChild(h("button.kb-key.wide", { type: "button", onclick: () => { upper = !upper; render(); } }, "⇧"));
        [...r].forEach((ch) => {
          const c = upper ? ch.toUpperCase() : ch;
          row.appendChild(h("button.kb-key", { type: "button", onclick: () => { insert(c); if (upper) { upper = false; render(); } } }, c));
        });
        if (i === rows.length - 1) row.appendChild(h("button.kb-key.wide", { type: "button", "aria-label": "backspace", onclick: () => {
          const s = input.selectionStart, e = input.selectionEnd;
          if (s !== e) insert("");
          else if (s > 0) { input.setSelectionRange(s - 1, s); insert(""); }
        } }, "⌫"));
        kb.appendChild(row);
      });
      kb.appendChild(h("div.kb-row", h("button.kb-key.space", { type: "button", onclick: () => insert(" ") }, " ")));
    };
    render();
    return kb;
  }

  function confetti() {
    const wrap = h("div.confetti", { "aria-hidden": "true" });
    const colors = ["#ff6b6b", "#ffd93d", "#6bcB77", "#4d96ff", "#c77dff"];
    for (let i = 0; i < 40; i++) {
      wrap.appendChild(h("i", { style: { left: Math.random() * 100 + "%", background: colors[i % colors.length], animationDelay: Math.random() * 0.6 + "s", transform: `rotate(${Math.random() * 360}deg)` } }));
    }
    document.body.appendChild(wrap);
    setTimeout(() => wrap.remove(), 2600);
  }

  // Save a file: platform downloads capability inside an artifact, plain link elsewhere.
  async function saveFile(filename, data, type) {
    if (root.claude && root.claude.use) {
      try {
        const dl = await root.claude.use("downloads");
        if (dl) { await dl.save({ filename, data: new Blob([data], { type }) }); return true; }
      } catch (e) { return false; }
      return false;
    }
    const a = h("a", { href: URL.createObjectURL(new Blob([data], { type })), download: filename });
    document.body.appendChild(a); a.click(); a.remove();
    return true;
  }

  // Tiny game sounds made with WebAudio (no files needed) + a little vibration.
  let actx = null;
  function sfx(kind) {
    const prof = root.LSApp && root.LSApp.profile();
    if (prof && prof.sfx === false) return;
    try {
      actx = actx || new (root.AudioContext || root.webkitAudioContext)();
      const notes = { right: [660, 880], wrong: [220, 175], combo: [660, 880, 1175], done: [523, 659, 784, 1047], tap: [520] }[kind] || [600];
      notes.forEach((f, i) => {
        const o = actx.createOscillator(), g = actx.createGain();
        o.type = kind === "wrong" ? "triangle" : "sine";
        o.frequency.value = f;
        const t0 = actx.currentTime + i * 0.09;
        g.gain.setValueAtTime(0.0001, t0);
        g.gain.exponentialRampToValueAtTime(kind === "tap" ? 0.05 : 0.16, t0 + 0.02);
        g.gain.exponentialRampToValueAtTime(0.0001, t0 + 0.22);
        o.connect(g); g.connect(actx.destination);
        o.start(t0); o.stop(t0 + 0.25);
      });
      if (navigator.vibrate) navigator.vibrate(kind === "wrong" ? [40, 60, 40] : kind === "right" ? 15 : 0);
    } catch (e) {}
  }

  root.LSUI = { sfx, saveFile, h, L, toast, confirmBox, speakerBtn, keyboard, confetti };
})(window);
