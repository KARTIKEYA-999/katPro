/**
 * State Administrator Controller
 * Analytics charts, C++ optimization runner, centers & user management
 */

let adminOfficials = [];
let adminFarmers = [];

function escapeHtml(str) {
    if (!str) return "";
    return String(str)
        .replace(/&/g, "&amp;")
        .replace(/</g, "&lt;")
        .replace(/>/g, "&gt;")
        .replace(/"/g, "&quot;")
        .replace(/'/g, "&#039;");
}

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
        const tabBadgeCenters = document.getElementById("tab-badge-centers");
        if (tabBadgeCenters) tabBadgeCenters.textContent = centers.length;
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
                    <td><span class="badge ${c.status === 'OPEN' || c.status === 'IN PROGRESS' ? 'badge-live' : (c.status === 'CLOSED' ? 'badge-danger' : 'badge-warning')}">${c.status}</span></td>
                    <td>
                        ${c.latitude && c.longitude ? `
                            <button class="btn btn-sm btn-outline" onclick="openAdminCenterMapModal(${c.id})" style="padding: 4px 8px; font-size: 0.8rem; display: inline-flex; align-items: center; gap: 4px; cursor: pointer;">
                                📍 Map
                            </button>
                        ` : `
                            <span style="color:#94a3b8; font-size:0.8rem;">No GPS</span>
                        `}
                    </td>
                    <td>
                        <div style="display: flex; gap: 6px;">
                            <button class="btn btn-sm btn-primary" onclick="openAdminEditCenterModal(${c.id})" style="padding: 4px 8px; font-size: 0.8rem; cursor: pointer;">✏️ Edit</button>
                            <button class="btn btn-sm btn-danger" onclick="deleteAdminCenter(${c.id})" style="padding: 4px 8px; font-size: 0.8rem; cursor: pointer;">🗑️ Delete</button>
                        </div>
                    </td>
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

        // Populate Center filter in Farmer Approval & Registry Queue
        const farmerCenterFilter = document.getElementById("admin-farmer-center-filter");
        if (farmerCenterFilter) {
            const currentVal = farmerCenterFilter.value;
            farmerCenterFilter.innerHTML = `<option value="">🏢 All Registered Centers (${centers.length})</option>` +
                centers.map(c => `<option value="${c.id}">🏢 ${c.name} (${c.center_code || c.district})</option>`).join('');
            if (currentVal) farmerCenterFilter.value = currentVal;
        }

        // Populate Center dropdown in Create Schedule Modal
        const createCenterSelect = document.getElementById("admin-create-center");
        if (createCenterSelect) {
            createCenterSelect.innerHTML = `<option value="">Select Center</option>` +
                centers.map(c => `<option value="${c.id}">${c.name} (${c.district})</option>`).join('');
        }

        // Populate Center dropdowns for Official Modals
        const officialCreateCenter = document.getElementById("admin-official-create-center");
        if (officialCreateCenter) {
            officialCreateCenter.innerHTML = `<option value="">Select Procurement Center</option>` +
                centers.map(c => `<option value="${c.id}">${c.name} (${c.district})</option>`).join('');
        }
        const officialEditCenter = document.getElementById("admin-official-edit-center");
        if (officialEditCenter) {
            officialEditCenter.innerHTML = `<option value="">Select Procurement Center</option>` +
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
                    <div style="display: flex; gap: 6px; align-items: center;">
                        <button class="btn btn-outline btn-sm" style="padding: 6px 10px; font-size: 0.95rem; min-height: 32px; border-radius: 6px;" onclick="openAdminEditScheduleModal(${s.id})" title="Edit Schedule Quota & Timing" aria-label="Edit Schedule">
                            ✏️
                        </button>
                        <button class="btn btn-outline btn-sm" style="padding: 6px 10px; font-size: 0.95rem; min-height: 32px; border-radius: 6px; color: var(--danger-color); border-color: var(--danger-color);" onclick="deleteOrCancelAdminSchedule(${s.id})" title="Cancel or Delete Schedule" aria-label="Delete Schedule">
                            🗑️
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

    // Ensure centers dropdown is populated
    if (!adminCenters || adminCenters.length === 0) {
        loadCentersTable();
    }

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
    const schedCenterSpan = document.getElementById("admin-edit-sched-center-name") || document.getElementById("admin-edit-center-name");
    if (schedCenterSpan) schedCenterSpan.textContent = sched.center_name || `Center #${sched.center_id}`;
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
        const res = await App.fetch(`/api/admin/users/${userId}/status?is_active=${newStatus}`, {
            method: "PUT"
        });
        App.showToast(res.message || "User status updated", "success");
        await loadUsers();
    } catch (e) {
        App.showToast(`Failed to update status: ${e.message}`, "alert");
    }
}

// 9. Central Office Users Management
async function loadAdminOfficials() {
    const tbody = document.getElementById("admin-officials-body");
    if (!adminOfficials || adminOfficials.length === 0) {
        if (tbody) tbody.innerHTML = `<tr><td colspan="9" style="text-align: center; padding: 20px;">Loading Central Office users...</td></tr>`;
    } else {
        renderAdminOfficialsTable(adminOfficials);
    }

    try {
        const officials = await App.fetch("/api/admin/officials");
        adminOfficials = officials;

        const badge = document.getElementById("tab-badge-officials");
        if (badge) badge.textContent = officials.length;

        const searchInp = document.getElementById("admin-official-search");
        if (searchInp && searchInp.value.trim()) {
            filterAdminOfficialsTable();
        } else {
            renderAdminOfficialsTable(officials);
        }
    } catch (e) {
        console.error("Failed to load officials:", e);
        if (tbody && (!adminOfficials || adminOfficials.length === 0)) {
            tbody.innerHTML = `<tr><td colspan="9" style="text-align: center; color: var(--danger-color); padding: 20px;">Failed to load Central Office users: ${e.message}</td></tr>`;
        }
    }
}

function renderAdminOfficialsTable(officials) {
    const tbody = document.getElementById("admin-officials-body");
    if (!tbody) return;

    if (!officials || officials.length === 0) {
        tbody.innerHTML = `<tr><td colspan="9" style="text-align: center; padding: 24px; color: var(--text-muted);">No Central Office users found matching search criteria.</td></tr>`;
        return;
    }

    tbody.innerHTML = officials.map(o => `
        <tr>
            <td>${o.id}</td>
            <td><strong>${escapeHtml(o.username)}</strong></td>
            <td>${escapeHtml(o.full_name)}</td>
            <td><span class="badge badge-primary">${escapeHtml(o.designation || 'Procurement Officer')}</span></td>
            <td><strong>${escapeHtml(o.center_name || 'Unassigned')}</strong><br><small style="color: var(--text-muted);">${o.center_code || ''}</small></td>
            <td>${escapeHtml(o.district || '-')}</td>
            <td>${escapeHtml(o.phone)}<br><small style="color: var(--text-muted);">${escapeHtml(o.email || '')}</small></td>
            <td><span class="badge ${o.is_active ? 'badge-live' : 'badge-danger'}">${o.is_active ? 'Active' : 'Suspended'}</span></td>
            <td>
                <div style="display: flex; gap: 6px; align-items: center;">
                    <button class="btn btn-outline btn-sm" style="padding: 6px 10px; font-size: 0.95rem; min-height: 32px; border-radius: 6px;" onclick="openAdminEditOfficialModal(${o.id})" title="Edit Central Office User" aria-label="Edit User">
                        ✏️
                    </button>
                    <button class="btn btn-danger btn-sm" style="padding: 6px 10px; font-size: 0.95rem; min-height: 32px; border-radius: 6px;" onclick="deleteAdminOfficial(${o.id}, '${escapeHtml(o.username)}')" title="Delete Central Office User" aria-label="Delete User">
                        🗑️
                    </button>
                </div>
            </td>
        </tr>
    `).join('');
}

function filterAdminOfficialsTable() {
    const searchInp = document.getElementById("admin-official-search");
    const q = (searchInp ? searchInp.value : "").toLowerCase().trim();
    if (!adminOfficials) return;
    const filtered = adminOfficials.filter(o =>
        (o.username && o.username.toLowerCase().includes(q)) ||
        (o.full_name && o.full_name.toLowerCase().includes(q)) ||
        (o.designation && o.designation.toLowerCase().includes(q)) ||
        (o.center_name && o.center_name.toLowerCase().includes(q)) ||
        (o.center_code && o.center_code.toLowerCase().includes(q)) ||
        (o.district && o.district.toLowerCase().includes(q)) ||
        (o.phone && o.phone.toLowerCase().includes(q)) ||
        (o.email && o.email.toLowerCase().includes(q))
    );
    renderAdminOfficialsTable(filtered);
}

function switchAdminTab(tabName) {
    const tabs = ["analytics", "centers", "officials", "approvals", "users"];
    tabs.forEach(t => {
        const btn = document.getElementById(`btn-tab-${t}`);
        const pane = document.getElementById(`tab-pane-${t}`);
        if (btn) {
            if (t === tabName) btn.classList.add("active");
            else btn.classList.remove("active");
        }
        if (pane) {
            if (t === tabName) pane.classList.add("active");
            else pane.classList.remove("active");
        }
    });

    try {
        const url = new URL(window.location);
        url.searchParams.set("tab", tabName);
        window.history.replaceState(null, null, url.toString());
    } catch (e) {}

    if (tabName === "centers") {
        loadCentersTable();
        loadAdminSchedules();
    } else if (tabName === "officials") {
        loadAdminOfficials();
    } else if (tabName === "approvals") {
        loadAdminFarmers();
    } else if (tabName === "users") {
        loadUsers();
    }
}

async function ensureCentersDropdownPopulated() {
    if (!adminCenters || adminCenters.length === 0) {
        try {
            adminCenters = await App.fetch("/api/admin/centers");
        } catch (e) {
            console.error("Failed to load centers for officials dropdown:", e);
        }
    }
    const createSelect = document.getElementById("admin-official-create-center");
    if (createSelect && adminCenters && adminCenters.length > 0) {
        createSelect.innerHTML = `<option value="">Select Procurement Center</option>` +
            adminCenters.map(c => `<option value="${c.id}">${c.name} (${c.district})</option>`).join('');
    }
    const editSelect = document.getElementById("admin-official-edit-center");
    if (editSelect && adminCenters && adminCenters.length > 0) {
        editSelect.innerHTML = `<option value="">Select Procurement Center</option>` +
            adminCenters.map(c => `<option value="${c.id}">${c.name} (${c.district})</option>`).join('');
    }
}

async function openAdminCreateOfficialModal() {
    const modal = document.getElementById("admin-create-official-modal");
    if (modal) {
        const form = document.getElementById("admin-create-official-form");
        if (form) form.reset();
        await ensureCentersDropdownPopulated();
        modal.style.display = "flex";
    }
}

function closeAdminCreateOfficialModal() {
    const modal = document.getElementById("admin-create-official-modal");
    if (modal) modal.style.display = "none";
}

async function handleAdminCreateOfficial(e) {
    e.preventDefault();
    const username = document.getElementById("admin-official-create-username").value.trim();
    const password = document.getElementById("admin-official-create-password").value;
    const fullName = document.getElementById("admin-official-create-fullname").value.trim();
    const phone = document.getElementById("admin-official-create-phone").value.trim();
    const email = document.getElementById("admin-official-create-email").value.trim();
    const centerId = document.getElementById("admin-official-create-center").value;
    const designation = document.getElementById("admin-official-create-designation").value.trim();

    try {
        await App.fetch("/api/admin/officials", {
            method: "POST",
            body: JSON.stringify({
                username,
                password,
                full_name: fullName,
                phone,
                email: email || null,
                center_id: parseInt(centerId),
                designation: designation || "Procurement Officer"
            })
        });

        App.showToast(`Central Office user "${username}" created successfully!`, "success");
        closeAdminCreateOfficialModal();
        await loadAdminOfficials();
        await loadUsers();
    } catch (err) {
        App.showToast(`Failed to create official: ${err.message}`, "alert");
    }
}

async function openAdminEditOfficialModal(officialId) {
    const official = adminOfficials.find(o => o.id === officialId);
    if (!official) return;

    await ensureCentersDropdownPopulated();

    document.getElementById("admin-official-edit-id").value = official.id;
    document.getElementById("admin-official-edit-username-disp").textContent = official.username;
    document.getElementById("admin-official-edit-fullname").value = official.full_name;
    document.getElementById("admin-official-edit-phone").value = official.phone;
    document.getElementById("admin-official-edit-email").value = official.email || "";
    document.getElementById("admin-official-edit-center").value = official.center_id;
    document.getElementById("admin-official-edit-designation").value = official.designation || "";
    document.getElementById("admin-official-edit-active").value = official.is_active ? "true" : "false";

    document.getElementById("admin-edit-official-modal").style.display = "flex";
}

function closeAdminEditOfficialModal() {
    const modal = document.getElementById("admin-edit-official-modal");
    if (modal) modal.style.display = "none";
}

async function handleAdminUpdateOfficial(e) {
    e.preventDefault();
    const officialId = document.getElementById("admin-official-edit-id").value;
    const fullName = document.getElementById("admin-official-edit-fullname").value.trim();
    const phone = document.getElementById("admin-official-edit-phone").value.trim();
    const email = document.getElementById("admin-official-edit-email").value.trim();
    const centerId = document.getElementById("admin-official-edit-center").value;
    const designation = document.getElementById("admin-official-edit-designation").value.trim();
    const isActive = document.getElementById("admin-official-edit-active").value === "true";

    try {
        await App.fetch(`/api/admin/officials/${officialId}`, {
            method: "PUT",
            body: JSON.stringify({
                full_name: fullName,
                phone,
                email: email || null,
                center_id: parseInt(centerId),
                designation: designation || null,
                is_active: isActive
            })
        });

        App.showToast("Central Office user updated successfully!", "success");
        closeAdminEditOfficialModal();
        await loadAdminOfficials();
        await loadUsers();
    } catch (err) {
        App.showToast(`Failed to update official: ${err.message}`, "alert");
    }
}

async function deleteAdminOfficial(officialId, username) {
    if (!confirm(`Are you sure you want to delete Central Office user "${username}"? This cannot be undone.`)) return;

    try {
        const res = await App.fetch(`/api/admin/officials/${officialId}`, {
            method: "DELETE"
        });
        App.showToast(res.message || "Central Office user deleted successfully.", "success");
        await loadAdminOfficials();
        await loadUsers();
    } catch (err) {
        App.showToast(`Failed to delete official: ${err.message}`, "alert");
    }
}

// 10. Farmer Approval Queue & Registry
async function loadAdminFarmers() {
    const statusFilter = document.getElementById("admin-farmer-approval-filter") ? document.getElementById("admin-farmer-approval-filter").value : "ALL";
    const centerFilter = document.getElementById("admin-farmer-center-filter") ? document.getElementById("admin-farmer-center-filter").value : "";
    const tbody = document.getElementById("admin-farmers-body");
    if (!adminFarmers || adminFarmers.length === 0) {
        if (tbody) tbody.innerHTML = `<tr><td colspan="8" style="text-align: center; padding: 20px;">Loading farmer registry...</td></tr>`;
    } else {
        renderAdminFarmersTable(adminFarmers);
    }

    try {
        let params = [];
        if (statusFilter && statusFilter !== 'ALL') params.push(`approval_status=${encodeURIComponent(statusFilter)}`);
        if (centerFilter) params.push(`center_id=${encodeURIComponent(centerFilter)}`);
        const qStr = params.length > 0 ? `?${params.join('&')}` : '';

        const url = `/api/admin/farmers${qStr}`;
        const farmers = await App.fetch(url);
        adminFarmers = farmers;

        // Fetch pending count separately so table filtering doesn't zero-out the header badge
        let pendingCount = farmers.filter(f => f.approval_status === "PENDING").length;
        if (statusFilter !== "PENDING" && statusFilter !== "ALL") {
            try {
                const pendingUrl = centerFilter ? `/api/admin/farmers?approval_status=PENDING&center_id=${encodeURIComponent(centerFilter)}` : "/api/admin/farmers?approval_status=PENDING";
                const pendingList = await App.fetch(pendingUrl);
                pendingCount = pendingList.length;
            } catch (e) {}
        }

        const badge = document.getElementById("admin-pending-farmers-badge");
        if (badge) {
            badge.textContent = `${pendingCount} Pending`;
            badge.className = pendingCount > 0 ? "badge badge-warning pulse" : "badge badge-live";
        }
        const tabBadge = document.getElementById("tab-badge-approvals");
        if (tabBadge) {
            tabBadge.textContent = `${pendingCount} Pending`;
            tabBadge.className = pendingCount > 0 ? "tab-badge badge-pending" : "tab-badge";
        }

        // Ensure center dropdown in header is populated if centers exist
        const farmerCenterFilter = document.getElementById("admin-farmer-center-filter");
        if (farmerCenterFilter && (!farmerCenterFilter.children || farmerCenterFilter.children.length <= 1) && adminCenters && adminCenters.length > 0) {
            const currentVal = farmerCenterFilter.value;
            farmerCenterFilter.innerHTML = `<option value="">🏢 All Registered Centers (${adminCenters.length})</option>` +
                adminCenters.map(c => `<option value="${c.id}">🏢 ${c.name} (${c.center_code || c.district})</option>`).join('');
            if (currentVal) farmerCenterFilter.value = currentVal;
        }

        renderAdminFarmersTable(farmers);
    } catch (e) {
        console.error("Failed to load farmers:", e);
        if (tbody && (!adminFarmers || adminFarmers.length === 0)) {
            tbody.innerHTML = `<tr><td colspan="8" style="text-align: center; color: var(--danger-color); padding: 20px;">Failed to load farmers: ${e.message}</td></tr>`;
        }
    }
}

function renderAdminFarmersTable(farmers) {
    const tbody = document.getElementById("admin-farmers-body");
    if (!tbody) return;

    if (!farmers || farmers.length === 0) {
        tbody.innerHTML = `<tr><td colspan="8" style="text-align: center; padding: 24px; color: var(--text-muted);">No farmers found matching the filter criteria.</td></tr>`;
        return;
    }

    tbody.innerHTML = farmers.map(f => {
        let statusBadge = "badge-live";
        if (f.approval_status === "PENDING") statusBadge = "badge-warning";
        else if (f.approval_status === "REJECTED") statusBadge = "badge-danger";

        const acres = f.land_area_acres != null ? f.land_area_acres : (f.land_size_acres != null ? f.land_size_acres : 0);

        return `
            <tr>
                <td><strong style="color: var(--primary-color);">${escapeHtml(f.farmer_code)}</strong></td>
                <td><strong>${escapeHtml(f.full_name)}</strong><br><small style="color: var(--text-muted);">Crop: ${escapeHtml(f.primary_crop || '-')}</small></td>
                <td>📞 ${escapeHtml(f.phone)}<br><small style="color: var(--text-muted);">Aadhaar: ${escapeHtml(f.aadhaar_number || '-')}</small></td>
                <td>${escapeHtml(f.village)}, ${escapeHtml(f.district)}<br><small style="color: var(--text-muted);">${escapeHtml(f.mandal || '')}</small></td>
                <td><strong>${acres}</strong> Acres<br><small style="color: var(--text-muted);">PB: ${escapeHtml(f.passbook_number || '-')}</small></td>
                <td>
                    <div style="font-weight: 600; color: #166534; display: flex; align-items: center; gap: 4px;">
                        🏢 <span>${escapeHtml(f.center_name || 'Not assigned')}</span>
                    </div>
                    ${f.center_code ? `<span class="badge" style="background: #f0fdf4; color: #166534; border: 1px solid #bbf7d0; font-size: 0.72rem; margin-top: 3px; display: inline-block;">${escapeHtml(f.center_code)}</span>` : ''}
                </td>
                <td>
                    <span class="badge ${statusBadge}">${f.approval_status}</span>
                    ${f.approval_status === 'REJECTED' && f.approval_remarks ? `
                        <div style="font-size: 0.75rem; color: #dc2626; margin-top: 4px; max-width: 140px; word-break: break-word;">
                            ${escapeHtml(f.approval_remarks)}
                        </div>
                    ` : ''}
                    ${f.approval_status === 'APPROVED' && f.approved_at ? `
                        <div style="font-size: 0.72rem; color: #16a34a; margin-top: 2px;">
                            ${new Date(f.approved_at).toLocaleDateString()}
                        </div>
                    ` : ''}
                </td>
                <td>
                    <div style="display: flex; gap: 6px; align-items: center;">
                        ${f.approval_status === 'PENDING' ? `
                            <button class="btn btn-success btn-sm" style="padding: 6px 10px; font-size: 0.95rem; min-height: 32px; border-radius: 6px;" onclick="approveFarmer(${f.id}, '${escapeHtml(f.full_name)}')" title="Approve Registration (Unlocks Token Booking)" aria-label="Approve">
                                ✅
                            </button>
                            <button class="btn btn-danger btn-sm" style="padding: 6px 10px; font-size: 0.95rem; min-height: 32px; border-radius: 6px;" onclick="openAdminRejectFarmerModal(${f.id}, '${escapeHtml(f.full_name)}', '${f.farmer_code}')" title="Reject Registration (Lock Booking & Send Alert)" aria-label="Reject">
                                ❌
                            </button>
                        ` : ''}
                        ${f.approval_status === 'REJECTED' ? `
                            <button class="btn btn-outline btn-sm" style="padding: 6px 10px; font-size: 0.95rem; min-height: 32px; border-radius: 6px;" onclick="approveFarmer(${f.id}, '${escapeHtml(f.full_name)}')" title="Re-Approve Farmer Registration" aria-label="Re-Approve">
                                🔄
                            </button>
                        ` : ''}
                        ${f.approval_status === 'APPROVED' ? `
                            <span class="badge badge-live" style="font-size: 0.8rem; font-weight: 600;">Allowed to Book</span>
                        ` : ''}
                    </div>
                </td>
            </tr>
        `;
    }).join('');
}

function filterAdminFarmersTable() {
    const q = (document.getElementById("admin-farmer-search").value || "").toLowerCase().trim();
    const centerFilter = document.getElementById("admin-farmer-center-filter") ? document.getElementById("admin-farmer-center-filter").value : "";
    const statusFilter = document.getElementById("admin-farmer-approval-filter") ? document.getElementById("admin-farmer-approval-filter").value : "ALL";

    const filtered = adminFarmers.filter(f => {
        // Filter by registered center id
        const matchesCenter = !centerFilter || (String(f.center_id) === String(centerFilter));

        // Filter by approval status
        const matchesStatus = !statusFilter || statusFilter === "ALL" || f.approval_status === statusFilter;

        // Search text matching: name, farmer_code, phone, village, district, mandal, center_name, center_code, primary_crop
        const matchesSearch = !q || (
            (f.full_name && f.full_name.toLowerCase().includes(q)) ||
            (f.farmer_code && f.farmer_code.toLowerCase().includes(q)) ||
            (f.phone && f.phone.includes(q)) ||
            (f.village && f.village.toLowerCase().includes(q)) ||
            (f.district && f.district.toLowerCase().includes(q)) ||
            (f.mandal && f.mandal.toLowerCase().includes(q)) ||
            (f.center_name && f.center_name.toLowerCase().includes(q)) ||
            (f.center_code && f.center_code.toLowerCase().includes(q)) ||
            (f.primary_crop && f.primary_crop.toLowerCase().includes(q))
        );

        return matchesCenter && matchesStatus && matchesSearch;
    });
    renderAdminFarmersTable(filtered);
}

async function approveFarmer(farmerId, farmerName) {
    if (!confirm(`Approve registration for farmer "${farmerName}"? This will immediately allow them to book procurement tokens.`)) return;

    try {
        const res = await App.fetch(`/api/admin/farmers/${farmerId}/approve`, {
            method: "PUT"
        });
        App.showToast(res.message || `Farmer ${farmerName} approved successfully!`, "success");
        await loadAdminFarmers();
    } catch (err) {
        App.showToast(`Approval failed: ${err.message}`, "alert");
    }
}

function openAdminRejectFarmerModal(farmerId, farmerName, farmerCode) {
    document.getElementById("admin-reject-farmer-id").value = farmerId;
    document.getElementById("admin-reject-farmer-name").textContent = farmerName;
    document.getElementById("admin-reject-farmer-code").textContent = farmerCode;
    document.getElementById("admin-reject-remarks").value = "";
    document.getElementById("admin-reject-farmer-modal").style.display = "flex";
}

function closeAdminRejectFarmerModal() {
    const modal = document.getElementById("admin-reject-farmer-modal");
    if (modal) modal.style.display = "none";
}

async function handleAdminRejectFarmer(e) {
    e.preventDefault();
    const farmerId = document.getElementById("admin-reject-farmer-id").value;
    const remarks = document.getElementById("admin-reject-remarks").value.trim();

    if (!remarks) {
        App.showToast("Please provide a reason for rejection.", "alert");
        return;
    }

    try {
        const res = await App.fetch(`/api/admin/farmers/${farmerId}/reject`, {
            method: "PUT",
            body: JSON.stringify({ remarks })
        });
        App.showToast(res.message || "Farmer registration rejected and alert notification dispatched.", "info");
        closeAdminRejectFarmerModal();
        await loadAdminFarmers();
    } catch (err) {
        App.showToast(`Rejection failed: ${err.message}`, "alert");
    }
}

async function initAdminPortal() {
    if (!App.checkAuthRedirect("ADMIN")) return;
    try { await loadAdminKPIs(); } catch (e) { console.error("KPIs load error:", e); }
    try { await loadAnalytics(); } catch (e) { console.error("Analytics load error:", e); }
    try { await loadCentersTable(); } catch (e) { console.error("Centers load error:", e); }
    try { await loadAdminCommodities(); } catch (e) { console.error("Commodities load error:", e); }
    try { await loadAdminSchedules(); } catch (e) { console.error("Schedules load error:", e); }
    try { await loadAdminOfficials(); } catch (e) { console.error("Officials load error:", e); }
    try { await loadAdminFarmers(); } catch (e) { console.error("Farmers load error:", e); }
    try { await loadUsers(); } catch (e) { console.error("Users load error:", e); }

    // Auto-select tab if specified via URL parameter or hash
    try {
        const params = new URLSearchParams(window.location.search);
        const tabParam = params.get("tab") || (window.location.hash ? window.location.hash.replace("#", "") : "");
        if (tabParam && ["analytics", "centers", "officials", "approvals", "users"].includes(tabParam)) {
            switchAdminTab(tabParam);
        }
    } catch (e) {}
}

if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", initAdminPortal);
} else {
    initAdminPortal();
}

// Explicit global exposure on window for inline HTML onclick handlers
window.switchAdminTab = switchAdminTab;
window.loadAdminKPIs = loadAdminKPIs;
window.loadAnalytics = loadAnalytics;
window.loadCentersTable = loadCentersTable;
window.loadAdminCommodities = loadAdminCommodities;
window.loadAdminSchedules = loadAdminSchedules;
window.loadAdminOfficials = loadAdminOfficials;
window.loadAdminFarmers = loadAdminFarmers;
window.loadUsers = loadUsers;
window.runCppOptimization = runCppOptimization;
window.runCppSimulation = runCppSimulation;
window.openAdminCreateScheduleModal = openAdminCreateScheduleModal;
window.closeAdminCreateScheduleModal = closeAdminCreateScheduleModal;
window.openAdminEditScheduleModal = openAdminEditScheduleModal;
window.closeAdminEditScheduleModal = closeAdminEditScheduleModal;
window.openAdminCreateOfficialModal = openAdminCreateOfficialModal;
window.closeAdminCreateOfficialModal = closeAdminCreateOfficialModal;
window.handleAdminCreateOfficial = handleAdminCreateOfficial;
window.openAdminEditOfficialModal = openAdminEditOfficialModal;
window.closeAdminEditOfficialModal = closeAdminEditOfficialModal;
window.handleAdminUpdateOfficial = handleAdminUpdateOfficial;
window.deleteAdminOfficial = deleteAdminOfficial;
window.approveFarmer = approveFarmer;
window.openAdminRejectFarmerModal = openAdminRejectFarmerModal;
window.closeAdminRejectFarmerModal = closeAdminRejectFarmerModal;
window.handleAdminRejectFarmer = handleAdminRejectFarmer;
window.filterAdminFarmersTable = filterAdminFarmersTable;
window.filterAdminFarmers = filterAdminFarmersTable;
window.filterAdminOfficialsTable = filterAdminOfficialsTable;
window.filterAdminOfficials = filterAdminOfficialsTable;
window.toggleUserStatus = toggleUserStatus;

// --- ADMIN PROCUREMENT CENTER CRUD & MAP MODALS ---
function openAdminCreateCenterModal() {
    const form = document.getElementById("admin-create-center-form");
    if (form) form.reset();
    document.getElementById("admin-new-center-start").value = "08:30";
    document.getElementById("admin-new-center-end").value = "17:30";
    document.getElementById("admin-new-center-capacity").value = "100.0";
    document.getElementById("admin-new-center-counters").value = "2";
    document.getElementById("admin-new-center-proctime").value = "480";
    document.getElementById("admin-new-center-state").value = "Telangana";
    document.getElementById("admin-new-center-status").value = "OPEN";
    document.getElementById("admin-create-center-modal").style.display = "flex";
}

function closeAdminCreateCenterModal() {
    document.getElementById("admin-create-center-modal").style.display = "none";
}

async function handleAdminCreateCenter(event) {
    event.preventDefault();
    const latVal = document.getElementById("admin-new-center-lat").value;
    const lngVal = document.getElementById("admin-new-center-lng").value;
    const payload = {
        center_code: document.getElementById("admin-new-center-code").value.trim(),
        name: document.getElementById("admin-new-center-name").value.trim(),
        district: document.getElementById("admin-new-center-district").value.trim(),
        state: document.getElementById("admin-new-center-state").value.trim() || "Telangana",
        address: document.getElementById("admin-new-center-address").value.trim(),
        contact_phone: document.getElementById("admin-new-center-phone").value.trim(),
        working_hours_start: document.getElementById("admin-new-center-start").value || "08:30:00",
        working_hours_end: document.getElementById("admin-new-center-end").value || "17:30:00",
        daily_capacity_mt: parseFloat(document.getElementById("admin-new-center-capacity").value) || 100.0,
        active_counters: parseInt(document.getElementById("admin-new-center-counters").value) || 2,
        avg_processing_seconds: parseInt(document.getElementById("admin-new-center-proctime").value) || 480,
        status: document.getElementById("admin-new-center-status").value || "OPEN",
        latitude: latVal ? parseFloat(latVal) : null,
        longitude: lngVal ? parseFloat(lngVal) : null
    };

    try {
        await App.fetch("/api/admin/centers", {
            method: "POST",
            body: JSON.stringify(payload)
        });
        App.showToast(`Procurement Center '${payload.name}' created successfully!`, "success");
        closeAdminCreateCenterModal();
        await loadCentersTable();
    } catch (err) {
        App.showToast(err.message || "Failed to create center", "alert");
    }
}

function openAdminEditCenterModal(centerId) {
    const center = adminCenters.find(c => c.id === centerId);
    if (!center) {
        App.showToast("Center not found", "alert");
        return;
    }
    document.getElementById("admin-edit-center-id").value = center.id;
    document.getElementById("admin-edit-center-code").value = center.center_code;
    document.getElementById("admin-edit-center-name").value = center.name;
    document.getElementById("admin-edit-center-district").value = center.district;
    document.getElementById("admin-edit-center-state").value = center.state;
    document.getElementById("admin-edit-center-address").value = center.address;
    document.getElementById("admin-edit-center-phone").value = center.contact_phone;
    document.getElementById("admin-edit-center-start").value = (center.working_hours_start || "08:30").slice(0, 5);
    document.getElementById("admin-edit-center-end").value = (center.working_hours_end || "17:30").slice(0, 5);
    document.getElementById("admin-edit-center-capacity").value = center.daily_capacity_mt;
    document.getElementById("admin-edit-center-counters").value = center.active_counters;
    document.getElementById("admin-edit-center-proctime").value = center.avg_processing_seconds;
    document.getElementById("admin-edit-center-status").value = center.status || "OPEN";
    document.getElementById("admin-edit-center-lat").value = center.latitude !== null && center.latitude !== undefined ? center.latitude : "";
    document.getElementById("admin-edit-center-lng").value = center.longitude !== null && center.longitude !== undefined ? center.longitude : "";
    
    document.getElementById("admin-edit-center-modal").style.display = "flex";
}

function closeAdminEditCenterModal() {
    document.getElementById("admin-edit-center-modal").style.display = "none";
}

async function handleAdminUpdateCenter(event) {
    event.preventDefault();
    const centerId = document.getElementById("admin-edit-center-id").value;
    const latVal = document.getElementById("admin-edit-center-lat").value;
    const lngVal = document.getElementById("admin-edit-center-lng").value;
    const payload = {
        center_code: document.getElementById("admin-edit-center-code").value.trim(),
        name: document.getElementById("admin-edit-center-name").value.trim(),
        district: document.getElementById("admin-edit-center-district").value.trim(),
        state: document.getElementById("admin-edit-center-state").value.trim() || "Telangana",
        address: document.getElementById("admin-edit-center-address").value.trim(),
        contact_phone: document.getElementById("admin-edit-center-phone").value.trim(),
        working_hours_start: document.getElementById("admin-edit-center-start").value || "08:30:00",
        working_hours_end: document.getElementById("admin-edit-center-end").value || "17:30:00",
        daily_capacity_mt: parseFloat(document.getElementById("admin-edit-center-capacity").value),
        active_counters: parseInt(document.getElementById("admin-edit-center-counters").value),
        avg_processing_seconds: parseInt(document.getElementById("admin-edit-center-proctime").value),
        status: document.getElementById("admin-edit-center-status").value,
        latitude: latVal ? parseFloat(latVal) : null,
        longitude: lngVal ? parseFloat(lngVal) : null
    };

    try {
        await App.fetch(`/api/admin/centers/${centerId}`, {
            method: "PUT",
            body: JSON.stringify(payload)
        });
        App.showToast("Procurement Center updated successfully!", "success");
        closeAdminEditCenterModal();
        await loadCentersTable();
    } catch (err) {
        App.showToast(err.message || "Failed to update center", "alert");
    }
}

async function deleteAdminCenter(centerId) {
    const center = adminCenters.find(c => c.id === centerId);
    const centerName = center ? center.name : `Center #${centerId}`;
    if (!confirm(`Are you sure you want to delete or decommission "${centerName}"?\n\nIf it has historical procurement transactions, it will be safely marked as CLOSED to preserve audit records.`)) {
        return;
    }

    try {
        const res = await App.fetch(`/api/admin/centers/${centerId}`, {
            method: "DELETE"
        });
        App.showToast(res.message || "Operation completed successfully", "success");
        await loadCentersTable();
    } catch (err) {
        App.showToast(err.message || "Failed to delete center", "alert");
    }
}

function openAdminCenterMapModal(centerId) {
    const center = adminCenters.find(c => c.id === centerId);
    if (!center || !center.latitude || !center.longitude) {
        App.showToast("GPS coordinates not configured for this center", "alert");
        return;
    }
    const lat = center.latitude;
    const lng = center.longitude;
    document.getElementById("admin-map-title").textContent = center.name;
    document.getElementById("admin-map-address").textContent = `${center.center_code} • ${center.address}`;
    document.getElementById("admin-map-coords").textContent = `GPS: ${Number(lat).toFixed(4)}° N, ${Number(lng).toFixed(4)}° E`;

    const delta = 0.015;
    const bbox = `${lng - delta}%2C${lat - delta}%2C${lng + delta}%2C${lat + delta}`;
    document.getElementById("admin-map-iframe").src = `https://www.openstreetmap.org/export/embed.html?bbox=${bbox}&layer=mapnik&marker=${lat}%2C${lng}`;
    document.getElementById("admin-map-gmaps-link").href = `https://www.google.com/maps/search/?api=1&query=${lat},${lng}`;

    document.getElementById("admin-center-map-modal").style.display = "flex";
}

function closeAdminCenterMapModal() {
    document.getElementById("admin-center-map-modal").style.display = "none";
    document.getElementById("admin-map-iframe").src = "";
}

window.openAdminCreateCenterModal = openAdminCreateCenterModal;
window.closeAdminCreateCenterModal = closeAdminCreateCenterModal;
window.handleAdminCreateCenter = handleAdminCreateCenter;
window.openAdminEditCenterModal = openAdminEditCenterModal;
window.closeAdminEditCenterModal = closeAdminEditCenterModal;
window.handleAdminUpdateCenter = handleAdminUpdateCenter;
window.deleteAdminCenter = deleteAdminCenter;
window.openAdminCenterMapModal = openAdminCenterMapModal;
window.closeAdminCenterMapModal = closeAdminCenterMapModal;


