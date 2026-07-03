// Global fetch interceptor for Authentication
const originalFetch = window.fetch;
window.fetch = async function(resource, init) {
    init = init || {};
    init.headers = init.headers || {};
    
    const token = localStorage.getItem("auth_token");
    if (token) {
        if (init.headers instanceof Headers) {
            init.headers.set("Authorization", `Bearer ${token}`);
        } else if (Array.isArray(init.headers)) {
            const hasAuth = init.headers.some(h => h[0].toLowerCase() === "authorization");
            if (!hasAuth) {
                init.headers.push(["Authorization", `Bearer ${token}`]);
            }
        } else {
            if (!init.headers["Authorization"] && !init.headers["authorization"]) {
                init.headers["Authorization"] = `Bearer ${token}`;
            }
        }
    }
    
    try {
        const response = await originalFetch(resource, init);
        if (response.status === 401) {
            localStorage.removeItem("auth_token");
            localStorage.removeItem("auth_username");
            showAuthScreen(true);
        }
        return response;
    } catch (error) {
        throw error;
    }
};

// Global variables
const API_BASE_URL = ""; 
let activeView = "view-dashboard";
let currentDatasetInfo = null;
let leafletMap = null;
let mapTileLayer = null;
let mapMarkers = [];
let charts = {};
let tableSort = { column: "Opportunity Score", order: "desc" };
let tablePage = 1;
const tablePageSize = 20;

// Scoring config
const scoringWeights = {
    website_missing: 40,
    rating_under_2_5: 20,
    rating_2_5_to_3_49: 15,
    rating_3_5_to_3_99: 10,
    reviews_under_10: 15,
    reviews_10_to_49: 10,
    reviews_50_to_99: 5,
    phone_missing: 5,
    verified_bonus_deduction: 10
};

// Required & Optional columns list matching backend
const REQUIRED_COLS = ["Business Name", "Category", "Rating", "Reviews", "Website", "Phone Number", "Address", "City"];
const OPTIONAL_COLS = [
    "Sub Category", "State", "Pincode", "Latitude", "Longitude", "Email", 
    "Google Maps Link", "Verified Business", "Open Now", "Opening Hours", 
    "Price Level", "Photos Count", "Business Description", "Established Year", 
    "GST Available", "WhatsApp Business", "UPI Accepted", "Google Business Verified"
];

// Document ready
document.addEventListener("DOMContentLoaded", () => {
    initTheme();
    initSidebar();
    initNavigation();
    initModals();
    initFilters();
    initUploader();
    initAuth();
    
    const token = localStorage.getItem("auth_token");
    if (token) {
        showAuthScreen(false);
        checkActiveDataset();
    } else {
        showAuthScreen(true);
    }
});

// Toast System
function showToast(message, type = 'info') {
    const container = document.getElementById("toast-container");
    if (!container) return;
    
    const toast = document.createElement("div");
    toast.className = `toast toast-${type}`;
    
    let iconName = "info";
    if (type === "success") iconName = "check-circle";
    if (type === "error") iconName = "alert-circle";
    
    toast.innerHTML = `
        <i data-lucide="${iconName}"></i>
        <span>${message}</span>
    `;
    container.appendChild(toast);
    if (window.lucide) lucide.createIcons();
    
    // Auto-remove
    setTimeout(() => {
        toast.style.opacity = "0";
        toast.style.transform = "translateY(10px)";
        setTimeout(() => {
            toast.remove();
        }, 300);
    }, 4000);
}

// Sidebar Collapsible State Handler
function initSidebar() {
    const appWrapper = document.getElementById("app-wrapper");
    const btnToggle = document.getElementById("btn-toggle-sidebar");
    const toggleIcon = document.getElementById("sidebar-toggle-icon");
    
    // Read and apply saved state immediately
    const collapsed = localStorage.getItem("sidebar_collapsed") === "true";
    if (collapsed) {
        appWrapper?.classList.add("sidebar-collapsed");
        toggleIcon?.setAttribute("data-lucide", "chevron-right");
    } else {
        appWrapper?.classList.remove("sidebar-collapsed");
        toggleIcon?.setAttribute("data-lucide", "chevron-left");
    }
    if (window.lucide) lucide.createIcons();
    
    btnToggle?.addEventListener("click", () => {
        appWrapper?.classList.toggle("sidebar-collapsed");
        const isCollapsed = appWrapper?.classList.contains("sidebar-collapsed");
        localStorage.setItem("sidebar_collapsed", isCollapsed ? "true" : "false");
        
        toggleIcon?.setAttribute("data-lucide", isCollapsed ? "chevron-right" : "chevron-left");
        if (window.lucide) lucide.createIcons();
        
        // Trigger responsive resize for leaflet map if visible
        setTimeout(() => {
            if (leafletMap) leafletMap.invalidateSize();
        }, 250);
    });
}

// Theme Switcher Handler
function initTheme() {
    const btnToggle = document.getElementById("btn-theme-toggle");
    
    // Read initial theme preference
    const savedTheme = localStorage.getItem("theme") || "dark";
    if (savedTheme === "light") {
        document.body.classList.add("light-theme");
    } else {
        document.body.classList.remove("light-theme");
    }
    
    btnToggle?.addEventListener("click", () => {
        document.body.classList.toggle("light-theme");
        const theme = document.body.classList.contains("light-theme") ? "light" : "dark";
        localStorage.setItem("theme", theme);
        
        // Reconfigure active Leaflet map layer
        if (leafletMap) {
            setMapTileLayer(theme === "light");
        }
        
        // Re-render charts
        if (activeView === "view-dashboard" && currentDatasetInfo) {
            refreshDashboard();
        }
        
        showToast(`Switched to ${theme === "light" ? "Light" : "Dark"} theme`, "info");
    });
}

// KPI animated count-up effect helper
function animateCountUp(element, endValue, duration = 1000) {
    if (!element) return;
    
    let startValue = 0;
    const currentText = element.textContent.replace(/[^\d]/g, '');
    if (currentText) {
        startValue = parseInt(currentText) || 0;
    }
    
    const isPercent = String(endValue).includes("%");
    const isFraction = String(endValue).includes("/");
    
    let endNum = 0;
    let fractionMax = "";
    if (isFraction) {
        const parts = String(endValue).split("/");
        endNum = parseFloat(parts[0]) || 0;
        fractionMax = "/" + parts[1];
    } else {
        endNum = parseFloat(String(endValue).replace(/[^\d.]/g, '')) || 0;
    }
    
    let startTimestamp = null;
    const step = (timestamp) => {
        if (!startTimestamp) startTimestamp = timestamp;
        const progress = Math.min((timestamp - startTimestamp) / duration, 1);
        const currentNum = Math.floor(progress * (endNum - startValue) + startValue);
        
        if (isFraction) {
            element.textContent = currentNum + fractionMax;
        } else if (isPercent) {
            element.textContent = currentNum + "%";
        } else {
            element.textContent = currentNum.toLocaleString();
        }
        
        if (progress < 1) {
            window.requestAnimationFrame(step);
        } else {
            element.textContent = endValue; // lock final formatting
        }
    };
    window.requestAnimationFrame(step);
}

// AUTHENTICATION AND SCREEN TOGGLING
function showAuthScreen(show) {
    const authScreen = document.getElementById("auth-screen");
    const appContainer = document.querySelector(".app-container");
    
    if (show) {
        authScreen.classList.add("active");
        appContainer.style.display = "none";
    } else {
        authScreen.classList.remove("active");
        appContainer.style.display = "flex";
        
        // Populate profile name and dashboard banner greetings
        const username = localStorage.getItem("auth_username") || "Authorized User";
        const displayEl = document.getElementById("user-display-name");
        if (displayEl) {
            displayEl.textContent = username;
        }
        const welcomeUserEl = document.getElementById("welcome-username");
        if (welcomeUserEl) {
            welcomeUserEl.textContent = username;
        }
    }
    if (window.lucide) lucide.createIcons();
}

function initAuth() {
    const tabLogin = document.getElementById("tab-login");
    const tabSignup = document.getElementById("tab-signup");
    const formLogin = document.getElementById("form-login");
    const formSignup = document.getElementById("form-signup");
    
    const loginError = document.getElementById("login-error-msg");
    const signupError = document.getElementById("signup-error-msg");
    const signupSuccess = document.getElementById("signup-success-msg");
    
    // Tab switching
    tabLogin?.addEventListener("click", () => {
        tabLogin.classList.add("active");
        tabSignup.classList.remove("active");
        formLogin.classList.add("active");
        formSignup.classList.remove("active");
        signupError.classList.add("hidden");
        signupSuccess.classList.add("hidden");
    });
    
    tabSignup?.addEventListener("click", () => {
        tabSignup.classList.add("active");
        tabLogin.classList.remove("active");
        formSignup.classList.add("active");
        formLogin.classList.remove("active");
        loginError.classList.add("hidden");
    });
    
    // Login Submit
    formLogin?.addEventListener("submit", (e) => {
        e.preventDefault();
        loginError.classList.add("hidden");
        
        const username = document.getElementById("login-username").value;
        const password = document.getElementById("login-password").value;
        
        fetch(API_BASE_URL + "/api/auth/login", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ username, password })
        })
        .then(res => {
            if (!res.ok) {
                return res.json().then(err => { throw new Error(err.detail || "Login failed") });
            }
            return res.json();
        })
        .then(data => {
            localStorage.setItem("auth_token", data.token);
            localStorage.setItem("auth_username", data.username);
            
            // Clear inputs
            document.getElementById("login-username").value = "";
            document.getElementById("login-password").value = "";
            
            showToast("Successfully logged in", "success");
            showAuthScreen(false);
            
            // Fetch initial dashboard metrics
            checkActiveDataset();
        })
        .catch(err => {
            loginError.textContent = err.message;
            loginError.classList.remove("hidden");
            showToast(err.message, "error");
        });
    });
    
    // Signup Submit
    formSignup?.addEventListener("submit", (e) => {
        e.preventDefault();
        signupError.classList.add("hidden");
        signupSuccess.classList.add("hidden");
        
        const username = document.getElementById("signup-username").value;
        const password = document.getElementById("signup-password").value;
        const confirm = document.getElementById("signup-confirm-password").value;
        
        if (password !== confirm) {
            signupError.textContent = "Passwords do not match";
            signupError.classList.remove("hidden");
            return;
        }
        
        fetch(API_BASE_URL + "/api/auth/signup", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ username, password })
        })
        .then(res => {
            if (!res.ok) {
                return res.json().then(err => { throw new Error(err.detail || "Registration failed") });
            }
            return res.json();
        })
        .then(data => {
            signupSuccess.textContent = "Account created successfully! Switching to Sign In...";
            signupSuccess.classList.remove("hidden");
            showToast("Account created successfully", "success");
            
            // Clear inputs
            document.getElementById("signup-username").value = "";
            document.getElementById("signup-password").value = "";
            document.getElementById("signup-confirm-password").value = "";
            
            setTimeout(() => {
                tabLogin?.click();
            }, 1800);
        })
        .catch(err => {
            signupError.textContent = err.message;
            signupError.classList.remove("hidden");
            showToast(err.message, "error");
        });
    });
    
    // Logout Click
    const btnLogout = document.getElementById("menu-btn-logout");
    btnLogout?.addEventListener("click", (e) => {
        e.preventDefault();
        
        const token = localStorage.getItem("auth_token");
        if (token) {
            fetch(API_BASE_URL + "/api/auth/logout", {
                method: "POST"
            }).finally(() => {
                localStorage.removeItem("auth_token");
                localStorage.removeItem("auth_username");
                showToast("Logged out successfully", "info");
                showAuthScreen(true);
            });
        } else {
            showAuthScreen(true);
        }
    });
}

// 1. NAVIGATION TAB SWITCHING
function initNavigation() {
    const menuItems = document.querySelectorAll(".menu-item");
    menuItems.forEach(item => {
        item.addEventListener("click", (e) => {
            const target = item.getAttribute("data-target");
            if (!target) return; 

            e.preventDefault();
            menuItems.forEach(i => i.classList.remove("active"));
            item.classList.add("active");
            
            activeView = target;
            
            // Toggle view visibility
            document.querySelectorAll(".dashboard-view").forEach(v => v.classList.remove("active"));
            document.getElementById(target)?.classList.add("active");
            
            // Set header title
            const spanEl = item.querySelector("span");
            const title = spanEl ? spanEl.textContent.trim() : item.textContent.trim();
            document.getElementById("current-view-title").textContent = title;
            
            // Trigger refresh depending on view
            if (target === "view-dashboard") {
                refreshDashboard();
            } else if (target === "view-opportunities") {
                refreshOpportunitiesTable();
            } else if (target === "view-inspector") {
                refreshInspector();
            } else if (target === "view-pipeline") {
                refreshPipeline();
            }
        });
    });
}

// 2. MODAL & DEMO GENERATOR DIALOGS
function initModals() {
    const btnOpenGen = document.getElementById("btn-open-generator-modal");
    const genModal = document.getElementById("generator-modal");
    const btnCloseGen = document.getElementById("btn-close-gen-modal");
    const btnCancelGen = document.getElementById("btn-cancel-generation");
    const btnTriggerGen = document.getElementById("btn-trigger-generation");
    const successModal = document.getElementById("success-modal");
    const btnContinueDashboard = document.getElementById("btn-continue-dashboard");
    
    if (btnOpenGen) {
        btnOpenGen.addEventListener("click", () => genModal.classList.add("active"));
    }
    
    const closeGen = () => genModal.classList.remove("active");
    if (btnCloseGen) btnCloseGen.addEventListener("click", closeGen);
    if (btnCancelGen) btnCancelGen.addEventListener("click", closeGen);
    
    if (btnTriggerGen) {
        btnTriggerGen.addEventListener("click", () => {
            closeGen();
            const size = document.querySelector('input[name="demo-size"]:checked').value;
            triggerDemoGeneration(parseInt(size));
        });
    }
    
    if (btnContinueDashboard) {
        btnContinueDashboard.addEventListener("click", () => {
            successModal.classList.remove("active");
            document.querySelector('[data-target="view-dashboard"]').click();
        });
    }
    
    const btnCloseDrawer = document.getElementById("btn-close-drawer");
    const drawer = document.getElementById("business-profile-drawer");
    const overlay = document.getElementById("profile-drawer-overlay");
    
    const closeDrawer = () => drawer.classList.remove("active");
    if (btnCloseDrawer) btnCloseDrawer.addEventListener("click", closeDrawer);
    if (overlay) overlay.addEventListener("click", closeDrawer);
}

function triggerDemoGeneration(size) {
    const progressModal = document.getElementById("progress-modal");
    const progressBar = document.getElementById("progress-bar-element");
    const progressText = document.getElementById("progress-step-text");
    
    progressModal.classList.add("active");
    progressBar.style.width = "0%";
    
    const steps = [
        { pct: 15, text: "Initializing Workspace Environment..." },
        { pct: 35, text: "Creating Indian Business Records..." },
        { pct: 60, text: "Injecting Preprocessing Quality Issues..." },
        { pct: 80, text: "Assembling Geospatial Coordinates..." },
        { pct: 95, text: "Finalizing Dataset Ingestion..." }
    ];
    
    let stepIdx = 0;
    const interval = setInterval(() => {
        if (stepIdx < steps.length) {
            progressBar.style.width = `${steps[stepIdx].pct}%`;
            progressText.textContent = steps[stepIdx].text;
            stepIdx++;
        }
    }, 400);
    
    fetch(API_BASE_URL + "/api/generate", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ record_count: size })
    })
    .then(res => {
        if (!res.ok) throw new Error("Dataset generation failed on server.");
        return res.json();
    })
    .then(data => {
        clearInterval(interval);
        progressBar.style.width = "100%";
        progressText.textContent = "Complete!";
        
        setTimeout(() => {
            progressModal.classList.remove("active");
            showSuccessSummary(data);
            showToast("Demo dataset generated successfully", "success");
            checkActiveDataset(); 
        }, 300);
    })
    .catch(err => {
        clearInterval(interval);
        progressModal.classList.remove("active");
        showToast(err.message, "error");
    });
}

function showSuccessSummary(data) {
    const successModal = document.getElementById("success-modal");
    const container = document.getElementById("success-summary-details");
    
    container.innerHTML = `
        <div class="prop-row"><span>Dataset Size:</span><span class="prop-value">${data.size} Records</span></div>
        <div class="prop-row"><span>Indian Cities:</span><span class="prop-value">${data.cities} Cities</span></div>
        <div class="prop-row"><span>Unique Categories:</span><span class="prop-value">${data.categories} Categories</span></div>
        <h5 style="margin-top:16px; margin-bottom:8px; font-weight:700; font-size:12.5px; color:var(--text-main);">Injected Anomalies Summary:</h5>
        <div class="prop-row"><span>Website Ownership Gap:</span><span class="prop-value" style="color:var(--red); font-weight:600;">${data.no_website} Missing</span></div>
        <div class="prop-row"><span>Duplicate Listings:</span><span class="prop-value">${data.duplicates} Rows</span></div>
        <div class="prop-row"><span>Invalid Customer Ratings:</span><span class="prop-value">${data.invalid_ratings} Clamped</span></div>
        <div class="prop-row"><span>Missing Phone Details:</span><span class="prop-value">${data.missing_phones} Omitted</span></div>
    `;
    successModal.classList.add("active");
}

// 3. GET DATASET STATUS
function checkActiveDataset() {
    fetch(API_BASE_URL + "/api/clean-summary")
    .then(res => res.json())
    .then(data => {
        const indicator = document.getElementById("active-file-indicator");
        if (data.status === "no_data" || !data.final_clean_records) {
            indicator.textContent = "Dataset: No Active Dataset Ingested";
            currentDatasetInfo = null;
            if (activeView === "view-dashboard") {
                document.getElementById("generator-modal").classList.add("active");
            }
        } else {
            indicator.textContent = `Dataset: Loaded (Clean Records: ${data.final_clean_records})`;
            currentDatasetInfo = data;
            
            populateDropdownFilters();
            
            if (activeView === "view-dashboard") {
                refreshDashboard();
            }
        }
    });
}

function populateDropdownFilters() {
    fetch(API_BASE_URL + "/api/charts")
    .then(res => res.json())
    .then(data => {
        if (!data.cities) return;
        
        // Populate Categories
        const catSelect = document.getElementById("filter-category");
        catSelect.innerHTML = '<option value="All">All Categories</option>';
        Object.keys(data.categories || {}).sort().forEach(cat => {
            catSelect.innerHTML += `<option value="${cat}">${cat}</option>`;
        });
        
        // Populate Cities
        const citySelect = document.getElementById("filter-city");
        citySelect.innerHTML = '<option value="All">All Cities</option>';
        Object.keys(data.cities || {}).sort().forEach(city => {
            citySelect.innerHTML += `<option value="${city}">${city}</option>`;
        });
    });
}

// 4. ADVANCED FILTER HANDLING
function initFilters() {
    const filters = ["filter-search", "filter-category", "filter-city", "filter-website", "filter-opportunity"];
    filters.forEach(id => {
        const el = document.getElementById(id);
        if (el) {
            el.addEventListener("change", () => {
                tablePage = 1; 
                if (activeView === "view-opportunities") {
                    refreshOpportunitiesTable();
                } else if (activeView === "view-dashboard") {
                    refreshDashboard();
                }
            });
            if (id === "filter-search") {
                let timeout = null;
                el.addEventListener("keyup", () => {
                    clearTimeout(timeout);
                    timeout = setTimeout(() => {
                        tablePage = 1;
                        if (activeView === "view-opportunities") {
                            refreshOpportunitiesTable();
                        } else if (activeView === "view-dashboard") {
                            refreshDashboard();
                        }
                    }, 400);
                });
            }
        }
    });
    
    const btnReset = document.getElementById("btn-reset-filters");
    if (btnReset) {
        btnReset.addEventListener("click", () => {
            document.getElementById("filter-search").value = "";
            document.getElementById("filter-category").value = "All";
            document.getElementById("filter-city").value = "All";
            document.getElementById("filter-website").value = "All";
            document.getElementById("filter-opportunity").value = "All";
            tablePage = 1;
            refreshOpportunitiesTable();
        });
    }
    
    const formats = ["pdf", "pptx", "excel", "csv"];
    formats.forEach(fmt => {
        const el = document.getElementById(`btn-export-${fmt}`);
        if (el) {
            el.addEventListener("click", () => {
                triggerFileExport(fmt);
            });
        }
        const elTable = document.getElementById(`btn-table-export-${fmt}`);
        if (elTable) {
            elTable.addEventListener("click", () => {
                triggerFileExport(fmt);
            });
        }
    });
}

function getActiveFiltersQuery() {
    const search = document.getElementById("filter-search")?.value || "";
    const category = document.getElementById("filter-category")?.value || "All";
    const city = document.getElementById("filter-city")?.value || "All";
    const website = document.getElementById("filter-website")?.value || "All";
    const opp = document.getElementById("filter-opportunity")?.value || "All";
    
    return `category=${encodeURIComponent(category)}&city=${encodeURIComponent(city)}&website_status=${encodeURIComponent(website)}&opportunity_level=${encodeURIComponent(opp)}&search=${encodeURIComponent(search)}`;
}

function triggerFileExport(format) {
    const queries = getActiveFiltersQuery();
    const baseUrl = API_BASE_URL || window.location.origin;
    const url = baseUrl + `/api/export/${format}?${queries}`;
    
    showToast(`Generating ${format.toUpperCase()} export report...`, "info");
    
    fetch(url)
    .then(res => {
        if (!res.ok) {
            return res.json().then(err => { throw new Error(err.detail || "Export failed") });
        }
        
        let filename = `business_opportunities.${format === 'excel' ? 'xlsx' : format === 'pptx' ? 'pptx' : format}`;
        const disposition = res.headers.get('Content-Disposition');
        if (disposition && disposition.indexOf('filename=') !== -1) {
            const filenameRegex = /filename[^;=\n]*=((['"]).*?\2|[^;\n]*)/;
            const matches = filenameRegex.exec(disposition);
            if (matches != null && matches[1]) { 
                filename = matches[1].replace(/['"]/g, '');
            }
        }
        return res.blob().then(blob => ({ blob, filename }));
    })
    .then(({ blob, filename }) => {
        const blobUrl = window.URL.createObjectURL(blob);
        const link = document.createElement("a");
        link.href = blobUrl;
        link.download = filename;
        document.body.appendChild(link);
        link.click();
        document.body.removeChild(link);
        window.URL.revokeObjectURL(blobUrl);
        
        showToast("Report exported successfully", "success");
    })
    .catch(err => {
        showToast("Export failed: " + err.message, "error");
    });
}

// 5. DATASET UPLOADER
function initUploader() {
    const uploader = document.getElementById("file-uploader");
    const indicator = document.getElementById("upload-status-indicator");
    const successCard = document.getElementById("upload-success-card");
    
    if (uploader) {
        uploader.addEventListener("change", (e) => {
            const file = e.target.files[0];
            if (!file) return;
            
            // Hide previous success card on upload retry
            successCard?.classList.add("hidden");
            
            indicator.style.color = "var(--text-main)";
            indicator.textContent = "Ingesting dataset file on backend server...";
            showToast("Uploading dataset...", "info");
            
            const formData = new FormData();
            formData.append("file", file);
            
            fetch(API_BASE_URL + "/api/upload", {
                method: "POST",
                body: formData
            })
            .then(res => {
                if (!res.ok) return res.json().then(err => { throw new Error(err.detail || "Validation check failed."); });
                return res.json();
            })
            .then(data => {
                if (!data.is_valid) {
                    indicator.style.color = "var(--red)";
                    indicator.innerHTML = `✖ **Validation Error**: Incomplete required columns.<br>Missing columns: ${data.missing_required.join(", ")}`;
                    showToast("Validation check failed: Incomplete columns", "error");
                } else {
                    indicator.style.color = "var(--green)";
                    indicator.innerHTML = `✔ **Uploaded Successfully!** Ingested ${data.total_records} rows. Cleaning complete.`;
                    showToast("Dataset uploaded and processed successfully", "success");
                    
                    // Render Success Summary Card
                    if (successCard) {
                        document.getElementById("success-dataset-name").textContent = file.name;
                        document.getElementById("success-total-businesses").textContent = data.cleaning_stats?.final_clean_records || data.total_records;
                        
                        // Set Upload Time formatted
                        const now = new Date();
                        const timeStr = now.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
                        document.getElementById("success-upload-time").textContent = timeStr;
                        
                        // Query charts API dynamically to gather unique counts
                        fetch(API_BASE_URL + "/api/charts")
                        .then(res => res.json())
                        .then(chartsData => {
                            const catCount = chartsData.categories ? Object.keys(chartsData.categories).length : 0;
                            const cityCount = chartsData.cities ? Object.keys(chartsData.cities).length : 0;
                            document.getElementById("success-categories-count").textContent = catCount + "+";
                            document.getElementById("success-cities-count").textContent = cityCount;
                        })
                        .catch(() => {
                            document.getElementById("success-categories-count").textContent = "Ingested";
                            document.getElementById("success-cities-count").textContent = "Ingested";
                        })
                        .finally(() => {
                            successCard.classList.remove("hidden");
                            if (window.lucide) lucide.createIcons();
                        });
                    }
                    
                    checkActiveDataset();
                }
            })
            .catch(err => {
                indicator.style.color = "var(--red)";
                indicator.textContent = `✖ Upload failed: ${err.message}`;
                showToast("Upload failed: " + err.message, "error");
            });
        });
    }
}

// 6. REFRESH DASHBOARD (KPI, Map, Checklist, Charts, AI Insights)
function refreshDashboard() {
    const queries = getActiveFiltersQuery();
    
    // Fetch KPI and brief summaries
    fetch(API_BASE_URL + `/api/executive-summary?${queries}`)
    .then(res => res.json())
    .then(data => {
        document.getElementById("exec-summary-paragraph").textContent = data.summary_text;
        
        const badgeContainer = document.getElementById("exec-highlight-badges");
        badgeContainer.innerHTML = `
            <span class="highlight-badge"><i data-lucide="building" style="color:var(--indigo);"></i> Total: ${data.total_businesses} Listings</span>
            <span class="highlight-badge"><i data-lucide="map" style="color:var(--blue);"></i> Cities: ${data.total_cities}</span>
            <span class="highlight-badge"><i data-lucide="alert-circle" style="color:var(--red);"></i> Web Gap: ${data.website_gap_percent}%</span>
            <span class="highlight-badge"><i data-lucide="zap" style="color:var(--orange);"></i> Avg Opportunity: ${data.avg_opportunity_score}</span>
            <span class="highlight-badge"><i data-lucide="shield" style="color:var(--green);"></i> Avg Quality: ${data.avg_data_quality_score}</span>
        `;
        if (window.lucide) lucide.createIcons();
        
        const focusCats = document.getElementById("exec-focus-categories");
        if (data.top_categories && data.top_categories.length > 0) {
            focusCats.textContent = data.top_categories.join(", ");
        } else {
            focusCats.textContent = "None";
        }
        
        // Count up numbers
        animateCountUp(document.getElementById("kpi-total-listings"), data.total_businesses);
        animateCountUp(document.getElementById("kpi-website-gap"), `${data.website_gap_percent}%`);
        animateCountUp(document.getElementById("kpi-avg-opp-score"), `${data.avg_opportunity_score}/100`);
        animateCountUp(document.getElementById("kpi-avg-dq-score"), `${data.avg_data_quality_score}/100`);
    });
    
    // Fetch AI insights
    fetch(API_BASE_URL + `/api/insights?${queries}`)
    .then(res => res.json())
    .then(insights => {
        const container = document.getElementById("ai-insights-container");
        container.innerHTML = "";
        
        if (insights.length === 0) {
            container.innerHTML = "<p class='text-muted text-center' style='grid-column: 1/-1;'>No Insights Compiled.</p>";
            return;
        }
        
        insights.forEach(ins => {
            container.innerHTML += `
                <div class="insight-item">
                    <i data-lucide="sparkles" class="insight-icon"></i>
                    <span class="insight-text">${ins}</span>
                </div>
            `;
        });
        if (window.lucide) lucide.createIcons();
    });
    
    // Fetch and populate charts & Leaflet Map markers
    fetch(API_BASE_URL + `/api/charts?${queries}`)
    .then(res => res.json())
    .then(data => {
        const mapContainer = document.getElementById("dashboard-map-container");
        const hasCoords = data.has_coordinates;
                          
        updateFeatureChecklist(data);
        
        if (hasCoords) {
            mapContainer.style.display = "block";
            initLeafletMap();
        } else {
            mapContainer.style.display = "none";
        }
        
        renderBICharts(data);
    });
}

function updateFeatureChecklist(data) {
    const checklist = document.getElementById("feature-checklist-container");
    checklist.innerHTML = "";
    
    const hasDataset = currentDatasetInfo !== null;
    
    const features = [
        { name: "KPI Dashboard", key: "kpi", enabled: hasDataset },
        { name: "Opportunity Analysis", key: "opp", enabled: hasDataset },
        { name: "Charts Gallery", key: "charts", enabled: hasDataset },
        { name: "Download PDF/PPTX Reports", key: "reports", enabled: hasDataset },
        { name: "Opportunity Recommendations", key: "rec", enabled: hasDataset },
        
        { name: "Geospatial Interactive Map", key: "map", enabled: hasDataset && data.has_coordinates },
        { name: "State Analysis Panel", key: "state", enabled: hasDataset && data.states && Object.keys(data.states).length > 0 },
        { name: "Cost Distribution (Price Level)", key: "price", enabled: hasDataset && data.price_levels && Object.keys(data.price_levels).length > 0 },
        { name: "Verified Business Audit", key: "verified", enabled: hasDataset && data.verified_counts && Object.keys(data.verified_counts).length > 0 }
    ];
    
    features.forEach(f => {
        const icon = f.enabled ? "check-circle" : "x-circle";
        const cls = f.enabled ? "enabled" : "disabled";
        const txt = f.enabled ? "Active" : "Omitted (Missing Columns)";
        
        checklist.innerHTML += `
            <li class="${cls}">
                <i data-lucide="${icon}"></i>
                <span><strong>${f.name}</strong>: ${txt}</span>
            </li>
        `;
    });
    if (window.lucide) lucide.createIcons();
}

// 7. LEAFLET INTERACTIVE MAP
function setMapTileLayer(isLight) {
    if (!leafletMap) return;
    if (mapTileLayer) {
        leafletMap.removeLayer(mapTileLayer);
    }
    
    // Use standard OpenStreetMap tiles to show detailed street names and area labels
    const url = "https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png";
    const attrib = '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors';
    
    mapTileLayer = L.tileLayer(url, { attribution: attrib }).addTo(leafletMap);
}

function initLeafletMap() {
    const queries = getActiveFiltersQuery();
    
    fetch(API_BASE_URL + `/api/listings?page_size=200&${queries}`)
    .then(res => res.json())
    .then(data => {
        const listings = data.listings.filter(l => l.Latitude && l.Longitude);
        if (listings.length === 0) return;
        
        const avgLat = listings.reduce((sum, l) => sum + l.Latitude, 0) / listings.length;
        const avgLng = listings.reduce((sum, l) => sum + l.Longitude, 0) / listings.length;
        
        const isLight = document.body.classList.contains("light-theme");
        
        if (!leafletMap) {
            leafletMap = L.map("business-leaflet-map").setView([avgLat, avgLng], 12);
            setMapTileLayer(isLight);
            
            // Listen to leaflet popups open, then render icons inside
            leafletMap.on('popupopen', () => {
                if (window.lucide) lucide.createIcons();
            });
        } else {
            leafletMap.setView([avgLat, avgLng], 12);
            setMapTileLayer(isLight);
            
            mapMarkers.forEach(m => leafletMap.removeLayer(m));
            mapMarkers = [];
        }
        
        listings.forEach(l => {
            let color = "#10b981"; 
            const lvl = l["Opportunity Level"];
            if (lvl === "Excellent Opportunity") color = "#ef4444"; 
            else if (lvl === "High Opportunity") color = "#f59e0b"; 
            else if (lvl === "Medium Opportunity") color = "#eab308"; 
            else if (lvl === "Low Opportunity") color = "#3b82f6"; 
            
            const marker = L.circleMarker([l.Latitude, l.Longitude], {
                radius: 8,
                fillColor: color,
                color: isLight ? "#ffffff" : "#1e293b",
                weight: 1.5,
                opacity: 1,
                fillOpacity: 0.85
            }).addTo(leafletMap);
            
            const safeName = (l['Business Name'] || '').replace(/'/g, "\\'").replace(/"/g, "&quot;");
            const safeCity = (l.City || '').replace(/'/g, "\\'").replace(/"/g, "&quot;");
            
            marker.bindPopup(`
                <div style="font-family:'Inter', sans-serif; font-size:11px; padding:4px; color:var(--text-main);">
                    <strong style="font-size:13px; display:block; margin-bottom:4px; color:var(--text-main);">${l["Business Name"]}</strong>
                    <span style="display:block; color:var(--text-muted); margin-bottom:2px;">Category: ${l.Category}</span>
                    <span style="display:block; color:var(--text-muted); margin-bottom:2px;">City: ${l.City}</span>
                    <span style="display:block; margin-top:6px;"><strong>Opp Score: ${l["Opportunity Score"]}</strong> (${l["Opportunity Level"]})</span>
                    <a href="#" onclick="openBusinessDrawer('${safeName}', '${safeCity}'); return false;" style="display:inline-block; margin-top:8px; color:var(--primary); font-weight:700; text-decoration:none;">View Business Profile →</a>
                </div>
            `);
            
            mapMarkers.push(marker);
        });
    });
}

// 8. RENDER CHART.JS GRAPHICS
function renderBICharts(data) {
    const isLight = document.body.classList.contains("light-theme");
    const gridColor = isLight ? 'rgba(15, 23, 42, 0.08)' : 'rgba(255, 255, 255, 0.08)';
    const textColor = isLight ? '#475569' : '#CBD5E1';
    
    // Set global default color configurations
    Chart.defaults.color = textColor;
    Chart.defaults.borderColor = gridColor;
    Chart.defaults.font.family = "'Inter', sans-serif";
    Chart.defaults.plugins.tooltip.backgroundColor = isLight ? '#FFFFFF' : '#1E293B';
    Chart.defaults.plugins.tooltip.titleColor = isLight ? '#0F172A' : '#F8FAFC';
    Chart.defaults.plugins.tooltip.bodyColor = isLight ? '#475569' : '#CBD5E1';
    Chart.defaults.plugins.tooltip.borderColor = isLight ? 'rgba(15, 23, 42, 0.1)' : 'rgba(255, 255, 255, 0.12)';
    Chart.defaults.plugins.tooltip.borderWidth = 1;
    
    // Destroy previous charts if they exist
    Object.keys(charts).forEach(key => {
        if (charts[key]) charts[key].destroy();
    });
    charts = {};
    
    // --- 1. Website Availability Pie Chart ---
    const ctxWeb = document.getElementById("chart-website-pie")?.getContext("2d");
    if (ctxWeb && data.website_status) {
        charts["website_pie"] = new Chart(ctxWeb, {
            type: 'pie',
            data: {
                labels: Object.keys(data.website_status),
                datasets: [{
                    data: Object.values(data.website_status),
                    backgroundColor: ['#10b981', '#ef4444'],
                    borderColor: isLight ? '#ffffff' : '#1e293b',
                    borderWidth: 2
                }]
            },
            options: { 
                responsive: true, 
                maintainAspectRatio: false,
                plugins: {
                    legend: { labels: { color: textColor } }
                }
            }
        });
    }
    
    // --- 2. Category distribution bar chart ---
    const ctxCat = document.getElementById("chart-category-bar")?.getContext("2d");
    if (ctxCat && data.categories) {
        charts["category_bar"] = new Chart(ctxCat, {
            type: 'bar',
            data: {
                labels: Object.keys(data.categories),
                datasets: [{
                    label: 'Listings Count',
                    data: Object.values(data.categories),
                    backgroundColor: '#2563eb',
                    borderRadius: 4
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                indexAxis: 'y',
                plugins: { legend: { display: false } },
                scales: {
                    x: { grid: { color: gridColor }, ticks: { color: textColor } },
                    y: { grid: { display: false }, ticks: { color: textColor } }
                }
            }
        });
    }
    
    // --- 3. Rating distribution histogram ---
    const ctxRate = document.getElementById("chart-rating-hist")?.getContext("2d");
    if (ctxRate && data.ratings) {
        charts["rating_hist"] = new Chart(ctxRate, {
            type: 'bar',
            data: {
                labels: Object.keys(data.ratings),
                datasets: [{
                    label: 'Count',
                    data: Object.values(data.ratings),
                    backgroundColor: '#10b981',
                    borderRadius: 4
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: { legend: { display: false } },
                scales: {
                    x: { grid: { display: false }, ticks: { color: textColor } },
                    y: { grid: { color: gridColor }, ticks: { color: textColor } }
                }
            }
        });
    }
    
    // --- 4. Reviews Volume distribution ---
    const ctxRev = document.getElementById("chart-reviews-hist")?.getContext("2d");
    if (ctxRev && data.reviews) {
        charts["reviews_hist"] = new Chart(ctxRev, {
            type: 'bar',
            data: {
                labels: Object.keys(data.reviews),
                datasets: [{
                    label: 'Count',
                    data: Object.values(data.reviews),
                    backgroundColor: '#f59e0b',
                    borderRadius: 4
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: { legend: { display: false } },
                scales: {
                    x: { grid: { display: false }, ticks: { color: textColor } },
                    y: { grid: { color: gridColor }, ticks: { color: textColor } }
                }
            }
        });
    }
    
    // --- 5. Opportunity Score histogram ---
    const ctxOpp = document.getElementById("chart-opp-hist")?.getContext("2d");
    if (ctxOpp && data.opportunity_levels) {
        charts["opp_hist"] = new Chart(ctxOpp, {
            type: 'bar',
            data: {
                labels: Object.keys(data.opportunity_levels),
                datasets: [{
                    label: 'Count',
                    data: Object.values(data.opportunity_levels),
                    backgroundColor: '#6366f1',
                    borderRadius: 4
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: { legend: { display: false } },
                scales: {
                    x: { grid: { display: false }, ticks: { color: textColor } },
                    y: { grid: { color: gridColor }, ticks: { color: textColor } }
                }
            }
        });
    }
    
    // --- 6. Opp Score vs Data Quality Scatter ---
    const ctxOppDq = document.getElementById("chart-opp-dq-scatter")?.getContext("2d");
    if (ctxOppDq && data.opp_dq_scatter) {
        const datasets = {};
        data.opp_dq_scatter.forEach(pt => {
            if (!datasets[pt.level]) {
                datasets[pt.level] = [];
            }
            datasets[pt.level].push({ x: pt.x, y: pt.y });
        });
        
        const colorsMap = {
            "Excellent Opportunity": "#ef4444",
            "High Opportunity": "#f59e0b",
            "Medium Opportunity": "#eab308",
            "Low Opportunity": "#3b82f6",
            "Digitally Established": "#10b981"
        };
        
        charts["opp_dq_scatter"] = new Chart(ctxOppDq, {
            type: 'scatter',
            data: {
                datasets: Object.keys(datasets).map(level => ({
                    label: level,
                    data: datasets[level],
                    backgroundColor: colorsMap[level] || '#2563eb',
                    pointRadius: 6
                }))
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                scales: {
                    x: { 
                        title: { display: true, text: "Opportunity Score", color: textColor }, 
                        min: 0, max: 100, 
                        grid: { color: gridColor }, ticks: { color: textColor } 
                    },
                    y: { 
                        title: { display: true, text: "Data Quality Score", color: textColor }, 
                        min: 0, max: 100, 
                        grid: { color: gridColor }, ticks: { color: textColor } 
                    }
                },
                plugins: {
                    legend: { labels: { color: textColor } }
                }
            }
        });
    }
    
    // --- 7. Average Rating by Category ---
    const ctxAvgR = document.getElementById("chart-avg-rating-category")?.getContext("2d");
    if (ctxAvgR && data.avg_rating_category) {
        charts["avg_rating_cat"] = new Chart(ctxAvgR, {
            type: 'bar',
            data: {
                labels: Object.keys(data.avg_rating_category),
                datasets: [{
                    label: 'Avg Rating',
                    data: Object.values(data.avg_rating_category),
                    backgroundColor: '#ec4899',
                    borderRadius: 4
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: { legend: { display: false } },
                scales: {
                    x: { grid: { display: false }, ticks: { color: textColor } },
                    y: { min: 1.0, max: 5.0, grid: { color: gridColor }, ticks: { color: textColor } }
                }
            }
        });
    }
    
    // --- 8. Businesses by City ---
    const ctxCity = document.getElementById("chart-city-bar")?.getContext("2d");
    if (ctxCity && data.cities) {
        charts["city_bar"] = new Chart(ctxCity, {
            type: 'bar',
            data: {
                labels: Object.keys(data.cities),
                datasets: [{
                    label: 'Count',
                    data: Object.values(data.cities),
                    backgroundColor: '#8b5cf6',
                    borderRadius: 4
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: { legend: { display: false } },
                scales: {
                    x: { grid: { display: false }, ticks: { color: textColor } },
                    y: { grid: { color: gridColor }, ticks: { color: textColor } }
                }
            }
        });
    }
    
    // --- 9. Website Status by Category (Stacked) ---
    const ctxStacked = document.getElementById("chart-website-category-stacked")?.getContext("2d");
    if (ctxStacked && data.website_category) {
        const labels = Object.keys(data.website_category);
        const hasWebData = labels.map(c => data.website_category[c]["Has Website"] || 0);
        const noWebData = labels.map(c => data.website_category[c]["No Website"] || 0);
        
        charts["web_cat_stacked"] = new Chart(ctxStacked, {
            type: 'bar',
            data: {
                labels: labels,
                datasets: [
                    { label: 'Has Website', data: hasWebData, backgroundColor: '#10b981', borderRadius: 4 },
                    { label: 'No Website', data: noWebData, backgroundColor: '#ef4444', borderRadius: 4 }
                ]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                scales: {
                    x: { stacked: true, grid: { display: false }, ticks: { color: textColor } },
                    y: { stacked: true, grid: { color: gridColor }, ticks: { color: textColor } }
                },
                plugins: {
                    legend: { labels: { color: textColor } }
                }
            }
        });
    }
    
    // --- 10. Rating vs Reviews Scatter ---
    const ctxScatter = document.getElementById("chart-rating-reviews-scatter")?.getContext("2d");
    if (ctxScatter && data.reviews_rating_scatter) {
        const datasets = {};
        data.reviews_rating_scatter.forEach(pt => {
            if (!datasets[pt.level]) {
                datasets[pt.level] = [];
            }
            datasets[pt.level].push({ x: pt.x, y: pt.y });
        });
        
        const colorsMap = {
            "Excellent Opportunity": "#ef4444",
            "High Opportunity": "#f59e0b",
            "Medium Opportunity": "#eab308",
            "Low Opportunity": "#3b82f6",
            "Digitally Established": "#10b981"
        };
        
        charts["rating_reviews_scatter"] = new Chart(ctxScatter, {
            type: 'scatter',
            data: {
                datasets: Object.keys(datasets).map(level => ({
                    label: level,
                    data: datasets[level],
                    backgroundColor: colorsMap[level] || '#2563eb',
                    pointRadius: 6
                }))
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                scales: {
                    x: { 
                        title: { display: true, text: "Rating (1.0 - 5.0)", color: textColor }, 
                        min: 1.0, max: 5.0, 
                        grid: { color: gridColor }, ticks: { color: textColor } 
                    },
                    y: { 
                        title: { display: true, text: "Reviews Count", color: textColor }, 
                        grid: { color: gridColor }, ticks: { color: textColor } 
                    }
                },
                plugins: {
                    legend: { labels: { color: textColor } }
                }
            }
        });
    }
    
    // --- 11. Top Opportunities Horizontal Bar ---
    const ctxTopO = document.getElementById("chart-top-opps-bar")?.getContext("2d");
    if (ctxTopO && data.top_opportunities) {
        charts["top_opps_bar"] = new Chart(ctxTopO, {
            type: 'bar',
            data: {
                labels: Object.keys(data.top_opportunities),
                datasets: [{
                    label: 'Opportunity Score',
                    data: Object.values(data.top_opportunities),
                    backgroundColor: '#ef4444',
                    borderRadius: 4
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                indexAxis: 'y',
                plugins: { legend: { display: false } },
                scales: {
                    x: { min: 0, max: 100, grid: { color: gridColor }, ticks: { color: textColor } },
                    y: { grid: { display: false }, ticks: { color: textColor } }
                }
            }
        });
    }
    
    // --- 12. State counts (optional Layer 3) ---
    const ctxState = document.getElementById("chart-state-bar")?.getContext("2d");
    const stateWrapper = document.getElementById("chart-state-wrapper");
    if (stateWrapper) {
        if (data.states && Object.keys(data.states).length > 0) {
            stateWrapper.style.display = "block";
            if (ctxState) {
                charts["state_bar"] = new Chart(ctxState, {
                    type: 'bar',
                    data: {
                        labels: Object.keys(data.states),
                        datasets: [{
                            label: 'Count',
                            data: Object.values(data.states),
                            backgroundColor: '#06b6d4',
                            borderRadius: 4
                        }]
                    },
                    options: {
                        responsive: true,
                        maintainAspectRatio: false,
                        plugins: { legend: { display: false } },
                        scales: {
                            x: { grid: { display: false }, ticks: { color: textColor } },
                            y: { grid: { color: gridColor }, ticks: { color: textColor } }
                        }
                    }
                });
            }
        } else {
            stateWrapper.style.display = "none";
        }
    }
}

// 9. TOP OPPORTUNITIES PAGINATED TABLE
function refreshOpportunitiesTable() {
    const queries = getActiveFiltersQuery();
    const sortQ = `sort_by=${encodeURIComponent(tableSort.column)}&sort_order=${tableSort.order}`;
    const baseUrl = API_BASE_URL || window.location.origin;
    const url = baseUrl + `/api/listings?page=${tablePage}&page_size=${tablePageSize}&${sortQ}&${queries}`;
    
    // Add lightweight skeleton inside table body
    const tbody = document.getElementById("opportunities-table-body");
    tbody.innerHTML = `
        <tr>
            <td colspan="8">
                <div class="skeleton-line"></div>
                <div class="skeleton-line"></div>
                <div class="skeleton-line"></div>
            </td>
        </tr>
    `;
    
    return fetch(url)
    .then(res => {
        if (!res.ok) throw new Error(`HTTP error! status: ${res.status}`);
        return res.json();
    })
    .then(data => {
        tbody.innerHTML = "";
        
        if (data.listings.length === 0) {
            tbody.innerHTML = `<tr><td colspan="8" class="text-center">No listings match the current filters.</td></tr>`;
            document.getElementById("pagination-info").textContent = "Showing 0 of 0 entries";
            document.getElementById("btn-prev-page").disabled = true;
            document.getElementById("btn-next-page").disabled = true;
            return;
        }
        
        data.listings.forEach(l => {
            const opp = l["Opportunity Score"];
            const dq = l["Data Quality Score"];
            
            let badgeClass = "badge-established";
            const lvl = l["Opportunity Level"];
            if (lvl === "Excellent Opportunity") badgeClass = "badge-excellent";
            else if (lvl === "High Opportunity") badgeClass = "badge-high";
            else if (lvl === "Medium Opportunity") badgeClass = "badge-medium";
            else if (lvl === "Low Opportunity") badgeClass = "badge-low";
            
            const webBadge = l["Website Status"] === "Has Website" ? "badge-has-web" : "badge-no-web";
            const cleanRating = l.Rating === null ? "N/A" : l.Rating;
            
            const safeName = (l['Business Name'] || '').replace(/'/g, "\\'").replace(/"/g, "&quot;");
            const safeCity = (l.City || '').replace(/'/g, "\\'").replace(/"/g, "&quot;");
            
            tbody.innerHTML += `
                <tr onclick="openBusinessDrawer('${safeName}', '${safeCity}')">
                    <td><strong>${l["Business Name"]}</strong></td>
                    <td>${l.Category}</td>
                    <td>${cleanRating}</td>
                    <td>${l.Reviews}</td>
                    <td><span class="badge ${webBadge}">${l["Website Status"]}</span></td>
                    <td><strong>${opp}</strong> <span class="badge ${badgeClass}">${lvl}</span></td>
                    <td><span class="badge" style="background-color:rgba(255,255,255,0.05); border:1px solid var(--border-color); color:var(--text-main); font-weight:700;">${dq}/100</span></td>
                    <td><small style="color:var(--secondary);">${l["Recommendation Reason"]}</small></td>
                </tr>
            `;
        });
        
        const startEntry = (tablePage - 1) * tablePageSize + 1;
        const endEntry = Math.min(tablePage * tablePageSize, data.total);
        document.getElementById("pagination-info").textContent = `Showing ${startEntry} to ${endEntry} of ${data.total} entries`;
        
        document.getElementById("btn-prev-page").disabled = (tablePage === 1);
        document.getElementById("btn-next-page").disabled = (tablePage >= data.pages);
        document.getElementById("current-page-num").textContent = `Page ${tablePage} of ${data.pages}`;
    });
}

// Table sort listener
const tableHeaders = document.querySelectorAll("#opportunities-table th[data-sort]");
tableHeaders.forEach(th => {
    th.addEventListener("click", () => {
        const col = th.getAttribute("data-sort");
        if (tableSort.column === col) {
            tableSort.order = tableSort.order === "asc" ? "desc" : "asc";
        } else {
            tableSort.column = col;
            tableSort.order = "desc";
        }
        
        // Update sorting arrow symbols in UI using Lucide attributes
        tableHeaders.forEach(header => {
            const arrow = header.querySelector("i");
            if (header === th) {
                arrow.setAttribute("data-lucide", tableSort.order === "asc" ? "chevron-up" : "chevron-down");
            } else {
                arrow.setAttribute("data-lucide", "chevrons-up-down");
            }
        });
        if (window.lucide) lucide.createIcons();
        
        tablePage = 1;
        refreshOpportunitiesTable();
    });
});

// Table pagination listeners
document.getElementById("btn-prev-page")?.addEventListener("click", () => {
    if (tablePage > 1) {
        tablePage--;
        refreshOpportunitiesTable().catch(err => {
            tablePage++; 
            showToast("Could not load page: Check backend connection.", "error");
        });
    }
});
document.getElementById("btn-next-page")?.addEventListener("click", () => {
    tablePage++;
    refreshOpportunitiesTable().catch(err => {
        tablePage--; 
        showToast("Could not load page: Check backend connection.", "error");
    });
});

// 10. BUSINESS PROFILE DRAWER
function openBusinessDrawer(name, city) {
    const drawer = document.getElementById("business-profile-drawer");
    const details = document.getElementById("business-profile-details");
    
    // Add loader spinner inside drawer
    details.innerHTML = `
        <div class="spinner-container">
            <div class="spinner"></div>
        </div>
    `;
    drawer.classList.add("active");
    
    fetch(API_BASE_URL + `/api/listings?search=${encodeURIComponent(name)}&city=${encodeURIComponent(city)}`)
    .then(res => res.json())
    .then(data => {
        if (data.listings.length === 0) return;
        const biz = data.listings[0];
        
        const recs = [];
        if (biz["Website"] === "No Website") {
            recs.push("Create a professional responsive business website.");
            recs.push("Register a custom domain name (e.g. .in or .co.in extension).");
        }
        if (biz.Rating < 4.0 || biz.Reviews < 30) {
            recs.push("Improve customer satisfaction and proactively gather reviews.");
        }
        if (biz["Phone Number"] === "") {
            recs.push("Add and update primary mobile contact details on Google Maps.");
        }
        if (biz["Verified Business"] === "No") {
            recs.push("Verify Business Listing with Google to improve visibility.");
        }
        if (biz["Photos Count"] < 10) {
            recs.push("Upload high-resolution images of products, storefront, and services.");
        }
        if (biz["WhatsApp Business"] === "No") {
            recs.push("Configure a WhatsApp Business API line to automate customer chats.");
        }
        if (biz["UPI Accepted"] === "No") {
            recs.push("Implement scan-to-pay UPI QR codes for frictionless billing.");
        }
        if (biz["GST Available"] === "No") {
            recs.push("Add valid GST details to increase credibility with corporate buyers.");
        }
        
        const hasWeb = biz["Website"] !== "No Website";
        const w_web = !hasWeb ? scoringWeights.website_missing : 0;
        
        let w_rate = 0;
        const rating = biz["Rating"];
        if (rating === null) w_rate = scoringWeights.rating_under_2_5;
        else if (rating < 2.5) w_rate = scoringWeights.rating_under_2_5;
        else if (rating < 3.5) w_rate = scoringWeights.rating_2_5_to_3_49;
        else if (rating < 4.0) w_rate = scoringWeights.rating_3_5_to_3_99;
        
        let w_rev = 0;
        const rev = biz["Reviews"];
        if (rev < 10) w_rev = scoringWeights.reviews_under_10;
        else if (rev < 50) w_rev = scoringWeights.reviews_10_to_49;
        else if (rev < 100) w_rev = scoringWeights.reviews_50_to_99;
        
        const w_phone = biz["Phone Number"] === "" ? scoringWeights.phone_missing : 0;
        
        const cat = biz["Category"];
        let w_cat = 5; 
        const catWeights = {
            "Restaurant": 8, "Cafe": 8, "Sweet Shop": 8, "Bakery": 8,
            "Retail Shop": 8, "Kirana Store": 8, "Garment Store": 8,
            "Electronics Shop": 8, "Mobile Repair Shop": 8, "Salon": 8,
            "Beauty Parlour": 8, "Gym": 8, "Fitness Centre": 8,
            "Medical Clinic": 10, "Hospital": 10, "Dental Clinic": 10,
            "Diagnostic Lab": 10, "Educational Institute": 10, "Coaching Centre": 10,
            "Construction Company": 10, "Interior Designer": 10, "Real Estate Agency": 10,
            "Travel Agency": 6, "Automobile Service Centre": 8, "Hotel": 8,
            "Pharmacy": 10, "Hardware Store": 8, "Service Provider": 5
        };
        if (catWeights[cat]) w_cat = catWeights[cat];
        
        const isVerified = biz["Verified Business"].toLowerCase() === "yes";
        const isExcellent = hasWeb && rating !== null && rating >= 4.2 && rev >= 100;
        const w_bonus = (isVerified && isExcellent) ? -scoringWeights.verified_bonus_deduction : 0;
        
        details.innerHTML = `
            <h4 style="font-size:18px; font-weight:700; color:var(--primary); margin-bottom:4px;">${biz["Business Name"]}</h4>
            <span class="badge ${biz["Website Status"] === "Has Website" ? "badge-has-web" : "badge-no-web"}" style="margin-bottom:12px;">${biz["Website Status"]}</span>
            
            <div class="profile-scores-row" style="margin-bottom:16px;">
                <div class="profile-score-box score-box-indigo">
                    <span style="font-size:11px; font-weight:600; text-transform:uppercase;">Opportunity Score</span>
                    <span class="score-box-num">${biz["Opportunity Score"]}</span>
                    <span style="font-size:10px; font-weight:500;">${biz["Opportunity Level"]}</span>
                </div>
                <div class="profile-score-box score-box-green">
                    <span style="font-size:11px; font-weight:600; text-transform:uppercase;">Data Quality Score</span>
                    <span class="score-box-num">${biz["Data Quality Score"]}</span>
                    <span style="font-size:10px; font-weight:500;">Completeness Stats</span>
                </div>
            </div>
            
            <div class="drawer-sec-title">Core Parameters</div>
            <div class="profile-field"><span class="profile-field-label">Category:</span><span class="profile-field-value">${biz["Category"]}</span></div>
            <div class="profile-field"><span class="profile-field-label">Rating:</span><span class="profile-field-value">${biz["Rating"] || 'N/A'} ★</span></div>
            <div class="profile-field"><span class="profile-field-label">Reviews Count:</span><span class="profile-field-value">${biz["Reviews"]} Reviews</span></div>
            <div class="profile-field"><span class="profile-field-label">Mobile Contact:</span><span class="profile-field-value">${biz["Phone Number"] || 'None'}</span></div>
            <div class="profile-field"><span class="profile-field-label">Address:</span><span class="profile-field-value" style="font-size:11.5px; max-width:60%;">${biz["Address"]}</span></div>
            <div class="profile-field"><span class="profile-field-label">City/State:</span><span class="profile-field-value">${biz["City"]} (${biz["State"] || 'N/A'})</span></div>
            
            <div class="drawer-sec-title">Opportunity Weights Breakdown</div>
            <div class="profile-field"><span class="profile-field-label">No Website Weight:</span><span class="profile-field-value">+${w_web}</span></div>
            <div class="profile-field"><span class="profile-field-label">Rating Severity Weight:</span><span class="profile-field-value">+${w_rate}</span></div>
            <div class="profile-field"><span class="profile-field-label">Reviews Volume Weight:</span><span class="profile-field-value">+${w_rev}</span></div>
            <div class="profile-field"><span class="profile-field-label">Missing Mobile Weight:</span><span class="profile-field-value">+${w_phone}</span></div>
            <div class="profile-field"><span class="profile-field-label">Category Weight Priority:</span><span class="profile-field-value">+${w_cat}</span></div>
            <div class="profile-field"><span class="profile-field-label">Verified Business Deduction:</span><span class="profile-field-value">${w_bonus}</span></div>
            <div class="profile-field" style="border-top:1px solid var(--border-color); font-weight:700;"><span class="profile-field-label" style="color:var(--text-main);">Final Score:</span><span class="profile-field-value" style="color:var(--primary); font-size:14px;">${biz["Opportunity Score"]}/100</span></div>
            
            <div class="drawer-sec-title">Suggested Digital Improvements</div>
            <ul class="action-bullets">
                ${recs.map(r => `<li><i data-lucide="chevron-right"></i> <span>${r}</span></li>`).join("")}
            </ul>
        `;
        if (window.lucide) lucide.createIcons();
    });
}

// Expose open drawer function to map popups click events
window.openBusinessDrawer = openBusinessDrawer;

// 11. REFRESH DATASET INSPECTOR
function refreshInspector() {
    if (!currentDatasetInfo) {
        document.getElementById("inspector-properties-list").innerHTML = "<p>No active dataset file ingested. Generating demo dataset is recommended.</p>";
        return;
    }
    
    const props = document.getElementById("inspector-properties-list");
    props.innerHTML = `
        <div class="spinner-container">
            <div class="spinner"></div>
        </div>
    `;
    
    fetch(API_BASE_URL + "/api/clean-summary")
    .then(res => res.json())
    .then(data => {
        props.innerHTML = `
            <div class="prop-row"><span>Ingested File Status:</span><span class="prop-value" style="color:var(--green);">Loaded</span></div>
            <div class="prop-row"><span>Final Clean Records Count:</span><span class="prop-value">${data.final_clean_records} Listings</span></div>
            <div class="prop-row"><span>Original Listings Count:</span><span class="prop-value">${data.original_records} Listings</span></div>
            <div class="prop-row"><span>Ingested Cities:</span><span class="prop-value">India-Focused List</span></div>
        `;
        
        const reqUl = document.getElementById("checklist-required-columns");
        reqUl.innerHTML = "";
        REQUIRED_COLS.forEach(col => {
            reqUl.innerHTML += `<li class="present"><i data-lucide="check-circle"></i> ${col}</li>`;
        });
        
        const optUl = document.getElementById("checklist-optional-columns");
        optUl.innerHTML = "";
        OPTIONAL_COLS.forEach(col => {
            optUl.innerHTML += `<li class="present"><i data-lucide="check-circle"></i> ${col}</li>`;
        });
        if (window.lucide) lucide.createIcons();
    });
}

// 12. REFRESH CLEANING PIPELINE
function refreshPipeline() {
    const statsList = document.getElementById("pipeline-cleaning-stats-list");
    statsList.innerHTML = `
        <div class="spinner-container">
            <div class="spinner"></div>
        </div>
    `;
    
    fetch(API_BASE_URL + "/api/clean-summary")
    .then(res => res.json())
    .then(data => {
        if (data.status === "no_data") {
            statsList.innerHTML = "<p>No cleaning pipeline history. Generate mock dataset.</p>";
            return;
        }
        
        statsList.innerHTML = `
            <div class="prop-row"><span>Original Records Ingested:</span><span class="prop-value">${data.original_records} Rows</span></div>
            <div class="prop-row"><span>Duplicate Records Removed:</span><span class="prop-value" style="color:var(--red); font-weight:600;">${data.duplicates_removed} Rows</span></div>
            <div class="prop-row"><span>Omitted Empty Names:</span><span class="prop-value">${data.empty_names_removed} Rows</span></div>
            <div class="prop-row"><span>Clamped Invalid Customer Ratings:</span><span class="prop-value" style="color:var(--orange);">${data.invalid_ratings_corrected} Corrections</span></div>
            <div class="prop-row"><span>Corrected Negative Customer Reviews:</span><span class="prop-value">${data.negative_reviews_corrected} Rows</span></div>
            <div class="prop-row"><span>Missing Websites Marked 'No Website':</span><span class="prop-value">${data.missing_websites_marked} Listings</span></div>
            <div class="prop-row"><span>Missing Phone Numbers Logged:</span><span class="prop-value">${data.missing_phones_logged} Listings</span></div>
            <div class="prop-row"><span>Standardized Category Names:</span><span class="prop-value">${data.categories_standardized} Spellings</span></div>
            <div class="prop-row" style="border-top:1px solid var(--border-color); font-weight:700; font-size:14px; padding-top:8px;">
                <span>Available Clean Dataset:</span><span class="prop-value" style="color:var(--green);">${data.final_clean_records} Records</span>
            </div>
        `;
        if (window.lucide) lucide.createIcons();
    });
}
