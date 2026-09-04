/**
 * State Administrator Controller
 * Analytics charts, C++ optimization runner, centers & user management
 */

// 1. Load Admin Dashboard KPIs
async function loadAdminKPIs() {
    try {
        const data = await App.fetch("/api/admin/dashboard");
        document.getElementById("admin-stat-farmers").textContent = data.total_registered_farmers;
        document.getElementById("admin-stat-centers").textContent = data.total_procurement_centers;
        document.getElementById("admin-stat-procured").textContent = data.total_procured_metric_tonnes.toLocaleString();
        document.getElementById("admin-stat-payout").textContent = `₹${data.total_disbursed_inr.toLocaleString()}`;
    } catch (e) {
        console.error("Failed to load admin KPIs:", e);
    }
}

// 2. Run C++ Workload Optimization Model
async function runCppOptimization() {
    const centerId = document.getElementById("cpp-center-select").value;
    const btn = document.getElementById("btn-run-cpp");
    btn.disabled = true;
    btn.textContent = "Running C++ Optimizer...";

    try {
        const res = await App.fetch("/api/admin/run-cpp-optimization", {
            method: "POST",
            body: JSON.stringify({
                center_id: parseInt(centerId),
                operating_hours: 8
            })
        });

        document.getElementById("cpp-res-title").textContent = `Optimization Report for ${res.center_name}`;
        document.getElementById("cpp-res-avg-wait").textContent = `${res.average_wait_minutes} min`;
        document.getElementById("cpp-res-peak-wait").textContent = `${res.peak_wait_minutes} min`;
        document.getElementById("cpp-res-utilization").textContent = `${res.counter_utilization_pct}%`;
        document.getElementById("cpp-res-rec-counters").textContent = `${res.recommended_counters} Counters`;
        document.getElementById("cpp-res-summary").textContent = res.status_summary;

        document.getElementById("cpp-results-box").style.display = "block";
        App.showToast("C++ optimization algorithm executed successfully!", "success");
    } catch (err) {
        App.showToast(err.message, "alert");
    } finally {
        btn.disabled = false;
        btn.innerHTML = `<span data-i18n="btn_run_cpp_opt">⚙️ Run C++ Workload Optimizer</span>`;
    }
}

// 3. Run C++ Stochastic Discrete-Event Simulation
async function runCppSimulation() {
    const btn = document.getElementById("btn-run-sim");
    btn.disabled = true;
    btn.textContent = "Running Simulation...";

    try {
        const res = await App.fetch("/api/admin/run-cpp-simulation", { method: "POST" });
        document.getElementById("cpp-res-title").textContent = `C++ Discrete-Event Simulation (80 Random Farmers)`;
        document.getElementById("cpp-res-avg-wait").textContent = `${res.simulated_avg_wait_min} min`;
        document.getElementById("cpp-res-peak-wait").textContent = `${res.simulated_max_wait_min} min`;
        document.getElementById("cpp-res-utilization").textContent = `${res.simulated_utilization_pct}%`;
        document.getElementById("cpp-res-rec-counters").textContent = `2 Counters (Simulated)`;
        document.getElementById("cpp-res-summary").textContent = 
            `Simulation modeled 80 farmer arrivals using exponential inter-arrival distribution and log-normal inspection durations. Maximum delay capped at ${res.simulated_max_wait_min} minutes.`;

        document.getElementById("cpp-results-box").style.display = "block";
        App.showToast("C++ day simulation completed!", "success");
    } catch (err) {
        App.showToast(err.message, "alert");
    } finally {
        btn.disabled = false;
        btn.innerHTML = `<span data-i18n="btn_run_cpp_sim">🎲 Run Stochastic Simulation</span>`;
    }
}

// 4. Load Analytics & Render Pure SVG Charts
async function loadAnalytics() {
    try {
        const data = await App.fetch("/api/admin/reports");

        // Render Center SVG Bar Chart
        renderCenterBarChart(data.centers);

        // Render Commodity Breakdown
        renderCommodityBreakdown(data.commodities);
    } catch (e) {
        console.error("Failed to load reports:", e);
    }
}

function renderCenterBarChart(centers) {
    const container = document.getElementById("center-chart-container");
    if (!centers || centers.length === 0) {
        container.innerHTML = `<p style="color: var(--text-muted);">No transaction data available.</p>`;
        return;
    }

    const maxVal = Math.max(...centers.map(c => c.total_weight_qtl), 100);
    const chartHeight = 180;
    const barWidth = 45;
    const gap = 35;
    const totalWidth = centers.length * (barWidth + gap) + 40;

    const bars = centers.map((c, idx) => {
        const height = Math.max(10, Math.round((c.total_weight_qtl / maxVal) * (chartHeight - 40)));
        const x = 30 + idx * (barWidth + gap);
        const y = chartHeight - height - 20;

        return `
            <rect x="${x}" y="${y}" width="${barWidth}" height="${height}" fill="#0f5132" rx="4" />
            <text x="${x + barWidth/2}" y="${y - 6}" font-size="11" font-weight="700" fill="#0f172a" text-anchor="middle">
                ${c.total_weight_qtl > 0 ? c.total_weight_qtl + 'Q' : '0'}
            </text>
            <text x="${x + barWidth/2}" y="${chartHeight}" font-size="10" fill="#64748b" text-anchor="middle">
                ${c.name.split(' ')[0]}
            </text>
        `;
    }).join('');

    container.innerHTML = `
        <svg width="100%" height="${chartHeight + 10}" viewBox="0 0 ${totalWidth} ${chartHeight + 10}" xmlns="http://www.w3.org/2000/svg">
            <line x1="20" y1="${chartHeight - 20}" x2="${totalWidth - 10}" y2="${chartHeight - 20}" stroke="#cbd5e1" stroke-width="2" />
            ${bars}
        </svg>
    `;
}

function renderCommodityBreakdown(commodities) {
    const container = document.getElementById("commodity-breakdown-container");
    if (!commodities || commodities.length === 0) {
        container.innerHTML = `<p style="color: var(--text-muted);">No commodity data.</p>`;
        return;
    }

    const totalWeight = commodities.reduce((acc, c) => acc + c.total_weight_qtl, 0) || 1;

    container.innerHTML = commodities.map(c => {
        const pct = Math.round((c.total_weight_qtl / totalWeight) * 100);
        return `
            <div style="margin-bottom: 14px;">
                <div style="display: flex; justify-content: space-between; font-size: 0.9rem; font-weight: 600; margin-bottom: 4px;">
                    <span>${c.name} (${c.transactions_count} lots)</span>
                    <span>${c.total_weight_qtl.toFixed(1)} Qtl • ₹${c.total_payout_inr.toLocaleString()}</span>
                </div>
                <div class="progress-bar-bg" style="height: 10px;">
                    <div class="progress-fill" style="width: ${Math.max(5, pct)}%;"></div>
                </div>
            </div>
        `;
    }).join('');
}

let adminSchedules = [];
let adminCenters = [];
let adminCommodities = [];

// 5. Load Procurement Centers Table
async function loadCentersTable() {
    try {
        const centers = await App.fetch("/api/admin/centers");
        adminCenters = centers;
        const tbody = document.getElementById("admin-centers-body");
        if (tbody) {
            tbody.innerHTML = centers.map(c => `
                <tr>
                    <td><strong>${c.center_code}</strong></td>
                    <td><strong>${c.name}</strong><br><small style="color: #64748b">${c.address}</small></td>
                    <td>${c.district}, ${c.state}</td>
                    <td>${c.active_counters} Counters</td>
                    <td>${c.daily_capacity_mt} MT</td>
                    <td><span class="badge badge-live">${c.current_token_seq > 0 ? 'A' + String(c.current_token_seq).padStart(3, '0') : 'None'}</span></td>
                    <td><span class="badge ${c.status === 'OPEN' ? 'badge-live' : 'badge-warning'}">${c.status}</span></td>
                </tr>
            `).join('');
        }

        // Populate Center filter in Schedule Management
        const schedCenterFilter = document.getElementById("admin-sched-center-filter");
        if (schedCenterFilter) {
            const currentVal = schedCenterFilter.value;
            schedCenterFilter.innerHTML = `<option value="">All Procurement Centers (${centers.length})</option>` +
                centers.map(c => `<option value="${c.id}">${c.name} (${c.district})</option>`).join('');
            if (currentVal) schedCenterFilter.value = currentVal;
        }

        // Populate Center dropdown in Create Schedule Modal
        const createCenterSelect = document.getElementById("admin-create-center");
        if (createCenterSelect) {
            createCenterSelect.innerHTML = `<option value="">Select Center</option>` +
                centers.map(c => `<option value="${c.id}">${c.name} (${c.district})</option>`).join('');
        }
    } catch (e) {
        console.error("Failed to load centers table:", e);
    }
}

// 6. Load Notified Commodities for Admin Schedule Creation
async function loadAdminCommodities() {
    try {
        const commodities = await App.fetch("/api/admin/commodities");
        adminCommodities = commodities;
        const commSelect = document.getElementById("admin-create-commodity");
        if (commSelect) {
            commSelect.innerHTML = `<option value="">Select Notified Commodity</option>` +
                commodities.map(c => `<option value="${c.id}">${c.name} (MSP: ₹${c.msp_per_quintal}/Qtl)</option>`).join('');
        }
    } catch (e) {
        console.error("Failed to load commodities:", e);
    }
}

// 7. Statewide Procurement Schedules & Capacity Management
async function loadAdminSchedules() {
    const filterEl = document.getElementById("admin-sched-center-filter");
    const centerId = filterEl ? filterEl.value : "";
    const tbody = document.getElementById("admin-schedules-body");
    if (tbody) tbody.innerHTML = `<tr><td colspan="8" style="text-align:center; padding: 20px;">Loading statewide schedules...</td></tr>`;

    try {
        const url = `/api/admin/schedules${centerId ? `?center_id=${centerId}` : ''}`;
        const schedules = await App.fetch(url);
        adminSchedules = schedules;
        renderAdminSchedulesTable(schedules);
    } catch (e) {
        console.error("Failed to load admin schedules:", e);
        if (tbody) tbody.innerHTML = `<tr><td colspan="8" style="text-align:center; color: var(--danger-color); padding: 20px;">Failed to load schedules: ${e.message}</td></tr>`;
    }
}

function renderAdminSchedulesTable(schedules) {
    const tbody = document.getElementById("admin-schedules-body");
    if (!tbody) return;

    if (!schedules || schedules.length === 0) {
        tbody.innerHTML = `<tr><td colspan="8" style="text-align: center; padding: 24px; color: var(--text-muted);">No procurement schedules found for the selected criteria. Click "Create New Schedule" to publish one.</td></tr>`;
        return;
    }

    tbody.innerHTML = schedules.map(s => {
        const booked = parseFloat(s.booked_capacity_quintals) || 0;
        const total = parseFloat(s.total_capacity_quintals) || 1;
        const pct = Math.min(100, Math.round((booked / total) * 100));

        let statusBadge = "badge-live";
        if (s.status === "FULL" || s.status === "PAUSED") statusBadge = "badge-warning";
        else if (s.status === "CANCELLED") statusBadge = "badge-danger";
        else if (s.status === "COMPLETED") statusBadge = "badge-primary";

        const startTimeStr = s.start_time ? s.start_time.slice(0, 5) : "--:--";
        const endTimeStr = s.end_time ? s.end_time.slice(0, 5) : "--:--";

        return `
            <tr>
                <td><strong>${s.schedule_date}</strong></td>
                <td>
                    <strong>${s.center_name}</strong>
                    <br><small style="color: var(--text-muted); font-size: 0.78rem;">Center ID: ${s.center_id}</small>
                </td>
                <td><span class="badge" style="background: #e2e8f0; color: #1e293b;">${s.commodity_name}</span></td>
                <td>${startTimeStr} - ${endTimeStr}</td>
                <td>
                    <div><strong>${booked.toFixed(1)} / ${total.toFixed(1)} Qtl</strong> (${pct}%)</div>
                    <div class="progress-bar-bg" style="height: 6px; margin-top: 4px; width: 110px;">
                        <div class="progress-fill" style="width: ${pct}%;"></div>
                    </div>
                </td>
                <td><span class="badge" style="background: var(--bg-card); border: 1px solid var(--border-color);">${s.slots ? s.slots.length : 0} Slots</span></td>
                <td><span class="badge ${statusBadge}">${s.status}</span></td>
                <td>
                    <div style="display: flex; gap: 6px;">
                        <button class="btn btn-outline" style="padding: 4px 8px; min-height: 28px; font-size: 0.8rem;" onclick="openAdminEditScheduleModal(${s.id})">
                            ✏️ Edit
                        </button>
                        <button class="btn btn-outline" style="padding: 4px 8px; min-height: 28px; font-size: 0.8rem; color: var(--danger-color); border-color: var(--danger-color);" onclick="deleteOrCancelAdminSchedule(${s.id})">
                            🗑️ Delete
                        </button>
                    </div>
                </td>
            </tr>
        `;
    }).join('');
}

function openAdminCreateScheduleModal() {
    const modal = document.getElementById("admin-create-schedule-modal");
    if (!modal) return;

    // Default date to tomorrow
    const tomorrow = new Date();
    tomorrow.setDate(tomorrow.getDate() + 1);
    const dateInput = document.getElementById("admin-create-date");
    if (dateInput) {
        dateInput.value = tomorrow.toISOString().split("T")[0];
        dateInput.min = new Date().toISOString().split("T")[0];
    }

    modal.style.display = "flex";
}

function closeAdminCreateScheduleModal() {
    const modal = document.getElementById("admin-create-schedule-modal");
    if (modal) modal.style.display = "none";
}

async function handleAdminCreateSchedule(event) {
    event.preventDefault();
    const centerId = parseInt(document.getElementById("admin-create-center").value);
    const commodityId = parseInt(document.getElementById("admin-create-commodity").value);
    const schedDate = document.getElementById("admin-create-date").value;
    let startTime = document.getElementById("admin-create-start").value;
    let endTime = document.getElementById("admin-create-end").value;
    const capacity = parseFloat(document.getElementById("admin-create-capacity").value);
    const tokensSlot = parseInt(document.getElementById("admin-create-tokens-slot").value) || 10;

    if (!centerId || !commodityId || !schedDate || !startTime || !endTime || !capacity) {
        App.showToast("Please fill in all required fields", "alert");
        return;
    }

    if (startTime.length === 5) startTime += ":00";
    if (endTime.length === 5) endTime += ":00";

    try {
        await App.fetch("/api/admin/schedules", {
            method: "POST",
            body: JSON.stringify({
                center_id: centerId,
                commodity_id: commodityId,
                schedule_date: schedDate,
                start_time: startTime,
                end_time: endTime,
                total_capacity_quintals: capacity,
                tokens_per_slot: tokensSlot
            })
        });

        App.showToast("Procurement schedule published statewide!", "success");
        closeAdminCreateScheduleModal();
        await loadAdminSchedules();
    } catch (e) {
        App.showToast(`Failed to create schedule: ${e.message}`, "alert");
    }
}

function openAdminEditScheduleModal(scheduleId) {
    const sched = adminSchedules.find(s => s.id === scheduleId);
    if (!sched) {
        App.showToast("Schedule not found", "alert");
        return;
    }

    document.getElementById("admin-edit-schedule-id").value = sched.id;
    document.getElementById("admin-edit-center-name").textContent = sched.center_name || `Center #${sched.center_id}`;
    document.getElementById("admin-edit-commodity-name").textContent = sched.commodity_name || "General";
    document.getElementById("admin-edit-date").value = sched.schedule_date;
    document.getElementById("admin-edit-start").value = sched.start_time ? sched.start_time.slice(0, 5) : "09:00";
    document.getElementById("admin-edit-end").value = sched.end_time ? sched.end_time.slice(0, 5) : "17:00";
    document.getElementById("admin-edit-capacity").value = sched.total_capacity_quintals;
    document.getElementById("admin-edit-status").value = sched.status;

    const modal = document.getElementById("admin-edit-schedule-modal");
    if (modal) modal.style.display = "flex";
}

function closeAdminEditScheduleModal() {
    const modal = document.getElementById("admin-edit-schedule-modal");
    if (modal) modal.style.display = "none";
}

async function handleAdminUpdateSchedule(event) {
    event.preventDefault();
    const schedId = document.getElementById("admin-edit-schedule-id").value;
    const schedDate = document.getElementById("admin-edit-date").value;
    let startTime = document.getElementById("admin-edit-start").value;
    let endTime = document.getElementById("admin-edit-end").value;
    const capacity = parseFloat(document.getElementById("admin-edit-capacity").value);
    const status = document.getElementById("admin-edit-status").value;

    if (startTime.length === 5) startTime += ":00";
    if (endTime.length === 5) endTime += ":00";

    try {
        await App.fetch(`/api/admin/schedules/${schedId}`, {
            method: "PUT",
            body: JSON.stringify({
                schedule_date: schedDate,
                start_time: startTime,
                end_time: endTime,
                total_capacity_quintals: capacity,
                status: status
            })
        });

        App.showToast("Procurement schedule updated successfully!", "success");
        closeAdminEditScheduleModal();
        await loadAdminSchedules();
    } catch (e) {
        App.showToast(`Failed to update schedule: ${e.message}`, "alert");
    }
}

async function deleteOrCancelAdminSchedule(scheduleId) {
    if (!confirm("Are you sure you want to delete or cancel this schedule? Active booked tokens will be protected.")) return;

    try {
        const res = await App.fetch(`/api/admin/schedules/${scheduleId}`, {
            method: "DELETE"
        });
        App.showToast(res.message || "Schedule removed successfully", "success");
        await loadAdminSchedules();
    } catch (e) {
        App.showToast(`Failed to delete schedule: ${e.message}`, "alert");
    }
}

// 8. Load System Users Table
async function loadUsers() {
    const role = document.getElementById("user-role-filter").value;
    try {
        const users = await App.fetch(`/api/admin/users${role ? `?role=${role}` : ''}`);
        const tbody = document.getElementById("admin-users-body");
        tbody.innerHTML = users.map(u => `
            <tr>
                <td>${u.id}</td>
                <td><strong>${u.username}</strong></td>
                <td>${u.full_name}</td>
                <td><span class="badge ${u.role === 'FARMER' ? 'badge-live' : (u.role === 'ADMIN' ? 'badge-warning' : 'badge-danger')}">${u.role}</span></td>
                <td>${u.phone}</td>
                <td>${u.language_pref.toUpperCase()}</td>
                <td><span class="badge ${u.is_active ? 'badge-live' : 'badge-danger'}">${u.is_active ? 'Active' : 'Suspended'}</span></td>
                <td>
                    <button class="btn btn-outline" style="padding: 4px 8px; min-height: 28px; font-size: 0.8rem;" onclick="toggleUserStatus(${u.id}, ${!u.is_active})">
                        ${u.is_active ? 'Suspend' : 'Activate'}
                    </button>
                </td>
            </tr>
        `).join('');
    } catch (e) {
        console.error("Failed to load users:", e);
    }
}

async function toggleUserStatus(userId, newStatus) {
    try {
        await App.fetch(`/api/admin/users/${userId}/status?is_active=${newStatus}`, { method: "PUT" });
        App.showToast("User status updated", "success");
        await loadUsers();
    } catch (e) {
        App.showToast(e.message, "alert");
    }
}

document.addEventListener("DOMContentLoaded", async () => {
    if (!App.checkAuthRedirect("ADMIN")) return;
    await loadAdminKPIs();
    await loadAnalytics();
    await loadCentersTable();
    await loadAdminCommodities();
    await loadAdminSchedules();
    await loadUsers();
});
