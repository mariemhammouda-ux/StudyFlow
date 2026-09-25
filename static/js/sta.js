// Graphique "Temps étudié par matière" (page /statistics)
// Les minutes de chaque matière sont écrites par Jinja dans data-minutes.
// Ici, on transforme ces minutes en largeur de barre (en pourcentage).

(function () {
  "use strict";

  var chart = document.getElementById("subject-chart");
  if (!chart) {
    return; // Pas de graphique sur la page (aucune session enregistrée)
  }

  var rows = chart.querySelectorAll(".stats-chart-row");
  var minutesList = [];
  var maxMinutes = 0;

  // 1. Lire les minutes de chaque ligne et trouver la valeur maximale
  rows.forEach(function (row) {
    var minutes = parseInt(row.dataset.minutes, 10);
    if (isNaN(minutes) || minutes < 0) {
      minutes = 0;
    }
    minutesList.push(minutes);
    if (minutes > maxMinutes) {
      maxMinutes = minutes;
    }
  });

  // 2. Appliquer la largeur et la couleur de chaque barre
  rows.forEach(function (row, index) {
    var bar = row.querySelector(".stats-chart-bar");
    var minutes = minutesList[index];
    var percent = 0;

    // La plus grande valeur = 100 %. Une matière à 0 minute reste à 0 %,
    // et le test maxMinutes > 0 évite toute division par zéro.
    if (maxMinutes > 0 && minutes > 0) {
      percent = Math.max((minutes / maxMinutes) * 100, 2); // 2 % minimum pour rester visible
    }
    bar.style.width = percent + "%";

    // Couleur de la matière, seulement si c'est une couleur CSS valide
    var color = row.dataset.color;
    if (color && window.CSS && CSS.supports("color", color)) {
      bar.style.backgroundColor = color;
    }
  });
})();