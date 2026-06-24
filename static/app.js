document.addEventListener("DOMContentLoaded", () => {
    // DOM Elements
    const sampleSelect = document.getElementById("sample-select");
    const bomTbody = document.getElementById("bom-tbody");
    const addRowBtn = document.getElementById("add-row-btn");
    const optimizeBtn = document.getElementById("optimize-btn");
    const chatInput = document.getElementById("chat-input");
    const chatSendBtn = document.getElementById("chat-send-btn");
    const chatBox = document.getElementById("chat-box");
    
    const openlcaStatus = document.getElementById("openlca-status");
    const ollamaStatus = document.getElementById("ollama-status");
    
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
        method_id: null
    };

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
        optimizeBtn.textContent = "Processing...";
        appendChatMessage("System", "Running automated ingestion, mass verification, sensitivity hotspot mapping, and multi-objective calculation setup. This takes a few seconds...");

        fetch("/api/optimize", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ items: items })
        })
        .then(res => res.json())
        .then(data => {
            optimizeBtn.disabled = false;
            optimizeBtn.textContent = "Run Optimization 🚀";
            
            if (data.success) {
                // Update active state
                activeState.exchanges = data.exchanges;
                activeState.report = data.report;
                activeState.temp_proc_id = data.temp_proc_id;
                activeState.temp_sys_id = data.temp_sys_id;
                activeState.method_id = data.method_id;
                
                // Enable chat console
                chatInput.disabled = false;
                chatSendBtn.disabled = false;
                chatInput.placeholder = "Ask Copilot a question or request a feedstock swap...";

                // Update UI elements
                updateDashboardUI(data);
                
                appendChatMessage("Copilot", `Ingested BOM items successfully. Dynamic hotspot analysis identified **${data.report.substituted_from}** as carrying the highest carbon footprint sensitivity. Substituted it with **${data.report.substituted_to}** (TVL verified). You can now chat below.`);
            } else {
                appendChatMessage("System Error", data.error);
                alert("Optimization calculation failed: " + data.error);
            }
        })
        .catch(err => {
            optimizeBtn.disabled = false;
            optimizeBtn.textContent = "Run Optimization 🚀";
            alert("Calculation network error: " + err);
        });
    });

    // 5. Update Metrics, TVL, and Charts on Dashboard
    function updateDashboardUI(data) {
        const report = data.report;
        const tvl = data.tvl_report;
        
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

        // 2. Update Metrics cards (Baseline, Optimized, Change)
        const metrics = report.metrics;
        
        // GWP
        updateMetricCard(metrics["Global Warming"], gwpBase, gwpOpt, gwpChange);
        // Acidification
        updateMetricCard(metrics["Acidification"], acidBase, acidOpt, acidChange);
        // Water
        updateMetricCard(metrics["Water Consumption"], waterBase, waterOpt, waterChange);
        // Cost
        updateMetricCard(metrics["Feedstock Cost"], costBase, costOpt, costChange);

        // 3. Update comparison trade-off chart image
        chartPlaceholder.style.display = "none";
        tradeoffChartImg.style.display = "block";
        tradeoffChartImg.src = `${data.chart_url}?t=${Date.now()}`;

        // 4. Update Justification Content
        if (data.justification) {
            justificationWrapper.style.display = "block";
            justificationContent.textContent = data.justification;
        } else {
            justificationWrapper.style.display = "none";
        }
    }

    function updateMetricCard(metricData, baseElem, optElem, changeElem) {
        if (!metricData) return;
        baseElem.textContent = metricData.baseline.toFixed(4);
        optElem.textContent = metricData.optimized.toFixed(4);
        
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
                method_id: activeState.method_id
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
                    
                    // Update UI elements
                    updateDashboardUI(data);
                    
                    appendChatMessage("Copilot", `Stock substitution calculation complete. Substituted target feedstock. Updated environmental and financial cost metrics. Visual chart re-plotted.`);
                } else {
                    appendChatMessage("Copilot", `Feedstock substitution calculation failed: ${data.error}`);
                }
            } else {
                appendChatMessage("Copilot", data.response);
            }
        })
        .catch(err => {
            chatInput.disabled = false;
            chatSendBtn.disabled = false;
            appendChatMessage("System Error", "Connection failed: " + err);
        });
    }

    function appendChatMessage(sender, text) {
        const msgDiv = document.createElement("div");
        msgDiv.className = `message ${sender.toLowerCase()}-msg`;
        msgDiv.innerHTML = `<strong>${sender}:</strong> ${text}`;
        chatBox.appendChild(msgDiv);
        
        // Auto-scroll chat box to bottom
        chatBox.scrollTop = chatBox.scrollHeight;
    }
});
