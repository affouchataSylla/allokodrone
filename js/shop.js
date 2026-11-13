(function () {
  document.querySelectorAll("form[data-once]").forEach(function (form) {
    form.addEventListener("submit", function () {
      var button = form.querySelector("[type=submit]");
      if (!button || button.dataset.locked === "1") return;
      button.dataset.locked = "1";
      button.setAttribute("aria-disabled", "true");
    });
  });

  var product = document.querySelector("[data-product-form]");
  if (!product) return;
  var out = product.querySelector("[data-live-price]");
  if (!out) return;

  function money(cents) {
    var sign = cents < 0 ? "-" : "";
    cents = Math.abs(cents);
    var centsPart = String(cents % 100).padStart(2, "0");
    return sign + Math.floor(cents / 100) + "," + centsPart + " \u20ac";
  }

  function refresh() {
    if (product.getAttribute("data-base-confirmed") !== "1") {
      out.textContent = "Prix à valider";
      return;
    }
    var total = parseInt(product.getAttribute("data-base-cents"), 10);
    var inputs = product.querySelectorAll("input[type=radio]:checked, input[type=checkbox]:checked");
    for (var i = 0; i < inputs.length; i++) {
      if (inputs[i].getAttribute("data-delta-confirmed") !== "1") {
        out.textContent = "Prix à valider";
        return;
      }
      total += parseInt(inputs[i].getAttribute("data-delta") || "0", 10);
    }
    var qtyField = product.querySelector("[name=quantite]");
    var qty = parseInt(qtyField && qtyField.value ? qtyField.value : "1", 10);
    if (!qty || qty < 1) qty = 1;
    out.textContent = money(total * qty);
  }

  product.addEventListener("change", refresh);
  product.addEventListener("input", refresh);
  refresh();

})();
