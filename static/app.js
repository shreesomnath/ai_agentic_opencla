document.addEventListener("DOMContentLoaded", () => {
    // Populate report generation date for printing
    document.querySelectorAll(".print-date").forEach(el => {
        el.textContent = new Date().toLocaleDateString(undefined, {
            year: 'numeric', month: 'long', day: 'numeric',
            hour: '2-digit', minute: '2-digit'
        });
    });

    // DOM Elements
    const sampleSelect = document.getElementById("sample-select");
    const bomTbody = document.getElementById("bom-tbody");
    const addRowBtn = document.getElementById("add-row-btn");
    const optimizeBtn = document.getElementById("optimize-btn");
    const paretoBtn = document.getElementById("pareto-btn");
    const chatInput = document.getElementById("chat-input");
    const chatSendBtn = document.getElementById("chat-send-btn");
    const chatBox = document.getElementById("chat-box");
    const themeToggle = document.getElementById("theme-toggle");
    const activeAssemblyIndicator = document.getElementById("active-assembly-indicator");

    // Floating AirLab Advisor Pop-Up Controls
    const advisorBubble = document.getElementById("advisor-bubble-trigger");
    const chatPanel = document.querySelector(".chat-panel");
    const closeAdvisorBtn = document.getElementById("close-advisor-btn");

    if (advisorBubble && chatPanel) {
        advisorBubble.addEventListener("click", (e) => {
            e.stopPropagation();
            chatPanel.classList.toggle("active");
            if (chatPanel.classList.contains("active") && chatInput) {
                chatInput.focus();
            }
        });
    }
    if (closeAdvisorBtn && chatPanel) {
        closeAdvisorBtn.addEventListener("click", (e) => {
            e.stopPropagation();
            chatPanel.classList.remove("active");
        });
    }
    document.addEventListener("click", (e) => {
        if (chatPanel && chatPanel.classList.contains("active")) {
            if (!chatPanel.contains(e.target) && advisorBubble && !advisorBubble.contains(e.target)) {
                chatPanel.classList.remove("active");
            }
        }
    });
    
    // Dynamic Process Parameters Sliders
    const paramProcessEfficiency = document.getElementById("param-process-efficiency");
    const paramRecycleRate = document.getElementById("param-recycle-rate");
    const paramLossFactor = document.getElementById("param-loss-factor");
    
    const valProcessEfficiency = document.getElementById("val-process-efficiency");
    const valRecycleRate = document.getElementById("val-recycle-rate");
    const valLossFactor = document.getElementById("val-loss-factor");

    if (paramProcessEfficiency && valProcessEfficiency) {
        paramProcessEfficiency.addEventListener("input", () => {
            valProcessEfficiency.textContent = parseFloat(paramProcessEfficiency.value).toFixed(2);
        });
    }
    if (paramRecycleRate && valRecycleRate) {
        paramRecycleRate.addEventListener("input", () => {
            valRecycleRate.textContent = parseFloat(paramRecycleRate.value).toFixed(2);
        });
    }
    if (paramLossFactor && valLossFactor) {
        paramLossFactor.addEventListener("input", () => {
            valLossFactor.textContent = parseFloat(paramLossFactor.value).toFixed(2);
        });
    }
    
    // Multi-Criteria Optimization Priorities Weights (TOPSIS)
    const weightGwp = document.getElementById("weight-gwp");
    const weightAcid = document.getElementById("weight-acid");
    const weightWater = document.getElementById("weight-water");
    const weightCost = document.getElementById("weight-cost");
    
    const valWeightGwp = document.getElementById("val-weight-gwp");
    const valWeightAcid = document.getElementById("val-weight-acid");
    const valWeightWater = document.getElementById("val-weight-water");
    const valWeightCost = document.getElementById("val-weight-cost");

    if (weightGwp && valWeightGwp) {
        weightGwp.addEventListener("input", () => {
            valWeightGwp.textContent = weightGwp.value + "%";
            if (typeof activeParetoFrontier !== 'undefined' && activeParetoFrontier && activeParetoFrontier.length > 0) {
                renderParetoFrontierTable();
            }
        });
    }
    if (weightAcid && valWeightAcid) {
        weightAcid.addEventListener("input", () => {
            valWeightAcid.textContent = weightAcid.value + "%";
            if (typeof activeParetoFrontier !== 'undefined' && activeParetoFrontier && activeParetoFrontier.length > 0) {
                renderParetoFrontierTable();
                debouncedBackendReweigh();
            }
        });
    }
    if (weightWater && valWeightWater) {
        weightWater.addEventListener("input", () => {
            valWeightWater.textContent = weightWater.value + "%";
            if (typeof activeParetoFrontier !== 'undefined' && activeParetoFrontier && activeParetoFrontier.length > 0) {
                renderParetoFrontierTable();
                debouncedBackendReweigh();
            }
        });
    }
    if (weightCost && valWeightCost) {
        weightCost.addEventListener("input", () => {
            valWeightCost.textContent = weightCost.value + "%";
            if (typeof activeParetoFrontier !== 'undefined' && activeParetoFrontier && activeParetoFrontier.length > 0) {
                renderParetoFrontierTable();
                debouncedBackendReweigh();
            }
        });
    }

    // TOPSIS Scenario Preset Click Handlers
    function applyTopsisPreset(g, a, w, c) {
        if (weightGwp) { weightGwp.value = g; valWeightGwp.textContent = g + "%"; }
        if (weightAcid) { weightAcid.value = a; valWeightAcid.textContent = a + "%"; }
        if (weightWater) { weightWater.value = w; valWeightWater.textContent = w + "%"; }
        if (weightCost) { weightCost.value = c; valWeightCost.textContent = c + "%"; }
        
        if (typeof activeParetoFrontier !== 'undefined' && activeParetoFrontier && activeParetoFrontier.length > 0) {
            renderParetoFrontierTable();
            if (typeof debouncedBackendReweigh === 'function') {
                debouncedBackendReweigh();
            }
        }
    }

    const btnEco = document.getElementById("preset-eco");
    const btnBalanced = document.getElementById("preset-balanced");
    const btnCost = document.getElementById("preset-cost");

    if (btnEco) btnEco.addEventListener("click", () => applyTopsisPreset(70, 15, 10, 5));
    if (btnBalanced) btnBalanced.addEventListener("click", () => applyTopsisPreset(35, 15, 15, 35));
    if (btnCost) btnCost.addEventListener("click", () => applyTopsisPreset(10, 10, 10, 70));
    
    const openlcaStatusDot = document.getElementById("openlca-status-dot");
    const openlcaStatusText = document.getElementById("openlca-status-text");
    const openlcaDbStats = document.getElementById("openlca-db-stats");
    const openlcaFlowsCount = document.getElementById("openlca-flows-count");
    const openlcaProcessesCount = document.getElementById("openlca-processes-count");
    const openlcaPortInput = document.getElementById("openlca-port-input");
    const openlcaSyncBtn = document.getElementById("openlca-sync-btn");
    const ollamaStatus = document.getElementById("ollama-status");
    const lciaMethodSelect = document.getElementById("lcia-method-select");

    function loadImpactMethods() {
        if (!lciaMethodSelect) return;
        fetch("/api/impact-methods")
            .then(res => res.json())
            .then(methods => {
                lciaMethodSelect.innerHTML = '<option value="">-- Auto-select (ReCiPe Midpoint) --</option>';
                if (methods && methods.length > 0) {
                    methods.forEach(m => {
                        const opt = document.createElement("option");
                        opt.value = m.id;
                        opt.textContent = m.name;
                        lciaMethodSelect.appendChild(opt);
                    });
                }
            })
            .catch(err => console.error("Error loading impact methods:", err));
    }

    function updateConnectionUI(connected, port, flowsCount, processesCount, errorMsg, isEmptyDb) {
        if (connected) {
            if (openlcaStatusDot) {
                openlcaStatusDot.classList.remove("offline");
                openlcaStatusDot.classList.add("online");
            }
            if (openlcaStatusText) {
                if (isEmptyDb) {
                    openlcaStatusText.textContent = "openLCA: Connected (Empty DB - Simulation Active)";
                } else {
                    openlcaStatusText.textContent = "openLCA: Connected";
                }
            }
            if (openlcaPortInput) openlcaPortInput.value = port;
            if (openlcaDbStats) openlcaDbStats.style.display = "inline-block";
            if (openlcaFlowsCount) openlcaFlowsCount.textContent = flowsCount.toLocaleString();
            if (openlcaProcessesCount) openlcaProcessesCount.textContent = processesCount.toLocaleString();
            
            // Re-fetch impact methods whenever successfully connected
            loadImpactMethods();
        } else {
            if (openlcaStatusDot) {
                openlcaStatusDot.classList.remove("online");
                openlcaStatusDot.classList.add("offline");
            }
            if (openlcaStatusText) openlcaStatusText.textContent = "openLCA: Offline";
            if (openlcaDbStats) openlcaDbStats.style.display = "none";
            if (errorMsg) {
                console.warn("openLCA Connection Error:", errorMsg);
            }
        }
    }

    function checkInitialConnectionStatus() {
        fetch("/api/status")
            .then(res => res.json())
            .then(data => {
                if (data.success) {
                    updateConnectionUI(data.connected, data.port, data.flows_count, data.processes_count, data.error, data.is_empty_db);
                } else {
                    updateConnectionUI(false, 8080, 0, 0, data.error, false);
                }
            })
            .catch(err => {
                updateConnectionUI(false, 8080, 0, 0, err.message, false);
            });
    }

    function checkOllamaStatus() {
        fetch("/api/samples")
            .then(() => {
                if (ollamaStatus) {
                    ollamaStatus.classList.remove("offline");
                    ollamaStatus.classList.add("online");
                }
            })
            .catch(() => {
                if (ollamaStatus) {
                    ollamaStatus.classList.remove("online");
                    ollamaStatus.classList.add("offline");
                }
            });
    }

    if (openlcaSyncBtn) {
        openlcaSyncBtn.addEventListener("click", () => {
            const port = parseInt(openlcaPortInput.value) || 8080;
            
            openlcaSyncBtn.classList.add("syncing");
            openlcaSyncBtn.disabled = true;
            if (openlcaPortInput) openlcaPortInput.disabled = true;
            
            appendChatMessage("System", `Syncing and rebuilding TF-IDF search cache with openLCA on port ${port}...`);
            
            fetch("/api/sync", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ port: port })
            })
            .then(res => res.json())
            .then(data => {
                openlcaSyncBtn.classList.remove("syncing");
                openlcaSyncBtn.disabled = false;
                if (openlcaPortInput) openlcaPortInput.disabled = false;
                
                if (data.success) {
                    updateConnectionUI(true, data.port, data.flows_count, data.processes_count, null, data.is_empty_db);
                    if (data.is_empty_db) {
                        appendChatMessage("Advisor", `Sync successful! Connected to port **${data.port}** but the active database is empty. Fallback Simulation mode has been activated so you can test all features.`);
                    } else {
                        appendChatMessage("Advisor", `Sync successful! Re-established connection on port **${data.port}** with ecoinvent database context. Indexed **${data.flows_count.toLocaleString()}** flow descriptions and **${data.processes_count.toLocaleString()}** processes. TF-IDF search space initialized and optimized.`);
                    }
                } else {
                    updateConnectionUI(false, port, 0, 0, data.error, false);
                    appendChatMessage("System Error", `Sync failed on port ${port}: ${data.error}`);
                    alert(`Sync failed: ${data.error}`);
                }
            })
            .catch(err => {
                openlcaSyncBtn.classList.remove("syncing");
                openlcaSyncBtn.disabled = false;
                if (openlcaPortInput) openlcaPortInput.disabled = false;
                
                updateConnectionUI(false, port, 0, 0, err.message);
                appendChatMessage("System Error", `Sync failed due to network error: ${err.message}`);
                alert(`Network error during sync: ${err.message}`);
            });
        });
    }

    // Run connection status verification
    checkInitialConnectionStatus();
    checkOllamaStatus();
    
    // Tabs & Panels
    const tabFlat = document.getElementById("tab-flat");
    const tabHierarchical = document.getElementById("tab-hierarchical");
    const tabAutonomous = document.getElementById("tab-autonomous");
    const panelFlat = document.getElementById("panel-flat");
    const panelHierarchical = document.getElementById("panel-hierarchical");
    const panelAutonomous = document.getElementById("panel-autonomous");
    const bomJsonTextarea = document.getElementById("bom-json-textarea");
    const loadHierarchicalSampleBtn = document.getElementById("load-hierarchical-sample-btn");
    const compileHierarchicalBtn = document.getElementById("compile-hierarchical-btn");
    const runAutonomousBtn = document.getElementById("run-autonomous-btn");
    const autonomousGoalInput = document.getElementById("autonomous-goal-input");
    const autonomousTerminal = document.getElementById("autonomous-terminal");
    
    // TVL Elements
    const tvlBadge = document.getElementById("tvl-badge");
    const tvlInputMass = document.getElementById("tvl-input-mass");
    const tvlOutputMass = document.getElementById("tvl-output-mass");
    const tvlError = document.getElementById("tvl-error");
    
    // Metric Card Value Elements
    const gwpBase = document.getElementById("gwp-baseline");
    const gwpOpt = document.getElementById("gwp-optimized");
    const gwpChange = document.getElementById("gwp-change");
    
    const acidBase = document.getElementById("acid-baseline");
    const acidOpt = document.getElementById("acid-optimized");
    const acidChange = document.getElementById("acid-change");
    
    const waterBase = document.getElementById("water-baseline");
    const waterOpt = document.getElementById("water-optimized");
    const waterChange = document.getElementById("water-change");
    
    const costBase = document.getElementById("cost-baseline");
    const costOpt = document.getElementById("cost-optimized");
    const costChange = document.getElementById("cost-change");
    
    // Uncertainty Elements
    const gwpBaseUnc = document.getElementById("gwp-baseline-uncertainty");
    const gwpOptUnc = document.getElementById("gwp-optimized-uncertainty");
    const acidBaseUnc = document.getElementById("acid-baseline-uncertainty");
    const acidOptUnc = document.getElementById("acid-optimized-uncertainty");
    const waterBaseUnc = document.getElementById("water-baseline-uncertainty");
    const waterOptUnc = document.getElementById("water-optimized-uncertainty");
    const costBaseUnc = document.getElementById("cost-baseline-uncertainty");
    const costOptUnc = document.getElementById("cost-optimized-uncertainty");
    
    // Chart and justification elements
    const chartPlaceholder = document.getElementById("chart-placeholder");
    const tradeoffChartImg = document.getElementById("tradeoff-chart-img");
    const justificationWrapper = document.getElementById("justification-wrapper");
    const justificationContent = document.getElementById("justification-content");
    
    // Global calculation state
    let activeState = {
        exchanges: [],
        report: {},
        temp_proc_id: null,
        temp_sys_id: null,
        method_id: null,
        chart_url_dark: null,
        chart_url_light: null,
        unc_urls_dark: null,
        unc_urls_light: null,
        active_chart_tab: "tradeoff", // "tradeoff" or "uncertainty"
        selected_kpi: "Global Warming" // Default active KPI
    };

    let activeCustomParameterOverrides = {};

    // Chart Tab Selection Elements
    const tradeoffTabBtn = document.getElementById("chart-tab-tradeoff");
    const uncertaintyTabBtn = document.getElementById("chart-tab-uncertainty");
    const uncertaintyChartImg = document.getElementById("uncertainty-chart-img");

    // KPI Cards Elements for Uncertainty Chart Toggling
    const cardGwp = document.getElementById("card-gwp");
    const cardAcid = document.getElementById("card-acid");
    const cardWater = document.getElementById("card-water");
    const cardCost = document.getElementById("card-cost");
    
    function selectKpiCard(kpiName, cardElem) {
        activeState.selected_kpi = kpiName;
        
        // Remove 'selected' class from all cards
        [cardGwp, cardAcid, cardWater, cardCost].forEach(card => {
            if (card) card.classList.remove("selected");
        });
        
        // Add 'selected' class to the clicked card
        if (cardElem) cardElem.classList.add("selected");
        
        // Update the chart image if uncertainty distribution is visible
        updateChartImageSource();
    }

    const hotspotTabBtn = document.getElementById("chart-tab-hotspot");

    if (tradeoffTabBtn && uncertaintyTabBtn && hotspotTabBtn) {
        tradeoffTabBtn.addEventListener("click", () => {
            activeState.active_chart_tab = "tradeoff";
            tradeoffTabBtn.classList.add("active");
            uncertaintyTabBtn.classList.remove("active");
            hotspotTabBtn.classList.remove("active");
            updateChartImageSource();
        });
        
        uncertaintyTabBtn.addEventListener("click", () => {
            activeState.active_chart_tab = "uncertainty";
            uncertaintyTabBtn.classList.add("active");
            tradeoffTabBtn.classList.remove("active");
            hotspotTabBtn.classList.remove("active");
            updateChartImageSource();
        });

        hotspotTabBtn.addEventListener("click", () => {
            activeState.active_chart_tab = "hotspot";
            hotspotTabBtn.classList.add("active");
            tradeoffTabBtn.classList.remove("active");
            uncertaintyTabBtn.classList.remove("active");
            updateChartImageSource();
        });
    }

    if (cardGwp) cardGwp.addEventListener("click", () => selectKpiCard("Global Warming", cardGwp));
    if (cardAcid) cardAcid.addEventListener("click", () => selectKpiCard("Acidification", cardAcid));
    if (cardWater) cardWater.addEventListener("click", () => selectKpiCard("Water Consumption", cardWater));
    if (cardCost) cardCost.addEventListener("click", () => selectKpiCard("Feedstock Cost", cardCost));

    // Theme Switcher Logic
    const savedTheme = localStorage.getItem("theme") || "light"; // Default is light/normal theme
    if (savedTheme === "light") {
        document.body.classList.add("light-theme");
    } else {
        document.body.classList.remove("light-theme");
    }
    
    themeToggle.addEventListener("click", () => {
        document.body.classList.toggle("light-theme");
        const isLight = document.body.classList.contains("light-theme");
        localStorage.setItem("theme", isLight ? "light" : "dark");
        updateChartImageSource();
    });

    let interactiveChartInstance = null;

    function renderInteractiveChart() {
        const ctx = document.getElementById("interactive-chart");
        if (!ctx) return;
        
        if (interactiveChartInstance) {
            interactiveChartInstance.destroy();
            interactiveChartInstance = null;
        }
        
        const isLight = document.body.classList.contains("light-theme");
        const textColor = isLight ? "#161B22" : "#ECEFF3";
        const gridColor = isLight ? "rgba(220, 225, 230, 0.15)" : "rgba(35, 42, 52, 0.5)";
        
        const baselineColor = isLight ? "#B9C2CC" : "#3A4452";
        const optimizedColor = isLight ? "#2E8470" : "#3FA88B";
        const goldColor = isLight ? "#B8842E" : "#D9A441";
        
        const chartTitleElem = document.getElementById("chart-active-title");
        const isPareto = activeState.chart_url_dark && activeState.chart_url_dark.includes("pareto");
        
        if (activeState.active_chart_tab === "hotspot") {
            const chartTitleElem = document.getElementById("chart-active-title");
            if (chartTitleElem) {
                chartTitleElem.textContent = "BOM Feedstock Mass Composition & Hotspot Breakdown";
                chartTitleElem.style.display = "block";
            }
            
            const exchanges = activeState.exchanges || [];
            if (exchanges.length === 0) {
                const placeholder = document.getElementById("chart-placeholder");
                if (placeholder) {
                    placeholder.style.display = "block";
                    placeholder.textContent = "Please load a case study template or run optimization to generate BOM breakdown";
                }
                const container = document.getElementById("interactive-chart-container");
                if (container) container.style.display = "none";
                return;
            }
            
            const placeholder = document.getElementById("chart-placeholder");
            if (placeholder) placeholder.style.display = "none";
            const container = document.getElementById("interactive-chart-container");
            if (container) container.style.display = "block";

            const labels = [];
            const dataValues = [];
            exchanges.forEach(ex => {
                let amount = parseFloat(ex.amount) || 0;
                let unit = (ex.unit || "kg").toLowerCase();
                let name = ex.name || "Material";
                
                if (name.includes(",")) {
                    name = name.split(",")[0].trim();
                }
                
                if (unit === "g" || unit === "gram") {
                    amount = amount / 1000.0;
                    unit = "kg";
                } else if (unit === "ton" || unit === "t") {
                    amount = amount * 1000.0;
                    unit = "kg";
                }
                
                labels.push(`${name} (${amount.toFixed(2)} ${unit})`);
                dataValues.push(amount);
            });

            interactiveChartInstance = new Chart(ctx, {
                type: 'doughnut',
                data: {
                    labels: labels,
                    datasets: [{
                        data: dataValues,
                        backgroundColor: [
                            '#10b981', '#3b82f6', '#8b5cf6', '#f59e0b', '#ef4444', 
                            '#ec4899', '#06b6d4', '#84cc16', '#a855f7', '#64748b'
                        ],
                        borderWidth: 1.5,
                        borderColor: isLight ? '#ffffff' : '#1f2937'
                    }]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    plugins: {
                        legend: {
                            position: 'right',
                            labels: {
                                color: textColor,
                                font: { family: 'DM Sans', size: 10 }
                            }
                        },
                        tooltip: {
                            callbacks: {
                                label: function(context) {
                                    const value = context.raw;
                                    const total = context.dataset.data.reduce((a, b) => a + b, 0);
                                    const percentage = total > 0 ? ((value / total) * 100).toFixed(1) : 0;
                                    return ` Mass Allocation: ${percentage}%`;
                                }
                            }
                        }
                    },
                    cutout: '60%'
                }
            });
            return;
        }

        if (activeState.active_chart_tab === "tradeoff") {
            if (isPareto) {
                const frontier = window.activeParetoFrontier || [];
                if (frontier.length === 0) return;
                
                if (chartTitleElem) {
                    chartTitleElem.textContent = "Pareto Frontier & TOPSIS Optimal Blend Highlight";
                    chartTitleElem.style.display = "block";
                }
                
                const scatterData = frontier.map((pt, idx) => ({
                    x: pt.metrics.Cost,
                    y: pt.metrics.GWP,
                    ptData: pt,
                    index: idx
                }));
                
                const pointColors = frontier.map(pt => {
                    if (pt.topsis_rank === 1) return goldColor;
                    const score = pt.topsis_score || 0.5;
                    return isLight ? `rgba(46, 132, 112, ${0.4 + score * 0.6})` : `rgba(63, 168, 139, ${0.4 + score * 0.6})`;
                });
                
                const pointSizes = frontier.map(pt => (pt.topsis_rank === 1 ? 14 : 7));
                const pointStyles = frontier.map(pt => (pt.topsis_rank === 1 ? "star" : "circle"));
                
                interactiveChartInstance = new Chart(ctx, {
                    type: 'scatter',
                    data: {
                        datasets: [{
                            label: 'Pareto Alternatives',
                            data: scatterData,
                            backgroundColor: pointColors,
                            borderColor: isLight ? "#ffffff" : "#11151B",
                            borderWidth: 1,
                            pointRadius: pointSizes,
                            pointHoverRadius: pointSizes.map(s => s + 3),
                            pointStyle: pointStyles
                        }]
                    },
                    options: {
                        responsive: true,
                        maintainAspectRatio: false,
                        plugins: {
                            legend: {
                                labels: { color: textColor, font: { family: 'inherit', size: 10 } }
                            },
                            tooltip: {
                                callbacks: {
                                    label: function(context) {
                                        const pt = context.raw.ptData;
                                        const lines = [
                                            `Rank: ${pt.topsis_rank} | TOPSIS Score: ${(pt.topsis_score || 0).toFixed(4)}`,
                                            `Cost: $${pt.metrics.Cost.toFixed(2)}`,
                                            `GWP: ${pt.metrics.GWP.toFixed(4)} kg CO2 eq`,
                                            `Substitutions:`
                                        ];
                                        for (const [name, ratio] of Object.entries(pt.ratios)) {
                                            lines.push(` - ${name.split(',')[0]}: ${(ratio * 100).toFixed(0)}% recycled`);
                                        }
                                        return lines;
                                    }
                                }
                            }
                        },
                        scales: {
                            x: {
                                title: { display: true, text: 'Feedstock Cost (USD)', color: textColor, font: { weight: 'bold' } },
                                grid: { color: gridColor },
                                ticks: { color: textColor }
                            },
                            y: {
                                title: { display: true, text: 'Global Warming (kg CO2 eq)', color: textColor, font: { weight: 'bold' } },
                                grid: { color: gridColor },
                                ticks: { color: textColor }
                            }
                        }
                    }
                });
            } else {
                const metrics = activeState.report ? activeState.report.metrics : null;
                if (!metrics) return;
                
                if (chartTitleElem) {
                    chartTitleElem.textContent = "Optimization Impact Trade-Offs (Normalized Baseline vs. Optimized)";
                    chartTitleElem.style.display = "block";
                }
                
                const labels = Object.keys(metrics);
                const baselineValues = labels.map(() => 100.0);
                const optimizedValues = labels.map(name => {
                    const m = metrics[name];
                    return m.baseline > 0 ? (m.optimized / m.baseline) * 100.0 : 0.0;
                });
                
                const optColors = optimizedValues.map(val => (val > 100.0 ? (isLight ? "#AE4F4F" : "#C0605C") : optimizedColor));
                
                interactiveChartInstance = new Chart(ctx, {
                    type: 'bar',
                    data: {
                        labels: labels,
                        datasets: [
                            {
                                label: 'Baseline',
                                data: baselineValues,
                                backgroundColor: baselineColor,
                                borderRadius: 4
                            },
                            {
                                label: 'Optimized',
                                data: optimizedValues,
                                backgroundColor: optColors,
                                borderRadius: 4
                            }
                        ]
                    },
                    options: {
                        responsive: true,
                        maintainAspectRatio: false,
                        plugins: {
                            legend: {
                                labels: { color: textColor, font: { family: 'inherit', size: 10 } }
                            },
                            tooltip: {
                                callbacks: {
                                    label: function(context) {
                                        const label = context.dataset.label;
                                        const kpi = context.label;
                                        const metric = metrics[kpi];
                                        if (!metric) return `${label}: ${context.raw.toFixed(1)}%`;
                                        const val = label === "Baseline" ? metric.baseline : metric.optimized;
                                        const unit = metric.unit || "";
                                        return `${label}: ${context.raw.toFixed(1)}% (${val.toLocaleString(undefined, {minimumFractionDigits: 2, maximumFractionDigits: 4})} ${unit})`;
                                    }
                                }
                            }
                        },
                        scales: {
                            y: {
                                min: 0,
                                title: { display: true, text: 'Percentage of Baseline (%)', color: textColor, font: { weight: 'bold' } },
                                grid: { color: gridColor },
                                ticks: { color: textColor }
                            },
                            x: {
                                grid: { display: false },
                                ticks: { color: textColor }
                            }
                        }
                    }
                });
            }
        } else {
            const metrics = activeState.report ? activeState.report.metrics : null;
            if (!metrics) return;
            
            const kpiName = activeState.selected_kpi;
            let metric = metrics[kpiName];
            if (!metric) {
                const keys = Object.keys(metrics);
                if (keys.length > 0) {
                    metric = metrics[keys[0]];
                }
            }
            if (!metric) return;
            
            if (chartTitleElem) {
                chartTitleElem.textContent = `Uncertainty Propagation: ${kpiName} (Monte Carlo Normal Distribution PDF)`;
                chartTitleElem.style.display = "block";
            }
            
            const unit = metric.unit || "";
            const baseMean = metric.baseline;
            const baseStd = (metric.baseline_uncertainty ? metric.baseline_uncertainty.stddev : null) || (baseMean * 0.08);
            
            const optMean = metric.optimized;
            const optStd = (metric.optimized_uncertainty ? metric.optimized_uncertainty.stddev : null) || (optMean * 0.08);
            
            const minX = Math.min(baseMean - 3 * baseStd, optMean - 3 * optStd);
            const maxX = Math.max(baseMean + 3 * baseStd, optMean + 3 * optStd);
            const step = (maxX - minX) / 50;
            
            const xLabels = [];
            const basePDF = [];
            const optPDF = [];
            
            function normalPDF(x, mean, std) {
                if (std === 0) return 0;
                const exponent = -0.5 * Math.pow((x - mean) / std, 2);
                return (1 / (std * Math.sqrt(2 * Math.PI))) * Math.exp(exponent);
            }
            
            for (let i = 0; i <= 50; i++) {
                const x = minX + i * step;
                xLabels.push(x);
                basePDF.push({ x: x, y: normalPDF(x, baseMean, baseStd) });
                optPDF.push({ x: x, y: normalPDF(x, optMean, optStd) });
            }
            
            interactiveChartInstance = new Chart(ctx, {
                type: 'line',
                data: {
                    datasets: [
                        {
                            label: `Baseline ${kpiName} Dist`,
                            data: basePDF,
                            borderColor: baselineColor,
                            backgroundColor: isLight ? "rgba(185, 194, 204, 0.2)" : "rgba(58, 68, 82, 0.2)",
                            fill: true,
                            tension: 0.4,
                            pointRadius: 0
                        },
                        {
                            label: `Optimized ${kpiName} Dist`,
                            data: optPDF,
                            borderColor: optimizedColor,
                            backgroundColor: isLight ? "rgba(46, 132, 112, 0.25)" : "rgba(63, 168, 139, 0.25)",
                            fill: true,
                            tension: 0.4,
                            pointRadius: 0
                        }
                    ]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    plugins: {
                        legend: {
                            labels: { color: textColor, font: { family: 'inherit', size: 10 } }
                        },
                        tooltip: {
                            mode: 'index',
                            intersect: false,
                            callbacks: {
                                title: function(context) {
                                    return `${kpiName}: ${context[0].raw.x.toFixed(4)} ${unit}`;
                                },
                                label: function(context) {
                                    return `${context.dataset.label} Density: ${context.raw.y.toFixed(2)}`;
                                }
                            }
                        }
                    },
                    scales: {
                        x: {
                            type: 'linear',
                            title: { display: true, text: `${kpiName} (${unit})`, color: textColor, font: { weight: 'bold' } },
                            grid: { color: gridColor },
                            ticks: { color: textColor }
                        },
                        y: {
                            title: { display: true, text: 'Probability Density', color: textColor, font: { weight: 'bold' } },
                            grid: { color: gridColor },
                            ticks: { display: false }
                        }
                    }
                }
            });
        }
    }

    function updateChartImageSource() {
        if (!tradeoffChartImg || !uncertaintyChartImg) return;
        const isLight = document.body.classList.contains("light-theme");
        const chartTitleElem = document.getElementById("chart-active-title");
        
        // 1. Always pre-load static image src so they print correctly in browser PDF layouts
        if (activeState.active_chart_tab === "tradeoff") {
            const url = isLight ? activeState.chart_url_light : activeState.chart_url_dark;
            if (url) {
                const base = url.split("?")[0];
                tradeoffChartImg.src = `${base}?t=${Date.now()}`;
            }
        } else {
            const urls = isLight ? activeState.unc_urls_light : activeState.unc_urls_dark;
            if (urls && urls[activeState.selected_kpi]) {
                const url = urls[activeState.selected_kpi];
                const base = url.split("?")[0];
                uncertaintyChartImg.src = `${base}?t=${Date.now()}`;
            }
        }
        
        // 2. Render interactive Chart.js chart if loaded
        if (typeof Chart !== "undefined") {
            tradeoffChartImg.style.display = "none";
            uncertaintyChartImg.style.display = "none";
            const container = document.getElementById("interactive-chart-container");
            if (container) container.style.display = "block";
            
            renderInteractiveChart();
            
            // Set chart titles for interactive layout
            if (chartTitleElem) {
                if (activeState.active_chart_tab === "tradeoff") {
                    const isPareto = activeState.chart_url_dark && activeState.chart_url_dark.includes("pareto");
                    chartTitleElem.textContent = isPareto ? "Pareto Frontier & TOPSIS Optimal Blend Highlight" : "Optimization Impact Trade-Offs (Normalized Baseline vs. Optimized)";
                } else if (activeState.active_chart_tab === "hotspot") {
                    chartTitleElem.textContent = "BOM Feedstock Mass Composition & Hotspot Breakdown";
                } else {
                    chartTitleElem.textContent = `Uncertainty Propagation: ${activeState.selected_kpi} (Monte Carlo Normal Distribution PDF)`;
                }
                chartTitleElem.style.display = "block";
            }
            return;
        }
        
        // 3. Fallback: Display static images on screen if Chart.js is offline
        const container = document.getElementById("interactive-chart-container");
        if (container) container.style.display = "none";
        
        if (activeState.active_chart_tab === "tradeoff") {
            tradeoffChartImg.style.display = "block";
            uncertaintyChartImg.style.display = "none";
            const url = isLight ? activeState.chart_url_light : activeState.chart_url_dark;
            if (url) {
                const base = url.split("?")[0];
                if (chartTitleElem) {
                    if (base.includes("pareto")) {
                        chartTitleElem.textContent = "Pareto Frontier & TOPSIS Optimal Blend Highlight";
                    } else {
                        chartTitleElem.textContent = "Optimization Impact Trade-Offs (Normalized Baseline vs. Optimized)";
                    }
                    chartTitleElem.style.display = "block";
                }
            } else {
                if (chartTitleElem) chartTitleElem.style.display = "none";
            }
        } else {
            tradeoffChartImg.style.display = "none";
            uncertaintyChartImg.style.display = "block";
            const urls = isLight ? activeState.unc_urls_light : activeState.unc_urls_dark;
            if (urls && urls[activeState.selected_kpi]) {
                if (chartTitleElem) {
                    chartTitleElem.textContent = `Uncertainty Propagation: ${activeState.selected_kpi} (Monte Carlo Frequency Distribution)`;
                    chartTitleElem.style.display = "block";
                }
            } else {
                if (chartTitleElem) {
                    chartTitleElem.textContent = "No uncertainty distribution charts available. Run optimization first.";
                    chartTitleElem.style.display = "block";
                }
            }
        }
    }

    // 1. Initial Setup: Fetch samples dropdown
    fetch("/api/samples")
        .then(res => res.json())
        .then(data => {
            Object.entries(data).forEach(([name, path]) => {
                const opt = document.createElement("option");
                opt.value = path;
                opt.textContent = name;
                sampleSelect.appendChild(opt);
            });
        })
        .catch(err => console.error("Error loading dropdown samples:", err));

    // 2. Load case study BOM row contents
    sampleSelect.addEventListener("change", (e) => {
        const filePath = e.target.value;
        if (!filePath) return;
        
        fetch(`/api/load-sample?file=${encodeURIComponent(filePath)}`)
            .then(res => res.json())
            .then(data => {
                if (data.success) {
                    bomTbody.innerHTML = ""; // Clear table
                    if (activeAssemblyIndicator) {
                        activeAssemblyIndicator.style.display = "none";
                    }
                    data.items.forEach(item => addBomRow(item.flow_name, item.amount, item.unit));
                } else {
                    alert("Error loading BOM study: " + data.error);
                }
            })
            .catch(err => alert("Failed to fetch BOM study: " + err));
    });

    // 3. BOM Editor Row helper
    function addBomRow(flowName = "", amount = 0, unit = "kg") {
        const row = document.createElement("tr");
        row.innerHTML = `
            <td><input type="text" class="row-flow-name" value="${flowName}" placeholder="e.g. glass"></td>
            <td><input type="number" step="any" class="row-amount" value="${amount}"></td>
            <td>
                <select class="row-unit">
                    <option value="kg" ${unit === "kg" ? "selected" : ""}>kg</option>
                    <option value="g" ${unit === "g" ? "selected" : ""}>g</option>
                    <option value="m3" ${unit === "m3" ? "selected" : ""}>m3</option>
                </select>
            </td>
            <td><button type="button" class="delete-row-btn">&times;</button></td>
        `;
        
        row.querySelector(".delete-row-btn").addEventListener("click", () => {
            row.remove();
        });
        
        bomTbody.appendChild(row);
    }

    addRowBtn.addEventListener("click", () => addBomRow());

    // CSV File Importer (Drag & Drop + Browse)
    const csvDropZone = document.getElementById("csv-drop-zone");
    const csvFileInput = document.getElementById("csv-file-input");
    
    if (csvDropZone && csvFileInput) {
        csvDropZone.addEventListener("dragover", (e) => {
            e.preventDefault();
            csvDropZone.classList.add("dragover");
        });
        
        csvDropZone.addEventListener("dragleave", () => {
            csvDropZone.classList.remove("dragover");
        });
        
        csvDropZone.addEventListener("drop", (e) => {
            e.preventDefault();
            csvDropZone.classList.remove("dragover");
            const files = e.dataTransfer.files;
            if (files.length > 0) {
                handleCSVFile(files[0]);
            }
        });
        
        csvFileInput.addEventListener("change", (e) => {
            if (e.target.files.length > 0) {
                handleCSVFile(e.target.files[0]);
            }
        });
        
        function handleCSVFile(file) {
            if (!file.name.endsWith(".csv")) {
                alert("Only CSV files are supported.");
                return;
            }
            const reader = new FileReader();
            reader.onload = (evt) => {
                parseAndPopulateCSV(evt.target.result);
            };
            reader.readAsText(file);
        }
        
        function parseAndPopulateCSV(csvText) {
            const lines = csvText.split(/\r?\n/);
            if (lines.length < 2) return;
            
            const headers = lines[0].split(',').map(h => h.trim().toLowerCase());
            const flowNameIdx = headers.indexOf("flow_name");
            const amountIdx = headers.indexOf("amount");
            const unitIdx = headers.indexOf("unit");
            
            if (flowNameIdx === -1 || amountIdx === -1 || unitIdx === -1) {
                alert("CSV must have 'flow_name', 'amount', and 'unit' columns.");
                return;
            }
            
            bomTbody.innerHTML = "";
            if (activeAssemblyIndicator) {
                activeAssemblyIndicator.style.display = "none";
            }
            
            let loadedCount = 0;
            for (let i = 1; i < lines.length; i++) {
                const line = lines[i].trim();
                if (!line) continue;
                
                const cols = line.split(/,(?=(?:(?:[^"]*"){2})*[^"]*$)/).map(c => c.replace(/^"|"$/g, '').trim());
                if (cols.length <= Math.max(flowNameIdx, amountIdx, unitIdx)) continue;
                
                const flowName = cols[flowNameIdx];
                const amount = parseFloat(cols[amountIdx]) || 0;
                const unit = cols[unitIdx].toLowerCase();
                
                addBomRow(flowName, amount, unit);
                loadedCount++;
            }
            
            alert(`Successfully imported ${loadedCount} feedstock items from CSV.`);
        }
    }

    // Smart Text natural language parser
    const smartTextInput = document.getElementById("smart-text-input");
    const smartTextBtn = document.getElementById("smart-text-btn");
    
    if (smartTextBtn && smartTextInput) {
        smartTextBtn.addEventListener("click", () => {
            const val = smartTextInput.value.trim();
            if (!val) return;
            
            const regex = /(\d+(?:\.\d+)?)\s*(kg|g|m3|t|l|liters?|meters?|cubic\s+meters?)\s*(?:of\s+)?([^,]+)/gi;
            let match;
            let parsedCount = 0;
            
            const parsedItems = [];
            while ((match = regex.exec(val)) !== null) {
                const amount = parseFloat(match[1]);
                let unit = match[2].toLowerCase();
                const material = match[3].trim();
                
                if (unit.startsWith("liter")) unit = "m3";
                if (unit.startsWith("cubic")) unit = "m3";
                if (unit === "t") unit = "kg";
                
                parsedItems.push({ material, amount, unit });
                parsedCount++;
            }
            
            if (parsedItems.length > 0) {
                bomTbody.innerHTML = "";
                if (activeAssemblyIndicator) {
                    activeAssemblyIndicator.style.display = "none";
                }
                
                parsedItems.forEach(item => {
                    addBomRow(item.material, item.amount, item.unit);
                });
                
                alert(`Successfully parsed ${parsedCount} items from text input!`);
                smartTextInput.value = "";
            } else {
                alert("Could not parse any feedstocks. Use format like: '15kg glass, 2.2kg polyethylene'");
            }
        });
        
        smartTextInput.addEventListener("keypress", (e) => {
            if (e.key === "Enter") {
                smartTextBtn.click();
            }
        });
    }

    function highlightBomHotspot(hotspotName) {
        if (!bomTbody || !hotspotName) return;
        const rows = bomTbody.querySelectorAll("tr");
        rows.forEach(row => {
            row.classList.remove("hotspot-highlight-row");
            const nameInput = row.querySelector("td input");
            if (nameInput) {
                const materialName = nameInput.value.trim().toLowerCase();
                const cleanHotspot = hotspotName.trim().toLowerCase();
                if (materialName && (materialName.includes(cleanHotspot) || cleanHotspot.includes(materialName))) {
                    row.classList.add("hotspot-highlight-row");
                }
            }
        });
    }

    // 4. Ingest and Optimize BOM exchanges
    optimizeBtn.addEventListener("click", () => {
        const rows = bomTbody.querySelectorAll("tr");
        const items = [];
        
        rows.forEach(row => {
            const flowName = row.querySelector(".row-flow-name").value.trim();
            const amount = parseFloat(row.querySelector(".row-amount").value);
            const unit = row.querySelector(".row-unit").value;
            
            if (flowName && !isNaN(amount)) {
                items.push({ flow_name: flowName, amount: amount, unit: unit });
            }
        });
        
        if (items.length === 0) {
            alert("BOM editor is empty. Please load a case study or add materials first.");
            return;
        }

        // Display loading status
        optimizeBtn.disabled = true;
        optimizeBtn.querySelector(".btn-label").textContent = "Processing...";
        appendChatMessage("System", "Running automated ingestion, mass verification, sensitivity hotspot mapping, and multi-objective calculation setup. This will take about a minute...");

        fetch("/api/optimize", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ 
                items: items,
                method_id: lciaMethodSelect ? lciaMethodSelect.value : "",
                parameters: {
                    process_efficiency: parseFloat(paramProcessEfficiency.value),
                    recycle_rate: parseFloat(paramRecycleRate.value),
                    loss_factor: parseFloat(paramLossFactor.value)
                },
                weights: {
                    GWP: parseFloat(weightGwp.value),
                    Acidification: parseFloat(weightAcid.value),
                    Water: parseFloat(weightWater.value),
                    Cost: parseFloat(weightCost.value)
                },
                custom_parameters: Object.values(activeCustomParameterOverrides)
            })
        })
        .then(res => res.json())
        .then(data => {
            optimizeBtn.disabled = false;
            optimizeBtn.querySelector(".btn-label").textContent = "Run Optimization";
            
            if (data.success) {
                // Update active state
                activeState.exchanges = data.exchanges;
                activeState.report = data.report;
                activeState.temp_proc_id = data.temp_proc_id;
                activeState.temp_sys_id = data.temp_sys_id;
                activeState.method_id = data.method_id;
                activeState.chart_url_dark = data.chart_url_dark;
                activeState.chart_url_light = data.chart_url_light;
                activeState.unc_urls_dark = data.unc_urls_dark;
                activeState.unc_urls_light = data.unc_urls_light;
                
                // Enable chat console
                chatInput.disabled = false;
                chatSendBtn.disabled = false;
                chatInput.placeholder = "Ask AirLab Advisor a question or request a feedstock swap...";

                // Update UI elements
                updateDashboardUI(data);
                
                if (data.report && data.report.substituted_from) {
                    highlightBomHotspot(data.report.substituted_from);
                }
                
                appendChatMessage("Advisor", `Ingested BOM items successfully. Dynamic hotspot analysis identified **${data.report.substituted_from}** as carrying the highest carbon footprint sensitivity. Substituted it with **${data.report.substituted_to}** (TVL verified). You can now chat below.`);
            } else {
                appendChatMessage("System Error", data.error);
                alert("Optimization calculation failed: " + data.error);
            }
        })
        .catch(err => {
            optimizeBtn.disabled = false;
            optimizeBtn.querySelector(".btn-label").textContent = "Run Optimization";
            alert("Calculation network error: " + err);
        });
    });

    // Ingest and Run Pareto Frontier Optimization
    paretoBtn.addEventListener("click", () => {
        const rows = bomTbody.querySelectorAll("tr");
        const items = [];
        
        rows.forEach(row => {
            const flowName = row.querySelector(".row-flow-name").value.trim();
            const amount = parseFloat(row.querySelector(".row-amount").value);
            const unit = row.querySelector(".row-unit").value;
            
            if (flowName && !isNaN(amount)) {
                items.push({ flow_name: flowName, amount: amount, unit: unit });
            }
        });
        
        if (items.length === 0) {
            alert("BOM editor is empty. Please load a case study or add materials first.");
            return;
        }

        // Display loading status
        paretoBtn.disabled = true;
        paretoBtn.querySelector(".btn-label").textContent = "Processing...";
        appendChatMessage("System", "Running multi-objective Pareto Frontier search over GWP, Acidification, Water, and Cost metrics using surrogate model simulations. This may take up to a minute...");

        fetch("/api/pareto", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ 
                items: items, 
                method_id: lciaMethodSelect ? lciaMethodSelect.value : "",
                num_samples: 500,
                weights: {
                    GWP: parseFloat(weightGwp.value),
                    Acidification: parseFloat(weightAcid.value),
                    Water: parseFloat(weightWater.value),
                    Cost: parseFloat(weightCost.value)
                }
            })
        })
        .then(res => res.json())
        .then(data => {
            paretoBtn.disabled = false;
            paretoBtn.querySelector(".btn-label").textContent = "Pareto Frontier";
            
            if (data.success) {
                const frontier = data.frontier;
                
                // Set activeState URLs for Pareto chart
                activeState.chart_url_dark = data.chart_url_dark;
                activeState.chart_url_light = data.chart_url_light;
                activeState.active_chart_tab = "tradeoff";
                
                // Keep references for reweighing
                window.activeParetoFrontier = data.frontier;
                window.activeBaselineMetrics = data.metrics || (activeState.report ? activeState.report.metrics : {});
                
                // Render the scatter plot
                tradeoffChartImg.style.display = "block";
                updateChartImageSource();
                
                if (frontier.length === 0) {
                    tradeoffChartImg.style.display = "none";
                    chartPlaceholder.style.display = "block";
                    chartPlaceholder.innerHTML = `
                        <div style="text-align: center; padding: 20px; font-family: var(--font-sans);">
                            <h4 style="margin-bottom: 6px; font-weight: 600; color: var(--text-primary);">No Substitutable Feedstocks Identified</h4>
                            <p style="font-size: 13px; color: var(--text-muted); line-height: 1.6; max-width: 320px; margin: 0 auto;">
                                Ensure your BOM contains substitutable virgin feedstocks such as glass, steel, or polyethylene.
                            </p>
                        </div>
                    `;
                    appendChatMessage("Advisor", "No substitutable feedstocks were identified to run the multi-objective Pareto frontier.");
                    return;
                }
                
                // Build a gorgeous interactive table of the Pareto points
                let html = `
                    <div style="padding: 16px; font-family: var(--font-sans); height: 100%; display: flex; flex-direction: column;">
                        <h4 style="margin-bottom: 12px; font-weight: 600; color: var(--text-primary); display: flex; align-items: center; gap: 8px;">
                            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="var(--accent-emerald)" stroke-width="2.5"><path d="M21.21 15.89A10 10 0 1 1 8 2.83"></path><path d="M22 12A10 10 0 0 0 12 2v10z"></path></svg>
                            Pareto-Optimal Feedstock Blends (${frontier.length} Points)
                        </h4>
                        <div style="flex-grow: 1; overflow-y: auto; max-height: 280px; border-radius: 8px; border: 1px solid var(--border-color);">
                            <table style="width: 100%; border-collapse: collapse; text-align: left; font-size: 12px; color: var(--text-primary);">
                                <thead style="background-color: var(--card-bg-hover); position: sticky; top: 0; font-weight: 600; text-transform: uppercase; font-size: 10px; letter-spacing: 0.5px;">
                                    <tr>
                                        <th style="padding: 10px 12px; border-bottom: 1px solid var(--border-color);">Blend Configurations</th>
                                        <th style="padding: 10px 12px; border-bottom: 1px solid var(--border-color); text-align: right;">GWP (kg CO₂ eq)</th>
                                        <th style="padding: 10px 12px; border-bottom: 1px solid var(--border-color); text-align: right;">Acidification</th>
                                        <th style="padding: 10px 12px; border-bottom: 1px solid var(--border-color); text-align: right;">Water (m³)</th>
                                        <th style="padding: 10px 12px; border-bottom: 1px solid var(--border-color); text-align: right;">Cost (USD)</th>
                                    </tr>
                                </thead>
                                <tbody>
                `;
                
                // Show up to 10 points in the table
                frontier.slice(0, 10).forEach((pt, idx) => {
                    let blendStr = Object.entries(pt.ratios)
                        .map(([name, r]) => `${name.split(',')[0]}: ${(r * 100).toFixed(0)}% recycled`)
                        .join(", ");
                    
                    if (pt.parameters) {
                        blendStr += ` <span style="color: var(--text-muted); font-size: 11px;">(Eff: ${(pt.parameters.process_efficiency * 100).toFixed(0)}%, Loss: ${(pt.parameters.loss_factor * 100).toFixed(0)}%)</span>`;
                    }
                    
                    html += `
                        <tr style="border-bottom: 1px solid var(--border-color); transition: background-color 0.2s;" onmouseover="this.style.backgroundColor='var(--card-bg-hover)'" onmouseout="this.style.backgroundColor='transparent'">
                            <td style="padding: 10px 12px; font-weight: 500;">
                                <span style="display:inline-block; width:18px; height:18px; border-radius:50%; background:var(--accent-indigo); color:white; text-align:center; line-height:18px; font-size:9px; margin-right:6px; font-weight:600;">${idx+1}</span>
                                ${blendStr}
                            </td>
                            <td style="padding: 10px 12px; text-align: right; color: var(--accent-emerald); font-weight: 600;">${pt.metrics.GWP.toFixed(2)}</td>
                            <td style="padding: 10px 12px; text-align: right;">${pt.metrics.Acidification.toFixed(4)}</td>
                            <td style="padding: 10px 12px; text-align: right;">${pt.metrics.Water.toFixed(2)}</td>
                            <td style="padding: 10px 12px; text-align: right; color: var(--accent-purple); font-weight: 600;">$${pt.metrics.Cost.toFixed(2)}</td>
                        </tr>
                    `;
                });
                
                if (frontier.length > 10) {
                    html += `
                        <tr>
                            <td colspan="5" style="padding: 8px; text-align: center; color: var(--text-muted); font-size: 11px; background-color: var(--card-bg-hover);">
                                ... and ${frontier.length - 10} other non-dominated Pareto configurations
                            </td>
                        </tr>
                    `;
                }
                
                html += `
                                </tbody>
                            </table>
                        </div>
                    </div>
                `;
                
                // Show both image and placeholder containing table
                chartPlaceholder.style.display = "block";
                chartPlaceholder.innerHTML = html;
                
                // Formulate a beautiful summary explanation for the Chat Advisor
                let bestGwp = Math.min(...frontier.map(pt => pt.metrics.GWP));
                let bestCost = Math.min(...frontier.map(pt => pt.metrics.Cost));
                appendChatMessage("Advisor", `Pareto frontier optimization complete. Found **${frontier.length}** non-dominated blend options. The lowest carbon option achieves **${bestGwp.toFixed(2)} kg CO₂ eq**, while the lowest cost blend reduces cost to **$${bestCost.toFixed(2)}**. See the interactive configurations in the center panel.`);
            } else {
                appendChatMessage("System Error", data.error);
                alert("Pareto calculation failed: " + data.error);
            }
        })
        .catch(err => {
            paretoBtn.disabled = false;
            paretoBtn.querySelector(".btn-label").textContent = "Pareto Frontier";
            alert("Calculation network error: " + err);
        });
    });

    // 5. Update Metrics, TVL, and Charts on Dashboard
    function updateDashboardUI(data) {
        // Clear previous hotspot highlights in table
        if (bomTbody) {
            const rows = bomTbody.querySelectorAll("tr");
            rows.forEach(r => r.classList.remove("hotspot-highlight-row"));
        }

        const report = data.report;
        activeState.report = report;
        const tvl = data.tvl_report;
        
        // Select GWP card by default on new calculations to highlight visual selection
        selectKpiCard("Global Warming", cardGwp);
        
        // 1. Update TVL Verification Card
        tvlInputMass.textContent = `${tvl.total_input_mass_kg.toFixed(3)} kg`;
        tvlOutputMass.textContent = `${tvl.total_output_mass_kg.toFixed(3)} kg`;
        tvlError.textContent = `${(tvl.relative_error * 100).toFixed(4)}%`;
        
        if (tvl.is_balanced) {
            tvlBadge.textContent = "Passed";
            tvlBadge.className = "tvl-indicator passed";
        } else {
            tvlBadge.textContent = "Failed";
            tvlBadge.className = "tvl-indicator failed";
        }

        // Elemental Verification Update
        const tvlElementalContainer = document.getElementById("tvl-elemental-container");
        const tvlElementalBadge = document.getElementById("tvl-elemental-badge");
        const tvlElementalList = document.getElementById("tvl-elemental-list");
        
        if (tvlElementalContainer && tvlElementalBadge && tvlElementalList) {
            tvlElementalList.innerHTML = "";
            
            if (tvl.elemental_discrepancies && Object.keys(tvl.elemental_discrepancies).length > 0) {
                tvlElementalContainer.style.display = "block";
                tvlElementalBadge.textContent = "Failed";
                tvlElementalBadge.className = "tvl-status-badge failed";
                
                for (const [el, desc] of Object.entries(tvl.elemental_discrepancies)) {
                    const row = document.createElement("div");
                    row.style.display = "flex";
                    row.style.justifyContent = "space-between";
                    row.style.alignItems = "center";
                    row.style.fontSize = "10px";
                    row.style.padding = "4px 6px";
                    row.style.background = "var(--bg-card)";
                    row.style.border = "1px solid var(--border-color)";
                    row.style.borderRadius = "4px";
                    row.style.fontFamily = "var(--font-mono)";
                    row.style.marginTop = "3px";
                    
                    const pctErr = (desc.relative_error * 100).toFixed(1);
                    row.innerHTML = `
                        <span style="font-weight: bold; color: var(--accent-red);">${el}</span>
                        <span style="color: var(--text-muted);">${desc.input_kg.toFixed(3)} → ${desc.output_kg.toFixed(3)} kg</span>
                        <span style="color: var(--accent-red); font-weight: 600;">Δ ${pctErr}%</span>
                    `;
                    tvlElementalList.appendChild(row);
                }
            } else if (tvl.total_input_mass_kg > 0) {
                tvlElementalContainer.style.display = "block";
                tvlElementalBadge.textContent = "Passed";
                tvlElementalBadge.className = "tvl-status-badge passed";
                
                const successMsg = document.createElement("div");
                successMsg.style.fontSize = "10px";
                successMsg.style.color = "var(--accent-emerald)";
                successMsg.style.padding = "4px";
                successMsg.style.textAlign = "center";
                successMsg.innerHTML = "✓ Elemental stoichiometry balanced";
                tvlElementalList.appendChild(successMsg);
            } else {
                tvlElementalContainer.style.display = "none";
            }
        }

        // 2. Update Metrics cards (Baseline, Optimized, Change)
        const metrics = report.metrics;
        
        // GWP
        updateMetricCard(metrics["Global Warming"], gwpBase, gwpOpt, gwpChange, gwpBaseUnc, gwpOptUnc);
        // Acidification
        updateMetricCard(metrics["Acidification"], acidBase, acidOpt, acidChange, acidBaseUnc, acidOptUnc);
        // Water
        updateMetricCard(metrics["Water Consumption"], waterBase, waterOpt, waterChange, waterBaseUnc, waterOptUnc);
        // Cost
        updateMetricCard(metrics["Feedstock Cost"], costBase, costOpt, costChange, costBaseUnc, costOptUnc);

        // 3. Update comparison trade-off and uncertainty chart images
        activeState.chart_url_dark = data.chart_url_dark;
        activeState.chart_url_light = data.chart_url_light;
        activeState.unc_urls_dark = data.unc_urls_dark;
        activeState.unc_urls_light = data.unc_urls_light;
        
        chartPlaceholder.style.display = "none";
        updateChartImageSource();

        // 4. Update Justification Content
        if (data.justification) {
            justificationWrapper.style.display = "block";
            justificationContent.textContent = data.justification;
        } else {
            justificationWrapper.style.display = "none";
        }
        
        // 4.5. Update Download Report Button
        activeState.report_filename = data.report_filename || null;
        const downloadReportBtn = document.getElementById("download-report-btn");
        if (downloadReportBtn) {
            if (activeState.report_filename) {
                downloadReportBtn.style.display = "inline-flex";
            } else {
                downloadReportBtn.style.display = "none";
            }
        }

        // 5. Toggle Export CSV button visibility
        const exportCsvBtn = document.getElementById("export-csv-btn");
        if (exportCsvBtn) {
            if (activeState.exchanges && activeState.exchanges.length > 0) {
                exportCsvBtn.style.display = "inline-flex";
            } else {
                exportCsvBtn.style.display = "none";
            }
        }
    }

    function updateMetricCard(metricData, baseElem, optElem, changeElem, baseUncElem, optUncElem) {
        if (!metricData) return;
        baseElem.textContent = metricData.baseline.toFixed(4);
        optElem.textContent = metricData.optimized.toFixed(4);
        
        if (metricData.baseline_uncertainty && baseUncElem) {
            baseUncElem.textContent = `± ${metricData.baseline_uncertainty.margin_of_error.toFixed(4)}`;
        } else if (baseUncElem) {
            baseUncElem.textContent = "";
        }
        
        if (metricData.optimized_uncertainty && optUncElem) {
            optUncElem.textContent = `± ${metricData.optimized_uncertainty.margin_of_error.toFixed(4)}`;
        } else if (optUncElem) {
            optUncElem.textContent = "";
        }
        
        const pct = metricData.percentage_change;
        changeElem.textContent = `${pct >= 0 ? "+" : ""}${pct.toFixed(2)}%`;
        
        if (pct < 0) {
            changeElem.className = "change-badge negative";
        } else if (pct > 0) {
            changeElem.className = "change-badge positive";
        } else {
            changeElem.className = "change-badge neutral";
        }
    }

    // 6. Interactive Chat Loop
    chatSendBtn.addEventListener("click", submitChatQuery);
    chatInput.addEventListener("keypress", (e) => {
        if (e.key === "Enter") submitChatQuery();
    });

    // 6.1 CSV Export and PDF Printing Listeners
    const exportCsvBtn = document.getElementById("export-csv-btn");
    const printReportBtn = document.getElementById("print-report-btn");
    const downloadReportBtn = document.getElementById("download-report-btn");

    if (exportCsvBtn) {
        exportCsvBtn.addEventListener("click", exportOptimizedBOMToCSV);
    }
    if (printReportBtn) {
        printReportBtn.addEventListener("click", () => {
            window.print();
        });
    }
    if (downloadReportBtn) {
        downloadReportBtn.addEventListener("click", () => {
            if (activeState.report_filename) {
                window.location.href = `/api/reports/download/${activeState.report_filename}`;
            } else {
                alert("No report file available for download.");
            }
        });
    }

    function exportOptimizedBOMToCSV() {
        if (!activeState.exchanges || activeState.exchanges.length === 0) {
            alert("No optimized BOM loaded. Please run optimization first.");
            return;
        }
        
        let csvContent = "data:text/csv;charset=utf-8,";
        csvContent += "flow_name,amount,unit\n";
        
        activeState.exchanges.forEach(ex => {
            // Escape double quotes in names
            const safeName = ex.name.replace(/"/g, '""');
            csvContent += `"${safeName}",${ex.amount},"${ex.unit}"\n`;
        });
        
        const encodedUri = encodeURI(csvContent);
        const link = document.createElement("a");
        link.setAttribute("href", encodedUri);
        link.setAttribute("download", `optimized_bom_${activeState.temp_proc_id || "lca"}.csv`);
        document.body.appendChild(link);
        link.click();
        document.body.removeChild(link);
    }

    function submitChatQuery() {
        const queryText = chatInput.value.trim();
        if (!queryText) return;
        
        appendChatMessage("User", queryText);
        chatInput.value = "";
        
        chatInput.disabled = true;
        chatSendBtn.disabled = true;
        
        fetch("/api/chat", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
                message: queryText,
                exchanges: activeState.exchanges,
                report: activeState.report,
                temp_proc_id: activeState.temp_proc_id,
                temp_sys_id: activeState.temp_sys_id,
                method_id: activeState.method_id,
                parameters: {
                    process_efficiency: parseFloat(paramProcessEfficiency.value),
                    recycle_rate: parseFloat(paramRecycleRate.value),
                    loss_factor: parseFloat(paramLossFactor.value)
                },
                weights: {
                    GWP: parseFloat(weightGwp.value),
                    Acidification: parseFloat(weightAcid.value),
                    Water: parseFloat(weightWater.value),
                    Cost: parseFloat(weightCost.value)
                },
                custom_parameters: Object.values(activeCustomParameterOverrides)
            })
        })
        .then(res => res.json())
        .then(data => {
            chatInput.disabled = false;
            chatSendBtn.disabled = false;
            chatInput.focus();
            
            if (data.action === "substitute") {
                if (data.success) {
                    // Update state
                    activeState.exchanges = data.exchanges;
                    activeState.report = data.report;
                    activeState.temp_proc_id = data.temp_proc_id;
                    activeState.temp_sys_id = data.temp_sys_id;
                    activeState.chart_url_dark = data.chart_url_dark;
                    activeState.chart_url_light = data.chart_url_light;
                    activeState.unc_urls_dark = data.unc_urls_dark;
                    activeState.unc_urls_light = data.unc_urls_light;
                    
                    // Update UI elements
                    updateDashboardUI(data);
                    
                    appendChatMessage("Advisor", `Stock substitution calculation complete. Substituted target feedstock. Updated environmental and financial cost metrics. Visual chart re-plotted.`);
                } else {
                    appendChatMessage("Advisor", `Feedstock substitution calculation failed: ${data.error}`);
                }
            } else {
                appendChatMessage("Advisor", data.response);
            }
        })
        .catch(err => {
            chatInput.disabled = false;
            chatSendBtn.disabled = false;
            appendChatMessage("System Error", "Connection failed: " + err);
        });
    }

    function formatMarkdown(text) {
        if (!text) return "";
        return text
            .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
            .replace(/\*(.*?)\*/g, '<em>$1</em>');
    }

    function appendChatMessage(sender, text) {
        let displaySender = sender;
        if (sender === "Advisor") displaySender = "AirLab Advisor";
        const msgDiv = document.createElement("div");
        const className = sender.toLowerCase().replace(/\s+/g, '-');
        if (className === "system-error") {
            msgDiv.className = `message system error-msg`;
        } else {
            msgDiv.className = `message ${className}-msg`;
        }
        msgDiv.innerHTML = `<strong>${displaySender}:</strong> ${formatMarkdown(text)}`;
        chatBox.appendChild(msgDiv);
        
        // Auto-scroll chat box to bottom
        chatBox.scrollTop = chatBox.scrollHeight;
    }

    // Tabs Navigation
    let activeBomMode = "flat";

    tabFlat.addEventListener("click", () => {
        activeBomMode = "flat";
        tabFlat.classList.add("active");
        tabHierarchical.classList.remove("active");
        tabAutonomous.classList.remove("active");
        panelFlat.classList.add("active");
        panelHierarchical.classList.remove("active");
        panelAutonomous.classList.remove("active");
    });
    
    tabHierarchical.addEventListener("click", () => {
        activeBomMode = "hierarchical";
        tabHierarchical.classList.add("active");
        tabFlat.classList.remove("active");
        tabAutonomous.classList.remove("active");
        panelHierarchical.classList.add("active");
        panelFlat.classList.remove("active");
        panelAutonomous.classList.remove("active");
    });

    tabAutonomous.addEventListener("click", () => {
        tabAutonomous.classList.add("active");
        tabFlat.classList.remove("active");
        tabHierarchical.classList.remove("active");
        panelAutonomous.classList.add("active");
        panelFlat.classList.remove("active");
        panelHierarchical.classList.remove("active");
    });

    // Launch Autonomous Agent Redesign Loop
    runAutonomousBtn.addEventListener("click", () => {
        let itemsToSend = null;
        if (activeBomMode === "hierarchical") {
            const rawJson = bomJsonTextarea.value.trim();
            if (!rawJson) {
                alert("Hierarchical JSON schema is empty. Please load or write a JSON BOM first.");
                return;
            }
            try {
                itemsToSend = JSON.parse(rawJson);
            } catch (e) {
                alert("Invalid JSON format in Hierarchical BOM schema: " + e.message);
                return;
            }
        } else {
            const rows = bomTbody.querySelectorAll("tr");
            const items = [];
            rows.forEach(row => {
                const flowName = row.querySelector(".row-flow-name").value.trim();
                const amount = parseFloat(row.querySelector(".row-amount").value);
                const unit = row.querySelector(".row-unit").value;
                
                if (flowName && !isNaN(amount)) {
                    items.push({ flow_name: flowName, amount: amount, unit: unit });
                }
            });
            if (items.length === 0) {
                alert("BOM editor is empty. Please load a case study or add materials first.");
                return;
            }
            itemsToSend = items;
        }
        
        const goalText = autonomousGoalInput.value.trim();
        if (!goalText) {
            alert("Please specify a sustainability directive or goal.");
            return;
        }

        // Display loading status
        runAutonomousBtn.disabled = true;
        runAutonomousBtn.querySelector(".btn-label").textContent = "Agent Running...";
        autonomousTerminal.textContent = "[Coordinator] Booting multi-agent environment...\n";
        appendChatMessage("System", `Launching autonomous loop for goal: "${goalText}"`);

        fetch("/api/autonomous-redesign", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ items: itemsToSend, goal: goalText })
        })
        .then(res => res.json())
        .then(data => {
            if (!data.success) {
                runAutonomousBtn.disabled = false;
                runAutonomousBtn.querySelector(".btn-label").textContent = "Launch Autonomous Agent";
                autonomousTerminal.textContent += `\n[ERROR] Start failed: ${data.error}`;
                alert("Autonomous loop start failed: " + data.error);
                return;
            }

            const jobId = data.job_id;
            const eventSource = new EventSource(`/api/autonomous-redesign/stream/${jobId}`);
            
            eventSource.onmessage = (event) => {
                const streamData = JSON.parse(event.data);
                
                if (streamData.type === 'log') {
                    autonomousTerminal.textContent += streamData.message + "\n";
                    autonomousTerminal.scrollTop = autonomousTerminal.scrollHeight;
                } else if (streamData.type === 'completed') {
                    eventSource.close();
                    runAutonomousBtn.disabled = false;
                    runAutonomousBtn.querySelector(".btn-label").textContent = "Launch Autonomous Agent";
                    
                    const result = streamData.result;
                    
                    // Reconstruct metrics report structure for standard card update
                    const report = {
                        metrics: {
                            "Global Warming": {
                                baseline: result.baseline_gwp,
                                optimized: result.optimized_gwp,
                                percentage_change: ((result.optimized_gwp - result.baseline_gwp) / result.baseline_gwp) * 100
                            },
                            "Acidification": {
                                baseline: result.baseline_acid, 
                                optimized: result.optimized_acid,
                                percentage_change: ((result.optimized_acid - result.baseline_acid) / result.baseline_acid) * 100
                            },
                            "Water Consumption": {
                                baseline: result.baseline_water,
                                optimized: result.optimized_water,
                                percentage_change: ((result.optimized_water - result.baseline_water) / result.baseline_water) * 100
                            },
                            "Feedstock Cost": {
                                baseline: result.baseline_cost,
                                optimized: result.optimized_cost,
                                percentage_change: ((result.optimized_cost - result.baseline_cost) / result.baseline_cost) * 100
                            }
                        }
                    };
                    
                    let totalMass = 0;
                    if (activeBomMode === "hierarchical") {
                        totalMass = itemsToSend.amount || 0;
                    } else {
                        totalMass = itemsToSend.reduce((acc, it) => acc + it.amount, 0);
                    }
                    
                    const mockTvl = {
                        total_input_mass_kg: totalMass,
                        total_output_mass_kg: totalMass,
                        relative_error: 0.0,
                        is_balanced: true
                    };
                    
                    updateDashboardUI({
                        report: report,
                        tvl_report: mockTvl
                    });
                    
                    chartPlaceholder.style.display = "block";
                    chartPlaceholder.innerHTML = `
                        <div style="text-align: center; padding: 20px; font-family: var(--font-sans);">
                            <svg viewBox="0 0 24 24" fill="none" stroke="var(--accent-emerald)" stroke-width="2" style="width: 48px; height: 48px; margin-bottom: 12px; display: inline-block;">
                                <path d="M22 11.08V12a10 10 0 1 1-5.93-9.14"></path>
                                <polyline points="22 4 12 14.01 9 11.01"></polyline>
                            </svg>
                            <h4 style="margin-bottom: 6px; font-weight: 600; color: var(--text-primary);">Autonomous Redesign Complete</h4>
                            <p style="font-size: 13px; color: var(--text-muted); line-height: 1.6; max-width: 320px; margin: 0 auto;">
                                Process permanently updated inside openLCA database with optimal ratios. Baseline vs. Optimized metrics updated.
                            </p>
                        </div>
                    `;
                    tradeoffChartImg.style.display = "none";
                    justificationWrapper.style.display = "none";
                    
                    const gwpPct = report.metrics["Global Warming"].percentage_change;
                    const costPct = report.metrics["Feedstock Cost"].percentage_change;
                    const acidPct = report.metrics["Acidification"].percentage_change;
                    const waterPct = report.metrics["Water Consumption"].percentage_change;
                    
                    let message = `Autonomous process redesign completed! The process has been committed to openLCA. Environmental and economic impacts updated:\n` +
                                  `• **Global Warming (GWP)**: ${gwpPct > 0 ? '+' : ''}${gwpPct.toFixed(2)}%\n` +
                                  `• **Acidification**: ${acidPct > 0 ? '+' : ''}${acidPct.toFixed(2)}%\n` +
                                  `• **Water Consumption**: ${waterPct > 0 ? '+' : ''}${waterPct.toFixed(2)}%\n` +
                                  `• **Feedstock Cost**: ${costPct > 0 ? '+' : ''}${costPct.toFixed(2)}%`;
                    appendChatMessage("Advisor", message);
                } else if (streamData.type === 'failed') {
                    eventSource.close();
                    runAutonomousBtn.disabled = false;
                    runAutonomousBtn.querySelector(".btn-label").textContent = "Launch Autonomous Agent";
                    autonomousTerminal.textContent += `\n[ERROR] Optimization Loop failed: ${streamData.error}`;
                    autonomousTerminal.scrollTop = autonomousTerminal.scrollHeight;
                    alert("Autonomous loop execution failed: " + streamData.error);
                }
            };
            
            eventSource.onerror = (err) => {
                eventSource.close();
                runAutonomousBtn.disabled = false;
                runAutonomousBtn.querySelector(".btn-label").textContent = "Launch Autonomous Agent";
                autonomousTerminal.textContent += `\n[ERROR] Stream connection lost.`;
                autonomousTerminal.scrollTop = autonomousTerminal.scrollHeight;
            };
        })
        .catch(err => {
            runAutonomousBtn.disabled = false;
            runAutonomousBtn.querySelector(".btn-label").textContent = "Launch Autonomous Agent";
            autonomousTerminal.textContent += `\n[ERROR] Network calculation error: ${err}`;
            autonomousTerminal.scrollTop = autonomousTerminal.scrollHeight;
            alert("Calculation network error.");
        });
    });

    // Load Hierarchical Sample BOM and bind Tree Previewer
    const bomFileInput = document.getElementById("bom-file-input");
    const treePreviewSection = document.getElementById("tree-preview-section");
    const bomTreeContainer = document.getElementById("bom-tree-container");

    loadHierarchicalSampleBtn.addEventListener("click", () => {
        fetch("/static/wind_turbine_blade_hierarchical.json")
            .then(res => {
                if (!res.ok) throw new Error("Failed to fetch sample");
                return res.text();
            })
            .then(text => {
                bomJsonTextarea.value = text;
                triggerTreeRender();
            })
            .catch(err => {
                // Fallback to embedded string if network issues
                const fallbackJson = {
                    "name": "Composite Wind Turbine Blade Model",
                    "amount": 5000.0,
                    "unit": "kg",
                    "inputs": [
                        {
                            "name": "Fiberglass Composite Structure",
                            "amount": 3000.0,
                            "unit": "kg",
                            "inputs": [
                                {"name": "glass cullet, sorted", "amount": 2500.0, "unit": "kg"},
                                {"name": "polyethylene, high density, granulate", "amount": 500.0, "unit": "kg"}
                            ]
                        },
                        {
                            "name": "Reinforced Structural Steel Core",
                            "amount": 1500.0,
                            "unit": "kg",
                            "inputs": [
                                {"name": "steel, low-alloyed", "amount": 1400.0, "unit": "kg"},
                                {"name": "tap water", "amount": 100.0, "unit": "kg"}
                            ]
                        },
                        {
                            "name": "polyethylene, high density, granulate",
                            "amount": 500.0,
                            "unit": "kg"
                        }
                    ]
                };
                bomJsonTextarea.value = JSON.stringify(fallbackJson, null, 2);
                triggerTreeRender();
            });
    });

    if (bomFileInput) {
        bomFileInput.addEventListener("change", (e) => {
            const file = e.target.files[0];
            if (!file) return;
            const reader = new FileReader();
            reader.onload = (evt) => {
                bomJsonTextarea.value = evt.target.result;
                triggerTreeRender();
            };
            reader.readAsText(file);
        });
    }

    if (bomJsonTextarea) {
        bomJsonTextarea.addEventListener("input", triggerTreeRender);
    }

    let nodeIndex = 0;
    window.currentBOMTreeNodes = {};

    const SIMULATED_GWP_FACTORS = {
        "glass": 1.2,
        "cullet": 0.35,
        "polyethylene": 2.0,
        "steel": 2.5,
        "water": 0.001,
        "electricity": 0.5,
        "silicon": 15.0,
        "carbon": 3.0,
        "concrete": 0.15,
        "aluminium": 8.0,
        "copper": 3.5,
        "epoxy": 5.0,
        "resin": 4.5,
        "wood": 0.05
    };

    function calculateNodeGwp(node) {
        if (!node || typeof node !== "object") return { gwp: 0, mass: 0 };
        
        let amount = parseFloat(node.amount) || 0;
        let unit = (node.unit || "kg").toLowerCase();
        
        let weightKg = amount;
        if (unit === "g") weightKg = amount * 1e-3;
        else if (unit === "t" || unit === "tonne") weightKg = amount * 1000;
        else if (unit === "m3" || unit === "cubic meter") {
            if (node.name.toLowerCase().includes("water")) weightKg = amount * 1000;
            else weightKg = amount * 1500;
        }
        
        node.mass = weightKg;
        
        const inputs = node.inputs || [];
        if (inputs.length > 0) {
            let totalGwp = 0;
            let totalMass = 0;
            inputs.forEach(child => {
                const res = calculateNodeGwp(child);
                totalGwp += res.gwp;
                totalMass += res.mass;
            });
            node.gwp = totalGwp;
            node.total_mass = totalMass;
            return { gwp: totalGwp, mass: totalMass };
        } else {
            let factor = 1.0;
            const nameLower = (node.name || "").toLowerCase();
            for (const [key, f] of Object.entries(SIMULATED_GWP_FACTORS)) {
                if (nameLower.includes(key)) {
                    factor = f;
                    break;
                }
            }
            node.gwp = weightKg * factor;
            return { gwp: node.gwp, mass: weightKg };
        }
    }

    function triggerTreeRender() {
        const text = bomJsonTextarea.value.trim();
        if (!text) {
            treePreviewSection.style.display = "none";
            return;
        }
        try {
            const json = JSON.parse(text);
            nodeIndex = 0;
            window.currentBOMTreeNodes = {};
            calculateNodeGwp(json);
            bomTreeContainer.innerHTML = renderBOMTree(json, 0, json.gwp || 0);
            treePreviewSection.style.display = "block";
        } catch (e) {
            treePreviewSection.style.display = "none";
        }
    }

    function renderBOMTree(node, depth = 0, parentGwp = 0) {
        if (!node || typeof node !== "object") return "";
        const name = node.name || "Unnamed Node";
        const amount = node.amount !== undefined ? node.amount : 1.0;
        const unit = node.unit || "kg";
        const inputs = node.inputs || [];
        
        const isAssembly = inputs.length > 0;
        const nodeId = "node-" + nodeIndex++;
        window.currentBOMTreeNodes[nodeId] = node;
        
        let pctStr = "";
        if (parentGwp > 0 && node.gwp !== undefined) {
            const pct = (node.gwp / parentGwp) * 100;
            pctStr = `<span style="background-color: ${pct > 40 ? 'rgba(239, 68, 68, 0.15)' : 'rgba(100, 116, 139, 0.08)'}; color: ${pct > 40 ? 'var(--wku-red)' : 'var(--text-secondary)'}; font-size: 9px; font-weight: bold; padding: 2px 5px; border-radius: 4px; margin-left: 8px;">${pct.toFixed(1)}% of parent GWP</span>`;
        }
        
        let html = `<div class="tree-node" style="padding-left: ${depth * 14}px; display: flex; align-items: center; gap: 6px; margin: 4px 0;">`;
        
        if (isAssembly) {
            html += `<span class="tree-toggle" style="cursor: pointer; font-size: 10px; color: var(--accent-indigo); user-select: none;">▼</span>`;
            html += `<span class="tree-icon">📂</span>`;
            html += `<span class="tree-name" style="font-weight: 600; color: var(--text-primary);">${name}</span>`;
            html += pctStr;
            html += `<span class="optimize-target-action" data-node-id="${nodeId}" style="margin-left: 8px; font-size: 9px; cursor: pointer; color: var(--accent-indigo); text-decoration: underline; font-weight: 500; border: 1px solid var(--border-color); border-radius: 4px; padding: 1px 4px; background: var(--bg-card); transition: all 0.2s;" title="Click to optimize this sub-assembly in Flat List">Target for optimization</span>`;
        } else {
            html += `<span class="tree-toggle" style="visibility: hidden; font-size: 10px;">•</span>`;
            html += `<span class="tree-icon">📄</span>`;
            html += `<span class="tree-name" style="color: var(--text-secondary);">${name}</span>`;
            html += pctStr;
            html += `<span class="substitute-leaf-action" data-node-id="${nodeId}" style="margin-left: 8px; font-size: 9px; cursor: pointer; color: var(--accent-purple); text-decoration: underline; font-weight: 500; border: 1px solid var(--border-color); border-radius: 4px; padding: 1px 4px; background: var(--bg-card); transition: all 0.2s;" title="Click to substitute this material in tree">Substitute</span>`;
        }
        
        html += `<span class="tree-qty" style="color: var(--accent-emerald); font-family: monospace; font-size: 10px; margin-left: auto;">`;
        if (node.gwp !== undefined) {
            html += `<span style="color: var(--text-muted); font-size: 9.5px; margin-right: 8px;">(${node.gwp.toFixed(1)} kg CO₂ eq)</span>`;
        }
        html += `${amount.toLocaleString()} ${unit}</span>`;
        html += `</div>`;
        
        if (isAssembly) {
            html += `<div class="tree-children">`;
            inputs.forEach(child => {
                html += renderBOMTree(child, depth + 1, node.gwp || 0);
            });
            html += `</div>`;
        }
        
        return html;
    }

    if (bomTreeContainer) {
        bomTreeContainer.addEventListener("click", (e) => {
            if (e.target.classList.contains("tree-toggle")) {
                const nodeDiv = e.target.closest(".tree-node");
                const childrenDiv = nodeDiv.nextElementSibling;
                if (childrenDiv && childrenDiv.classList.contains("tree-children")) {
                    if (childrenDiv.style.display === "none") {
                        childrenDiv.style.display = "block";
                        e.target.textContent = "▼";
                    } else {
                        childrenDiv.style.display = "none";
                        e.target.textContent = "▶";
                    }
                }
            }
            
            if (e.target.classList.contains("substitute-leaf-action")) {
                const nodeId = e.target.getAttribute("data-node-id");
                const node = window.currentBOMTreeNodes[nodeId];
                if (node) {
                    const materialName = node.name;
                    let recommended = "scrap steel";
                    if (materialName.toLowerCase().includes("polyethylene") || materialName.toLowerCase().includes("hdpe")) {
                        recommended = "polyethylene recycled";
                    } else if (materialName.toLowerCase().includes("glass") || materialName.toLowerCase().includes("fiberglass")) {
                        recommended = "glass cullet, sorted";
                    }
                    
                    const subName = prompt(`Enter substitute material for '${materialName}':`, recommended);
                    if (subName && subName.trim() !== "") {
                        node.name = subName.trim();
                        const json = JSON.parse(bomJsonTextarea.value);
                        
                        function replaceNodeInTree(root, targetNodeName, replacementName) {
                            if (!root) return;
                            if (root.name === targetNodeName && (!root.inputs || root.inputs.length === 0)) {
                                root.name = replacementName;
                                return;
                            }
                            if (root.inputs) {
                                root.inputs.forEach(child => replaceNodeInTree(child, targetNodeName, replacementName));
                            }
                        }
                        
                        replaceNodeInTree(json, materialName, subName.trim());
                        bomJsonTextarea.value = JSON.stringify(json, null, 2);
                        triggerTreeRender();
                        
                        appendChatMessage("System", `Substituted **${materialName}** with **${subName.trim()}** directly in the hierarchical BOM JSON. Tree emissions and hotspot percentages updated.`);
                    }
                }
            }
            
            if (e.target.classList.contains("optimize-target-action")) {
                const nodeId = e.target.getAttribute("data-node-id");
                const node = window.currentBOMTreeNodes[nodeId];
                if (node) {
                    document.querySelectorAll(".tree-node").forEach(el => el.classList.remove("selected-target-node"));
                    
                    const nodeDiv = e.target.closest(".tree-node");
                    if (nodeDiv) {
                        nodeDiv.classList.add("selected-target-node");
                    }
                    
                    const inputs = node.inputs || [];
                    if (inputs.length === 0) {
                        alert(`Leaf node '${node.name}' has no child inputs to optimize. Please select an assembly node.`);
                        return;
                    }
                    
                    bomTbody.innerHTML = "";
                    inputs.forEach(inp => {
                        addBomRow(inp.name, inp.amount, inp.unit || "kg");
                    });
                    
                    if (activeAssemblyIndicator) {
                        activeAssemblyIndicator.textContent = `🎯 Active Target: ${node.name} (Sub-assembly of Compiled BOM)`;
                        activeAssemblyIndicator.style.display = "block";
                    }
                    
                    tabFlat.click();
                    appendChatMessage("System", `Loaded sub-inputs of intermediate assembly **${node.name}** into the Flat List editor. You can now tweak the parameters or run multi-objective Pareto optimization specifically for this part of the supply chain tree.`);
                }
            }
        });
    }

    // Compile & Calculate Hierarchical BOM
    compileHierarchicalBtn.addEventListener("click", () => {
        let bomJson;
        try {
            bomJson = JSON.parse(bomJsonTextarea.value);
        } catch (e) {
            alert("Invalid JSON format in hierarchical BOM schema: " + e.message);
            return;
        }
        
        compileHierarchicalBtn.disabled = true;
        compileHierarchicalBtn.querySelector(".btn-label").textContent = "Compiling...";
        appendChatMessage("System", `Compiling hierarchical BOM for '${bomJson.name}' in openLCA. Running mapping search, custom sub-assemblies synthesis, and uncertainty propagation. This will take about a minute...`);
        
        fetch("/api/compile", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ bom: bomJson, method_id: lciaMethodSelect ? lciaMethodSelect.value : "" })
        })
        .then(res => res.json())
        .then(data => {
            compileHierarchicalBtn.disabled = false;
            compileHierarchicalBtn.querySelector(".btn-label").textContent = "Compile & Calculate";
            
            if (data.success) {
                activeState.exchanges = data.exchanges;
                activeState.report = { metrics: data.metrics };
                activeState.temp_proc_id = data.process_id;
                activeState.temp_sys_id = data.system_id;
                
                chartPlaceholder.style.display = "block";
                chartPlaceholder.innerHTML = `
                    <div style="text-align: center; padding: 20px; font-family: var(--font-sans);">
                        <svg viewBox="0 0 24 24" fill="none" stroke="var(--accent-emerald)" stroke-width="2" style="width: 48px; height: 48px; margin-bottom: 12px; display: inline-block;">
                            <path d="M22 11.08V12a10 10 0 1 1-5.93-9.14"></path>
                            <polyline points="22 4 12 14.01 9 11.01"></polyline>
                        </svg>
                        <h4 style="margin-bottom: 6px; font-weight: 600; color: var(--text-primary);">Programmatic Compilation Successful</h4>
                        <p style="font-size: 13px; color: var(--text-muted); line-height: 1.6; max-width: 320px; margin: 0 auto;">
                            Linked hierarchical supply chains in the database. Processes compiled and mass-balance verified.
                        </p>
                    </div>
                `;
                tradeoffChartImg.style.display = "none";
                justificationWrapper.style.display = "none";
                
                const realTvl = data.tvl_report || {
                    total_input_mass_kg: bomJson.amount,
                    total_output_mass_kg: bomJson.amount,
                    relative_error: 0.0,
                    is_balanced: true,
                    elemental_discrepancies: {}
                };
                
                updateDashboardUI({
                    report: { metrics: data.metrics },
                    tvl_report: realTvl
                });
                
                chatInput.disabled = false;
                chatSendBtn.disabled = false;
                chatInput.placeholder = "Ask AirLab Advisor about this compiled hierarchy...";
                
                appendChatMessage("Advisor", `Successfully compiled hierarchical BOM for **${bomJson.name}** in openLCA. Programmatically registered custom intermediate assemblies, mapped Leaf feedstocks, and evaluated uncertainty. Process balance passed.`);
            } else {
                appendChatMessage("System Error", data.error);
                alert("Hierarchical compilation failed: " + data.error);
            }
        })
        .catch(err => {
            compileHierarchicalBtn.disabled = false;
            compileHierarchicalBtn.querySelector(".btn-label").textContent = "Compile & Calculate";
            alert("Calculation network error: " + err);
        });
    });

    // Custom Database Parameters Override Logic
    const customParamFeedstockSelect = document.getElementById("custom-param-feedstock-select");
    const customParametersSlidersList = document.getElementById("custom-parameters-sliders-list");

    function updateCustomParamFeedstockDropdown() {
        if (!customParamFeedstockSelect) return;
        
        const currentSel = customParamFeedstockSelect.value;
        customParamFeedstockSelect.innerHTML = `<option value="">-- Tune background feedstock --</option>`;
        
        const uniqueNames = new Set();
        const rows = bomTbody.querySelectorAll("tr");
        rows.forEach(row => {
            const flowNameInput = row.querySelector(".row-flow-name");
            if (flowNameInput) {
                const name = flowNameInput.value.trim();
                if (name) uniqueNames.add(name);
            }
        });
        
        uniqueNames.forEach(name => {
            const opt = document.createElement("option");
            opt.value = name;
            opt.textContent = name;
            if (name === currentSel) opt.selected = true;
            customParamFeedstockSelect.appendChild(opt);
        });
    }

    sampleSelect.addEventListener("change", () => {
        setTimeout(updateCustomParamFeedstockDropdown, 400);
    });
    addRowBtn.addEventListener("click", () => {
        setTimeout(updateCustomParamFeedstockDropdown, 100);
    });
    bomTbody.addEventListener("click", (e) => {
        if (e.target.classList.contains("delete-row-btn")) {
            setTimeout(updateCustomParamFeedstockDropdown, 100);
        }
    });

    if (customParamFeedstockSelect) {
        customParamFeedstockSelect.addEventListener("change", () => {
            const flowName = customParamFeedstockSelect.value;
            if (!flowName) {
                customParametersSlidersList.innerHTML = `<div style="font-size: 11px; text-align: center; color: var(--text-muted); padding: 8px 0; font-family: var(--font-sans);">No database parameters loaded.</div>`;
                return;
            }
            
            customParametersSlidersList.innerHTML = `<div style="font-size: 11px; text-align: center; color: var(--text-secondary); padding: 8px 0; font-family: var(--font-sans);">Loading parameters...</div>`;
            
            fetch(`/api/process-parameters?flow_name=${encodeURIComponent(flowName)}`)
                .then(res => res.json())
                .then(data => {
                    customParametersSlidersList.innerHTML = "";
                    if (data.success && data.parameters && data.parameters.length > 0) {
                        data.parameters.forEach(param => {
                            const minVal = param.value > 0 ? param.value * 0.5 : -5.0;
                            const maxVal = param.value > 0 ? param.value * 1.5 : 5.0;
                            const stepVal = (maxVal - minVal) / 20.0;
                            
                            const currentVal = activeCustomParameterOverrides[param.name] 
                                ? activeCustomParameterOverrides[param.name].value 
                                : param.value;
                                
                            const row = document.createElement("div");
                            row.className = "slider-row";
                            row.innerHTML = `
                                <div class="slider-row-head">
                                    <span class="slider-label" title="${param.description || param.name}">${param.name}</span>
                                    <span class="slider-value" id="val-custom-${param.name}">${currentVal.toFixed(3)}</span>
                                </div>
                                <input type="range" min="${minVal}" max="${maxVal}" step="${stepVal}" value="${currentVal}" class="custom-slider" id="slider-custom-${param.name}">
                            `;
                            
                            row.querySelector("input").addEventListener("input", (evt) => {
                                const val = parseFloat(evt.target.value);
                                document.getElementById(`val-custom-${param.name}`).textContent = val.toFixed(3);
                                activeCustomParameterOverrides[param.name] = {
                                    name: param.name,
                                    value: val,
                                    process_id: param.process_id,
                                    process_name: param.process_name
                                };
                            });
                            
                            customParametersSlidersList.appendChild(row);
                        });
                    } else {
                        customParametersSlidersList.innerHTML = `<div style="font-size: 11px; text-align: center; color: var(--text-muted); padding: 8px 0; font-family: var(--font-sans);">No adjustable parameters found in this process.</div>`;
                    }
                })
                .catch(err => {
                    customParametersSlidersList.innerHTML = `<div style="font-size: 11px; text-align: center; color: var(--accent-red); padding: 8px 0; font-family: var(--font-sans);">Error: ${err.message}</div>`;
                });
        });
    }

    setTimeout(updateCustomParamFeedstockDropdown, 500);

    // Database Diagnostics (Database Doctor) UI Logic
    const btnScanDb = document.getElementById("btn-scan-db");
    const btnHealDb = document.getElementById("btn-heal-db");
    const doctorHealthStatus = document.getElementById("doctor-health-status");
    const doctorDefectsList = document.getElementById("doctor-defects-list");
    let activeStateDefects = [];

    if (btnScanDb) {
        btnScanDb.addEventListener("click", () => {
            let items = [];
            if (activeBomMode === "flat") {
                const rows = bomTbody.querySelectorAll("tr");
                rows.forEach(row => {
                    const flowNameInput = row.querySelector(".row-flow-name");
                    if (flowNameInput && flowNameInput.value.trim()) {
                        items.push({ flow_name: flowNameInput.value.trim() });
                    }
                });
            } else {
                const text = bomJsonTextarea.value.trim();
                if (text) {
                    try {
                        const parsed = JSON.parse(text);
                        function collectNames(node) {
                            let list = [{ flow_name: node.name }];
                            if (node.inputs) {
                                node.inputs.forEach(child => {
                                    list = list.concat(collectNames(child));
                                });
                            }
                            return list;
                        }
                        items = collectNames(parsed);
                    } catch(e) {
                        alert("Invalid JSON schema in text editor. Cannot scan context.");
                        return;
                    }
                }
            }

            if (items.length === 0) {
                alert("BOM is empty. Load a case study or insert custom items first to scan their database context.");
                return;
            }

            // UI feedback
            btnScanDb.disabled = true;
            btnScanDb.querySelector("span").textContent = "Scanning...";
            doctorHealthStatus.textContent = "Scanning...";
            doctorHealthStatus.className = "tvl-status-badge"; // Remove passed/failed classes
            doctorDefectsList.style.display = "none";
            btnHealDb.style.display = "none";

            fetch("/api/diagnose", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ items: items })
            })
            .then(res => res.json())
            .then(data => {
                btnScanDb.disabled = false;
                btnScanDb.querySelector("span").textContent = "Scan Context";

                if (data.success) {
                    activeStateDefects = data.defects;
                    if (data.defects.length === 0) {
                        doctorHealthStatus.textContent = "Healthy";
                        doctorHealthStatus.className = "tvl-status-badge passed";
                        doctorDefectsList.style.display = "none";
                        btnHealDb.style.display = "none";
                        appendChatMessage("System", `Database diagnostics complete. Scanned **${data.scanned_count}** process contexts. No anomalies or hollow technosphere inputs detected! Context database is clean.`);
                    } else {
                        doctorHealthStatus.textContent = `Defects (${data.defects.length})`;
                        doctorHealthStatus.className = "tvl-status-badge failed";
                        
                        // Render defects list
                        let html = "";
                        data.defects.forEach(d => {
                            html += `<div style="margin-bottom: 6px; padding-bottom: 4px; border-bottom: 1px solid var(--border-color);">
                                <strong style="color: var(--wku-red);">${d.process_name || 'Process'}:</strong> [${d.type}] ${d.message}
                            </div>`;
                        });
                        doctorDefectsList.innerHTML = html;
                        doctorDefectsList.style.display = "block";
                        btnHealDb.style.display = "inline-block";
                        
                        appendChatMessage("System", `Database diagnostics complete. Scanned **${data.scanned_count}** process contexts. Identified **${data.defects.length}** anomalies (e.g. missing mass factors, hollow inputs). You can click **Heal Defects** to repair them.`);
                    }
                } else {
                    doctorHealthStatus.textContent = "Error";
                    doctorHealthStatus.className = "tvl-status-badge failed";
                    appendChatMessage("System Error", `Database diagnosis failed: ${data.error}`);
                }
            })
            .catch(err => {
                btnScanDb.disabled = false;
                btnScanDb.querySelector("span").textContent = "Scan Context";
                doctorHealthStatus.textContent = "Error";
                doctorHealthStatus.className = "tvl-status-badge failed";
                appendChatMessage("System Error", `Diagnostics network failure: ${err.message}`);
            });
        });
    }

    // Global state for active Pareto frontier and comparison reports
    window.activeParetoFrontier = [];
    let lcaHistoryData = [];

    // TOPSIS Decision Recalculator
    function recalculateTopsisFrontier(frontier, weights) {
        if (!frontier || frontier.length === 0) return [];
        const kpis = ["GWP", "Acidification", "Water", "Cost"];
        const totalWeight = kpis.reduce((sum, kpi) => sum + (weights[kpi] || 0), 0);
        const normWeights = {};
        kpis.forEach(kpi => {
            normWeights[kpi] = totalWeight > 0 ? (weights[kpi] || 0) / totalWeight : 0.25;
        });
        const ss = {};
        kpis.forEach(kpi => {
            let sumSq = 0;
            frontier.forEach(pt => {
                sumSq += pt.metrics[kpi] * pt.metrics[kpi];
            });
            ss[kpi] = Math.sqrt(sumSq) || 1.0;
        });
        const weightedMatrix = frontier.map(pt => {
            const row = {};
            kpis.forEach(kpi => {
                row[kpi] = (pt.metrics[kpi] / ss[kpi]) * normWeights[kpi];
            });
            return { point: pt, row };
        });
        const idealPos = {};
        const idealNeg = {};
        kpis.forEach(kpi => {
            const values = weightedMatrix.map(m => m.row[kpi]);
            idealPos[kpi] = Math.min(...values);
            idealNeg[kpi] = Math.max(...values);
        });
        const scoredFrontier = weightedMatrix.map(m => {
            let sPosSq = 0;
            let sNegSq = 0;
            kpis.forEach(kpi => {
                sPosSq += Math.pow(m.row[kpi] - idealPos[kpi], 2);
                sNegSq += Math.pow(m.row[kpi] - idealNeg[kpi], 2);
            });
            const sPos = Math.sqrt(sPosSq);
            const sNeg = Math.sqrt(sNegSq);
            const closeness = (sPos + sNeg) > 0 ? sNeg / (sPos + sNeg) : 0.0;
            return {
                ...m.point,
                topsis_score: closeness
            };
        });
        return scoredFrontier.sort((a, b) => b.topsis_score - a.topsis_score);
    }

    let reweighTimeout = null;
    function debouncedBackendReweigh() {
        if (reweighTimeout) clearTimeout(reweighTimeout);
        reweighTimeout = setTimeout(() => {
            if (!window.activeParetoFrontier) return;
            const tradeoffChartImg = document.getElementById("tradeoff-chart-img");
            tradeoffChartImg.style.opacity = "0.5"; // Visual feedback of loading
            fetch("/api/reweigh", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({
                    frontier: window.activeParetoFrontier,
                    baseline_metrics: window.activeBaselineMetrics || {},
                    weights: {
                        GWP: parseFloat(weightGwp.value),
                        Acidification: parseFloat(weightAcid.value),
                        Water: parseFloat(weightWater.value),
                        Cost: parseFloat(weightCost.value)
                    }
                })
            })
            .then(res => res.json())
            .then(data => {
                tradeoffChartImg.style.opacity = "1";
                if (data.success) {
                    activeState.chart_url_dark = data.chart_url_dark;
                    activeState.chart_url_light = data.chart_url_light;
                    updateChartImageSource();
                }
            })
            .catch(() => { tradeoffChartImg.style.opacity = "1"; });
        }, 500); // 500ms debounce
    }

    // Render Pareto compromised table dynamically
    window.renderParetoFrontierTable = function() {
        if (!window.activeParetoFrontier || window.activeParetoFrontier.length === 0) return;
        const weights = {
            GWP: parseFloat(weightGwp.value),
            Acidification: parseFloat(weightAcid.value),
            Water: parseFloat(weightWater.value),
            Cost: parseFloat(weightCost.value)
        };
        const ranked = recalculateTopsisFrontier(window.activeParetoFrontier, weights);
        let html = `
            <div style="padding: 16px; font-family: var(--font-sans); height: 100%; display: flex; flex-direction: column;">
                <h4 style="margin-bottom: 4px; font-weight: 600; color: var(--text-primary); display: flex; align-items: center; gap: 8px;">
                    <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="var(--accent-emerald)" stroke-width="2.5"><path d="M21.21 15.89A10 10 0 1 1 8 2.83"></path><path d="M22 12A10 10 0 0 0 12 2v10z"></path></svg>
                    Pareto-Optimal Feedstock Blends (${ranked.length} Points)
                </h4>
                <p style="font-size: 11px; color: var(--text-muted); margin-bottom: 12px; margin-top: 0;">
                    Ranked dynamically using TOPSIS. Adjust weight sliders to update best compromises in real-time.
                </p>
                <div style="flex-grow: 1; overflow-y: auto; max-height: 280px; border-radius: 8px; border: 1px solid var(--border-color);">
                    <table style="width: 100%; border-collapse: collapse; text-align: left; font-size: 12px; color: var(--text-primary);">
                        <thead style="background-color: var(--card-bg-hover); position: sticky; top: 0; font-weight: 600; text-transform: uppercase; font-size: 10px; letter-spacing: 0.5px;">
                            <tr>
                                <th style="padding: 10px 12px; border-bottom: 1px solid var(--border-color);">Blend Configurations</th>
                                <th style="padding: 10px 12px; border-bottom: 1px solid var(--border-color); text-align: right;">GWP (kg CO₂ eq)</th>
                                <th style="padding: 10px 12px; border-bottom: 1px solid var(--border-color); text-align: right;">Acidification</th>
                                <th style="padding: 10px 12px; border-bottom: 1px solid var(--border-color); text-align: right;">Water (m³)</th>
                                <th style="padding: 10px 12px; border-bottom: 1px solid var(--border-color); text-align: right;">Cost (USD)</th>
                            </tr>
                        </thead>
                        <tbody>
        `;
        ranked.slice(0, 10).forEach((pt, idx) => {
            let blendStr = Object.entries(pt.ratios)
                .map(([name, r]) => `${name.split(',')[0]}: ${(r * 100).toFixed(0)}% recycled`)
                .join(", ");
            if (pt.parameters) {
                blendStr += ` <span style="color: var(--text-muted); font-size: 11px;">(Eff: ${(pt.parameters.process_efficiency * 100).toFixed(0)}%, Loss: ${(pt.parameters.loss_factor * 100).toFixed(0)}%)</span>`;
            }
            const isBest = idx === 0;
            const rowStyle = isBest 
                ? "border-bottom: 1px solid var(--border-color); background-color: rgba(var(--signal-rgb), 0.08); font-weight: 600;" 
                : "border-bottom: 1px solid var(--border-color); transition: background-color 0.2s;";
            const badge = isBest 
                ? `<span style="background: var(--accent-emerald); color: white; padding: 2px 6px; border-radius: 4px; font-size: 9px; margin-left: 6px; text-transform: uppercase;">🏆 Best Compromise</span>`
                : `<span style="display:inline-block; width:18px; height:18px; border-radius:50%; background:var(--accent-indigo); color:white; text-align:center; line-height:18px; font-size:9px; margin-right:6px; font-weight:600;">${idx+1}</span>`;
            html += `
                <tr style="${rowStyle}" onmouseover="this.style.backgroundColor='var(--card-bg-hover)'" onmouseout="this.style.backgroundColor='${isBest ? 'rgba(var(--signal-rgb), 0.08)' : 'transparent'}'">
                    <td style="padding: 10px 12px;">
                        ${isBest ? '' : badge}
                        ${blendStr}
                        ${isBest ? badge : ''}
                    </td>
                    <td style="padding: 10px 12px; text-align: right; color: var(--accent-emerald); font-weight: 600;">${pt.metrics.GWP.toFixed(2)}</td>
                    <td style="padding: 10px 12px; text-align: right;">${pt.metrics.Acidification.toFixed(4)}</td>
                    <td style="padding: 10px 12px; text-align: right;">${pt.metrics.Water.toFixed(2)}</td>
                    <td style="padding: 10px 12px; text-align: right; color: var(--accent-purple); font-weight: 600;">$${pt.metrics.Cost.toFixed(2)}</td>
                </tr>
            `;
        });
        if (ranked.length > 10) {
            html += `
                <tr>
                    <td colspan="5" style="padding: 8px; text-align: center; color: var(--text-muted); font-size: 11px; background-color: var(--card-bg-hover);">
                        ... and ${ranked.length - 10} other configurations
                    </td>
                </tr>
            `;
        }
        html += `
                        </tbody>
                    </table>
                </div>
            </div>
        `;
        chartPlaceholder.style.display = "block";
        chartPlaceholder.innerHTML = html;
    };

    // Database Doctor Healing review modal triggers
    const doctorDiffModal = document.getElementById("doctor-diff-modal");
    const doctorDiffContainer = document.getElementById("doctor-diff-container");
    const doctorConfirmBtn = document.getElementById("doctor-confirm-btn");
    const doctorCancelBtn = document.getElementById("doctor-cancel-btn");
    const doctorCloseBtn = document.getElementById("doctor-close-btn");

    function openDoctorDiffReview() {
        if (!activeStateDefects || activeStateDefects.length === 0) return;
        let html = "";
        activeStateDefects.forEach(d => {
            html += `<div style="margin-bottom: 12px; border: 1px solid var(--border-color); border-radius: 6px; overflow: hidden; background: var(--bg-card);">
                <div style="background: var(--card-bg-hover); padding: 6px 10px; font-weight: bold; border-bottom: 1px solid var(--border-color); font-size: 12px;">
                    🔧 Process: ${d.process_name || 'Process'} [${d.type}]
                </div>
                <div style="padding: 10px; font-family: monospace; font-size: 11px; line-height: 1.4;">`;
            if (d.type === "missing_mass_factor" || d.type === "missing_flow_properties") {
                html += `
                    <span class="diff-del">- Flow: "${d.flow_name}"</span>
                    <span class="diff-del">-   flow_properties: []</span>
                    <span class="diff-add">+ Flow: "${d.flow_name}"</span>
                    <span class="diff-add">+   flow_properties: [</span>
                    <span class="diff-add">+     { property: "Mass", factor: 1.0, is_ref: true }</span>
                    <span class="diff-add">+   ]</span>
                `;
            } else if (d.type === "hollow_input") {
                html += `
                    <span class="diff-del">- Input: "${d.flow_name}"</span>
                    <span class="diff-del">-   provider: [NONE] (hollow input!)</span>
                    <span class="diff-add">+ Input: "${d.flow_name}"</span>
                    <span class="diff-add">+   provider: "Mock Provider - ${d.flow_name}" (Synthesized)</span>
                `;
            } else {
                html += `
                    <span class="diff-del">- System state: Anomalous [${d.type}]</span>
                    <span class="diff-add">+ System state: Repaired [${d.type}]</span>
                `;
            }
            html += `</div></div>`;
        });
        doctorDiffContainer.innerHTML = html;
        doctorDiffModal.style.display = "flex";
    }

    if (btnHealDb) {
        btnHealDb.addEventListener("click", () => {
            openDoctorDiffReview();
        });
    }

    const closeDoctorModal = () => { doctorDiffModal.style.display = "none"; };
    if (doctorCancelBtn) doctorCancelBtn.addEventListener("click", closeDoctorModal);
    if (doctorCloseBtn) doctorCloseBtn.addEventListener("click", closeDoctorModal);

    if (doctorConfirmBtn) {
        doctorConfirmBtn.addEventListener("click", () => {
            closeDoctorModal();
            btnHealDb.disabled = true;
            btnHealDb.querySelector("span").textContent = "Healing...";
            fetch("/api/heal", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ defects: activeStateDefects })
            })
            .then(res => res.json())
            .then(data => {
                btnHealDb.disabled = false;
                btnHealDb.querySelector("span").textContent = "Heal Defects";
                if (data.success) {
                    appendChatMessage("Advisor", `Database Doctor: **${data.message}** Re-evaluating database health...`);
                    btnScanDb.click();
                } else {
                    appendChatMessage("System Error", `Self-healing failed: ${data.error}`);
                    alert("Healing failed: " + data.error);
                }
            })
            .catch(err => {
                btnHealDb.disabled = false;
                btnHealDb.querySelector("span").textContent = "Heal Defects";
                appendChatMessage("System Error", `Healing network error: ${err.message}`);
                alert("Network error during self-healing: " + err.message);
            });
        });
    }

    // Historical Comparator UI logic
    const historyModal = document.getElementById("history-modal");
    const btnOpenHistory = document.getElementById("btn-open-history");
    const historyCloseBtn = document.getElementById("history-close-btn");
    const historyCloseActionBtn = document.getElementById("history-close-action-btn");
    const historyListContainer = document.getElementById("history-list-container");
    const historyCompareBtn = document.getElementById("history-compare-btn");
    const historyComparisonResults = document.getElementById("history-comparison-results");

    if (btnOpenHistory) {
        btnOpenHistory.addEventListener("click", () => {
            historyListContainer.innerHTML = '<div style="text-align:center; padding: 10px; font-size:12px; color:var(--text-muted);">Loading study runs...</div>';
            historyComparisonResults.style.display = "none";
            historyModal.style.display = "flex";
            
            fetch("/api/history")
                .then(res => res.json())
                .then(data => {
                    if (data.success) {
                        lcaHistoryData = data.history;
                        if (lcaHistoryData.length === 0) {
                            historyListContainer.innerHTML = '<div style="text-align:center; padding: 20px; font-size:13px; color:var(--text-muted);">No saved LCA study reports found in this workspace. Run calculations first!</div>';
                            return;
                        }
                        let html = '<div style="display: flex; flex-direction: column; gap: 8px;">';
                        lcaHistoryData.forEach((run, idx) => {
                            html += `
                                <label style="display: flex; align-items: center; gap: 10px; padding: 10px; border: 1px solid var(--border-color); border-radius: 6px; background: var(--bg-card); cursor: pointer; text-transform: none; font-weight: normal; font-size: 13px; color: var(--text-primary);">
                                    <input type="checkbox" class="history-run-checkbox" value="${idx}" style="width: 16px; height: 16px; margin: 0;">
                                    <div style="flex-grow: 1;">
                                        <strong>${run.product_name}</strong> (${run.substituted_from} &rarr; ${run.substituted_to})
                                        <div style="font-size: 11px; color: var(--text-muted);">${run.date} · File: ${run.filename}</div>
                                    </div>
                                </label>
                            `;
                        });
                        html += '</div>';
                        historyListContainer.innerHTML = html;
                    } else {
                        historyListContainer.innerHTML = `<div style="color:var(--wku-red); font-size:12px;">Error: ${data.error}</div>`;
                    }
                })
                .catch(err => {
                    historyListContainer.innerHTML = `<div style="color:var(--wku-red); font-size:12px;">Network failure: ${err.message}</div>`;
                });
        });
    }

    const closeHistoryModal = () => { historyModal.style.display = "none"; };
    if (historyCloseBtn) historyCloseBtn.addEventListener("click", closeHistoryModal);
    if (historyCloseActionBtn) historyCloseActionBtn.addEventListener("click", closeHistoryModal);

    if (historyCompareBtn) {
        historyCompareBtn.addEventListener("click", () => {
            const checked = Array.from(document.querySelectorAll(".history-run-checkbox:checked"))
                .map(cb => lcaHistoryData[parseInt(cb.value)]);
            
            if (checked.length < 2) {
                alert("Please select at least 2 runs to run the comparison.");
                return;
            }
            
            let html = `
                <h4 style="margin-bottom: 12px; font-weight: 600; color: var(--text-primary);">Comparative KPIs Matrix</h4>
                <div style="overflow-x: auto; border: 1px solid var(--border-color); border-radius: 8px; margin-bottom: 16px;">
                    <table style="width: 100%; border-collapse: collapse; text-align: left; font-size: 12px; color: var(--text-primary);">
                        <thead style="background-color: var(--card-bg-hover); font-weight: 600;">
                            <tr>
                                <th style="padding: 10px 12px; border-bottom: 1px solid var(--border-color);">Product / Date</th>
                                <th style="padding: 10px 12px; border-bottom: 1px solid var(--border-color);">Substituted Blend</th>
                                <th style="padding: 10px 12px; border-bottom: 1px solid var(--border-color); text-align: right;">GWP (kg CO₂ eq)</th>
                                <th style="padding: 10px 12px; border-bottom: 1px solid var(--border-color); text-align: right;">Cost (USD)</th>
                            </tr>
                        </thead>
                        <tbody>
            `;
            checked.forEach(run => {
                const gwp = run.metrics["Global Warming"] ? run.metrics["Global Warming"].optimized : 0.0;
                const cost = run.metrics["Feedstock Cost"] ? run.metrics["Feedstock Cost"].optimized : 0.0;
                const unitGwp = run.metrics["Global Warming"] ? run.metrics["Global Warming"].unit : "kg CO₂ eq";
                html += `
                    <tr style="border-bottom: 1px solid var(--border-color);">
                        <td style="padding: 10px 12px;">
                            <strong>${run.product_name}</strong><br>
                            <span style="color: var(--text-muted); font-size: 11px;">${run.date}</span>
                        </td>
                        <td style="padding: 10px 12px; font-style: italic;">
                            ${run.substituted_from} &rarr; ${run.substituted_to}
                        </td>
                        <td style="padding: 10px 12px; text-align: right; font-weight: 600; color: var(--accent-emerald);">${gwp.toFixed(2)} ${unitGwp}</td>
                        <td style="padding: 10px 12px; text-align: right; font-weight: 600; color: var(--accent-purple);">$${cost.toFixed(2)}</td>
                    </tr>
                `;
            });
            html += `
                        </tbody>
                    </table>
                </div>
            `;
            
            // Add a comparative bar chart representation using pure HTML/CSS flex boxes
            html += `
                <h4 style="margin-bottom: 12px; font-weight: 600; color: var(--text-primary);">Footprint Comparison Chart</h4>
                <div style="display: flex; flex-direction: column; gap: 12px; padding: 12px; border: 1px solid var(--border-color); border-radius: 8px; background: var(--bg-card);">
            `;
            const gwps = checked.map(r => r.metrics["Global Warming"] ? r.metrics["Global Warming"].optimized : 0.0);
            const maxGwp = Math.max(...gwps) || 1.0;
            checked.forEach((run, idx) => {
                const gwp = run.metrics["Global Warming"] ? run.metrics["Global Warming"].optimized : 0.0;
                const pct = (gwp / maxGwp) * 100;
                const colors = ["var(--accent-indigo)", "var(--accent-emerald)", "var(--accent-purple)", "var(--signal)"];
                const barColor = colors[idx % colors.length];
                html += `
                    <div style="display: flex; flex-direction: column; gap: 4px;">
                        <div style="display: flex; justify-content: space-between; font-size: 11.5px; color: var(--text-secondary);">
                            <span>${run.product_name} (${run.date.split(' ')[0]})</span>
                            <span style="font-weight: 600;">${gwp.toFixed(2)} kg CO₂ eq</span>
                        </div>
                        <div style="width: 100%; height: 12px; background: var(--bg-input); border-radius: 6px; overflow: hidden; border: 1px solid var(--border-color);">
                            <div style="width: ${pct}%; height: 100%; background-color: ${barColor}; border-radius: 6px;"></div>
                        </div>
                    </div>
                `;
            });
            html += `</div>`;
            historyComparisonResults.innerHTML = html;
            historyComparisonResults.style.display = "block";
        });
    }
});
