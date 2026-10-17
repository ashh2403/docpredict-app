// Apply the stored theme before first paint to avoid a flash. Kept as a file (not inline)
// so the Content-Security-Policy can forbid inline scripts.
try {
  var t = localStorage.getItem("docpredict.theme") || "system";
  var dark = t === "dark" || (t === "system" && window.matchMedia("(prefers-color-scheme: dark)").matches);
  document.documentElement.dataset.theme = dark ? "dark" : "light";
} catch (e) {}
