/**
 * Official Control Room Controller
 * Live queue advancing, weighbridge completion, and real-time announcements
 */

let officialCenterId = null;
let currentQueueItems = [];
let wsClient = null;

// 1. Load Official Dashboard Stats
async function loadDashboard() {
    try {
        const stats = await App.fetch("/api/official/dashboard");
        officialCenterId = stats.center_id;

        document.getElementById("official-center-name").textContent = stats.center_name;
        document.getElementById("official-inspector-sub").textContent = 
            `Center Code: ${stats.center_code} • District: ${stats.district} • Hours: ${stats.working_hours}`;
        document.getElementById("official-top-title").textContent = `${stats.center_name} (Control Room)`;

        document.getElementById("stat-current-token").textContent = stats.current_token;
        document.getElementById("stat-waiting-farmers").textContent = stats.waiting_farmers;
        document.getElementById("stat-total-today").textContent = stats.total_farmers_today;
        document.getElementById("stat-completed-farmers").textContent = stats.completed_farmers;
        document.getElementById("stat-avg-wait").innerHTML = `${stats.estimated_avg_wait_minutes} <span style="font-size: 1rem;">min</span>`;

        const statusSelect = document.getElementById("center-status-select");
        statusSelect.value = stats.status;

        // Update Pause/Resume button state
        const pauseBtn = document.getElementById("btn-pause-queue");
        if (stats.status === "PAUSED") {
            pauseBtn.innerHTML = "<span>▶️ Resume Queue</span>";
            pauseBtn.className = "btn btn-success";
        } else {
            pauseBtn.innerHTML = "<span>⏸️ Pause Queue</span>";
            pauseBtn.className = "btn btn-outline";
        }

        // Initialize WebSocket for this center
        if (!wsClient && officialCenterId) {
            wsClient = App.initWebSocket(officialCenterId, null, handleOfficialWsEvent);
        }
    } catch (e) {
        console.error("Failed to load official dashboard:", e);
    }
}

// 2. Load Queue Roster Table
async function loadQueueRoster() {
    try {
        currentQueueItems = await App.fetch("/api/official/queue");
        renderQueueTable(currentQueueItems);
    } catch (e) {
        console.error("Failed to load queue:", e);
    }
}

function renderQueueTable(items) {
    const tbody = document.getElementById("queue-roster-body");
    if (!items || items.length === 0) {
        tbody.innerHTML = `<tr><td colspan="9" style="text-align: center; padding: 20px; color: var(--text-muted);">No tokens scheduled today.</td></tr>`;
        return;
    }

    tbody.innerHTML = items.map(item => {
        let badgeClass = "badge-live";
        if (item.status === "PROCESSING") badgeClass = "badge-danger pulse";
        else if (item.status === "COMPLETED") badgeClass = "badge-live";
        else if (item.status === "SKIPPED") badgeClass = "badge-warning";
        else badgeClass = "badge-warning";

        return `
            <tr id="row-token-${item.token_id}">
                <td><strong style="font-size: 1.1rem; color: var(--primary-color);">${item.token_number}</strong></td>
                <td><strong>${item.farmer_name}</strong></td>
                <td>${item.farmer_phone}</td>
                <td>${item.village}</td>
                <td>${item.commodity}</td>
                <td><strong>${item.estimated_quantity_qtl.toFixed(2)}</strong></td>
                <td><small style="color: var(--text-muted);">${item.slot_name}</small></td>
                <td><span class="badge ${badgeClass}">${item.status}</span></td>
                <td>
                    <div style="display: flex; gap: 6px;">
                        ${item.status === 'WAITING' ? `
                            <button class="btn btn-outline" style="padding: 4px 8px; min-height: 32px; font-size: 0.8rem;" onclick="skipFarmerToken(${item.token_id})">
                                Skip
                            </button>
                        ` : ''}
                        ${item.status === 'PROCESSING' ? `
                            <button class="btn btn-success" style="padding: 4px 10px; min-height: 32px; font-size: 0.8rem;" onclick="openWeighModal(${item.token_id})">
                                Weigh
                            </button>
                        ` : ''}
                    </div>
                </td>
            </tr>
        `;
    }).join('');
}

// 3. Official Calls Next Farmer in Queue
async function callNextFarmer() {
    const btn = document.getElementById("btn-call-next");
    btn.disabled = true;
    btn.textContent = "Calling Next Farmer...";

    try {
        const resp = await App.fetch("/api/official/call-next", { method: "POST" });
        App.showToast(`📢 Called ${resp.current_token_number} (${resp.farmer_name})`, "success");
        App.playChime("turn");
        await loadDashboard();
        await loadQueueRoster();
    } catch (err) {
        App.showToast(err.message, "alert");
    } finally {
        btn.disabled = false;
        btn.innerHTML = `<span data-i18n="call_next_farmer">📢 CALL NEXT FARMER</span>`;
    }
}

// 4. Center Operational Status Change
async function handleCenterStatusChange() {
    const newStatus = document.getElementById("center-status-select").value;
    try {
        await App.fetch("/api/official/update-center-status", {
            method: "POST",
            body: JSON.stringify({ status: newStatus })
        });
        App.showToast(`Center status updated to ${newStatus}`, "info");
        await loadDashboard();
    } catch (err) {
        App.showToast(err.message, "alert");
    }
}

// 5. Toggle Pause / Resume Queue
async function togglePauseQueue() {
    const select = document.getElementById("center-status-select");
    const current = select.value;
    const target = (current === "PAUSED") ? "OPEN" : "PAUSED";
    select.value = target;
    await handleCenterStatusChange();
}

// 6. Weighing and Transaction Completion
function openWeighModal(preSelectedTokenId = null) {
    const select = document.getElementById("weigh-token-select");
    const processingTokens = currentQueueItems.filter(i => i.status === "PROCESSING" || i.status === "WAITING");

    if (processingTokens.length === 0) {
        App.showToast("No active or processing tokens to weigh. Call next farmer first.", "alert");
        return;
    }

    select.innerHTML = processingTokens.map(i => `
        <option value="${i.token_id}" ${preSelectedTokenId === i.token_id ? 'selected' : ''}>
            ${i.token_number} - ${i.farmer_name} (${i.commodity}, Est: ${i.estimated_quantity_qtl} Qtl)
        </option>
    `).join('');

    recalcNetWeight();
    document.getElementById("weigh-modal").style.display = "flex";
}

function closeWeighModal() {
    document.getElementById("weigh-modal").style.display = "none";
}

function recalcNetWeight() {
    const gross = parseFloat(document.getElementById("weigh-gross").value) || 0;
    const tare = parseFloat(document.getElementById("weigh-tare").value) || 0;
    const net = Math.max(0, gross - tare);
    document.getElementById("weigh-net").value = net.toFixed(2);

    // Approximate MSP calculation: ~₹2,203/Qtl
    const msp = 2203.00;
    const est = net * msp;
    document.getElementById("weigh-payout-est").textContent = `₹${est.toLocaleString(undefined, {minimumFractionDigits: 2, maximumFractionDigits: 2})}`;
}

async function handleCompleteTransaction(e) {
    e.preventDefault();
    const tokenId = document.getElementById("weigh-token-select").value;
    const gross = parseFloat(document.getElementById("weigh-gross").value);
    const tare = parseFloat(document.getElementById("weigh-tare").value);
    const moisture = parseFloat(document.getElementById("weigh-moisture").value);
    const grade = document.getElementById("weigh-grade").value;

    try {
        const res = await App.fetch("/api/official/complete-token", {
            method: "POST",
            body: JSON.stringify({
                token_id: parseInt(tokenId),
                gross_weight_qtl: gross,
                tare_weight_qtl: tare,
                moisture_content_pct: moisture,
                quality_grade: grade
            })
        });

        App.showToast(`Transaction ${res.transaction_ref} recorded! Amount: ₹${res.final_amount.toLocaleString()}`, "success");
        closeWeighModal();
        await loadDashboard();
        await loadQueueRoster();
    } catch (err) {
        App.showToast(err.message, "alert");
    }
}

// 7. Skip / No-show Token
async function skipFarmerToken(tokenId) {
    if (!confirm("Are you sure you want to mark this farmer as No-Show/Skipped?")) return;

    try {
        await App.fetch("/api/official/skip-token", {
            method: "POST",
            body: JSON.stringify({ token_id: tokenId })
        });
        App.showToast("Farmer token marked as skipped.", "info");
        await loadDashboard();
        await loadQueueRoster();
    } catch (err) {
        App.showToast(err.message, "alert");
    }
}

// 8. Urgent Announcements
function openAnnouncementModal() {
    document.getElementById("announcement-modal").style.display = "flex";
}

function closeAnnouncementModal() {
    document.getElementById("announcement-modal").style.display = "none";
}

async function handleBroadcastAnnouncement(e) {
    e.preventDefault();
    const urgency = document.getElementById("ann-urgency").value;
    const title = document.getElementById("ann-title").value.trim();
    const message = document.getElementById("ann-message").value.trim();

    try {
        await App.fetch("/api/official/announcements", {
            method: "POST",
            body: JSON.stringify({ urgency, title, message })
        });
        App.showToast("Notice broadcasted to all queued farmers!", "success");
        closeAnnouncementModal();
    } catch (err) {
        App.showToast(err.message, "alert");
    }
}

// 9. Table Search Filter
function filterQueueTable() {
    const q = document.getElementById("queue-search").value.toLowerCase();
    const filtered = currentQueueItems.filter(i => 
        i.token_number.toLowerCase().includes(q) || 
        i.farmer_name.toLowerCase().includes(q) ||
        i.commodity.toLowerCase().includes(q)
    );
    renderQueueTable(filtered);
}

// 10. WebSocket Event Receiver
function handleOfficialWsEvent(evt) {
    console.log("Official WS Event:", evt);
    if (evt.event === "NEW_TOKEN_BOOKED" || evt.event === "TOKEN_ADVANCED" || evt.event === "TRANSACTION_COMPLETED") {
        loadDashboard();
        loadQueueRoster();
    }
}

document.addEventListener("DOMContentLoaded", async () => {
    if (!App.checkAuthRedirect("OFFICIAL")) return;
    await loadDashboard();
    await loadQueueRoster();
});
