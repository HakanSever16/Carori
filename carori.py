import gradio as gr
import os
import json
import html
# Grafik sistemi için eklenen kütüphaneler
import pandas as pd
import matplotlib.pyplot as plt
import requests
import concurrent.futures

# ==========================================
# AYARLAR (GRAFİK SİSTEMİ İÇİN)
# ==========================================
# Matplotlib ayarları
plt.rcParams['font.family'] = 'DejaVu Sans'

# Python tarafındaki istekler için API adresi
GRAPH_API_URL = "http://192.168.1.108:3939/fiyat_getir"

BRANDS_MAP = {
    "SHELL": "Shell",
    "OPET": "Opet",
    "PETROL": "Petrol Ofisi", 
    "BP": "BP",
    "TOTAL": "Total"
}

# ==========================================
# HARİTA VE ARAYÜZ OLUŞTURUCU (MEVCUT KOD)
# ==========================================

def load_map_html_with_json(html_path="harita.html", json_path="marka_duzeltme.json"):
    
    # 1. Dosya Kontrolü
    if not os.path.exists(html_path):
        return "<h1>Hata: harita.html dosyası bulunamadı!</h1>"
    
    with open(html_path, "r", encoding="utf-8") as f:
        html_content = f.read()

    # 2. JSON Verisi
    json_veri_string = "{}" 
    if os.path.exists(json_path):
        try:
            with open(json_path, "r", encoding="utf-8") as f:
                data = json.load(f)
                json_veri_string = json.dumps(data, ensure_ascii=False)
        except Exception:
            pass

    target = "var KOORDINAT_DUZELTMELERI = {};"
    replacement = f"var KOORDINAT_DUZELTMELERI = {json_veri_string};"
    html_content = html_content.replace(target, replacement)

    manifest_fix = '<link rel="icon" href="data:,"><link rel="manifest" href="data:application/json;base64,ewp9">'
    if "<head>" in html_content:
        html_content = html_content.replace("<head>", f"<head>{manifest_fix}")

    # --- ARAYÜZ (CSS & JS) ---
    custom_interface = """
    <style>
        /* --- STİLLER AYNI --- */
        body { margin: 0; padding: 0; overflow: hidden; }
        .leaflet-sidebar { z-index: 2000 !important; }
        
        @media (max-width: 768px) {
            .leaflet-sidebar {
                width: 100% !important; max-width: 100% !important;
                left: 0 !important; right: 0 !important; bottom: 0 !important; top: auto !important; 
                height: 60% !important; background: transparent !important;
                box-shadow: none !important; border: none !important; z-index: 99999 !important; pointer-events: none; 
            }
            .leaflet-sidebar-tabs {
                display: flex !important; position: absolute !important; top: -45px !important; 
                left: 0 !important; width: 100% !important; height: 45px !important;
                background-color: white !important; border-top: 1px solid #ccc; border-bottom: 1px solid #ccc;
                margin: 0 !important; padding: 0 !important; justify-content: space-around; align-items: center;
                pointer-events: auto !important; z-index: 100000 !important;
            }
            .leaflet-sidebar-tabs > li { height: 45px !important; width: 45px !important; display: flex !important; align-items: center; justify-content: center; }
            .leaflet-sidebar-tabs > li > a { line-height: 45px !important; font-size: 22px !important; color: #333 !important; }
            .leaflet-sidebar-tabs > li.active > a { color: #c0392b !important; }
            .leaflet-sidebar-content {
                position: absolute !important; top: 0 !important; bottom: 0 !important; width: 100% !important;
                background: white; padding: 15px !important; overflow-y: auto !important;
                border-top: 1px solid #eee; pointer-events: auto !important; display: block; 
            }
            .leaflet-sidebar-content.content-hidden { display: none !important; }
            input[type="text"] { font-size: 16px !important; padding: 12px !important; }
            .landing-container { width: 95% !important; padding: 10px; }
            .hero-title { font-size: 28px !important; }
        }

        #landing-overlay {
            position: fixed; top: 0; left: 0; width: 100%; height: 100%;
            background: linear-gradient(135deg, #2c3e50 0%, #000000 100%);
            z-index: 100000; display: flex; flex-direction: column; align-items: center; justify-content: flex-start;
            padding-top: 80px; overflow-y: auto; color: white; font-family: 'Segoe UI', sans-serif; transition: opacity 0.5s ease;
        }
        .landing-container { width: 90%; max-width: 700px; text-align: center; }
        .hero-title { font-size: 42px; font-weight: bold; margin-bottom: 10px; color: #3498db; }
        .hero-subtitle { font-size: 18px; color: #ecf0f1; margin-bottom: 40px; font-weight: 300; opacity: 0.8; }
        .search-box-wrapper {
            background: rgba(255, 255, 255, 0.1); padding: 30px; border-radius: 20px;
            backdrop-filter: blur(15px); box-shadow: 0 15px 35px rgba(0,0,0,0.3);
            border: 1px solid rgba(255,255,255,0.1);
            display: flex; flex-direction: column; gap: 15px; margin-bottom: 30px; width: 100%; box-sizing: border-box;
        }
        #modelInputLanding { width: 100%; padding: 16px; border-radius: 10px; border: 2px solid transparent; font-size: 18px; outline: none; background: #ffffff; color: #333; box-sizing: border-box; transition: 0.3s; }
        #modelInputLanding:focus { border-color: #3498db; box-shadow: 0 0 15px rgba(52, 152, 219, 0.3); }
        #searchBtnLanding { width: 100%; background: linear-gradient(to right, #e74c3c, #c0392b); color: white; border: none; padding: 16px; border-radius: 10px; font-size: 18px; font-weight: bold; cursor: pointer; transition: transform 0.2s; }
        #searchBtnLanding:hover { transform: translateY(-2px); }
        #results-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(220px, 1fr)); gap: 20px; width: 100%; padding-bottom: 50px; }
        .car-card { background: white; border-radius: 12px; overflow: hidden; cursor: pointer; transition: 0.3s; position: relative; text-align: left; }
        .car-card:hover { transform: translateY(-5px); box-shadow: 0 10px 20px rgba(0,0,0,0.3); }
        .car-img-wrapper { width: 100%; height: 140px; background: #fff; display: flex; align-items: center; justify-content: center; padding: 10px; border-bottom: 1px solid #eee; }
        .car-img-wrapper img { max-width: 100%; max-height: 100%; object-fit: contain; }
        .car-info { padding: 15px; color: #333; }
        .car-title { font-weight: bold; font-size: 15px; margin-bottom: 10px; color: #2c3e50; }
        .select-overlay-btn { display: block; width: 100%; padding: 10px; background: #3498db; color: white; border: none; border-radius: 6px; font-weight: bold; cursor: pointer; }
        #loading-landing { display: none; font-size: 18px; margin: 20px; color: #f1c40f; font-weight:bold;}
        #carSelect { display: none !important; }
        
        #selectedCarDisplay {
            background: #ecf0f1; border-left: 5px solid #2ecc71; color: #2c3e50;
            padding: 10px; border-radius: 4px; font-weight: normal; font-size: 14px;
            display: flex; align-items: center; gap: 10px; margin-bottom: 15px;
            box-shadow: 0 2px 5px rgba(0,0,0,0.05);
        }
        .change-car-btn {
            background: #fff; color: #7f8c8d; border: 1px solid #bdc3c7;
            width: 26px; height: 26px; border-radius: 50%; cursor: pointer; margin-left: auto;
            display: flex; align-items: center; justify-content: center;
        }
        #detailed-station-list { padding: 15px; background: #fff; border-radius: 8px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); margin-top: 20px; max-height: 260px; overflow-y: auto; }
        .route-station-item { display: flex; flex-direction: column; padding: 10px 0; border-bottom: 1px dotted #eee; }
        .station-header { display: flex; justify-content: space-between; align-items: flex-start; width: 100%; }
        .station-trip-cost { font-size: 12px; color: #2ecc71; font-weight: bold; margin-top: 4px; background: #e8f8f5; padding: 4px; border-radius: 4px; display: inline-block; width: fit-content; }
        .station-price { font-weight: bold; white-space: nowrap; margin-left: 10px; }
        .price-found { color: #333; }
        .price-missing { color: #f39c12; }
        .station-brand { font-weight: 500; color: #333; display: block; }
        .station-district { font-size: 12px; color: #7f8c8d; font-weight: normal; margin-left: 5px; }
    </style>

    <div id="landing-overlay">
        <div class="landing-container">
            <div class="hero-title"><i class="fas fa-route"></i> Akıllı Rota Sistemi</div>
            <div class="hero-subtitle">Hesaplama için aracınızı seçin.</div>
            <div class="search-box-wrapper">
                <input type="text" id="modelInputLanding" placeholder="Marka ve Model (Örn: Honda Civic)" autocomplete="off">
                <button id="searchBtnLanding" onclick="landingSearch()">ARA VE SEÇ</button>
            </div>
            <div id="loading-landing">⏳ Veritabanı Taranıyor...</div>
            <div id="results-grid"></div>
        </div>
    </div>

    <script>
        const CAR_API = "http://192.168.1.110:5000"; 
        const FUEL_API = "http://192.168.1.110:3939"; 
        
        window.selectedLocations = { start: null, end: null };
        window.currentFuelPrice = 0; 
        window.fuelType = "benzin"; 
        window.selectedCarFuelType = null;
        window.foundRoutes = [];

        function strictTurkishNormalize(str) {
            if (!str) return "";
            return str.replace(/i/g, "İ").replace(/ı/g, "I").toUpperCase();
        }

        window.addEventListener('DOMContentLoaded', () => {
            const contentDiv = document.querySelector('.leaflet-sidebar-content');
            document.addEventListener('click', function(e) {
                const tab = e.target.closest('.leaflet-sidebar-tabs li a');
                if (tab) {
                    e.preventDefault(); 
                    const content = document.querySelector('.leaflet-sidebar-content');
                    if(content) {
                        content.classList.toggle('content-hidden');
                    }
                }
            });
            setTimeout(() => {
                const content = document.querySelector('.leaflet-sidebar-content');
                if(content) content.classList.remove('content-hidden');
            }, 800);

            const carInputGroup = document.querySelector('.input-group'); 
            if(carInputGroup) {
                const displayDiv = document.createElement('div');
                displayDiv.id = 'selectedCarDisplay';
                displayDiv.innerHTML = '<i class="fas fa-car fa-lg"></i> <span>Araç Seçilmedi</span>';
                const selectBox = document.getElementById('carSelect');
                if(selectBox) { carInputGroup.insertBefore(displayDiv, selectBox); }
            }
            
            const inputField = document.getElementById("modelInputLanding");
            if(inputField) {
                inputField.focus(); 
                inputField.addEventListener("keyup", function(event) { if (event.key === "Enter") landingSearch(); });
            }

            window.setupAutocomplete = function(inputId, listId) {
                const input = document.getElementById(inputId);
                const list = document.getElementById(listId);
                let debounceTimer;
                input.addEventListener("input", function(e) {
                    if (inputId === 'startInput') window.selectedLocations.start = null;
                    if (inputId === 'endInput') window.selectedLocations.end = null;
                    const val = this.value;
                    if (!val || val.length < 3) { list.innerHTML = ""; return; }
                    clearTimeout(debounceTimer);
                    debounceTimer = setTimeout(() => {
                        fetch(`https://nominatim.openstreetmap.org/search?format=json&q=${encodeURIComponent(val)}&countrycodes=tr&addressdetails=1&limit=8`)
                            .then(res => res.json())
                            .then(data => {
                                list.innerHTML = "";
                                const seenNames = new Set();
                                data.forEach(item => {
                                    const cleanName = item.display_name.trim().toLowerCase();
                                    if (seenNames.has(cleanName)) return;
                                    seenNames.add(cleanName);
                                    const div = document.createElement("div");
                                    div.className = "autocomplete-item";
                                    let iconClass = "fa-map-marker-alt";
                                    if(item.type === "hotel") iconClass = "fa-bed";
                                    div.innerHTML = `<i class="fas ${iconClass}"></i><div class="place-info"><span class="place-name">${item.display_name.split(",")[0]}</span><span class="place-address">${item.display_name.split(",").slice(1).join(", ")}</span></div>`;
                                    div.addEventListener("mousedown", function(e) {
                                        e.preventDefault(); 
                                        input.value = item.display_name;
                                        if (inputId === 'startInput') window.selectedLocations.start = { lat: item.lat, lon: item.lon, display_name: item.display_name };
                                        else window.selectedLocations.end = { lat: item.lat, lon: item.lon, display_name: item.display_name };
                                        list.innerHTML = ""; 
                                    });
                                    list.appendChild(div);
                                });
                            });
                    }, 300);
                });
                document.addEventListener("click", function(e) { if (e.target !== input) { list.innerHTML = ""; } });
            }
            setupAutocomplete("startInput", "startInput-list");
            setupAutocomplete("endInput", "endInput-list");

            window.fetchStationPricesForRoute = async function (stations, fuelType) {
                const routeResultsContainer = document.getElementById("route-results-container");
                const pricesHost = document.getElementById("mobile-prices-panel") || routeResultsContainer;
                const existingDetailedList = document.getElementById("detailed-station-list");
                if (existingDetailedList) existingDetailedList.remove();

                pricesHost.innerHTML = `
                    <div id="detailed-station-list">
                        <h3>⛽ İstasyon Bazlı Maliyet</h3>
                        <div id="station-list-progress" style="color: #555;">Hesaplanıyor (${fuelType})...</div>
                        <div id="station-list-body"></div>
                    </div>
                `;
                const progressEl = document.getElementById("station-list-progress");
                const listBodyEl = document.getElementById("station-list-body");
                
                let tripDistanceKm = 0;
                if(window.foundRoutes && window.foundRoutes.length > 0) tripDistanceKm = window.foundRoutes[0].summary.totalDistance / 1000;
                
                const selectEl = document.getElementById("carSelect");
                const selectedOption = selectEl.options[selectEl.selectedIndex];
                const avgConsumption = parseFloat(selectedOption.getAttribute('data-avg')) || parseFloat(selectEl.value);

                const filteredStations = stations.filter(st => st.Firma && st.Firma.toUpperCase() !== "YEREL İSTASYON");
                const promises = filteredStations.map(async (station, index) => {
                    const rawBrand = station.Firma.split(" ")[0]; 
                    const stationBrand = strictTurkishNormalize(rawBrand); 
                    const cleanIl = strictTurkishNormalize(station.İl);
                    const cleanIlce = strictTurkishNormalize(station.İlçe);
                    try {
                        progressEl.innerText = `Fiyatlar (${fuelType}) Çekiliyor (${index + 1}/${filteredStations.length})`;
                        const response = await fetch(`${FUEL_API}/fiyat_getir`, {
                            method: "POST", headers: { "Content-Type": "application/json" },
                            body: JSON.stringify({ istasyonlar: [stationBrand], il: cleanIl, ilce: cleanIlce, yakit: fuelType })
                        });
                        const data = await response.json();
                        if (data.fiyatlar && Object.keys(data.fiyatlar).length > 0) {
                            const price = parseFloat(Object.values(data.fiyatlar)[0]);
                            if (!isNaN(price) && price > 0) return { ...station, price, status: "success" };
                        }
                        return { ...station, status: "not_found" };
                    } catch (error) { return { ...station, status: "error" }; }
                });

                const results = await Promise.all(promises);
                progressEl.style.display = "none";
                let successCount = 0; let totalPrice = 0;

                const listHtml = results.map(r => {
                    let priceDisplay, costHtml;
                    if (r.status === "success") { 
                        priceDisplay = `${r.price.toFixed(2)} TL`; 
                        if(tripDistanceKm > 0 && avgConsumption > 0) {
                            const totalTripCost = (tripDistanceKm / 100) * avgConsumption * r.price;
                            costHtml = `<div class="station-trip-cost">🏁 Yolculuk: ${totalTripCost.toFixed(2)} TL</div>`;
                        } else { costHtml = `<div class="station-trip-cost" style="color:#999;">Mesafe Bilinmiyor</div>`; }
                        successCount++; totalPrice += r.price; 
                    } else { 
                        priceDisplay = "Fiyat Yok"; costHtml = "";
                    }
                    return `<div class="route-station-item"><div class="station-header"><span class="station-brand">${r.Firma}<span class="station-district">(${r.İlçe})</span></span><span class="station-price ${r.status === 'success' ? 'price-found' : 'price-missing'}">${priceDisplay}</span></div>${costHtml}</div>`;
                }).join("");
                
                listBodyEl.innerHTML = listHtml || "<div style='color:#ccc'>Veri yok.</div>";
                if (successCount > 0) {
                    window.currentFuelPrice = totalPrice / successCount;
                    if (typeof window.updateRouteCardsWithCost === 'function') window.updateRouteCardsWithCost();
                }
            };

            window.adresleriCozVeRotaCiz = async function() {
                var startInput = document.getElementById("startInput");
                var endInput = document.getElementById("endInput");
                if(!startInput.value || !endInput.value) { alert("Konumları doldurun."); return; }
                
                document.getElementById("loading").style.display = "block";
                document.getElementById("route-results-container").innerHTML = "";

                let normalizedFuelType = window.selectedCarFuelType || "benzin";
                window.fuelType = normalizedFuelType; // Global değişkeni güncelle

                try {
                    let startCoords, endCoords;
                    if (window.selectedLocations.start) startCoords = L.latLng(window.selectedLocations.start.lat, window.selectedLocations.start.lon);
                    else {
                        let startRes = await fetch(`https://nominatim.openstreetmap.org/search?format=json&q=${encodeURIComponent(startInput.value)}&countrycodes=tr&limit=1`);
                        let startJson = await startRes.json();
                        if(startJson.length===0) throw new Error("Başlangıç bulunamadı");
                        startCoords = L.latLng(startJson[0].lat, startJson[0].lon);
                    }
                    if (window.selectedLocations.end) endCoords = L.latLng(window.selectedLocations.end.lat, window.selectedLocations.end.lon);
                    else {
                        let endRes = await fetch(`https://nominatim.openstreetmap.org/search?format=json&q=${encodeURIComponent(endInput.value)}&countrycodes=tr&limit=1`);
                        let endJson = await endRes.json();
                        if(endJson.length===0) throw new Error("Varış bulunamadı");
                        endCoords = L.latLng(endJson[0].lat, endJson[0].lon);
                    }

                    if(startMarker) map.removeLayer(startMarker);
                    if(endMarker) map.removeLayer(endMarker);
                    startMarker = L.marker(startCoords).addTo(map).bindPopup("Başlangıç");
                    endMarker = L.marker(endCoords).addTo(map).bindPopup("Varış");
                    
                    routingControl.setWaypoints([startCoords, endCoords]);
                } catch (error) {
                    alert(error.message);
                    document.getElementById("loading").style.display = "none";
                }
            }

            if (typeof routingControl !== 'undefined') {
                window.updateRouteCardsWithCost = function() {
                    if (!window.foundRoutes || window.currentFuelPrice <= 0) return;
                    const selectEl = document.getElementById("carSelect");
                    const selectedOption = selectEl.options[selectEl.selectedIndex];
                    const avgConsumption = parseFloat(selectedOption.getAttribute('data-avg')) || parseFloat(selectEl.value);

                    window.foundRoutes.forEach((route, index) => {
                        const distanceKm = route.summary.totalDistance / 1000;
                        const totalCost = (distanceKm / 100) * avgConsumption * window.currentFuelPrice;
                        const costEl = document.getElementById(`cost-badge-${index}`);
                        if (costEl) {
                            costEl.innerHTML = `💵 <b>${totalCost.toFixed(2)} TL</b>`;
                            costEl.style.background = "#2ecc71";
                            costEl.style.color = "white";
                        }
                    });
                };

                routingControl.on('routesfound', function(e) {
                    document.getElementById("loading").style.display = "none";
                    window.foundRoutes = e.routes;
                    var container = document.getElementById("route-results-container");
                    container.innerHTML = "<div style='color:#ccc; font-size:12px; margin-bottom:10px;'>Rota Seçiniz:</div>";

                    window.foundRoutes.forEach((route, index) => {
                        var km = (route.summary.totalDistance / 1000).toFixed(1);
                        var selectEl = document.getElementById("carSelect");
                        var selectedOption = selectEl.options[selectEl.selectedIndex];
                        var avgC = parseFloat(selectedOption.getAttribute('data-avg')) || parseFloat(selectEl.value);
                        var title = `Rota ${index + 1}` + (index === 0 ? " (Önerilen)" : "");
                        
                        let costHtml = `<span id="cost-badge-${index}" style="background:#bdc3c7; color:white; padding:4px 8px; border-radius:4px; font-size:12px;">⏳ Hesaplanıyor...</span>`;
                        if (window.currentFuelPrice > 0) {
                             const currentCost = (parseFloat(km) / 100) * avgC * window.currentFuelPrice;
                             costHtml = `<span id="cost-badge-${index}" style="background:#2ecc71; color:white; padding:4px 8px; border-radius:4px; font-size:12px;">💵 <b>${currentCost.toFixed(2)} TL</b></span>`;
                        }
                        var card = document.createElement("div");
                        card.className = "route-option-card";
                        card.id = "route-card-" + index; 
                        card.innerHTML = `<div class="route-info-left"><div style="display:flex; justify-content:space-between; align-items:center;"><span style="font-weight:bold; color:#333;">${title}</span>${costHtml}</div><span style="color:#666; font-size:11px; display:block; margin-top:5px;">${km} km</span></div>`;
                        card.onclick = function() {
                            document.querySelectorAll(".route-option-card").forEach(c => c.classList.remove("selected"));
                            card.classList.add("selected");
                            selectRoute(index);
                        };
                        container.appendChild(card);
                    });
                });
            }
        });

        function reOpenLanding() {
            const overlay = document.getElementById('landing-overlay');
            overlay.style.display = 'flex';
            setTimeout(() => { overlay.style.opacity = '1'; document.getElementById("modelInputLanding").focus(); }, 10);
        }

        window.addEventListener("load", () => {
            const overlay = document.getElementById("landing-overlay");
            if (overlay) { overlay.style.display = "flex"; overlay.style.opacity = "1"; }
        });

        async function landingSearch() {
            const query = document.getElementById("modelInputLanding").value.trim();
            const grid = document.getElementById("results-grid");
            const loading = document.getElementById("loading-landing");
            const btn = document.getElementById("searchBtnLanding");
            if (!query) return alert("Model ismi girin.");
            grid.innerHTML = ""; loading.style.display = "block"; btn.disabled = true;

            try {
                const response = await fetch(`${CAR_API}/arac`, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ models: query }) });
                const data = await response.json();
                loading.style.display = "none"; btn.disabled = false;
                if (data.error || !Array.isArray(data)) { grid.innerHTML = "<p>Sonuç yok.</p>"; return; }
                
                data.forEach(arac => {
                    const card = document.createElement("div");
                    card.className = "car-card";
                    const imgUrl = arac.image_url ? arac.image_url : "";
                    card.innerHTML = `<div class="car-img-wrapper"><img src="${imgUrl}" alt="Car"></div><div class="car-info"><div class="car-title">${arac.title}</div><button class="select-overlay-btn" onclick="selectAndClose('${arac.url}', '${arac.title.replace(/'/g, "")}', '${imgUrl}')">SEÇ</button></div>`;
                    grid.appendChild(card);
                });
            } catch (error) { loading.style.display = "none"; btn.disabled = false; alert("Hata"); }
        }

        async function selectAndClose(url, title, imgUrl) {
            try {
                const response = await fetch(`${CAR_API}/arac/detay?url=${encodeURIComponent(url)}`);
                const data = await response.json();
                const avgFuel = data.fuel_consumption_l_per_100km['Ortalama'];
                const cityFuel = data.fuel_consumption_l_per_100km['Şehir İçi'];
                const hwyFuel = data.fuel_consumption_l_per_100km['Şehir Dışı'];
                
                // --- GÜNCELLEME BURADA YAPILDI ---
                // 1. Yakıt Tipini Belirle
                let fuelType = "benzin";
                if((data.yakit_turu||"").toLowerCase().includes("dizel")) fuelType = "dizel";
                window.selectedCarFuelType = fuelType;
                
                // 2. Ortalama Yoksa Diğerlerinden Birini Al
                const displayFuel = avgFuel || cityFuel || hwyFuel;
                if(!displayFuel) { alert("Bu araç için yakıt verisi yok."); return; }

                // 3. Dropdown Güncelleme
                const selectBox = document.getElementById('carSelect');
                if(selectBox) {
                    const opt = document.createElement('option');
                    opt.value = displayFuel; opt.innerHTML = title; opt.selected = true;
                    if(avgFuel) opt.setAttribute('data-avg', avgFuel);
                    selectBox.appendChild(opt); selectBox.value = displayFuel; 
                }

                // 4. Görsel Kutuyu Güncelleme (Şehir İçi / Dışı Eklendi)
                const displayDiv = document.getElementById('selectedCarDisplay');
                if(displayDiv) {
                     // Yakıt Tipi Etiketi
                     const fuelLabel = fuelType === "dizel" ? "DİZEL" : "BENZİN";
                     const fuelColor = fuelType === "dizel" ? "#27ae60" : "#e74c3c"; // Dizel yeşil, Benzin kırmızı ton

                     // Detay HTML'i hazırla
                     let detailsHtml = `<div><b>Ort: ${avgFuel || '-'} lt</b></div>`;
                     if(cityFuel) detailsHtml += `<div style="font-size:11px; color:#555;">Ş.İçi: ${cityFuel} lt</div>`;
                     if(hwyFuel) detailsHtml += `<div style="font-size:11px; color:#555;">Ş.Dışı: ${hwyFuel} lt</div>`;

                     displayDiv.innerHTML = `
                        <div style="width:50px; height:50px; border-radius:50%; overflow:hidden; border:1px solid #ddd; background:white; flex-shrink:0;">
                            <img src="${imgUrl}" style="width:100%; height:100%; object-fit:cover;">
                        </div>
                        <div style="flex-grow:1; margin-left:10px;">
                            <div style="font-weight:bold; font-size:13px; line-height:1.2;">${title.substring(0,30)}</div>
                            <div style="font-size:10px; font-weight:bold; background:${fuelColor}; color:white; padding:2px 5px; border-radius:3px; display:inline-block; margin:2px 0;">${fuelLabel}</div>
                            <div style="margin-top:2px;">${detailsHtml}</div>
                        </div>
                        <button class="change-car-btn" onclick="reOpenLanding()"><i class="fas fa-sync-alt"></i></button>
                     `;
                }

                const overlay = document.getElementById('landing-overlay');
                overlay.style.opacity = '0';
                setTimeout(() => { overlay.style.display = 'none'; }, 500);
            } catch (e) { alert("Hata oluştu: " + e.message); }
        }
    </script>
    """

    final_html = html_content + custom_interface
    
    # HTML escape işlemi ile iframe oluştur
    iframe = f"""
    <iframe srcdoc="{html.escape(final_html)}" 
            id="map-frame" 
            style="width: 100%; height: 90vh; border: none;">
    </iframe>
    """
    return iframe

# ==========================================
# GRAFİK SİSTEMİ FONKSİYONLARI (ALIGRAFIK.PY)
# ==========================================

def fetch_single_price(brand_key, fuel_type, city, district):
    """Tek bir marka ve yakıt türü için API'den fiyat çeker."""
    try:
        payload = {
            "istasyonlar": [brand_key],
            "il": city,
            "ilce": district,
            "yakit": fuel_type
        }
        # Timeout kısa tutuldu ki grafik hızlı dönsün
        response = requests.post(GRAPH_API_URL, json=payload, timeout=4)
        
        if response.status_code == 200:
            data = response.json()
            # API Dönüş Formatı: {"fiyatlar": {"SHELL": "42.50"}}
            prices = data.get("fiyatlar", {})
            # API'den gelen anahtarı bul (büyük/küçük harf duyarsızlığı için)
            for k, v in prices.items():
                if brand_key in k or k in brand_key:
                    return float(str(v).replace(",", "."))
    except Exception as e:
        print(f"Veri çekme hatası ({brand_key}-{fuel_type}): {e}")
    
    return 0.0

def get_real_fuel_data(city, district):
    """Belirtilen konum için tüm markaların verilerini paralel isteklerle toplar."""
    data_list = []
    
    # ThreadPool ile istekleri aynı anda atalım (Hız kazandırır)
    with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
        future_map = {}
        
        for key, name in BRANDS_MAP.items():
            # Hem Benzin hem Dizel için istek oluştur
            f_benzin = executor.submit(fetch_single_price, key, "benzin", city, district)
            f_dizel = executor.submit(fetch_single_price, key, "dizel", city, district)
            
            future_map[f_benzin] = (name, "Benzin")
            future_map[f_dizel]  = (name, "Dizel")
            
        # Sonuçları topla
        for future in concurrent.futures.as_completed(future_map):
            brand_name, fuel_type = future_map[future]
            price = 0.0
            try:
                price = future.result()
            except: pass
            
            # Sadece fiyatı 0'dan büyük olanları ekle
            if price > 0:
                data_list.append({
                    "Marka": brand_name,
                    "Yakıt Türü": fuel_type,
                    "Fiyat": price
                })
            
    df = pd.DataFrame(data_list)
    return df

def create_chic_chart(city, district):
    """Matplotlib kullanarak şık bir karşılaştırma grafiği oluşturur."""
    if not city or not district:
        city, district = "istanbul", "kadikoy"
        
    df = get_real_fuel_data(city, district)
    
    # Eğer veri yoksa veya hepsi 0 ise bilgi ver
    if df.empty:
        fig_empty, ax_empty = plt.subplots(figsize=(8, 4))
        ax_empty.text(0.5, 0.5, "Veri Bulunamadı veya API Kapalı\n(Lütfen API'nin çalıştığından emin olun)", 
                      ha='center', va='center', fontsize=12)
        ax_empty.axis('off')
        return fig_empty

    # Veriyi Grafiğe Hazırla (Pivot)
    df_pivot = df.pivot(index='Marka', columns='Yakıt Türü', values='Fiyat')
    # Sıralamayı garantiye al
    cols = [c for c in ["Benzin", "Dizel"] if c in df_pivot.columns]
    df_pivot = df_pivot[cols]

    # Stil ve Grafik Oluşturma
    plt.style.use('seaborn-v0_8-darkgrid') 
    fig, ax = plt.subplots(figsize=(10, 6))
    colors = ['#F39C12', '#2ECC71'] 
    
    df_pivot.plot(kind='bar', ax=ax, color=colors, width=0.75, edgecolor='white', linewidth=1.2, rot=0)

    # Başlık ve Eksenler
    ax.set_title(f"⛽ {city.upper()} / {district.upper()} Akaryakıt Fiyatları", fontsize=14, fontweight='bold', pad=15, color='#34495E')
    ax.set_xlabel("Markalar", fontsize=11)
    ax.set_ylabel("Fiyat (TL)", fontsize=11)
    
    # Y Ekseni limitleri
    vals = df['Fiyat']
    if len(vals) > 0:
        y_min = vals.min() * 0.98
        y_max = vals.max() * 1.01
        ax.set_ylim(y_min, y_max)

    # Çubukların Üzerine Etiket Ekleme
    for container in ax.containers:
        ax.bar_label(container, fmt='%.2f', padding=3, fontsize=9, fontweight='bold')

    ax.legend(title=None, frameon=True, facecolor='white', loc='lower right')
    plt.tight_layout()
    return fig

# --------------------------------------------------------------------------
#                         GRADIO ARAYÜZÜ
# --------------------------------------------------------------------------

with gr.Blocks(title="Yakıt Hesaplama & Analiz Sistemi", css="body { margin: 0; padding: 0; }") as demo:
    
    with gr.Tabs():
        
        # SEKME 1: HARİTA VE ROTA (MEVCUT)
        with gr.TabItem("🗺️ Harita ve Rota"):
            gr.HTML(value=load_map_html_with_json())

        # SEKME 2: FİYAT ANALİZİ (YENİ)
        with gr.TabItem("📊 Fiyat Analizi"):
            gr.Markdown("### 🔍 İl ve İlçe Bazlı Detaylı Fiyat Karşılaştırması")
            with gr.Row():
                city_input = gr.Textbox(label="Şehir (İl)", placeholder="Örn: istanbul", value="istanbul")
                dist_input = gr.Textbox(label="İlçe", placeholder="Örn: kadikoy", value="kadikoy")
            
            btn_analiz = gr.Button("Grafiği Oluştur", variant="primary")
            plot_output = gr.Plot(label="Fiyat Grafiği")
            
            btn_analiz.click(
                fn=create_chic_chart, 
                inputs=[city_input, dist_input], 
                outputs=plot_output
            )

if __name__ == "__main__":
    demo.launch(server_name="0.0.0.0", server_port=7860, share=True)
