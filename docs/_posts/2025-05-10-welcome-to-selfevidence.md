---
layout: single
title: "Welcome to Self Evidence (with Plotly)"
date: 2025-09-14
---

This is an interactive Plotly chart embedded in a Jekyll post.

<div id="plotly-chart"></div>

<script src="https://cdn.plot.ly/plotly-latest.min.js"></script>
<script>
  var trace = {
    x: [1, 2, 3, 4],
    y: [10, 15, 13, 17],
    type: 'scatter'
  };

  Plotly.newPlot('plotly-chart', [trace]);
</script>

<iframe src="{{ site.baseurl }}/assets/charts/01_cpi_chart_1984.html" width="100%" height="700" frameborder="0"></iframe>