/* Sales report charts, drawn with Chart.js 4.5.1 (static/reports/vendor/chart.umd.min.js).
   Each <canvas data-chart="ID"> reads its labels and data sets from the JSON script
   element ID. The charts are drawn again after an HTMX swap (the salesperson filter). */
(function () {
  "use strict";

  function draw(root) {
    if (typeof Chart === "undefined" || !root.querySelectorAll) {
      return;
    }
    root.querySelectorAll("canvas[data-chart]").forEach(function (canvas) {
      var source = document.getElementById(canvas.dataset.chart);
      if (!source) {
        return;
      }
      var existing = Chart.getChart(canvas);
      if (existing) {
        existing.destroy();
      }
      new Chart(canvas, {
        type: "bar",
        data: JSON.parse(source.textContent),
        options: {
          responsive: true,
          plugins: { legend: { position: "bottom" } },
          scales: {
            x: { stacked: true },
            y: { stacked: true, beginAtZero: true },
          },
        },
      });
    });
  }

  document.addEventListener("DOMContentLoaded", function () {
    draw(document);
  });
  document.addEventListener("htmx:afterSettle", function (event) {
    draw(event.target);
  });
})();
