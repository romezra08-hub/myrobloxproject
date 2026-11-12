// Handwriting practice: trace a faded letter, then write it alone. Scores coverage + neatness.
(function (root) {
  const { h } = root.LSUI;
  const { t } = root.LSI18n;

  const FONTS = {
    print: '"Nunito", "Segoe UI", Arial, sans-serif',
    cursive: '"Marck Script", "Segoe Script", cursive',
  };

  function tracePad(opts) {
    const size = opts.size || 300;
    const dpr = Math.min(2, root.devicePixelRatio || 1);
    const canvas = h("canvas.trace-canvas", { width: size * dpr, height: size * dpr, style: { width: size + "px", height: size + "px" }, "aria-label": t("trace") });
    const g = canvas.getContext("2d");
    g.scale(dpr, dpr);
    let text = opts.text, style = opts.style || "print", showGuide = true;
    const strokes = [];
    let cur = null;

    function fontFor(txt) {
      const base = txt.length > 2 ? size * 0.42 : size * 0.62;
      return `${style === "cursive" ? "" : "600 "}${Math.round(base)}px ${FONTS[style]}`;
    }

    function drawGuide(ctx2, color, lineWidth) {
      ctx2.save();
      ctx2.font = fontFor(text);
      ctx2.textAlign = "center";
      ctx2.textBaseline = "middle";
      if (lineWidth) {
        ctx2.strokeStyle = color; ctx2.lineWidth = lineWidth; ctx2.lineJoin = "round";
        ctx2.strokeText(text, size / 2, size * 0.54);
      }
      ctx2.fillStyle = color;
      ctx2.fillText(text, size / 2, size * 0.54);
      ctx2.restore();
    }

    function redraw() {
      g.clearRect(0, 0, size, size);
      // writing lines
      g.strokeStyle = "rgba(120,140,170,.35)";
      g.lineWidth = 1;
      g.setLineDash([6, 6]);
      [0.3, 0.54, 0.75].forEach((y) => { g.beginPath(); g.moveTo(10, size * y); g.lineTo(size - 10, size * y); g.stroke(); });
      g.setLineDash([]);
      if (showGuide) drawGuide(g, "rgba(120,140,200,.22)");
      g.strokeStyle = opts.ink || "#2b59c3";
      g.lineWidth = Math.max(8, size / 26);
      g.lineCap = "round"; g.lineJoin = "round";
      strokes.forEach((s) => {
        g.beginPath();
        s.forEach((p, i) => (i ? g.lineTo(p.x, p.y) : g.moveTo(p.x, p.y)));
        if (s.length === 1) g.lineTo(s[0].x + 0.1, s[0].y);
        g.stroke();
      });
    }

    const pos = (e) => {
      const r = canvas.getBoundingClientRect();
      return { x: ((e.clientX - r.left) / r.width) * size, y: ((e.clientY - r.top) / r.height) * size };
    };
    canvas.addEventListener("pointerdown", (e) => { e.preventDefault(); canvas.setPointerCapture(e.pointerId); cur = [pos(e)]; strokes.push(cur); redraw(); });
    canvas.addEventListener("pointermove", (e) => { if (!cur) return; e.preventDefault(); cur.push(pos(e)); redraw(); });
    const up = () => { cur = null; };
    canvas.addEventListener("pointerup", up);
    canvas.addEventListener("pointercancel", up);
    canvas.style.touchAction = "none";

    // Score: how much of the letter you covered + how much of your ink is on the letter.
    function score() {
      if (!strokes.length) return 0;
      const n = 100;
      const mk = () => { const c = document.createElement("canvas"); c.width = n; c.height = n; const x = c.getContext("2d"); x.scale(n / size, n / size); return [c, x]; };
      const [, lg] = mk();
      drawGuide(lg, "#000");
      const [, near] = mk();
      drawGuide(near, "#000", size / 9);
      const [, ug] = mk();
      ug.strokeStyle = "#000"; ug.lineWidth = Math.max(8, size / 26) * 2.2; ug.lineCap = "round"; ug.lineJoin = "round";
      strokes.forEach((s) => { ug.beginPath(); s.forEach((p, i) => (i ? ug.lineTo(p.x, p.y) : ug.moveTo(p.x, p.y))); if (s.length === 1) ug.lineTo(s[0].x + 0.1, s[0].y); ug.stroke(); });
      const ink2 = mk()[1]; // thin user ink for precision
      ink2.strokeStyle = "#000"; ink2.lineWidth = Math.max(8, size / 26); ink2.lineCap = "round";
      strokes.forEach((s) => { ink2.beginPath(); s.forEach((p, i) => (i ? ink2.lineTo(p.x, p.y) : ink2.moveTo(p.x, p.y))); if (s.length === 1) ink2.lineTo(s[0].x + 0.1, s[0].y); ink2.stroke(); });
      const A = lg.getImageData(0, 0, n, n).data, B = near.getImageData(0, 0, n, n).data, Cc = ug.getImageData(0, 0, n, n).data, I = ink2.getImageData(0, 0, n, n).data;
      let letterPx = 0, covered = 0, inkPx = 0, inkGood = 0;
      for (let i = 3; i < A.length; i += 4) {
        if (A[i] > 100) { letterPx++; if (Cc[i] > 50) covered++; }
        if (I[i] > 100) { inkPx++; if (B[i] > 50) inkGood++; }
      }
      const coverage = letterPx ? covered / letterPx : 0;
      const precision = inkPx ? inkGood / inkPx : 0;
      return Math.round(Math.max(0, Math.min(1, coverage * 0.6 + precision * 0.4)) * 100);
    }

    redraw();
    return {
      el: canvas,
      clear() { strokes.length = 0; redraw(); },
      setText(tx) { text = tx; strokes.length = 0; redraw(); },
      setStyle(s) { style = s; redraw(); },
      setGuide(v) { showGuide = v; redraw(); },
      score,
      hasInk: () => strokes.length > 0,
      redraw,
    };
  }

  root.LSWriting = { tracePad, FONTS };
})(window);
