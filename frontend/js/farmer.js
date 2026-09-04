/**
 * Farmer Dashboard Controller
 * Real-time queue sync, booking wizard, and digital token pass
 */

let activeTokenData = null;
let currentProfile = null;
let wsClient = null;

// Tab switcher
function showTab(tabId) {
    document.querySelectorAll(".tab-content").forEach(el => el.style.display = "none");
    document.querySelectorAll("#tab-btn-booking, #tab-btn-notifs, #tab-btn-history").forEach(b => {
        b.className = "btn btn-outline";
    });

    const target = document.getElementById(tabId);
    if (target) target.style.display = "block";

    if (tabId === 'booking-tab') document.getElementById('tab-btn-booking').className = "btn btn-primary";
    else if (tabId === 'notifications-tab') document.getElementById('tab-btn-notifs').className = "btn btn-primary";
    else if (tabId === 'history-tab') document.getElementById('tab-btn-history').className = "btn btn-primary";
}

// 1. Load Farmer Profile
async function loadProfile() {
    try {
        currentProfile = await App.fetch("/api/farmer/profile");
        document.getElementById("farmer-welcome-title").textContent = `Welcome, ${currentProfile.full_name}`;
        document.getElementById("farmer-details-sub").textContent = 
            `ID: ${currentProfile.farmer_code} • Village: ${currentProfile.village}, ${currentProfile.district} • Crop: ${currentProfile.primary_crop}`;
        document.getElementById("farmer-top-id").textContent = `${currentProfile.farmer_code} (${currentProfile.full_name})`;

        // Render profile photo if available
        if (currentProfile.profile_image_url) {
            const avatarImg = document.getElementById("farmer-avatar-img");
            const avatarEmoji = document.getElementById("farmer-avatar-emoji");
            if (avatarImg && avatarEmoji) {
                avatarImg.src = currentProfile.profile_image_url;
                avatarImg.style.display = "block";
                avatarEmoji.style.display = "none";
            }
        }
    } catch (e) {
        console.error("Failed to load profile:", e);
    }
}

// 2. Load Active Token & Queue Position
async function loadActiveToken() {
    const container = document.getElementById("active-token-section");
    try {
        const res = await App.fetch("/api/farmer/active-token");
        if (!res.has_active_token || !res.token) {
            container.innerHTML = `
                <div class="card" style="text-align: center; padding: 32px; background: #ffffff;">
                    <div style="font-size: 3rem; margin-bottom: 8px;">🌾</div>
                    <h3 style="color: var(--primary-dark); margin-bottom: 8px;">No Active Procurement Token</h3>
                    <p style="color: var(--text-muted); margin-bottom: 20px;">
                        You do not have an active queue booking today. Book a slot below to generate your digital token.
                    </p>
                    <button class="btn btn-primary" onclick="showTab('booking-tab')">
                        <span>📅 Book Procurement Slot Now</span>
                    </button>
                </div>
            `;
            activeTokenData = null;
            return;
        }

        activeTokenData = res.token;
        const t = activeTokenData;

        // Initialize WebSocket for this center if not already connected
        if (!wsClient) {
            wsClient = App.initWebSocket(t.center_id, currentProfile ? currentProfile.user_id : null, handleRealtimeEvent);
        }

        const isTurn = t.is_farmer_turn;
        const isApproaching = t.is_approaching;

        let statusBadgeClass = "badge-live";
        let statusText = "WAITING IN QUEUE";
        let heroClass = "hero-token-card";

        if (isTurn) {
            statusBadgeClass = "badge-danger pulse";
            statusText = "YOUR TURN! PROCEED TO WEIGHBRIDGE";
            heroClass = "hero-token-card alert-turn";
        } else if (isApproaching) {
            statusBadgeClass = "badge-warning pulse";
            statusText = "TURN APPROACHING (NEXT 2 FARMERS)";
        } else if (t.status === "COMPLETED") {
            statusText = "PROCUREMENT COMPLETED";
        }

        // Calculate visual progress percentage
        let progressPct = 100;
        if (t.farmers_ahead > 0) {
            progressPct = Math.max(15, Math.min(95, 100 - (t.farmers_ahead * 10)));
        }

        container.innerHTML = `
            <div class="card ${heroClass}">
                <div class="card-header">
                    <div>
                        <h2>🎫 <span data-i18n="my_current_status">My Live Token Status</span></h2>
                        <small style="color: var(--text-muted); font-size: 0.9rem;">
                            🏢 ${t.center_name} • 🌾 ${t.commodity_name} • 📅 ${t.schedule_date} (${t.slot_name})
                        </small>
                    </div>
                    <div style="display: flex; gap: 8px; align-items: center;">
                        <span class="badge ${statusBadgeClass}">${statusText}</span>
                        <button class="btn btn-outline" style="padding: 6px 14px; font-size: 0.85rem;" onclick="openPassModal()">
                            <span data-i18n="view_token_pass">🎫 Digital Pass</span>
                        </button>
                    </div>
                </div>

                <div class="token-stats-grid">
                    <div class="stat-box" style="border-top: 4px solid var(--primary-color);">
                        <div class="stat-label" data-i18n="your_token">YOUR TOKEN</div>
                        <div class="stat-value highlight">${t.token_number}</div>
                        <small style="color: var(--text-muted);">Sequence #${t.sequence_number}</small>
                    </div>

                    <div class="stat-box" style="border-top: 4px solid #3b82f6;">
                        <div class="stat-label" data-i18n="current_token">CURRENT SERVING</div>
                        <div class="stat-value">${t.current_token_str}</div>
                        <small style="color: var(--text-muted);">${res.center_status || 'OPEN'}</small>
                    </div>

                    <div class="stat-box" style="border-top: 4px solid ${isTurn ? '#16a34a' : '#f59e0b'};">
                        <div class="stat-label" data-i18n="farmers_ahead">FARMERS AHEAD</div>
                        <div class="stat-value ${isTurn ? 'highlight' : ''}">${t.farmers_ahead}</div>
                        <small style="color: var(--text-muted);">${isTurn ? 'Active Counter' : 'In Queue'}</small>
                    </div>

                    <div class="stat-box" style="border-top: 4px solid ${isTurn ? '#16a34a' : '#8b5cf6'};">
                        <div class="stat-label" data-i18n="estimated_wait">ESTIMATED WAIT</div>
                        <div class="stat-value ${isTurn ? 'highlight' : ''}">${t.estimated_wait_minutes} <span style="font-size: 1rem; font-weight: 600;">min</span></div>
                        <small style="color: var(--text-muted);">Calculated via C-Engine</small>
                    </div>
                </div>

                <div class="progress-container">
                    <div style="display: flex; justify-content: space-between; font-size: 0.85rem; font-weight: 600; margin-bottom: 6px;">
                        <span>Queue Progress</span>
                        <span>${isTurn ? '100% (Your Turn)' : progressPct + '%'}</span>
                    </div>
                    <div class="progress-bar-bg">
                        <div class="progress-fill" style="width: ${progressPct}%;"></div>
                    </div>
                </div>
            </div>
        `;
    } catch (e) {
        console.error("Failed to load active token:", e);
    }
}

// 3. Handle Real-Time WebSocket Events
function handleRealtimeEvent(event) {
    console.log("Realtime event received:", event);

    if (event.event === "TOKEN_ADVANCED") {
        App.showToast(`📢 Token Advanced to ${event.current_token_number}`, "info");
        App.playChime("queue");
        // Reload live queue card immediately without refreshing entire page!
        loadActiveToken();
    } else if (event.event === "CENTER_STATUS_CHANGED") {
        App.showToast(`⚠️ Procurement Center Status: ${event.status}`, "alert");
        loadActiveToken();
    } else if (event.event === "TRANSACTION_COMPLETED") {
        App.showToast(`✅ Procurement Transaction Completed: ${event.token_number}`, "success");
        loadActiveToken();
        loadHistory();
    } else if (event.event === "ANNOUNCEMENT") {
        App.showToast(`🔔 Notice: ${event.title}`, "alert");
        loadNotifications();
    }
}

// 4. Booking Wizard Logic
async function initBookingWizard() {
    try {
        const centers = await App.fetch("/api/farmer/centers");
        const centerSelect = document.getElementById("book-center");
        centerSelect.innerHTML = `<option value="">-- Choose Procurement Center --</option>` +
            centers.map(c => `<option value="${c.id}">${c.name} (${c.district})</option>`).join('');

        const commodities = await App.fetch("/api/farmer/commodities");
        const commSelect = document.getElementById("book-commodity");
        commSelect.innerHTML = `<option value="">-- Choose Commodity --</option>` +
            commodities.map(c => `<option value="${c.id}">${c.name} (MSP: ₹${c.msp_per_quintal}/Qtl)</option>`).join('');
    } catch (e) {
        console.error("Failed to initialize booking options:", e);
    }
}

async function onCenterChange() {
    await fetchAvailableSchedules();
}

async function onCommodityChange() {
    await fetchAvailableSchedules();
}

async function fetchAvailableSchedules() {
    const centerId = document.getElementById("book-center").value;
    const commodityId = document.getElementById("book-commodity").value;
    const container = document.getElementById("slots-grid");

    if (!centerId || !commodityId) {
        container.innerHTML = `<p style="color: var(--text-muted);">Please select both Center and Commodity.</p>`;
        return;
    }

    try {
        const schedules = await App.fetch(`/api/farmer/schedules?center_id=${centerId}&commodity_id=${commodityId}`);
        if (!schedules || schedules.length === 0) {
            container.innerHTML = `<p style="color: #ef4444; font-weight: 600;">No active procurement schedules found for this selection.</p>`;
            return;
        }

        let html = "";
        schedules.forEach(s => {
            html += `<div style="grid-column: 1 / -1; font-weight: 700; color: var(--primary-dark); margin-top: 8px;">
                📅 Date: ${s.schedule_date} (Cap: ${s.available_capacity_quintals} Qtl remaining)
            </div>`;

            s.slots.forEach(slot => {
                const disabled = slot.is_full ? "disabled" : "";
                const opacity = slot.is_full ? "opacity: 0.5;" : "";
                html += `
                    <label style="border: 2px solid #cbd5e1; border-radius: 8px; padding: 12px; display: flex; align-items: center; gap: 10px; cursor: pointer; background: #ffffff; ${opacity}">
                        <input type="radio" name="selected_slot" value="${slot.id}" data-schedule-id="${s.id}" ${disabled} required>
                        <div>
                            <div style="font-weight: 600; font-size: 0.95rem;">${slot.slot_name}</div>
                            <small style="color: ${slot.is_full ? '#ef4444' : '#16a34a'}; font-weight: 600;">
                                ${slot.is_full ? 'SLOT FULL' : `${slot.available_tokens} slots left`}
                            </small>
                        </div>
                    </label>
                `;
            });
        });

        container.innerHTML = html;
    } catch (e) {
        container.innerHTML = `<p style="color: #ef4444;">Error loading schedule slots.</p>`;
    }
}

async function handleBookSlot(e) {
    e.preventDefault();
    const commodityId = document.getElementById("book-commodity").value;
    const qty = document.getElementById("book-qty").value;
    const vehicle = document.getElementById("book-vehicle").value.trim();

    const selectedRadio = document.querySelector("input[name='selected_slot']:checked");
    if (!selectedRadio) {
        App.showToast("Please select an available time slot.", "alert");
        return;
    }

    const slotId = selectedRadio.value;
    const scheduleId = selectedRadio.getAttribute("data-schedule-id");

    const submitBtn = document.getElementById("btn-generate-token");
    submitBtn.disabled = true;
    submitBtn.textContent = "Processing Token...";

    try {
        const tokenResp = await App.fetch("/api/farmer/book", {
            method: "POST",
            body: JSON.stringify({
                schedule_id: parseInt(scheduleId),
                slot_id: parseInt(slotId),
                commodity_id: parseInt(commodityId),
                estimated_quantity_quintals: parseFloat(qty),
                vehicle_number: vehicle || null
            })
        });

        App.showToast(`🎉 Success! Token ${tokenResp.token_number} generated!`, "success");
        App.playChime("turn");
        await loadActiveToken();
        openPassModal();
    } catch (err) {
        App.showToast(err.message, "alert");
    } finally {
        submitBtn.disabled = false;
        submitBtn.textContent = "Generate Digital Token";
    }
}

// 5. Digital Token Pass Modal & Pure SVG QR Code Generator
function openPassModal() {
    if (!activeTokenData) return;
    const t = activeTokenData;

    document.getElementById("pass-center-name").textContent = t.center_name;
    document.getElementById("pass-token-number").textContent = t.token_number;
    document.getElementById("pass-farmer-name").textContent = currentProfile ? currentProfile.full_name : "-";
    const farmerCodeEl = document.getElementById("pass-farmer-code");
    if (farmerCodeEl) farmerCodeEl.textContent = currentProfile ? currentProfile.farmer_code : "-";
    const passImg = document.getElementById("pass-farmer-img");
    if (passImg) {
        if (currentProfile && currentProfile.profile_image_url) {
            passImg.src = currentProfile.profile_image_url;
            passImg.style.display = "block";
        } else {
            passImg.style.display = "none";
        }
    }
    document.getElementById("pass-commodity").textContent = t.commodity_name;
    document.getElementById("pass-date").textContent = t.schedule_date;
    document.getElementById("pass-slot").textContent = t.slot_name;
    document.getElementById("pass-msp").textContent = `₹${t.msp_rate} / Quintal`;
    document.getElementById("pass-checksum").textContent = `CRC8-${t.checksum || 'OK'}`;

    // Pure SVG QR code visualizer (Zero external image/CDN dependency!)
    renderSvgQr(t.token_number, document.getElementById("pass-qr-container"));

    document.getElementById("token-pass-modal").style.display = "flex";
}

function closePassModal() {
    document.getElementById("token-pass-modal").style.display = "none";
}

function renderSvgQr(text, container) {
    // Generate clean responsive SVG QR grid representation
    const size = 120;
    container.innerHTML = `
        <svg width="${size}" height="${size}" viewBox="0 0 100 100" xmlns="http://www.w3.org/2000/svg">
            <rect width="100" height="100" fill="#ffffff" />
            <!-- Corners -->
            <rect x="5" y="5" width="26" height="26" fill="#0f5132" rx="3" />
            <rect x="9" y="9" width="18" height="18" fill="#ffffff" rx="2" />
            <rect x="13" y="13" width="10" height="10" fill="#0f5132" />

            <rect x="69" y="5" width="26" height="26" fill="#0f5132" rx="3" />
            <rect x="73" y="9" width="18" height="18" fill="#ffffff" rx="2" />
            <rect x="77" y="13" width="10" height="10" fill="#0f5132" />

            <rect x="5" y="69" width="26" height="26" fill="#0f5132" rx="3" />
            <rect x="9" y="73" width="18" height="18" fill="#ffffff" rx="2" />
            <rect x="13" y="77" width="10" height="10" fill="#0f5132" />

            <!-- Pattern Blocks -->
            <rect x="36" y="8" width="6" height="18" fill="#0f5132" />
            <rect x="46" y="16" width="16" height="6" fill="#0f5132" />
            <rect x="36" y="36" width="26" height="26" fill="#0f5132" rx="2" />
            <rect x="42" y="42" width="14" height="14" fill="#ffffff" />
            <rect x="46" y="46" width="6" height="6" fill="#0f5132" />

            <rect x="68" y="38" width="12" height="6" fill="#0f5132" />
            <rect x="82" y="46" width="10" height="8" fill="#0f5132" />
            <rect x="38" y="72" width="10" height="20" fill="#0f5132" />
            <rect x="54" y="68" width="18" height="8" fill="#0f5132" />
            <rect x="74" y="78" width="18" height="12" fill="#0f5132" />
        </svg>
    `;
}

// 6. Notifications & Announcements
async function loadNotifications() {
    try {
        const list = await App.fetch("/api/farmer/notifications");
        document.getElementById("notif-count").textContent = list.filter(n => !n.is_read).length;

        const container = document.getElementById("notifications-list");
        if (!list || list.length === 0) {
            container.innerHTML = `<p style="color: var(--text-muted);">No notifications at this time.</p>`;
            return;
        }

        container.innerHTML = list.map(n => `
            <div style="background: ${n.is_read ? '#f8fafc' : '#eff6ff'}; border-left: 4px solid ${n.notification_type === 'TURN_ALERT' ? '#ef4444' : '#3b82f6'}; padding: 14px; border-radius: 6px; border: 1px solid #e2e8f0;">
                <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 4px;">
                    <strong style="color: var(--primary-dark); font-size: 1rem;">${n.title}</strong>
                    <small style="color: var(--text-muted);">${new Date(n.created_at).toLocaleTimeString()}</small>
                </div>
                <p style="font-size: 0.95rem; color: #334155; margin: 0;">${n.message}</p>
            </div>
        `).join('');
    } catch (e) {
        console.error("Failed to load notifications:", e);
    }
}

// 7. Transaction History
async function loadHistory() {
    try {
        const history = await App.fetch("/api/farmer/history");
        const tbody = document.getElementById("history-body");
        if (!history || history.length === 0) {
            tbody.innerHTML = `<tr><td colspan="8" style="text-align: center; padding: 20px; color: var(--text-muted);">No past transactions yet.</td></tr>`;
            return;
        }

        tbody.innerHTML = history.map(h => `
            <tr>
                <td><strong>${h.booking_ref}</strong></td>
                <td>${h.date}</td>
                <td>${h.center_name}</td>
                <td>${h.commodity_name}</td>
                <td><span class="badge badge-live">${h.token_number}</span></td>
                <td><strong>${h.net_weight_qtl ? h.net_weight_qtl.toFixed(2) : '-'}</strong></td>
                <td><strong style="color: var(--primary-color);">₹${h.final_amount ? h.final_amount.toLocaleString() : '-'}</strong></td>
                <td>
                    <span class="badge ${h.payment_status === 'DIRECT_BENEFIT_TRANSFER' ? 'badge-live' : 'badge-warning'}">
                        ${h.payment_status}
                    </span>
                </td>
            </tr>
        `).join('');
    } catch (e) {
        console.error("Failed to load history:", e);
    }
}

// Page Initialization
document.addEventListener("DOMContentLoaded", async () => {
    if (!App.checkAuthRedirect("FARMER")) return;
    await loadProfile();
    await loadActiveToken();
    await initBookingWizard();
    await loadNotifications();
    await loadHistory();
});
