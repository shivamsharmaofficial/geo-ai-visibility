// static/js/app.js

document.addEventListener("DOMContentLoaded", () => {
  console.log("app.js loaded");

  const openBtn = document.getElementById("openBrandModal");
  const backdrop = document.getElementById("brandModalBackdrop");
  const closeBtn = document.getElementById("closeBrandModal");

  const step1 = document.getElementById("brandStep1");
  const step2 = document.getElementById("brandStep2");
  const nextBtn = document.getElementById("brandStepNext");
  const createBtn = document.getElementById("brandCreateBtn");
  const cancelStep1 = document.getElementById("cancelBrandModal");
  const cancelStep2 = document.getElementById("cancelBrandModalStep2");
  const errorBox = document.getElementById("brandModalError");
  const modalTitle = document.getElementById("brandModalTitle");

  // Step 1 inputs
  const brandNameStep1 = document.getElementById("brandNameStep1");
  const brandDescStep1 = document.getElementById("brandDescStep1");

  // Step 2 inputs
  const brandNameStep2 = document.getElementById("brandNameStep2");
  const brandDescStep2 = document.getElementById("brandDescStep2");
  const brandUrlStep2 = document.getElementById("brandUrlStep2");
  const brandRegionStep2 = document.getElementById("brandRegionStep2");
  const brandLangStep2 = document.getElementById("brandLangStep2");
  const brandTopicsStep2 = document.getElementById("brandTopicsStep2");
  const brandRegenerateBtn = document.getElementById("brandRegenerate");

  // Analysis status bar
  const analysisBar = document.getElementById("analysisStatus");
  const analysisProgressFill = document.getElementById("analysisProgressFill");
  const analysisPercentLabel = document.getElementById("analysisPercentLabel");
  const analysisPromptsLabel = document.getElementById("analysisPromptsLabel");

  // Metric cards (top 3)
  const cardBrandMentionsLabel = document.getElementById("cardBrandMentionsLabel");
  const cardBrandMentionsSubtitle = document.getElementById("cardBrandMentionsSubtitle");
  const cardMentionsValue = document.getElementById("cardMentionsValue");

  const cardBrandAvgRankLabel = document.getElementById("cardBrandAvgRankLabel");
  const cardBrandAvgRankSubtitle = document.getElementById("cardBrandAvgRankSubtitle");
  const cardAvgRankValue = document.getElementById("cardAvgRankValue");

  const cardCitationsValue = document.getElementById("cardCitationsValue");
  const cardBrandCitationsSubtitle = document.getElementById("cardBrandCitationsSubtitle");

  // Trend / donut chart controls
  const trendTabVisibility = document.getElementById("trendTabVisibility");
  const trendTabRank = document.getElementById("trendTabRank");
  const trendTopicSelect = document.getElementById("trendTopicSelect");

  // Chart.js instances and state
  let visibilityTrendChart = null;
  let mentionsDonutChart = null;

  const chartColors = [
    "#2563eb", // blue
    "#22c55e", // green
    "#a855f7", // purple
    "#f97316", // orange
    "#0ea5e9", // cyan
    "#64748b", // slate
    "#16a34a", // green-dark
    "#facc15", // yellow
    "#ec4899", // pink
    "#94a3b8", // gray
  ];

  const trendState = {
    labels: [],
    visibilityDatasets: [],
    rankDatasets: [],
    currentMetric: "visibility",
  };

  // ----- Progress animation state -----
  let progressInterval = null;
  let visualProgress = 0;

  function startProgressAnimation() {
    stopProgressAnimation();
    visualProgress = 0;
    progressInterval = setInterval(() => {
      // Slowly go up to 90% while waiting for backend
      if (visualProgress < 90) {
        visualProgress += 1;
        updateAnalysisProgress(visualProgress, 0, 0);
      }
    }, 120); // adjust speed as you like
  }

  function stopProgressAnimation() {
    if (progressInterval) {
      clearInterval(progressInterval);
      progressInterval = null;
    }
  }

  // ---- Modal helpers ----

  function resetModal() {
    if (step1) step1.classList.add("is-active");
    if (step2) step2.classList.remove("is-active");

    if (errorBox) {
      errorBox.style.display = "none";
      errorBox.textContent = "";
    }
    if (modalTitle) modalTitle.textContent = "Add New Brand";

    if (brandNameStep1) brandNameStep1.value = "";
    if (brandDescStep1) brandDescStep1.value = "";

    if (brandNameStep2) brandNameStep2.value = "";
    if (brandDescStep2) brandDescStep2.value = "";
    if (brandUrlStep2) brandUrlStep2.value = "";
    if (brandRegionStep2) brandRegionStep2.value = "";
    if (brandLangStep2) brandLangStep2.value = "";
    if (brandTopicsStep2) brandTopicsStep2.value = "";

    if (nextBtn) {
      nextBtn.disabled = false;
      nextBtn.textContent = "Next";
    }
  }

  function openModal() {
    resetModal();
    backdrop?.classList.add("is-visible");
  }

  function closeModal() {
    backdrop?.classList.remove("is-visible");
  }

  function showError(msg) {
    if (!errorBox) return;
    if (!msg) {
      errorBox.style.display = "none";
      errorBox.textContent = "";
      return;
    }
    errorBox.textContent = msg;
    errorBox.style.display = "block";
  }

  // ---- Analysis bar helpers ----

  function showAnalysisBar() {
    if (!analysisBar) {
      console.warn("analysisStatus element not found");
      return;
    }
    console.log("showAnalysisBar()");
    analysisBar.classList.remove("analysis-status--hidden");
    // Force visible in case some other CSS is interfering
    analysisBar.style.display = "flex";
  }

  function hideAnalysisBar() {
    if (!analysisBar) return;
    analysisBar.classList.add("analysis-status--hidden");
    analysisBar.style.display = "none";
  }

  function updateAnalysisProgress(percent, used, total) {
    const safePercent = Math.min(Math.max(percent, 0), 100);

    if (analysisProgressFill) {
      analysisProgressFill.style.width = `${safePercent}%`;
    }
    if (analysisPercentLabel) {
      analysisPercentLabel.textContent = `${Math.round(safePercent)}%`;
    }
    if (analysisPromptsLabel) {
      analysisPromptsLabel.textContent = `Prompts ${used} / ${total}`;
    }
  }

  // ---- Metric cards updater ----

  function updateMetricCardsFromAnalysis(data, fallbackBrandName) {
    const brandName = data?.brand?.name || fallbackBrandName || "";
    const metrics = data?.metrics || {};

    const mentionsRaw = metrics.brand_share_pct ?? 0;
    const avgRankRaw = metrics.avg_rank ?? 0;
    const citationsRaw = metrics.citations ?? 0;

    const mentions = Number(mentionsRaw) || 0;
    const avgRank = Number(avgRankRaw) || 0;
    const citations = Number(citationsRaw) || 0;

    // Mentions card
    if (cardBrandMentionsLabel) cardBrandMentionsLabel.textContent = brandName || "Brand";
    if (cardBrandMentionsSubtitle) cardBrandMentionsSubtitle.textContent = brandName || "brand";
    if (cardMentionsValue) cardMentionsValue.textContent = mentions.toFixed(1);

    // Average rank card
    if (cardBrandAvgRankLabel) cardBrandAvgRankLabel.textContent = brandName || "Brand";
    if (cardBrandAvgRankSubtitle) cardBrandAvgRankSubtitle.textContent = brandName || "brand";
    if (cardAvgRankValue) cardAvgRankValue.textContent = avgRank.toFixed(1);

    // Citations card
    if (cardCitationsValue) cardCitationsValue.textContent = citations.toString();
    if (cardBrandCitationsSubtitle) cardBrandCitationsSubtitle.textContent = brandName || "brand";
  }

  // ---- Helpers for topics ----

  function parseTopics(topicsText) {
    if (!topicsText || typeof topicsText !== "string") return [];
    return topicsText
      .split(/\r?\n/)
      .map((t) => t.trim())
      .filter((t) => t.length > 0);
  }

  function populateTopicDropdown(topics) {
    if (!trendTopicSelect) return;

    trendTopicSelect.innerHTML = "";
    const allOpt = document.createElement("option");
    allOpt.value = "";
    allOpt.textContent = "All Topics";
    trendTopicSelect.appendChild(allOpt);

    topics.forEach((t) => {
      const opt = document.createElement("option");
      opt.value = t;
      opt.textContent = t;
      trendTopicSelect.appendChild(opt);
    });
  }

  // ---- Chart helpers ----

function buildDatasetsFromSeries(series, brandName) {
  if (!series) return [];

  // NEW: handle array form from Gemini
  if (Array.isArray(series)) {
    // Ensure main brand first
    const ordered = [];
    if (brandName) {
      const main = series.find((s) => s.name === brandName);
      if (main) ordered.push(main);
    }
    series.forEach((s) => {
      if (!ordered.includes(s)) ordered.push(s);
    });

    const limited = ordered.slice(0, 10); // at most 10 brands

    return limited.map((item, idx) => ({
      label: item.name,
      data: Array.isArray(item.values) ? item.values : [],
      borderColor: chartColors[idx % chartColors.length],
      backgroundColor: chartColors[idx % chartColors.length],
      tension: 0.35,
      pointRadius: 1.5,
      fill: false,
      borderWidth: 2,
    }));
  }

  // OLD fallback: object form (kept just in case)
  if (typeof series !== "object") return [];

  const allBrands = Object.keys(series);
  const ordered = [];

  if (brandName && series[brandName]) {
    ordered.push(brandName);
  }
  allBrands.forEach((b) => {
    if (!ordered.includes(b)) ordered.push(b);
  });

  const limited = ordered.slice(0, 10);

  return limited.map((name, idx) => ({
    label: name,
    data: series[name] || [],
    borderColor: chartColors[idx % chartColors.length],
    backgroundColor: chartColors[idx % chartColors.length],
    tension: 0.35,
    pointRadius: 1.5,
    fill: false,
    borderWidth: 2,
  }));
}




  function setTrendTabs(metric) {
    if (!trendTabVisibility || !trendTabRank) return;

    if (metric === "visibility") {
      trendTabVisibility.classList.add("active");
      trendTabRank.classList.remove("active");
    } else {
      trendTabVisibility.classList.remove("active");
      trendTabRank.classList.add("active");
    }
  }

  function createOrUpdateTrendChart(metric) {
    const ctxElem = document.getElementById("visibilityTrendChart");
    if (!ctxElem || !window.Chart) {
      return;
    }

    const ctx = ctxElem.getContext("2d");
    const datasets =
      metric === "rank" ? trendState.rankDatasets : trendState.visibilityDatasets;

    const yTitle =
      metric === "rank" ? "Average Rank" : "Share of Voice (%)";

    if (!visibilityTrendChart) {
      visibilityTrendChart = new Chart(ctx, {
        type: "line",
        data: {
          labels: trendState.labels,
          datasets: datasets,
        },
        options: {
          responsive: true,
          maintainAspectRatio: false,
          scales: {
            y: {
              beginAtZero: metric === "visibility",
              title: { display: true, text: yTitle },
              ticks: { precision: 0 },
            },
            x: {
              title: { display: true, text: "Time" },
            },
          },
          plugins: {
            legend: {
              position: "top",
            },
          },
        },
      });
    } else {
      visibilityTrendChart.data.labels = trendState.labels;
      visibilityTrendChart.data.datasets = datasets;
      visibilityTrendChart.options.scales.y.beginAtZero =
        metric === "visibility";
      visibilityTrendChart.options.scales.y.title.text = yTitle;
      visibilityTrendChart.update();
    }

    trendState.currentMetric = metric;
    setTrendTabs(metric);
  }

  function createOrUpdateDonutChart(donutData) {
    const ctxElem = document.getElementById("mentionsDonutChart");
    if (!ctxElem || !window.Chart) {
      return;
    }
    const ctx = ctxElem.getContext("2d");

    const labels = (donutData || []).map((d) => d.label);
    const values = (donutData || []).map((d) => d.value);
    const bgColors = labels.map(
      (_, idx) => chartColors[idx % chartColors.length]
    );

    const data = {
      labels,
      datasets: [
        {
          data: values,
          backgroundColor: bgColors,
          borderWidth: 1,
        },
      ],
    };

    if (!mentionsDonutChart) {
      mentionsDonutChart = new Chart(ctx, {
        type: "doughnut",
        data,
        options: {
          responsive: true,
          maintainAspectRatio: false,
          plugins: {
            legend: {
              position: "bottom",
            },
          },
          cutout: "60%",
        },
      });
    } else {
      mentionsDonutChart.data = data;
      mentionsDonutChart.update();
    }
  }

  function updateChartsFromAnalysis(data, brandName, topicsText) {
  const metrics = data?.metrics || {};
  const trend = metrics.trend || {};
  const donut = metrics.donut || [];

  // Trend state
  const labels = trend.labels || [];
  const visibilitySeries = trend.visibility || []; // ⬅️ change {} → []
  const avgRankSeries = trend.avg_rank || [];      // ⬅️ change {} → []

  trendState.labels = labels;
  trendState.visibilityDatasets = buildDatasetsFromSeries(
    visibilitySeries,
    brandName
  );
  trendState.rankDatasets = buildDatasetsFromSeries(
    avgRankSeries,
    brandName
  );

  // Initial metric: Visibility
  createOrUpdateTrendChart("visibility");

  // Donut chart: brand vs competitors
  createOrUpdateDonutChart(donut);

  // Topics dropdown
  const topics = parseTopics(topicsText);
  populateTopicDropdown(topics);
}


  // ---- Analysis runner ----

  async function runBrandAnalysisFromStep2() {
    console.log("runBrandAnalysisFromStep2 called");

    if (!brandNameStep2) {
      console.warn("brandNameStep2 not found in DOM");
      return;
    }

    const brandName = (brandNameStep2.value || "").trim();
    const brandDesc = (brandDescStep2?.value || "").trim();
    const brandUrl = (brandUrlStep2?.value || "").trim();
    const region = (brandRegionStep2?.value || "").trim();
    const language = (brandLangStep2?.value || "").trim();
    const topicsText = (brandTopicsStep2?.value || "").trim();

    console.log("brandNameStep2 value:", brandName);

    if (!brandName) {
      console.warn("Brand name empty, skipping /brand/analyze/ call");
      return;
    }

    // Show bar and start animation as soon as Create is clicked
    showAnalysisBar();
    updateAnalysisProgress(0, 0, 0);
    startProgressAnimation();

    try {
      const resp = await fetch("/brand/analyze/", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          brand_name: brandName,
          brand_description: brandDesc,
          brand_url: brandUrl,
          region: region,
          language: language,
          initial_topics: topicsText,
        }),
      });

      let data;
      try {
        data = await resp.json();
      } catch (e) {
        console.error("Invalid JSON from /brand/analyze/:", e);
        stopProgressAnimation();
        return;
      }

      console.log("Brand Analysis Response:", data);

      const promptStats = data?.metrics?.prompt_stats || {};
      const used = promptStats.used || 0;
      const total = promptStats.total || 0;

      // Stop the fake animation and set final progress to 100%
      stopProgressAnimation();
      updateAnalysisProgress(100, used, total);

      // Update cards
      updateMetricCardsFromAnalysis(data, brandName);

      // Update charts (trend + donut + topic dropdown)
      updateChartsFromAnalysis(data, brandName, topicsText);
    } catch (err) {
      console.error("Error calling /brand/analyze/:", err);
      stopProgressAnimation();
      // Optionally: hideAnalysisBar();
    }
  }

  // ---- Step 1 -> Step 2 (lookup_brand) ----

  async function goToStep2(useRegenerate = false) {
    if (!nextBtn) return;

    const rawName = useRegenerate ? brandNameStep2?.value : brandNameStep1?.value;
    const rawDesc = useRegenerate ? brandDescStep2?.value : brandDescStep1?.value;

    const brandName = (rawName || "").trim();
    const brandDesc = rawDesc || "";

    if (!brandName) {
      showError("Please enter a brand name.");
      return;
    }

    nextBtn.disabled = true;
    nextBtn.textContent = useRegenerate ? "Re-generating..." : "Generating...";
    showError("");

    try {
      const resp = await fetch("/brand/lookup/", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          brand_name: brandName,
          brand_description: brandDesc,
        }),
      });

      let data;
      try {
        data = await resp.json();
        console.log("Brand Lookup Response:", data);
      } catch {
        showError(`Server returned an invalid response (${resp.status}).`);
        return;
      }

      if (!resp.ok || data.error) {
        showError(data.error || `Backend error: ${resp.status}`);
        return;
      }

      if (brandNameStep2) brandNameStep2.value = data.brand_name || brandName;
      if (brandDescStep2) brandDescStep2.value = data.brand_description || brandDesc;
      if (brandUrlStep2) brandUrlStep2.value = data.brand_url || "";
      if (brandRegionStep2) brandRegionStep2.value = data.region || "";
      if (brandLangStep2) brandLangStep2.value = data.language || "";
      if (brandTopicsStep2) brandTopicsStep2.value = data.initial_topics || "";

      if (step1) step1.classList.remove("is-active");
      if (step2) step2.classList.add("is-active");
      if (modalTitle) modalTitle.textContent = "Configure Brand";
    } catch (err) {
      console.error(err);
      showError("Something went wrong while contacting the server.");
    } finally {
      nextBtn.disabled = false;
      nextBtn.textContent = "Next";
    }
  }

  // ---- Event binding ----

  openBtn?.addEventListener("click", openModal);
  closeBtn?.addEventListener("click", closeModal);
  cancelStep1?.addEventListener("click", closeModal);
  cancelStep2?.addEventListener("click", closeModal);

  nextBtn?.addEventListener("click", (e) => {
    e.preventDefault();
    goToStep2(false);
  });

  brandRegenerateBtn?.addEventListener("click", (e) => {
    e.preventDefault();
    goToStep2(true);
  });

  backdrop?.addEventListener("click", (e) => {
    if (e.target === backdrop) closeModal();
  });

  // Trend tabs
  trendTabVisibility?.addEventListener("click", () => {
    createOrUpdateTrendChart("visibility");
  });
  trendTabRank?.addEventListener("click", () => {
    createOrUpdateTrendChart("rank");
  });

  // Topic select (later you can use it to filter / re-run analysis by topic)
  trendTopicSelect?.addEventListener("change", (e) => {
    console.log("Selected topic for trend:", e.target.value);
  });

  // Create: close modal and start analysis (shows analysisStatus bar + prompts count)
  createBtn?.addEventListener("click", (e) => {
    e.preventDefault();
    console.log("Create button clicked");
    closeModal();
    runBrandAnalysisFromStep2();
  });
});
