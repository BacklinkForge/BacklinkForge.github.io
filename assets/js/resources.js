/* BacklinkForge — resources directory: renders assets/data/resources.json
   with live search and category filtering. All outbound links open in a
   new tab with rel="noopener noreferrer". */
(function () {
  "use strict";

  var DATA_URL = "assets/data/resources.json";

  function el(tag, cls, text) {
    var n = document.createElement(tag);
    if (cls) n.className = cls;
    if (text != null) n.textContent = text;
    return n;
  }

  function hostOf(url) {
    try { return new URL(url).hostname.replace(/^www\./, ""); }
    catch (e) { return ""; }
  }

  function card(item) {
    var c = el("article", "card resource-card");
    c.appendChild(el("span", "badge", item.category || "Other"));
    var h = el("h3");
    var a = el("a", null, item.name);
    a.href = item.url;
    a.target = "_blank";
    a.rel = "noopener noreferrer";
    a.innerHTML += ' <span class="ext-icon" aria-hidden="true">&#8599;</span>';
    h.appendChild(a);
    c.appendChild(h);
    var host = hostOf(item.url);
    if (host) c.appendChild(el("p", "resource-url", host));
    var link = el("a", "card-link", "Visit resource");
    link.href = item.url;
    link.target = "_blank";
    link.rel = "noopener noreferrer";
    c.appendChild(link);
    return c;
  }

  function init(data) {
    var grid = document.getElementById("resource-grid");
    var search = document.getElementById("resource-search");
    var filter = document.getElementById("category-filter");
    var count = document.getElementById("result-count");
    if (!grid) return;

    // Populate category dropdown from the data itself.
    var cats = [];
    data.forEach(function (d) {
      if (d.category && cats.indexOf(d.category) === -1) cats.push(d.category);
    });
    cats.sort();
    cats.forEach(function (c) {
      var o = document.createElement("option");
      o.value = c; o.textContent = c + " (" +
        data.filter(function (d) { return d.category === c; }).length + ")";
      filter.appendChild(o);
    });

    function render() {
      var q = (search.value || "").toLowerCase().trim();
      var cat = filter.value;
      var shown = data.filter(function (d) {
        var okCat = !cat || d.category === cat;
        var hay = ((d.name || "") + " " + (d.url || "")).toLowerCase();
        return okCat && (!q || hay.indexOf(q) !== -1);
      });
      grid.innerHTML = "";
      if (!shown.length) {
        grid.appendChild(el("p", null,
          "No resources match your search. Try a different keyword or category."));
      }
      shown.forEach(function (d) { grid.appendChild(card(d)); });
      count.textContent = shown.length + " of " + data.length + " resources shown.";
    }

    search.addEventListener("input", render);
    filter.addEventListener("change", render);
    render();
  }

  document.addEventListener("DOMContentLoaded", function () {
    if (!document.getElementById("resource-grid")) return;
    fetch(DATA_URL)
      .then(function (r) {
        if (!r.ok) throw new Error("HTTP " + r.status);
        return r.json();
      })
      .then(init)
      .catch(function () {
        var grid = document.getElementById("resource-grid");
        grid.innerHTML = "<p>Sorry — the resource list could not be loaded. " +
          "Please try again later.</p>";
      });
  });
})();
