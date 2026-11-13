(function () {
  bootKitchen();
  bootPasswordToggles();

  var header = document.querySelector(".site-header");
  var toggle = document.querySelector(".nav-toggle");
  var nav = document.querySelector("#site-nav");
  if (!toggle || !nav) return;
  var label = toggle.querySelector(".sr-only");

  function setNav(open) {
    nav.classList.toggle("is-open", open);
    toggle.setAttribute("aria-expanded", open ? "true" : "false");
    document.body.classList.toggle("nav-open", open);
    label.textContent = open ? "Fermer le menu" : "Ouvrir le menu";
    if (open) {
      var first = nav.querySelector("a");
      if (first) first.focus();
    }
  }

  toggle.addEventListener("click", function () {
    setNav(!nav.classList.contains("is-open"));
  });

  nav.querySelectorAll("a").forEach(function (link) {
    link.addEventListener("click", function () {
      if (!nav.classList.contains("is-open")) return;
      setNav(false);
      toggle.focus();
    });
  });

  document.addEventListener("keydown", function (event) {
    if (event.key === "Escape" && nav.classList.contains("is-open")) {
      setNav(false);
      toggle.focus();
    }
  });

  if (header) {
    function onScroll() {
      header.classList.toggle("is-scrolled", window.scrollY > 8);
    }

    onScroll();
    window.addEventListener("scroll", onScroll, { passive: true });
  }

  var spyLinks = Array.prototype.slice.call(document.querySelectorAll("a[data-spy]"));
  var groups = new Map();

  spyLinks.forEach(function (link) {
    var id = link.getAttribute("href");
    if (!id || id.charAt(0) !== "#") return;
    var section = document.querySelector(id);
    if (!section) return;
    var scope = link.closest("nav, .menu-index");
    if (!groups.has(section)) groups.set(section, []);
    groups.get(section).push({ link: link, scope: scope });
  });

  if ("IntersectionObserver" in window) {
    var observer = new IntersectionObserver(
      function (entries) {
        entries.forEach(function (entry) {
          if (!entry.isIntersecting) return;
          var items = groups.get(entry.target) || [];
          items.forEach(function (item) {
            if (!item.scope) return;
            item.scope.querySelectorAll("a[data-spy]").forEach(function (other) {
              other.removeAttribute("aria-current");
            });
            item.link.setAttribute("aria-current", "true");
          });
        });
      },
      { rootMargin: "-45% 0px -48% 0px", threshold: 0 }
    );

    groups.forEach(function (_, section) {
      observer.observe(section);
    });
  }
})();

function bootPasswordToggles() {
  document.querySelectorAll("[data-password-toggle]").forEach(function (button) {
    if (button.getAttribute("data-bound") === "1") return;
    button.setAttribute("data-bound", "1");
    button.addEventListener("click", function () {
      var wrap = button.closest("span");
      var input = wrap && wrap.querySelector('input[type="password"], input[type="text"]');
      if (!input) return;
      var show = input.type === "password";
      input.type = show ? "text" : "password";
      button.setAttribute("aria-pressed", show ? "true" : "false");
      button.setAttribute("aria-label", show ? "Masquer le mot de passe" : "Afficher le mot de passe");
      var eyeShow = button.querySelector('[data-eye="show"]');
      var eyeHide = button.querySelector('[data-eye="hide"]');
      if (eyeShow) eyeShow.classList.toggle("hidden", show);
      if (eyeHide) eyeHide.classList.toggle("hidden", !show);
    });
  });
}

function bootKitchen() {
  var root = document.getElementById("kds");
  if (!root || root.getAttribute("data-bound") === "1") return;
  root.setAttribute("data-bound", "1");
  tickKitchen();
  window.setInterval(tickKitchen, 1000);
  window.setInterval(function () {
    pollKitchen(root);
  }, 5000);
  var full = root.querySelector("[data-kds-full]");
  if (!full) return;
  full.addEventListener("click", function () {
    if (document.fullscreenElement) document.exitFullscreen();
    else root.requestFullscreen();
  });
}

function tickKitchen() {
  var now = Date.now();
  document.querySelectorAll("[data-since]").forEach(function (node) {
    var then = Date.parse(node.getAttribute("data-since"));
    if (!then) return;
    var minutes = Math.max(0, Math.floor((now - then) / 60000));
    if (minutes < 60) node.textContent = minutes + " min";
    else node.textContent = Math.floor(minutes / 60) + " h " + String(minutes % 60).padStart(2, "0");
  });
}

function pollKitchen(root) {
  var active = document.activeElement;
  if (active && root.contains(active) && /^(INPUT|TEXTAREA|SELECT)$/.test(active.tagName)) return;
  var live = document.getElementById("kds-live");
  fetch(root.getAttribute("data-poll"), { credentials: "same-origin", headers: { Accept: "text/html" } })
    .then(function (response) {
      if (!response.ok) throw new Error("reseau");
      return response.text().then(function (html) {
        var box = document.createElement("div");
        box.innerHTML = html;
        var next = box.querySelector("#kds-sync");
        var current = document.getElementById("kds-sync");
        if (!next || !current) return;
        if (next.getAttribute("data-revision") === current.getAttribute("data-revision")) {
          if (live) live.textContent = "En direct";
          return;
        }
        var received = Number(next.getAttribute("data-received") || 0);
        var previous = Number(current.getAttribute("data-received") || 0);
        var scrolls = {};
        current.querySelectorAll("[data-kds-scroll]").forEach(function (node) {
          var column = node.parentElement && node.parentElement.getAttribute("data-kds-column");
          if (column) scrolls[column] = node.scrollTop;
        });
        current.replaceWith(next);
        next.querySelectorAll("[data-kds-scroll]").forEach(function (node) {
          var column = node.parentElement && node.parentElement.getAttribute("data-kds-column");
          if (column && scrolls[column]) node.scrollTop = scrolls[column];
        });
        if (live) live.textContent = received > previous ? "Nouvelle commande" : "En direct";
        tickKitchen();
      });
    })
    .catch(function () {
      if (live) live.textContent = "Connexion interrompue. Nouvel essai…";
    });
}
