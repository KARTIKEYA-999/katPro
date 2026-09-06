/**
 * Official Control Room Controller
 * Live queue advancing, weighbridge completion, and real-time announcements
 */

let officialCenterId = null;
let currentQueueItems = [];
let officialFarmers = [];
let wsClient = null;

function escapeHtml(str) {
    if (!str) return "";
    return String(str)
        .replace(/&/g, "&amp;")
        .replace(/</g, "&lt;")
        .replace(/>/g, "&gt;")
        .replace(/"/g, "&quot;")
        .replace(/'/g, "&#039;");
}

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

function switchOfficialTab(tabName) {
    const tabs = ["queue", "registry"];
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

    if (tabName === "registry") {
        loadOfficialFarmers();
    } else if (tabName === "queue") {
        loadDashboard();
        loadQueueRoster();
    }
}

// 11. Center Farmer Registry Management
async function loadOfficialFarmers() {
    const tbody = document.getElementById("official-farmers-body");
    if (tbody) tbody.innerHTML = `<tr><td colspan="9" style="text-align: center; padding: 20px;">Loading center farmer registry...</td></tr>`;

    try {
        const farmers = await App.fetch("/api/official/farmers");
        officialFarmers = farmers;

        const badge = document.getElementById("tab-badge-farmers");
        if (badge) badge.textContent = farmers.length;

        // Populate quick certificate download selector
        const quickSelect = document.getElementById("quick-cert-farmer-select");
        if (quickSelect) {
            quickSelect.innerHTML = `<option value="">-- Choose from Enrolled Farmers --</option>` +
                farmers.map(f => `<option value="${f.id}">${f.farmer_code} - ${escapeHtml(f.full_name)} (${f.phone})</option>`).join('');
        }

        renderOfficialFarmersTable(farmers);
    } catch (e) {
        console.error("Failed to load official farmers:", e);
        if (tbody) tbody.innerHTML = `<tr><td colspan="9" style="text-align: center; color: var(--danger-color); padding: 20px;">Failed to load farmers: ${e.message}</td></tr>`;
    }
}

function renderOfficialFarmersTable(farmers) {
    const tbody = document.getElementById("official-farmers-body");
    if (!tbody) return;

    if (!farmers || farmers.length === 0) {
        tbody.innerHTML = `<tr><td colspan="9" style="text-align: center; padding: 24px; color: var(--text-muted);">No farmers enrolled under this procurement center yet. Click "Register New Farmer" to add one.</td></tr>`;
        return;
    }

    tbody.innerHTML = farmers.map(f => {
        let statusBadge = "badge-live";
        if (f.approval_status === "PENDING") statusBadge = "badge-warning";
        else if (f.approval_status === "REJECTED") statusBadge = "badge-danger";

        return `
            <tr id="row-farmer-${f.id}">
                <td><strong style="color: var(--primary-color);">${escapeHtml(f.farmer_code)}</strong></td>
                <td><strong>${escapeHtml(f.full_name)}</strong></td>
                <td>${escapeHtml(f.phone)}</td>
                <td>${escapeHtml(f.aadhaar_number || '-')}</td>
                <td>${escapeHtml(f.village)}, ${escapeHtml(f.mandal || '')}</td>
                <td><strong>${f.land_area_acres}</strong></td>
                <td>${escapeHtml(f.primary_crop || '-')}</td>
                <td>
                    <span class="badge ${statusBadge}">${f.approval_status}</span>
                    ${f.approval_status === 'REJECTED' && f.approval_remarks ? `
                        <div style="font-size: 0.75rem; color: #dc2626; margin-top: 2px;">
                            ${escapeHtml(f.approval_remarks)}
                        </div>
                    ` : ''}
                </td>
                <td>
                    <div style="display: flex; gap: 6px; flex-wrap: wrap;">
                        <button class="btn btn-primary" style="padding: 4px 10px; min-height: 28px; font-size: 0.82rem; font-weight: 600;" onclick="openFarmerRegistrationFormModal(${f.id})">
                            📄 Download Form
                        </button>
                        <button class="btn btn-outline" style="padding: 4px 8px; min-height: 28px; font-size: 0.8rem;" onclick="openOfficialEditFarmerModal(${f.id})">
                            ✏️ Edit
                        </button>
                        <button class="btn btn-danger" style="padding: 4px 8px; min-height: 28px; font-size: 0.8rem;" onclick="deleteOfficialFarmer(${f.id}, '${escapeHtml(f.full_name)}')">
                            🗑️ Delete
                        </button>
                    </div>
                </td>
            </tr>
        `;
    }).join('');
}

function filterOfficialFarmersTable() {
    const q = (document.getElementById("official-farmer-search").value || "").toLowerCase();
    const filtered = officialFarmers.filter(f =>
        f.full_name.toLowerCase().includes(q) ||
        f.farmer_code.toLowerCase().includes(q) ||
        (f.phone && f.phone.includes(q)) ||
        (f.village && f.village.toLowerCase().includes(q))
    );
    renderOfficialFarmersTable(filtered);
}

function openOfficialCreateFarmerModal() {
    const modal = document.getElementById("official-create-farmer-modal");
    if (modal) {
        document.getElementById("official-create-farmer-form").reset();
        modal.style.display = "flex";
    }
}

function closeOfficialCreateFarmerModal() {
    const modal = document.getElementById("official-create-farmer-modal");
    if (modal) modal.style.display = "none";
}

async function handleOfficialCreateFarmer(e) {
    e.preventDefault();
    const username = document.getElementById("official-farmer-create-username").value.trim();
    const password = document.getElementById("official-farmer-create-password").value;
    const fullName = document.getElementById("official-farmer-create-fullname").value.trim();
    const phone = document.getElementById("official-farmer-create-phone").value.trim();
    const email = document.getElementById("official-farmer-create-email").value.trim();
    const aadhaar = document.getElementById("official-farmer-create-aadhaar").value.trim();
    const village = document.getElementById("official-farmer-create-village").value.trim();
    const mandal = document.getElementById("official-farmer-create-mandal").value.trim();
    const district = document.getElementById("official-farmer-create-district").value.trim();
    const land = document.getElementById("official-farmer-create-land").value;
    const passbook = document.getElementById("official-farmer-create-passbook").value.trim();
    const crop = document.getElementById("official-farmer-create-crop").value.trim();
    const bankAcc = document.getElementById("official-farmer-create-bank-acc").value.trim();
    const bankIfsc = document.getElementById("official-farmer-create-bank-ifsc").value.trim();
    const bankName = document.getElementById("official-farmer-create-bank-name").value.trim();

    try {
        await App.fetch("/api/official/farmers", {
            method: "POST",
            body: JSON.stringify({
                username,
                password,
                full_name: fullName,
                phone,
                email: email || null,
                aadhaar_number: aadhaar,
                village,
                mandal,
                district,
                pincode: "508213",
                land_area_acres: parseFloat(land),
                passbook_number: passbook,
                primary_crop: crop,
                bank_account_number: bankAcc,
                bank_ifsc_code: bankIfsc,
                bank_name: bankName
            })
        });

        App.showToast(`Farmer ${fullName} enrolled! Status is PENDING for State Admin approval.`, "success");
        closeOfficialCreateFarmerModal();
        await loadOfficialFarmers();
    } catch (err) {
        App.showToast(`Failed to register farmer: ${err.message}`, "alert");
    }
}

function openOfficialEditFarmerModal(farmerId) {
    const farmer = officialFarmers.find(f => f.id === farmerId);
    if (!farmer) return;

    document.getElementById("official-farmer-edit-id").value = farmer.id;
    document.getElementById("official-farmer-edit-code-disp").textContent = farmer.farmer_code;
    const statusBadge = document.getElementById("official-farmer-edit-status-badge");
    statusBadge.textContent = farmer.approval_status;
    statusBadge.className = farmer.approval_status === "APPROVED" ? "badge badge-live" : (farmer.approval_status === "PENDING" ? "badge badge-warning" : "badge badge-danger");

    document.getElementById("official-farmer-edit-fullname").value = farmer.full_name;
    document.getElementById("official-farmer-edit-phone").value = farmer.phone;
    document.getElementById("official-farmer-edit-village").value = farmer.village;
    document.getElementById("official-farmer-edit-mandal").value = farmer.mandal || "";
    document.getElementById("official-farmer-edit-district").value = farmer.district;
    document.getElementById("official-farmer-edit-land").value = farmer.land_area_acres;
    document.getElementById("official-farmer-edit-passbook").value = farmer.passbook_number || "";
    document.getElementById("official-farmer-edit-crop").value = farmer.primary_crop || "";
    document.getElementById("official-farmer-edit-bank-acc").value = farmer.bank_account_number || "";
    document.getElementById("official-farmer-edit-bank-ifsc").value = farmer.bank_ifsc_code || "";
    document.getElementById("official-farmer-edit-bank-name").value = farmer.bank_name || "";

    document.getElementById("official-edit-farmer-modal").style.display = "flex";
}

function closeOfficialEditFarmerModal() {
    const modal = document.getElementById("official-edit-farmer-modal");
    if (modal) modal.style.display = "none";
}

async function handleOfficialUpdateFarmer(e) {
    e.preventDefault();
    const farmerId = document.getElementById("official-farmer-edit-id").value;
    const fullName = document.getElementById("official-farmer-edit-fullname").value.trim();
    const phone = document.getElementById("official-farmer-edit-phone").value.trim();
    const village = document.getElementById("official-farmer-edit-village").value.trim();
    const mandal = document.getElementById("official-farmer-edit-mandal").value.trim();
    const district = document.getElementById("official-farmer-edit-district").value.trim();
    const land = document.getElementById("official-farmer-edit-land").value;
    const passbook = document.getElementById("official-farmer-edit-passbook").value.trim();
    const crop = document.getElementById("official-farmer-edit-crop").value.trim();
    const bankAcc = document.getElementById("official-farmer-edit-bank-acc").value.trim();
    const bankIfsc = document.getElementById("official-farmer-edit-bank-ifsc").value.trim();
    const bankName = document.getElementById("official-farmer-edit-bank-name").value.trim();

    try {
        await App.fetch(`/api/official/farmers/${farmerId}`, {
            method: "PUT",
            body: JSON.stringify({
                full_name: fullName,
                phone,
                village,
                mandal,
                district,
                land_area_acres: parseFloat(land),
                passbook_number: passbook,
                primary_crop: crop,
                bank_account_number: bankAcc,
                bank_ifsc_code: bankIfsc,
                bank_name: bankName
            })
        });

        App.showToast("Farmer profile updated successfully!", "success");
        closeOfficialEditFarmerModal();
        await loadOfficialFarmers();
    } catch (err) {
        App.showToast(`Failed to update farmer: ${err.message}`, "alert");
    }
}

async function deleteOfficialFarmer(farmerId, farmerName) {
    if (!confirm(`Are you sure you want to delete farmer "${farmerName}"? This will permanently remove their records.`)) return;

    try {
        const res = await App.fetch(`/api/official/farmers/${farmerId}`, {
            method: "DELETE"
        });
        App.showToast(res.message || "Farmer profile removed successfully.", "success");
        await loadOfficialFarmers();
    } catch (err) {
        App.showToast(`Failed to delete farmer: ${err.message}`, "alert");
    }
}

// 12. Printable Registration Form & Certificate
async function openFarmerRegistrationFormModal(farmerId) {
    try {
        const data = await App.fetch(`/api/official/farmers/${farmerId}/form-data`);
        
        document.getElementById("cert-ref-number").textContent = `SIH-REG-${data.farmer_code}`;
        document.getElementById("cert-issue-date").textContent = new Date().toLocaleDateString('en-IN', {
            year: 'numeric', month: 'long', day: 'numeric'
        });

        document.getElementById("cert-farmer-name").textContent = data.full_name;
        document.getElementById("cert-farmer-code").textContent = data.farmer_code;
        document.getElementById("cert-aadhaar").textContent = `XXXX-XXXX-${data.aadhaar_last4}`;
        document.getElementById("cert-phone").textContent = data.phone;
        document.getElementById("cert-village-mandal").textContent = `${data.village}, ${data.mandal || '-'}`;
        document.getElementById("cert-district-state").textContent = `${data.district}, ${data.state}`;
        document.getElementById("cert-land-area").textContent = `${data.land_area_acres} Acres`;
        document.getElementById("cert-passbook").textContent = data.passbook_number || '-';
        document.getElementById("cert-crop").textContent = data.primary_crop || '-';
        document.getElementById("cert-center").textContent = `${data.center_name} (${data.center_code})`;
        document.getElementById("cert-bank-acc").textContent = data.bank_account_number ? `XXXX-XXXX-${data.bank_account_number.slice(-4)}` : '-';
        document.getElementById("cert-bank-ifsc").textContent = `${data.bank_ifsc_code || '-'} (${data.bank_name || '-'})`;

        const statusEl = document.getElementById("cert-approval-status");
        const statusBanner = document.getElementById("cert-status-banner");
        statusEl.textContent = data.approval_status;
        if (data.approval_status === "APPROVED") {
            statusBanner.style.background = "#f0fdf4";
            statusBanner.style.borderColor = "#86efac";
            statusEl.style.color = "#15803d";
        } else if (data.approval_status === "PENDING") {
            statusBanner.style.background = "#fffbeb";
            statusBanner.style.borderColor = "#fde68a";
            statusEl.style.color = "#b45309";
        } else {
            statusBanner.style.background = "#fef2f2";
            statusBanner.style.borderColor = "#fecaca";
            statusEl.style.color = "#b91c1c";
        }

        document.getElementById("cert-approval-remarks").textContent = data.approval_remarks || (data.approval_status === "APPROVED" ? "Verified with Land Revenue (Pahani) Records" : "Pending State Admin Verification");
        document.getElementById("cert-officer-name").textContent = `${data.center_name} Control Room`;
        document.getElementById("cert-sign-date").textContent = `Verified on ${new Date().toLocaleDateString()}`;

        document.getElementById("official-farmer-form-modal").style.display = "flex";
    } catch (err) {
        App.showToast(`Failed to load registration certificate: ${err.message}`, "alert");
    }
}

function closeFarmerRegistrationFormModal() {
    const modal = document.getElementById("official-farmer-form-modal");
    if (modal) modal.style.display = "none";
}

function openQuickDownloadCertModal() {
    const modal = document.getElementById("official-quick-cert-modal");
    if (modal) {
        document.getElementById("quick-cert-farmer-query").value = "";
        modal.style.display = "flex";
    }
}

function closeQuickDownloadCertModal() {
    const modal = document.getElementById("official-quick-cert-modal");
    if (modal) modal.style.display = "none";
}

function onQuickCertFarmerSelect(val) {
    if (val) {
        closeQuickDownloadCertModal();
        openFarmerRegistrationFormModal(parseInt(val));
    }
}

function handleQuickCertSubmit() {
    const select = document.getElementById("quick-cert-farmer-select");
    if (select && select.value) {
        closeQuickDownloadCertModal();
        openFarmerRegistrationFormModal(parseInt(select.value));
        return;
    }

    const query = document.getElementById("quick-cert-farmer-query").value.trim().toLowerCase();
    if (!query) {
        App.showToast("Please select or enter a farmer code, name, or phone number.", "alert");
        return;
    }

    const found = officialFarmers.find(f =>
        f.farmer_code.toLowerCase() === query ||
        (f.phone && f.phone.includes(query)) ||
        f.full_name.toLowerCase().includes(query)
    );

    if (found) {
        closeQuickDownloadCertModal();
        openFarmerRegistrationFormModal(found.id);
    } else {
        App.showToast(`No enrolled farmer found matching "${query}".`, "alert");
    }
}

function openBlankRegistrationForm() {
    closeQuickDownloadCertModal();

    document.getElementById("cert-ref-number").textContent = "SIH-REG-BLANK-FORM";
    document.getElementById("cert-issue-date").textContent = new Date().toLocaleDateString('en-IN', {
        year: 'numeric', month: 'long', day: 'numeric'
    });

    document.getElementById("cert-farmer-name").textContent = "____________________________________";
    document.getElementById("cert-farmer-code").textContent = "FAR-TS-_______________";
    document.getElementById("cert-aadhaar").textContent = "[    ]  [    ]  [    ]  [    ] - [    ]  [    ]  [    ]  [    ] - [    ]  [    ]  [    ]  [    ]";
    document.getElementById("cert-phone").textContent = "+91 __________________";
    document.getElementById("cert-village-mandal").textContent = "____________________, Mandal: ____________________";
    document.getElementById("cert-district-state").textContent = "District: ____________________, State: Telangana";
    document.getElementById("cert-land-area").textContent = "________ Acres (Dry / Wet)";
    document.getElementById("cert-passbook").textContent = "Pattadar PB No: ____________________";
    document.getElementById("cert-crop").textContent = "Paddy / Maize / Cotton / Other: ____________";
    document.getElementById("cert-center").textContent = (officialProfile && officialProfile.center_name) ? officialProfile.center_name : "Central Procurement Center";
    document.getElementById("cert-bank-acc").textContent = "A/c: ____________________________________";
    document.getElementById("cert-bank-ifsc").textContent = "IFSC: ____________________ Bank: ____________________";

    const statusEl = document.getElementById("cert-approval-status");
    const statusBanner = document.getElementById("cert-status-banner");
    statusEl.textContent = "OFFICIAL REGISTRATION APPLICATION";
    statusBanner.style.background = "#f8fafc";
    statusBanner.style.borderColor = "#cbd5e1";
    statusEl.style.color = "#334155";

    document.getElementById("cert-approval-remarks").textContent = "Subject to Revenue (Pahani) and State Admin Verification";
    document.getElementById("official-farmer-form-modal").style.display = "flex";
}

function printFarmerForm() {
    window.print();
}

document.addEventListener("DOMContentLoaded", async () => {
    if (!App.checkAuthRedirect("OFFICIAL")) return;
    await loadDashboard();
    await loadQueueRoster();
    await loadOfficialFarmers();
});

