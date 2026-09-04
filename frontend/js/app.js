/**
 * Shared Application Utilities & WebSocket Client
 * Rural-optimized, zero external framework dependencies
 */

const App = {
    // Authentication Helpers
    getToken() {
        return localStorage.getItem("sih_procurement_token") || localStorage.getItem("sih_token");
    },
    getUser() {
        const u = localStorage.getItem("sih_procurement_user") || localStorage.getItem("sih_user");
        return u ? JSON.parse(u) : null;
    },
    setAuth(token, user) {
        localStorage.setItem("sih_procurement_token", token);
        localStorage.setItem("sih_procurement_user", JSON.stringify(user));
        localStorage.setItem("sih_token", token);
        localStorage.setItem("sih_user", JSON.stringify(user));
    },
    clearAuth() {
        localStorage.removeItem("sih_procurement_token");
        localStorage.removeItem("sih_procurement_user");
        localStorage.removeItem("sih_token");
        localStorage.removeItem("sih_user");
    },
    logout() {
        this.clearAuth();
        window.location.href = "/index.html";
    },
    checkAuthRedirect(requiredRole = null) {
        const token = this.getToken();
        const user = this.getUser();
        if (!token || !user) {
            window.location.replace(`/index.html?auth_required=true${requiredRole ? `&module=${encodeURIComponent(requiredRole)}` : ''}`);
            return false;
        }
        if (requiredRole && user.role !== requiredRole) {
            window.location.replace(`/index.html?auth_required=true&module=${encodeURIComponent(requiredRole)}&unauthorized_role=true`);
            return false;
        }
        return true;
    },

    // Authenticated API Fetch
    async fetch(url, options = {}) {
        const headers = options.headers || {};
        const token = this.getToken();
        if (token) {
            headers["Authorization"] = `Bearer ${token}`;
        }
        if (!headers["Content-Type"] && !(options.body instanceof FormData)) {
            headers["Content-Type"] = "application/json";
        }
        options.headers = headers;

        try {
            const resp = await fetch(url, options);
            if (resp.status === 401) {
                // If it is an auth attempt (login/register), do NOT reload the page - let caller display error!
                if (!url.includes("/api/auth/")) {
                    this.clearAuth();
                    if (!window.location.pathname.endsWith("index.html") && window.location.pathname !== "/") {
                        window.location.href = "/";
                    }
                    throw new Error("Session expired. Please log in again.");
                }
            }
            if (!resp.ok) {
                const err = await resp.json().catch(() => ({ detail: resp.statusText }));
                throw new Error(err.detail || "Request failed");
            }
            return await resp.json();
        } catch (e) {
            throw e;
        }
    },

    // Synthesized Audio Alerts via Web Audio API (Zero external MP3 asset dependency!)
    playChime(type = "turn") {
        try {
            const AudioContext = window.AudioContext || window.webkitAudioContext;
            if (!AudioContext) return;
            const ctx = new AudioContext();

            if (type === "turn") {
                // High-priority arrival chime: C5 -> E5 -> G5
                const notes = [523.25, 659.25, 783.99, 1046.50];
                notes.forEach((freq, idx) => {
                    const osc = ctx.createOscillator();
                    const gain = ctx.createGain();
                    osc.type = "triangle";
                    osc.frequency.value = freq;
                    gain.gain.setValueAtTime(0.2, ctx.currentTime + idx * 0.15);
                    gain.gain.exponentialRampToValueAtTime(0.001, ctx.currentTime + idx * 0.15 + 0.4);
                    osc.connect(gain);
                    gain.connect(ctx.destination);
                    osc.start(ctx.currentTime + idx * 0.15);
                    osc.stop(ctx.currentTime + idx * 0.15 + 0.45);
                });
            } else {
                // Gentle queue movement chime
                const osc = ctx.createOscillator();
                const gain = ctx.createGain();
                osc.type = "sine";
                osc.frequency.value = 587.33; // D5
                gain.gain.setValueAtTime(0.15, ctx.currentTime);
                gain.gain.exponentialRampToValueAtTime(0.001, ctx.currentTime + 0.3);
                osc.connect(gain);
                gain.connect(ctx.destination);
                osc.start(ctx.currentTime);
                osc.stop(ctx.currentTime + 0.35);
            }
        } catch (e) {
            console.warn("Audio chime prevented by browser auto-play policy:", e);
        }
    },

    // UI Toast Notification Banner
    showToast(message, type = "info") {
        let container = document.getElementById("toast-container");
        if (!container) {
            container = document.createElement("div");
            container.id = "toast-container";
            container.className = "toast-container";
            document.body.appendChild(container);
        }

        const toast = document.createElement("div");
        toast.className = `toast toast-${type}`;
        toast.innerHTML = `
            <div class="toast-content">
                <span class="toast-icon">${type === 'success' ? '✅' : (type === 'alert' ? '🚨' : 'ℹ️')}</span>
                <span>${message}</span>
            </div>
        `;
        container.appendChild(toast);

        setTimeout(() => {
            toast.classList.add("fade-out");
            setTimeout(() => toast.remove(), 400);
        }, 4000);
    },

    // Real-Time WebSocket Client with Reconnect
    initWebSocket(centerId, userId, onEventCallback) {
        const protocol = window.location.protocol === "https:" ? "wss:" : "ws:";
        const wsUrl = `${protocol}//${window.location.host}/ws/live?center_id=${centerId || 1}&user_id=${userId || ''}`;

        let ws = null;
        let reconnectTimer = null;

        function connect() {
            ws = new WebSocket(wsUrl);

            ws.onopen = () => {
                console.log("WebSocket connected to live procurement server.");
                const badge = document.getElementById("ws-status-badge");
                if (badge) {
                    badge.textContent = "LIVE CONNECTED";
                    badge.className = "badge badge-live pulse";
                }
            };

            ws.onmessage = (evt) => {
                try {
                    const data = JSON.parse(evt.data);
                    if (onEventCallback) onEventCallback(data);
                } catch (e) {
                    console.error("Invalid WS message:", evt.data);
                }
            };

            ws.onclose = () => {
                console.warn("WebSocket disconnected. Reconnecting in 3s...");
                const badge = document.getElementById("ws-status-badge");
                if (badge) {
                    badge.textContent = "RECONNECTING...";
                    badge.className = "badge badge-warning";
                }
                clearTimeout(reconnectTimer);
                reconnectTimer = setTimeout(connect, 3000);
            };

            ws.onerror = (err) => {
                console.error("WebSocket encountered error:", err);
                ws.close();
            };
        }

        connect();
        return {
            sendPing: () => {
                if (ws && ws.readyState === WebSocket.OPEN) ws.send("ping");
            }
        };
    }
};
