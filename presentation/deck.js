/* ------------------------------------------------------------------ *
 *  Navigazione del deck + iniezione dei dati (window.METRICS).
 *  I numeri arrivano da assets/data.js, rigenerato dalla pipeline Python:
 *  basta ri-eseguire ./refresh.sh e ricaricare la pagina.
 * ------------------------------------------------------------------ */

// ---- formattazione localizzata (it-IT) ----
const IT = new Intl.NumberFormat("it-IT");
const fmt = {
  int0:   v => IT.format(Math.round(v)),
  pct0:   v => IT.format(Math.round(v * 100)) + "%",
  pct1:   v => (v * 100).toFixed(1).replace(".", ",") + "%",
  pct0abs:v => "−" + IT.format(Math.round(Math.abs(v) * 100)) + "%",
  raw:    v => String(v),
};

function dig(obj, path) {
  return path.split(".").reduce((o, k) => (o == null ? o : o[k]), obj);
}

function injectMetrics() {
  const M = window.METRICS;
  if (!M) return;
  document.querySelectorAll("[data-m]").forEach(el => {
    const val = dig(M, el.getAttribute("data-m"));
    if (val === undefined || val === null) return;
    const f = el.getAttribute("data-fmt");
    el.textContent = f && fmt[f] ? fmt[f](val) : val;
  });
}

// ---- motore di navigazione ----
const slides = Array.from(document.querySelectorAll(".slide"));
const total = slides.length;
let idx = 0;

const elProgress = document.getElementById("progress");
const elCur = document.getElementById("cur");
const elTot = document.getElementById("tot");
const elDots = document.getElementById("dots");

elTot.textContent = total;
slides.forEach((_, i) => {
  const d = document.createElement("i");
  d.addEventListener("click", () => go(i));
  elDots.appendChild(d);
});
const dots = Array.from(elDots.children);

function go(n) {
  idx = Math.max(0, Math.min(total - 1, n));
  slides.forEach((s, i) => s.classList.toggle("active", i === idx));
  dots.forEach((d, i) => d.classList.toggle("on", i === idx));
  elCur.textContent = idx + 1;
  elProgress.style.width = ((idx) / (total - 1)) * 100 + "%";
}

function next() { go(idx + 1); }
function prev() { go(idx - 1); }

document.addEventListener("keydown", e => {
  if (["ArrowRight", "ArrowDown", " ", "PageDown"].includes(e.key)) { e.preventDefault(); next(); }
  else if (["ArrowLeft", "ArrowUp", "PageUp"].includes(e.key)) { e.preventDefault(); prev(); }
  else if (e.key === "Home") go(0);
  else if (e.key === "End") go(total - 1);
});

// avanzamento al click (non sui pallini / link)
document.getElementById("deck").addEventListener("click", e => {
  if (e.target.closest(".dots") || e.target.closest("a")) return;
  next();
});

// swipe su mobile
let tx = 0;
addEventListener("touchstart", e => { tx = e.changedTouches[0].clientX; }, { passive: true });
addEventListener("touchend", e => {
  const dx = e.changedTouches[0].clientX - tx;
  if (Math.abs(dx) > 50) (dx < 0 ? next : prev)();
}, { passive: true });

injectMetrics();
go(0);
