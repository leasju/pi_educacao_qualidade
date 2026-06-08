// ═════════════════════════════════════════════════════════════
// PI ANÁLISE - GRÁFICOS RECRIADOS EM CHART.JS (EXATA CÓPIA DO NOTEBOOK)
// ═════════════════════════════════════════════════════════════
// Reprodução 1:1 dos 6 gráficos principais do PI_ANÁLISE.ipynb

// Paleta de cores do site
const colorPalette = {
    accent: '#f5a623',           // Orange primary
    accentDarker: '#d4851a',     // Darker orange
    primary: '#6FDC96',          // Green
    secondary: '#4A90E2',        // Blue
    warning: '#FF6B6B',          // Red
    info: '#74BCFF',             // Light blue
    gridColor: 'rgba(255,255,255,0.08)', // Subtle grid
    textColor: '#c2c2c2',        // Light text
    textMuted: '#888'            // Muted text
};

const chartState = {
  mainChart: null,
  payload: null,
  charts: {}
};

async function fetchChartData() {
  try {
    const response = await fetch('/api/chart-data');
    if (!response.ok) {
      throw new Error(`Erro ao buscar dados de gráfico: ${response.statusText}`);
    }
    return await response.json();
  } catch (error) {
    console.error(error);
    return { error: 'Falha ao carregar dados de gráficos.' };
  }
}

function createChartInstance(canvasId, config) {
  const element = document.getElementById(canvasId);
  if (!element) {
    console.warn(`⚠️ Canvas not found: ${canvasId}`);
    return null;
  }
  const ctx = element.getContext('2d');
  const chartInstance = new Chart(ctx, config);
  chartState.charts[canvasId] = chartInstance;
  return chartInstance;
}

function createBarChart(canvasId, data) {
  const config = {
    type: 'bar',
    data: {
      labels: data.labels,
      datasets: [{
        label: data.datasets[0].label || 'Dados',
        data: data.datasets[0].data,
        backgroundColor: colorPalette.accent,
        borderColor: colorPalette.accentDarker,
        borderWidth: 1,
      }]
    },
    options: {
      responsive: true,
      maintainAspectRatio: true,
      plugins: {
        legend: {
          display: true,
          labels: {
            color: colorPalette.textColor,
            font: { family: "'DM Sans', sans-serif", size: 12 }
          }
        },
        tooltip: {
          mode: 'index',
          intersect: false,
          backgroundColor: 'rgba(22, 22, 22, 0.8)',
          titleColor: colorPalette.textColor,
          bodyColor: colorPalette.textColor,
          borderColor: colorPalette.gridColor,
          borderWidth: 1
        }
      },
      scales: {
        x: {
          ticks: { color: colorPalette.textColor },
          grid: { display: false }
        },
        y: {
          ticks: { color: colorPalette.textColor },
          grid: { color: colorPalette.gridColor }
        }
      }
    }
  };
  createChartInstance(canvasId, config);
}

function createLineChart(canvasId, data) {
  const colors = [colorPalette.accent, colorPalette.primary, colorPalette.secondary, colorPalette.info];
  
  const datasets = data.datasets.map((dataset, idx) => ({
    label: dataset.label,
    data: dataset.data,
    borderColor: colors[idx % colors.length],
    backgroundColor: colors[idx % colors.length] + '20',
    borderWidth: 2,
    pointRadius: 4,
    pointBackgroundColor: colors[idx % colors.length],
    pointBorderColor: '#fff',
    pointBorderWidth: 1,
    tension: 0.4,
    fill: false
  }));

  const config = {
    type: 'line',
    data: {
      labels: data.labels,
      datasets
    },
    options: {
      responsive: true,
      maintainAspectRatio: true,
      plugins: {
        legend: {
          display: true,
          labels: {
            color: colorPalette.textColor,
            font: { family: "'DM Sans', sans-serif", size: 12 }
          }
        },
        tooltip: {
          mode: 'index',
          intersect: false,
          backgroundColor: 'rgba(22, 22, 22, 0.8)',
          titleColor: colorPalette.textColor,
          bodyColor: colorPalette.textColor,
          borderColor: colorPalette.gridColor,
          borderWidth: 1
        }
      },
      scales: {
        x: {
          ticks: { color: colorPalette.textColor },
          grid: { display: false }
        },
        y: {
          ticks: { color: colorPalette.textColor },
          grid: { color: colorPalette.gridColor }
        }
      }
    }
  };
  createChartInstance(canvasId, config);
}

function createScatterChart(canvasId, data) {
  const config = {
    type: 'scatter',
    data: {
      datasets: [{
        label: 'Dados de Correlação',
        data: data.data.map(d => ({ x: d.x, y: d.y })),
        backgroundColor: colorPalette.accent + 'cc',
        borderColor: colorPalette.accentDarker,
        borderWidth: 1,
        pointRadius: 6,
        pointHoverRadius: 8
      }]
    },
    options: {
      responsive: true,
      maintainAspectRatio: true,
      plugins: {
        legend: { display: false },
        tooltip: {
          backgroundColor: 'rgba(22, 22, 22, 0.8)',
          titleColor: colorPalette.textColor,
          bodyColor: colorPalette.textColor,
          borderColor: colorPalette.gridColor,
          borderWidth: 1,
          callbacks: {
            label: ctx => `X: ${ctx.raw.x.toFixed(2)}, Y: ${ctx.raw.y.toFixed(2)}`
          }
        }
      },
      scales: {
        x: {
          type: 'linear',
          ticks: { color: colorPalette.textColor },
          grid: { color: colorPalette.gridColor }
        },
        y: {
          ticks: { color: colorPalette.textColor },
          grid: { color: colorPalette.gridColor }
        }
      }
    }
  };
  createChartInstance(canvasId, config);
}

function createStackedBarChart(canvasId, data) {
  const colors = [colorPalette.accent, colorPalette.primary, colorPalette.warning, colorPalette.info];

  const datasets = data.datasets.map((dataset, idx) => ({
    label: dataset.label,
    data: dataset.data,
    backgroundColor: colors[idx % colors.length],
    borderColor: colors[idx % colors.length],
    borderWidth: 0
  }));

  const config = {
    type: 'bar',
    data: {
      labels: data.labels,
      datasets
    },
    options: {
      responsive: true,
      maintainAspectRatio: true,
      indexAxis: 'x',
      plugins: {
        legend: {
          display: true,
          labels: {
            color: colorPalette.textColor,
            font: { family: "'DM Sans', sans-serif", size: 12 }
          }
        },
        tooltip: {
          backgroundColor: 'rgba(22, 22, 22, 0.8)',
          titleColor: colorPalette.textColor,
          bodyColor: colorPalette.textColor,
          borderColor: colorPalette.gridColor,
          borderWidth: 1
        }
      },
      scales: {
        x: {
          stacked: true,
          ticks: { color: colorPalette.textColor },
          grid: { display: false }
        },
        y: {
          stacked: true,
          ticks: { color: colorPalette.textColor },
          grid: { color: colorPalette.gridColor }
        }
      }
    }
  };
  createChartInstance(canvasId, config);
}

async function renderCharts() {
  const payload = await fetchChartData();
  chartState.payload = payload;

  console.log('📊 Dados recebidos:', payload);

  if (payload.error) {
    console.error('❌ Erro ao carregar dados:', payload.error);
    return;
  }

  // Chart 1: Proficiência por Município (Barras Agrupadas)
  if (payload['MÉDIA_PROFICIÊNCIA']) {
    console.log('📈 Renderizando chart-proficiency');
    createBarChart('chart-proficiency', payload['MÉDIA_PROFICIÊNCIA']);
  }

  // Chart 2: Proficiência × Absenteísmo (Dispersão)
  if (payload['PROFICIÊNCIA_VS_AUSÊNCIA']) {
    console.log('📈 Renderizando chart-absence-prof');
    createScatterChart('chart-absence-prof', payload['PROFICIÊNCIA_VS_AUSÊNCIA']);
  }

  // Chart 3: Taxa de Aprovação e Reprovação (Barras Empilhadas)
  if (payload['APROVAÇÃO_E_REPROVAÇÃO']) {
    console.log('📈 Renderizando chart-approval');
    createStackedBarChart('chart-approval', payload['APROVAÇÃO_E_REPROVAÇÃO']);
  }

  // Chart 4: Fluxo × Infraestrutura (Dispersão)
  if (payload['FLUXO_VS_INFRAESTRUTURA']) {
    console.log('📈 Renderizando chart-flux-infra');
    createScatterChart('chart-flux-infra', payload['FLUXO_VS_INFRAESTRUTURA']);
  }

  // Chart 5: Ausências por Mês (Linhas)
  if (payload['TOTAL_DIAS_AUSENTES']) {
    console.log('📈 Renderizando chart-absence-trend');
    createLineChart('chart-absence-trend', payload['TOTAL_DIAS_AUSENTES']);
  }

  // Chart 6: Infraestrutura × Desempenho (Linhas / Trend)
  if (payload['INFRA_TREND']) {
    console.log('📈 Renderizando chart-infra-performance');
    createLineChart('chart-infra-performance', payload['INFRA_TREND']);
  }

  buildMainChart('bar');
}

function buildMainChart(type = 'bar') {
  const payload = chartState.payload;
  if (!payload || !payload.main_chart) {
    console.warn('⚠️ main_chart não disponível');
    return;
  }

  // Destruir gráfico anterior se existe
  if (chartState.mainChart) {
    chartState.mainChart.destroy();
  }

  const mainData = payload.main_chart;
  const colors = [colorPalette.accent, colorPalette.primary, colorPalette.secondary, colorPalette.info];

  let config;

  if (type === 'bar') {
    const datasets = mainData.datasets.map((dataset, idx) => ({
      label: dataset.label,
      data: dataset.data,
      backgroundColor: colors[idx % colors.length],
      borderColor: colors[idx % colors.length],
      borderWidth: 0
    }));

    config = {
      type: 'bar',
      data: {
        labels: mainData.labels,
        datasets
      },
      options: {
        responsive: true,
        maintainAspectRatio: true,
        plugins: {
          legend: {
            display: true,
            labels: {
              color: colorPalette.textColor,
              font: { family: "'DM Sans', sans-serif", size: 12 }
            }
          },
          tooltip: {
            backgroundColor: 'rgba(22, 22, 22, 0.8)',
            titleColor: colorPalette.textColor,
            bodyColor: colorPalette.textColor,
            borderColor: colorPalette.gridColor,
            borderWidth: 1
          }
        },
        scales: {
          x: {
            ticks: { color: colorPalette.textColor },
            grid: { display: false }
          },
          y: {
            ticks: { color: colorPalette.textColor },
            grid: { color: colorPalette.gridColor }
          }
        }
      }
    };
  } else if (type === 'scatter') {
    const scatterData = mainData.labels.map((label, idx) => ({
      x: idx + 1,
      y: mainData.datasets[0].data[idx]
    }));

    config = {
      type: 'scatter',
      data: {
        datasets: [{
          label: 'Municípios por proficiência',
          data: scatterData,
          backgroundColor: colorPalette.primary + 'cc',
          borderColor: colorPalette.primary,
          borderWidth: 1,
          pointRadius: 7,
          pointHoverRadius: 9
        }]
      },
      options: {
        responsive: true,
        maintainAspectRatio: true,
        plugins: {
          legend: { display: false },
          tooltip: {
            backgroundColor: 'rgba(22, 22, 22, 0.8)',
            titleColor: colorPalette.textColor,
            bodyColor: colorPalette.textColor,
            borderColor: colorPalette.gridColor,
            borderWidth: 1
          }
        },
        scales: {
          x: {
            type: 'linear',
            ticks: { color: colorPalette.textColor },
            grid: { color: colorPalette.gridColor }
          },
          y: {
            ticks: { color: colorPalette.textColor },
            grid: { color: colorPalette.gridColor }
          }
        }
      }
    };
  } else if (type === 'line') {
    const datasets = mainData.datasets.map((dataset, idx) => ({
      label: dataset.label,
      data: dataset.data,
      borderColor: colors[idx % colors.length],
      backgroundColor: colors[idx % colors.length] + '20',
      borderWidth: 2,
      pointRadius: 5,
      pointBackgroundColor: colors[idx % colors.length],
      pointBorderColor: '#fff',
      pointBorderWidth: 1,
      tension: 0.4,
      fill: false
    }));

    config = {
      type: 'line',
      data: {
        labels: mainData.labels,
        datasets
      },
      options: {
        responsive: true,
        maintainAspectRatio: true,
        plugins: {
          legend: {
            display: true,
            labels: {
              color: colorPalette.textColor,
              font: { family: "'DM Sans', sans-serif", size: 12 }
            }
          },
          tooltip: {
            mode: 'index',
            intersect: false,
            backgroundColor: 'rgba(22, 22, 22, 0.8)',
            titleColor: colorPalette.textColor,
            bodyColor: colorPalette.textColor,
            borderColor: colorPalette.gridColor,
            borderWidth: 1
          }
        },
        scales: {
          x: {
            ticks: { color: colorPalette.textColor },
            grid: { display: false }
          },
          y: {
            ticks: { color: colorPalette.textColor },
            grid: { color: colorPalette.gridColor }
          }
        }
      }
    };
  } else if (type === 'radar') {
    config = {
      type: 'radar',
      data: {
        labels: mainData.labels,
        datasets: mainData.datasets.map((dataset, idx) => ({
          label: dataset.label,
          data: dataset.data,
          borderColor: colors[idx % colors.length],
          backgroundColor: colors[idx % colors.length] + '33',
          pointBackgroundColor: colors[idx % colors.length],
          pointBorderColor: '#fff',
          pointBorderWidth: 1
        }))
      },
      options: {
        responsive: true,
        maintainAspectRatio: true,
        plugins: {
          legend: {
            display: true,
            labels: {
              color: colorPalette.textColor,
              font: { family: "'DM Sans', sans-serif", size: 12 }
            }
          }
        },
        scales: {
          r: {
            ticks: { color: colorPalette.textColor },
            grid: { color: colorPalette.gridColor }
          }
        }
      }
    };
  }

  const element = document.getElementById('chart-main');
  if (element) {
    const ctx = element.getContext('2d');
    chartState.mainChart = new Chart(ctx, config);
  }
}

// Event listeners para mudar tipo de gráfico
document.addEventListener('DOMContentLoaded', () => {
  renderCharts();

  const radioButtons = document.querySelectorAll('input[name="chart-type"]');
  radioButtons.forEach(radio => {
    radio.addEventListener('change', e => {
      buildMainChart(e.target.value);
    });
  });
});
