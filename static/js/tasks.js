// Page "Tâches" : recherche, filtres par priorité / statut, dates relatives.
// Les données viennent des attributs data-* écrits par Jinja dans tasks.html.

(function () {
  "use strict";

  var list = document.getElementById("task-list");
  if (!list) {
    return; // aucune tâche : état vide, rien à filtrer
  }

  var rows = Array.prototype.slice.call(list.querySelectorAll(".tk-row"));
  var search = document.getElementById("task-search");
  var noResult = document.getElementById("task-noresult");
  var state = { status: "all", priority: "all", text: "" };

  function applyFilters() {
    var visible = 0;
    rows.forEach(function (row) {
      var show =
        (state.status === "all" || row.dataset.status === state.status) &&
        (state.priority === "all" || row.dataset.priority === state.priority) &&
        row.dataset.search.indexOf(state.text) !== -1;
      row.hidden = !show;
      if (show) { visible++; }
    });
    noResult.hidden = visible !== 0;
  }

  function bindGroup(selector, key) {
    var buttons = document.querySelectorAll(selector);
    buttons.forEach(function (button) {
      button.addEventListener("click", function () {
        buttons.forEach(function (b) {
          b.classList.remove("active");
          b.setAttribute("aria-pressed", "false");
        });
        button.classList.add("active");
        button.setAttribute("aria-pressed", "true");
        state[key] = button.dataset.filter;
        applyFilters();
      });
    });
  }

  bindGroup(".tk-tab", "status");
  bindGroup(".tk-chip", "priority");

  search.addEventListener("input", function () {
    state.text = search.value.trim().toLowerCase();
    applyFilters();
  });

  // Dates relatives : "Aujourd'hui", "Demain", "3j", "-2j"
  var today = new Date();
  today.setHours(0, 0, 0, 0);

  rows.forEach(function (row) {
    var parts = (row.dataset.due || "").slice(0, 10).split("-");
    if (parts.length !== 3) { return; }
    var due = new Date(Number(parts[0]), Number(parts[1]) - 1, Number(parts[2]));
    if (isNaN(due.getTime())) { return; }

    var diff = Math.round((due - today) / 86400000);
    var label = diff === 0 ? "Aujourd'hui" : diff === 1 ? "Demain" : diff + "j";
    var element = row.querySelector(".tk-due");
    element.title = element.textContent.trim(); // la date complète reste en infobulle
    element.textContent = label;
  });
})();