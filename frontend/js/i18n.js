/**
 * SIH 2026 Problem Statement PS ID: 26032
 * Multi-Language Localization System (English, Hindi, Telugu)
 */

const TRANSLATIONS = {
    en: {
        portal_title: "National Digital Agricultural Procurement System",
        portal_subtitle: "Smart India Hackathon 2026 • PS ID: 26032",
        nav_home: "Home",
        nav_farmer: "Farmer Portal",
        nav_official: "Official Portal",
        nav_admin: "Admin Console",
        login_title: "Sign In to Your Account",
        select_role: "Select Your Role",
        role_farmer: "Farmer",
        role_official: "Center Official",
        role_admin: "Administrator",
        username: "Username",
        password: "Password",
        btn_login: "Sign In",
        btn_register: "Register as New Farmer",
        demo_logins: "Quick SIH Demo Access",
        demo_farmer_btn: "👨‍🌾 Demo Farmer (A023 in Queue)",
        demo_official_btn: "🏢 Demo Official (Suryapet CPC)",
        demo_admin_btn: "🏛️ Demo State Administrator",
        my_current_status: "My Live Token Status",
        your_token: "YOUR TOKEN",
        current_token: "CURRENT SERVING",
        farmers_ahead: "FARMERS AHEAD",
        estimated_wait: "ESTIMATED WAIT",
        status_in_queue: "WAITING IN QUEUE",
        status_your_turn: "YOUR TURN! PROCEED TO COUNTER",
        status_processing: "CURRENTLY BEING PROCESSED",
        status_completed: "PROCUREMENT COMPLETED",
        minutes: "min",
        book_slot_title: "Book Procurement Slot",
        select_center: "1. Select Procurement Center",
        select_commodity: "2. Select Commodity",
        select_date_slot: "3. Choose Date & Time Slot",
        estimated_qty: "Estimated Quantity (Quintals)",
        vehicle_num: "Vehicle Number (Optional)",
        btn_confirm_booking: "Generate Digital Token",
        live_queue_title: "Live Center Queue Roster",
        notifications_title: "Alerts & Announcements",
        history_title: "Procurement Transaction History",
        official_dashboard: "Procurement Center Control Room",
        center_status: "Center Operational Status",
        call_next_farmer: "📢 CALL NEXT FARMER",
        mark_processing: "Start Processing",
        complete_weigh: "⚖️ Complete & Weigh",
        skip_farmer: "Skip / No-Show",
        pause_queue: "⏸️ Pause Queue",
        resume_queue: "▶️ Resume Queue",
        today_total: "Today's Total Farmers",
        waiting_count: "Waiting in Queue",
        completed_count: "Completed",
        avg_wait_time: "Avg Wait Time",
        table_token: "Token",
        table_farmer: "Farmer Name",
        table_phone: "Phone",
        table_commodity: "Commodity",
        table_qty: "Qty (Qtl)",
        table_status: "Status",
        table_actions: "Actions",
        admin_dashboard: "State Agricultural Procurement Analytics",
        kpi_farmers: "Total Registered Farmers",
        kpi_centers: "Active Procurement Centers",
        kpi_procured: "Total Procured (Tonnes)",
        kpi_disbursed: "Total DBT Disbursed",
        cpp_optimizer_title: "C++ Workload & Scheduling Optimizer",
        btn_run_cpp_opt: "Run C++ Optimization Model",
        btn_run_cpp_sim: "Run C++ Day Simulation",
        center_management: "Procurement Center Directory",
        user_management: "System Users Management",
        logout: "Sign Out",
        welcome_farmer: "Welcome, Farmer",
        view_token_pass: "🎫 View Digital Token Pass",
        print_pass: "🖨️ Print Pass",
        close: "Close"
    },
    hi: {
        portal_title: "राष्ट्रीय डिजिटल कृषि खरीद प्रणाली",
        portal_subtitle: "स्मार्ट इंडिया हैकाथॉन 2026 • पीएस आईडी: 26032",
        nav_home: "मुख्य पृष्ठ",
        nav_farmer: "किसान पोर्टल",
        nav_official: "अधिकारी पोर्टल",
        nav_admin: "प्रशासन कंसोल",
        login_title: "अपने खाते में लॉग इन करें",
        select_role: "अपनी भूमिका चुनें",
        role_farmer: "किसान",
        role_official: "केंद्र अधिकारी",
        role_admin: "प्रशासक",
        username: "उपयोगकर्ता नाम",
        password: "पासवर्ड",
        btn_login: "लॉग इन करें",
        btn_register: "नए किसान के रूप में पंजीकरण करें",
        demo_logins: "त्वरित एसआईएच डेमो लॉगिन",
        demo_farmer_btn: "👨‍🌾 डेमो किसान (कतार में A023)",
        demo_official_btn: "🏢 डेमो अधिकारी (सूर्यपेट केंद्र)",
        demo_admin_btn: "🏛️ डेमो राज्य प्रशासक",
        my_current_status: "मेरा वर्तमान टोकन विवरण",
        your_token: "आपका टोकन",
        current_token: "वर्तमान चालू टोकन",
        farmers_ahead: "आपके आगे किसान",
        estimated_wait: "अनुमानित प्रतीक्षा समय",
        status_in_queue: "कतार में प्रतीक्षा",
        status_your_turn: "आपकी बारी! काउंटर पर जाएं",
        status_processing: "प्रक्रिया जारी है",
        status_completed: "खरीद पूर्ण हो गई",
        minutes: "मिनट",
        book_slot_title: "खरीद स्लॉट बुक करें",
        select_center: "1. खरीद केंद्र चुनें",
        select_commodity: "2. फसल/जिंस चुनें",
        select_date_slot: "3. दिनांक और समय स्लॉट चुनें",
        estimated_qty: "अनुमानित मात्रा (क्विंटल)",
        vehicle_num: "वाहन संख्या (वैकल्पिक)",
        btn_confirm_booking: "डिजिटल टोकन उत्पन्न करें",
        live_queue_title: "लाइव केंद्र कतार सूची",
        notifications_title: "सूचनाएं और घोषणाएं",
        history_title: "खरीद लेनदेन इतिहास",
        official_dashboard: "खरीद केंद्र नियंत्रण कक्ष",
        center_status: "केंद्र परिचालन स्थिति",
        call_next_farmer: "📢 अगले किसान को बुलाएं",
        mark_processing: "प्रसंस्करण शुरू करें",
        complete_weigh: "⚖️ तौलें और पूर्ण करें",
        skip_farmer: "अनुपस्थित / छोड़ें",
        pause_queue: "⏸️ कतार रोकें",
        resume_queue: "▶️ कतार पुनः चालू करें",
        today_total: "आज के कुल किसान",
        waiting_count: "कतार में प्रतीक्षारत",
        completed_count: "पूर्ण लेनदेन",
        avg_wait_time: "औसत प्रतीक्षा समय",
        table_token: "टोकन",
        table_farmer: "किसान का नाम",
        table_phone: "फोन",
        table_commodity: "फसल",
        table_qty: "मात्रा (क्विंटल)",
        table_status: "स्थिति",
        table_actions: "कार्रवाई",
        admin_dashboard: "राज्य कृषि खरीद विश्लेषिकी",
        kpi_farmers: "कुल पंजीकृत किसान",
        kpi_centers: "सक्रिय खरीद केंद्र",
        kpi_procured: "कुल खरीद (टन)",
        kpi_disbursed: "कुल डीबीटी भुगतान",
        cpp_optimizer_title: "C++ कार्यभार और शेड्यूलिंग अनुकूलक",
        btn_run_cpp_opt: "C++ अनुकूलन मॉडल चलाएं",
        btn_run_cpp_sim: "C++ दिवस सिमुलेशन चलाएं",
        center_management: "खरीद केंद्र प्रबंधन",
        user_management: "उपयोगकर्ता प्रबंधन",
        logout: "लॉग आउट",
        welcome_farmer: "स्वागत है, किसान बंधु",
        view_token_pass: "🎫 डिजिटल टोकन पास देखें",
        print_pass: "🖨️ पास प्रिंट करें",
        close: "बंद करें"
    },
    te: {
        portal_title: "జాతీయ డిజిటల్ వ్యవసాయ సేకరణ వ్యవస్థ",
        portal_subtitle: "స్మార్ట్ ఇండియా హ్యాకథాన్ 2026 • PS ID: 26032",
        nav_home: "హోమ్",
        nav_farmer: "రైతు పోర్టల్",
        nav_official: "అధికారుల పోర్టల్",
        nav_admin: "అడ్మిన్ కన్సోల్",
        login_title: "మీ ఖాతాలోకి లాగిన్ అవ్వండి",
        select_role: "మీ హోదాను ఎంచుకోండి",
        role_farmer: "రైతు",
        role_official: "కేంద్ర అధికారి",
        role_admin: "అడ్మినిస్ట్రేటర్",
        username: "యూజర్ పేరు",
        password: "పాస్వర్డ్",
        btn_login: "లాగిన్ అవ్వండి",
        btn_register: "కొత్త రైతుగా నమోదు చేసుకోండి",
        demo_logins: "త్వరిత SIH డెమో లాగిన్",
        demo_farmer_btn: "👨‍🌾 డెమో రైతు (క్యూలో A023)",
        demo_official_btn: "🏢 డెమో అధికారి (సూర్యాపేట CPC)",
        demo_admin_btn: "🏛️ డెమో రాష్ట్ర అడ్మినిస్ట్రేటర్",
        my_current_status: "నా లైవ్ టోకెన్ వివరాలు",
        your_token: "మీ టోకెన్",
        current_token: "ప్రస్తుత టోకెన్",
        farmers_ahead: "ముందున్న రైతులు",
        estimated_wait: "అంచనా నిరీక్షణ సమయం",
        status_in_queue: "క్యూలో వేచి ఉన్నారు",
        status_your_turn: "మీ వంతు వచ్చింది! కౌంటర్‌కు వెళ్లండి",
        status_processing: "పరిశీలన జరుగుతోంది",
        status_completed: "సేకరణ పూర్తయింది",
        minutes: "నిమిషాలు",
        book_slot_title: "సేకరణ స్లాట్ బుక్ చేసుకోండి",
        select_center: "1. సేకరణ కేంద్రాన్ని ఎంచుకోండి",
        select_commodity: "2. పంట రకాన్ని ఎంచుకోండి",
        select_date_slot: "3. తేదీ & సమయ స్లాట్ ఎంచుకోండి",
        estimated_qty: "అంచనా పరిమాణం (క్వింటాళ్ళు)",
        vehicle_num: "వాహనం నంబర్ (ఐచ్ఛికం)",
        btn_confirm_booking: "డిజిటల్ టోకెన్ రూపొందించండి",
        live_queue_title: "లైవ్ కేంద్రం క్యూ వివరాలు",
        notifications_title: "నోటిఫికేషన్లు & ప్రకటనలు",
        history_title: "గత సేకరణ లావాదేవీల చరిత్ర",
        official_dashboard: "ధాన్యం సేకరణ కేంద్ర నియంత్రణ గది",
        center_status: "కేంద్రం పనితీరు స్థితి",
        call_next_farmer: "📢 తదుపరి రైతును పిలవండి",
        mark_processing: "పరిశీలన ప్రారంభించండి",
        complete_weigh: "⚖️ తూకం వేసి పూర్తి చేయండి",
        skip_farmer: "రానివారు / దాటవేయండి",
        pause_queue: "⏸️ క్యూ నిలపండి",
        resume_queue: "▶️ క్యూ కొనసాగించండి",
        today_total: "నేటి మొత్తం రైతులు",
        waiting_count: "క్యూలో ఉన్నవారు",
        completed_count: "పూర్తయినవి",
        avg_wait_time: "సగటు నిరీక్షణ సమయం",
        table_token: "టోకెన్",
        table_farmer: "రైతు పేరు",
        table_phone: "ఫోన్",
        table_commodity: "పంట",
        table_qty: "పరిమాణం (క్వింటాళ్ళు)",
        table_status: "స్థితి",
        table_actions: "చర్యలు",
        admin_dashboard: "రాష్ట్ర స్థాయి వ్యవసాయ సేకరణ విశ్లేషణ",
        kpi_farmers: "మొత్తం నమోదైన రైతులు",
        kpi_centers: "క్రియాశీల సేకరణ కేంద్రాలు",
        kpi_procured: "మొత్తం సేకరించిన పంట (టన్నులు)",
        kpi_disbursed: "రైతులకు చేరిన మొత్తం DBT సొమ్ము",
        cpp_optimizer_title: "C++ వర్క్‌లోడ్ & షెడ్యూలింగ్ ఆప్టిమైజర్",
        btn_run_cpp_opt: "C++ ఆప్టిమైజేషన్ మోడల్ రన్ చేయండి",
        btn_run_cpp_sim: "C++ డే సిమ్యులేషన్ రన్ చేయండి",
        center_management: "సేకరణ కేంద్రాల నిర్వహణ",
        user_management: "వినియోగదారుల నిర్వహణ",
        logout: "లాగ్ అవుట్",
        welcome_farmer: "రైతు బంధువుకు స్వాగతం",
        view_token_pass: "🎫 డిజిటల్ టోకెన్ పాస్ చూడండి",
        print_pass: "🖨️ పాస్ ప్రింట్ తీసుకోండి",
        close: "మూసివేయి"
    }
};

let currentLang = localStorage.getItem("sih_procurement_lang") || "en";

function t(key) {
    if (TRANSLATIONS[currentLang] && TRANSLATIONS[currentLang][key]) {
        return TRANSLATIONS[currentLang][key];
    }
    if (TRANSLATIONS.en[key]) {
        return TRANSLATIONS.en[key];
    }
    return key;
}

function setLanguage(lang) {
    if (!TRANSLATIONS[lang]) lang = "en";
    currentLang = lang;
    localStorage.setItem("sih_procurement_lang", lang);

    // Update all elements with data-i18n attribute
    document.querySelectorAll("[data-i18n]").forEach(el => {
        const key = el.getAttribute("data-i18n");
        if (TRANSLATIONS[lang] && TRANSLATIONS[lang][key]) {
            el.textContent = TRANSLATIONS[lang][key];
        }
    });

    // Update placeholders
    document.querySelectorAll("[data-i18n-placeholder]").forEach(el => {
        const key = el.getAttribute("data-i18n-placeholder");
        if (TRANSLATIONS[lang] && TRANSLATIONS[lang][key]) {
            el.placeholder = TRANSLATIONS[lang][key];
        }
    });

    // Update active state in language selector
    document.querySelectorAll(".lang-btn").forEach(btn => {
        if (btn.getAttribute("data-lang") === lang) {
            btn.classList.add("active");
        } else {
            btn.classList.remove("active");
        }
    });

    // Notify backend of preference if logged in
    const token = localStorage.getItem("sih_procurement_token");
    if (token) {
        fetch(`/api/farmer/language?lang=${lang}`, {
            method: "PUT",
            headers: { "Authorization": `Bearer ${token}` }
        }).catch(() => {});
    }
}

document.addEventListener("DOMContentLoaded", () => {
    setLanguage(currentLang);
});
