/*! PickWorth — device UI switcher (display layer only)
 *  Toggles body.is-mobile / body.is-desktop so CSS can render two
 *  independent layouts. NEVER changes text nodes or the document body —
 *  every page ships the full desktop content; this only reflows it.
 *  SEO/GEO-safe: crawlers (desktop UA) get the complete content; the
 *  mobile layout is a CSS reflow of the SAME markup, never a shorter version.
 */
(function () {
  var q = window.matchMedia("(max-width: 899px)");

  function apply() {
    var html = document.documentElement;
    var body = document.body;
    var mobile = q.matches;
    // Set on BOTH <html> and <body> so either selector in the CSS works:
    // html.is-desktop / body.is-desktop. <html> is present pre-paint;
    // <body> is appended to before our script runs (deferred in head).
    html.classList.toggle("is-mobile", mobile);
    html.classList.toggle("is-desktop", !mobile);
    if (body) {
      body.classList.toggle("is-mobile", mobile);
      body.classList.toggle("is-desktop", !mobile);
    }
  }

  apply();
  if (q.addEventListener) q.addEventListener("change", apply);
  else if (q.addListener) q.addListener(apply);
  window.addEventListener("resize", apply, { passive: true });
})();
