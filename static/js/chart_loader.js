// static/js/chart_loader.js
// Fetches /api/chart-data with async/await and renders the Chart.js dashboards.

const colorPalette = {
  accent: '#f5a623',
  accentDarker: '#d4851a',
  primary: '#6FDC96',
  secondary: '#4A90E2',
  warning: '#FF6B6B',
  info: '#74BCFF',
  gridColor: 'rgba(255,255,255,0.14)',
  textColor: '#f2f2f2',
  textMuted: '#b8b8b8'
};

const datasetColors = [
  colorPalette.accent,
  colorPalette.primary,
  colorPalette.secondary,
  colorPalette.warning,
  colorPalette.info,
  colorPalette.accentDarker
];

const chartInstances = new Map();
let chartPayload = null;

if (window.ChartDataLabels) {
  Chart.register(window.ChartDataLabels);
}

async function fetchChartData() {
  const response = await fetch('/api/chart-data');

  if (!response.ok) {
    const errorBody = await response.json().catch(() => ({}));
    throw new Error(errorBody.error || 'Falha ao carregar dados dos gráficos.');
  }

  return response.json();
}

function destroyChart(canvas) {
  const existing = chartInstances.get(canvas.id);
  if (existing) existing.destroy();
}

function mountChart(canvas, config) {
  destroyChart(canvas);
  const chart = new Chart(canvas, config);
  chartInstances.set(canvas.id, chart);
  return chart;
}

function linearRegressionLine(points) {
  const validPoints = points.filter(point => Number.isFinite(point.x) && Number.isFinite(point.y));
  const n = validPoints.length;

  if (n < 2) return [];

  const sumX = validPoints.reduce((sum, point) => sum + point.x, 0);
  const sumY = validPoints.reduce((sum, point) => sum + point.y, 0);
  const sumXY = validPoints.reduce((sum, point) => sum + point.x * point.y, 0);
  const sumXX = validPoints.reduce((sum, point) => sum + point.x * point.x, 0);
  const denominator = n * sumXX - sumX * sumX;

  if (denominator === 0) return [];

  const slope = (n * sumXY - sumX * sumY) / denominator;
  const intercept = (sumY - slope * sumX) / n;
  const xValues = validPoints.map(point => point.x);
  const minX = Math.min(...xValues);
  const maxX = Math.max(...xValues);

  return [
    { x: minX, y: slope * minX + intercept },
    { x: maxX, y: slope * maxX + intercept }
  ];
}

function baseOptions(title, xLabel, yLabel) {
  return {
    responsive: true,
    maintainAspectRatio: false,
    animation: { duration: 650 },
    layout: { padding: { top: 8, right: 28, bottom: 10, left: 8 } },
    elements: {
      point: { borderWidth: 2 },
      line: { borderWidth: 3 },
      bar: { borderWidth: 1 }
    },
    plugins: {
      title: {
        display: true,
        text: title,
        color: colorPalette.textColor,
        font: { size: 15, weight: '600' },
        padding: { bottom: 16 }
      },
      legend: {
        labels: {
          color: colorPalette.textColor,
          boxWidth: 14,
          boxHeight: 14,
          padding: 16,
          font: { size: 12, weight: '500' }
        }
      },
      tooltip: {
        backgroundColor: 'rgba(15,15,15,0.95)',
        borderColor: colorPalette.accent,
        borderWidth: 1,
        titleColor: colorPalette.textColor,
        bodyColor: colorPalette.textColor,
        padding: 10
      },
      datalabels: { display: false }
    },
    scales: {
      x: {
        title: { display: Boolean(xLabel), text: xLabel, color: colorPalette.textColor, font: { size: 12, weight: '600' } },
        ticks: { color: colorPalette.textMuted, maxRotation: 45, minRotation: 0, font: { size: 11 } },
        grid: { color: colorPalette.gridColor },
        border: { color: 'rgba(255,255,255,0.22)' }
      },
      y: {
        title: { display: Boolean(yLabel), text: yLabel, color: colorPalette.textColor, font: { size: 12, weight: '600' } },
        ticks: { color: colorPalette.textMuted, font: { size: 11 } },
        grid: { color: colorPalette.gridColor },
        border: { color: 'rgba(255,255,255,0.22)' },
        beginAtZero: true
      }
    }
  };
}

function scatterConfig(chartData) {
  const points = chartData.data.map(item => ({
    x: Number(item.x),
    y: Number(item.y),
    label: item.label
  }));

  const options = baseOptions(chartData.title, chartData.xLabel, chartData.yLabel);
  options.plugins.datalabels = {
    display: true,
    align: 'top',
    anchor: 'end',
    offset: 4,
    formatter: (value, context) => {
      // linha de tendência não tem label, oculta
      if (context.datasetIndex !== 0) return null;
      return value.label ?? '';
    },
    color: colorPalette.textColor,
    font: { size: 9, weight: '600' }
  };

  return {
    type: 'scatter',
    data: {
      datasets: [
        {
          label: 'Municípios',
          data: points,
          backgroundColor: colorPalette.info,
          borderColor: '#ffffff',
          pointRadius: 7,
          pointHoverRadius: 9
        },
        {
          label: 'Tendência',
          type: 'line',
          data: linearRegressionLine(points),
          borderColor: colorPalette.accent,
          backgroundColor: colorPalette.accent,
          borderWidth: 3,
          pointRadius: 0,
          fill: false
        }
      ]
    },
    options
  };
}

function barConfig(chartData, horizontal = false) {
  const options = baseOptions(chartData.title, horizontal ? 'Índice Educação' : '', horizontal ? 'Município' : 'Valor Normalizado');
  options.indexAxis = horizontal ? 'y' : 'x';
  options.layout.padding.right = horizontal ? 54 : 28;
  options.plugins.datalabels = horizontal ? {
    display: true,
    anchor: 'end',
    align: 'right',
    clamp: true,
    color: colorPalette.textColor,
    formatter: value => Number(value).toFixed(3),
    font: { size: 11, weight: '600' }
  } : { display: false };
  options.scales.x.ticks.font.size = horizontal ? 11 : 10;
  options.scales.y.ticks.font.size = horizontal ? 11 : 10;

  return {
    type: 'bar',
    data: {
      labels: chartData.labels,
      datasets: chartData.datasets.map((dataset, index) => ({
        ...dataset,
        backgroundColor: datasetColors[index % datasetColors.length],
        borderColor: 'rgba(255,255,255,0.35)',
        borderWidth: 1,
        borderRadius: 4,
        maxBarThickness: horizontal ? 26 : 34
      }))
    },
    options
  };
}

function lineConfig(chartData) {
  const options = baseOptions(chartData.title, 'Ano', 'Valor Normalizado');

  return {
    type: 'line',
    data: {
      labels: chartData.labels,
      datasets: chartData.datasets.map((dataset, index) => ({
        ...dataset,
        borderColor: datasetColors[index % datasetColors.length],
        backgroundColor: datasetColors[index % datasetColors.length],
        borderWidth: 3,
        pointRadius: 5,
        pointHoverRadius: 7,
        pointBorderColor: '#ffffff',
        pointBorderWidth: 1.5,
        tension: 0.25,
        fill: false
      }))
    },
    options
  };
}

function radarConfig(chartData) {
  return {
    type: 'radar',
    data: {
      labels: chartData.labels,
      datasets: chartData.datasets.map((dataset, index) => ({
        ...dataset,
        borderColor: datasetColors[index % datasetColors.length],
        backgroundColor: `${datasetColors[index % datasetColors.length]}33`,
        pointBackgroundColor: datasetColors[index % datasetColors.length],
        pointBorderColor: '#ffffff',
        borderWidth: 2,
        pointRadius: 4
      }))
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      plugins: {
        title: { display: true, text: chartData.title, color: colorPalette.textColor, font: { size: 15, weight: '600' } },
        legend: { labels: { color: colorPalette.textColor, font: { size: 12, weight: '500' } } },
        datalabels: { display: false }
      },
      scales: {
        r: {
          suggestedMin: 0,
          suggestedMax: 1,
          angleLines: { color: colorPalette.gridColor },
          grid: { color: colorPalette.gridColor },
          pointLabels: { color: colorPalette.textColor, font: { size: 11, weight: '600' } },
          ticks: { color: colorPalette.textMuted, backdropColor: 'transparent', font: { size: 10 } }
        }
      }
    }
  };
}

function createChartConfig(chartKey, chartData) {
  if (chartData.type === 'scatter') return scatterConfig(chartData);
  if (chartKey === 'ranking_municipios') return barConfig(chartData, true);
  if (chartData.type === 'bar') return barConfig(chartData);
  if (chartData.type === 'line') return lineConfig(chartData);
  return barConfig(chartData);
}

function setError(wrapper, message) {
  wrapper.classList.add('has-error');
  const loading = wrapper.querySelector('.chart-loading');
  if (loading) loading.hidden = true;          // ← linha nova
  const errorElement = wrapper.querySelector('.chart-error');
  if (errorElement) {
    errorElement.textContent = message;
    errorElement.hidden = false;
  }
}

function normalizeMunicipalityName(value) {
  return String(value || '')
    .normalize('NFD')
    .replace(/[\u0300-\u036f]/g, '')
    .toUpperCase()
    .trim();
}

function selectedMunicipalities() {
  const checked = [...document.querySelectorAll('.sidebar input[type="checkbox"]:checked')]
    .map(input => input.value || input.closest('label')?.textContent.trim())
    .filter(Boolean)
    .map(normalizeMunicipalityName);
  return checked;
}

function selectedChartType() {
  return document.querySelector('input[name="chart-type"]:checked')?.value || 'bar';
}

function filteredChartData(source) {
  const selected = selectedMunicipalities();
  const selectedIndexes = source.labels
    .map((label, index) => ({ label, index }))
    .filter(item => selected.includes(normalizeMunicipalityName(item.label)));

  const indexes = selectedIndexes.length ? selectedIndexes.map(item => item.index) : source.labels.map((_, index) => index);
  const labels = indexes.map(index => source.labels[index]);

  return {
    ...source,
    labels,
    datasets: source.datasets.map(dataset => ({
      ...dataset,
      data: indexes.map(index => dataset.data[index])
    }))
  };
}

function filteredScatterConfig(chartData) {
  const labels = chartData.labels;
  const datasets = chartData.datasets;
  const points = labels.map((label, index) => ({
    x: Number(datasets[2]?.data[index] ?? 0),
    y: Number(datasets[0]?.data[index] ?? 0),
    label
  }));

  return scatterConfig({
    title: 'Infraestrutura x SARESP por Município Selecionado',
    xLabel: 'Infraestrutura Normalizada',
    yLabel: 'SARESP Normalizado',
    data: points
  });
}

function filteredLineConfig(chartData) {
  return lineConfig({
    ...chartData,
    title: 'Indicadores por Município Selecionado'
  });
}

function renderFilteredChart() {
  if (!chartPayload?.municipio_filtro) return;

  const wrapper = document.querySelector('[data-filter-chart="true"]');
  const canvas = document.getElementById('chart-main');
  if (!wrapper || !canvas) return;

  const source = filteredChartData(chartPayload.municipio_filtro);
  const type = selectedChartType();
  let config;

  if (type === 'scatter') {
    config = filteredScatterConfig(source);
  } else if (type === 'line') {
    config = filteredLineConfig(source);
  } else if (type === 'radar') {
    config = radarConfig({ ...source, title: 'Radar de Indicadores por Município' });
  } else {
    config = barConfig({ ...source, title: 'Comparativo por Município Selecionado' });
  }

  mountChart(canvas, config);
  wrapper.classList.add('is-loaded');

  const label = document.getElementById('chart-main-label');
  const sub = document.getElementById('chart-main-sub');
  if (label) label.textContent = config.options?.plugins?.title?.text || 'Comparativo por Município Selecionado';
  if (sub) {
    sub.textContent = type === 'scatter'
      ? 'eixo x: Infraestrutura normalizada · eixo y: SARESP normalizado'
      : 'indicadores normalizados por município selecionado';
  }
}

function bindFilteredControls() {
  document.querySelectorAll('.sidebar input[type="checkbox"], input[name="chart-type"]').forEach(input => {
    input.addEventListener('change', renderFilteredChart);
  });
}

async function renderCharts() {
  const wrappers = document.querySelectorAll('[data-chart-key]');

  try {
    chartPayload = await fetchChartData();

    wrappers.forEach(wrapper => {
      const chartKey = wrapper.dataset.chartKey;
      const canvas = wrapper.querySelector('canvas');
      const chartData = chartPayload[chartKey];

      if (!canvas || !chartData) {
        setError(wrapper, 'Dados indisponíveis para este gráfico.');
        return;
      }

      mountChart(canvas, createChartConfig(chartKey, chartData));
      wrapper.classList.add('is-loaded');
      const errorEl = wrapper.querySelector('.chart-error');
      if (errorEl) {
        errorEl.hidden = true;        // ← garante que fica oculta
        errorEl.style.pointerEvents = 'none';  // ← não bloqueia o mouse
      }
    });

    renderFilteredChart();
    bindFilteredControls();
  } catch (error) {
    wrappers.forEach(wrapper => setError(wrapper, error.message));
    const filteredWrapper = document.querySelector('[data-filter-chart="true"]');
    if (filteredWrapper) setError(filteredWrapper, error.message);
  }
}

document.addEventListener('DOMContentLoaded', renderCharts);