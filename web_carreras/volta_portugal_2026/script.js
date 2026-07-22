// Volta a Portugal 2026 - Visor de Rutas
(function () {
    'use strict';

    const GPX_DIR = 'gpx';
    const STAGE_COLORS = [
        '#3b82f6', '#ef4444', '#10b981', '#f59e0b', '#8b5cf6',
        '#ec4899', '#06b6d4', '#84cc16', '#f97316', '#6366f1', '#14b8a6'
    ];

    let stages = [];
    let currentStage = null;
    let map = null;
    let overviewLayerGroup = null;
    let routeLayer = null;
    let startMarker = null;
    let endMarker = null;
    let elevationChart = null;
    let profileHoverMarker = null;
    let currentStageWind = null;

    const stageList = document.getElementById('stage-list');
    const stageCount = document.getElementById('stage-count');
    const stageTitle = document.getElementById('stage-title');
    const stageSubtitle = document.getElementById('stage-subtitle');
    const stageStats = document.getElementById('stage-stats');
    const mapOverlay = document.getElementById('map-overlay');
    const elevationStats = document.getElementById('elevation-stats');
    const backButton = document.getElementById('back-button');

    function init() {
        fetch('stages.json')
            .then(res => {
                if (!res.ok) throw new Error('Error al cargar stages.json');
                return res.json();
            })
            .then(data => {
                stages = data;
                stageCount.textContent = stages.length;
                renderStageList();
                showOverviewMap();
            })
            .catch(err => {
                console.error(err);
                stageTitle.textContent = 'Error';
                stageSubtitle.textContent = 'No se pudieron cargar los datos de las etapas.';
            });

        if (backButton) {
            backButton.addEventListener('click', showOverviewMap);
        }

        const btnFullscreen = document.getElementById('btn-fullscreen');
        if (btnFullscreen) btnFullscreen.addEventListener('click', toggleFullscreen);

        document.addEventListener('fullscreenchange', handleFullscreenChange);
        document.addEventListener('webkitfullscreenchange', handleFullscreenChange);
        document.addEventListener('keydown', (e) => {
            if (e.key === 'Escape') {
                const mapContainer = document.querySelector('.map-container');
                if (mapContainer && mapContainer.classList.contains('is-fullscreen-fallback')) {
                    mapContainer.classList.remove('is-fullscreen-fallback');
                    handleFullscreenChange();
                }
            }
        });
    }

    function toggleFullscreen() {
        const mapContainer = document.querySelector('.map-container');
        if (!mapContainer) return;

        const isFS = Boolean(
            document.fullscreenElement ||
            document.webkitFullscreenElement ||
            mapContainer.classList.contains('is-fullscreen-fallback')
        );

        if (!isFS) {
            if (mapContainer.requestFullscreen) {
                mapContainer.requestFullscreen().catch(() => {
                    mapContainer.classList.add('is-fullscreen-fallback');
                    handleFullscreenChange();
                });
            } else if (mapContainer.webkitRequestFullscreen) {
                mapContainer.webkitRequestFullscreen();
            } else if (mapContainer.msRequestFullscreen) {
                mapContainer.msRequestFullscreen();
            } else {
                mapContainer.classList.add('is-fullscreen-fallback');
                handleFullscreenChange();
            }
        } else {
            if (document.fullscreenElement || document.webkitFullscreenElement) {
                if (document.exitFullscreen) {
                    document.exitFullscreen();
                } else if (document.webkitExitFullscreen) {
                    document.webkitExitFullscreen();
                }
            }
            if (mapContainer.classList.contains('is-fullscreen-fallback')) {
                mapContainer.classList.remove('is-fullscreen-fallback');
                handleFullscreenChange();
            }
        }
    }

    function handleFullscreenChange() {
        const btnFullscreen = document.getElementById('btn-fullscreen');
        const mapContainer = document.querySelector('.map-container');
        const isFS = Boolean(
            document.fullscreenElement ||
            document.webkitFullscreenElement ||
            (mapContainer && mapContainer.classList.contains('is-fullscreen-fallback'))
        );

        if (btnFullscreen) {
            if (isFS) {
                btnFullscreen.innerHTML = '🗗 Reducir mapa';
                btnFullscreen.classList.add('active');
            } else {
                btnFullscreen.innerHTML = '⛶ Ampliar mapa';
                btnFullscreen.classList.remove('active');
            }
        }

        if (map) {
            setTimeout(() => {
                map.invalidateSize();
            }, 150);
        }
    }

    function renderStageList() {
        stageList.innerHTML = '';
        stages.forEach((stage, index) => {
            const card = document.createElement('div');
            card.className = 'stage-card ' + getStageTypeClass(stage, index);
            card.dataset.index = index;

            const route = extractRouteFromName(stage.name);
            const dist = stage.distance_km.toFixed(1);
            const elev = Math.round(stage.elevation_gain_m);
            const elevDisplay = elev.toLocaleString();

            card.innerHTML = `
                <div class="stage-number">
                    <span class="stage-badge">${formatStageNumber(stage.name)}</span>
                    <span class="stage-type-badge">${getStageType(stage, index)}</span>
                </div>
                <div class="stage-name">${escapeHtml(route.name)}</div>
                <div class="stage-route">${escapeHtml(route.from)} → ${escapeHtml(route.to)}</div>
                <div class="stage-meta">
                    <div class="stage-meta-item">
                        <span class="icon">📏</span>
                        <span>${dist} km</span>
                    </div>
                    <div class="stage-meta-item">
                        <span class="icon">⛰️</span>
                        <span>+${elevDisplay} m</span>
                    </div>
                </div>
            `;

            card.addEventListener('click', () => showStageDetail(index));
            stageList.appendChild(card);
        });
    }

    function showStageDetail(index) {
        const stage = stages[index];
        if (!stage) return;

        currentStage = stage;

        // UI: selección activa en sidebar
        document.querySelectorAll('.stage-card').forEach(c => c.classList.remove('active'));
        const card = stageList.querySelector(`[data-index="${index}"]`);
        if (card) {
            card.classList.add('active');
            card.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
        }

        // UI: títulos y botón volver
        const route = extractRouteFromName(stage.name);
        stageTitle.textContent = `${formatStageNumber(stage.name)}: ${escapeHtml(route.from)} → ${escapeHtml(route.to)}`;
        stageSubtitle.textContent = stage.name;
        if (backButton) backButton.classList.remove('hidden');

        // Estadísticas
        const statsHtml = `
            <div class="stat-card">
                <div class="stat-label">Distancia</div>
                <div class="stat-value">${stage.distance_km.toFixed(1)} km</div>
            </div>
            <div class="stat-card">
                <div class="stat-label">Desnivel +</div>
                <div class="stat-value">+${Math.round(stage.elevation_gain_m).toLocaleString()} m</div>
            </div>
            <div class="stat-card">
                <div class="stat-label">Altitud Max</div>
                <div class="stat-value">${Math.round(stage.max_ele_m).toLocaleString()} m</div>
            </div>
            <div class="stat-card">
                <div class="stat-label">Altitud Min</div>
                <div class="stat-value">${Math.round(stage.min_ele_m).toLocaleString()} m</div>
            </div>
        `;
        stageStats.innerHTML = statsHtml;

        loadStageMap(stage);
    }

    function showOverviewMap() {
        currentStage = null;
        document.querySelectorAll('.stage-card').forEach(c => c.classList.remove('active'));

        stageTitle.textContent = 'Resumen de Etapas';
        stageSubtitle.textContent = 'Haz clic en una etapa para ver el detalle';
        if (backButton) backButton.classList.add('hidden');
        stageStats.innerHTML = '';
        elevationStats.innerHTML = '';
        document.getElementById('climbs-list').innerHTML = '';

        const elevationContainer = document.querySelector('.elevation-container');
        if (elevationContainer) {
            elevationContainer.classList.add('hidden');
        }

        const mapLegend = document.getElementById('map-legend');
        if (mapLegend) {
            mapLegend.classList.add('hidden');
        }

        if (map) {
            profileHoverMarker = null;
            map.remove();
            map = null;
            routeLayer = null;
            startMarker = null;
            endMarker = null;
            overviewLayerGroup = null;
        }

        map = L.map('map', {
            zoomControl: true,
            attributionControl: true
        });

        L.tileLayer('https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png', {
            attribution: '\u00A9 <a href="https://www.openstreetmap.org/copyright">OSM</a> \u00A9 <a href="https://carto.com/attributions">CARTO</a>',
            subdomains: 'abcd',
            maxZoom: 20
        }).addTo(map);

        overviewLayerGroup = L.layerGroup().addTo(map);

        const allBounds = [];

        stages.forEach((stage, index) => {
            const color = STAGE_COLORS[index % STAGE_COLORS.length];
            const startLatLng = [stage.start_lat, stage.start_lon];
            const endLatLng = [stage.end_lat, stage.end_lon];

            if (stage.distance_km < 0.5 && stage.start_lat === stage.end_lat && stage.start_lon === stage.end_lon) {
                const marker = L.circleMarker(startLatLng, {
                    radius: 8,
                    fillColor: color,
                    color: '#fff',
                    weight: 3,
                    opacity: 1,
                    fillOpacity: 0.9
                }).addTo(overviewLayerGroup);

                marker.bindPopup(`<b>${formatStageNumber(stage.name)}</b><br>${stage.distance_km.toFixed(1)} km`);
                marker.on('click', () => showStageDetail(index));
                allBounds.push(startLatLng);
                return;
            }

            const polyline = L.polyline([startLatLng, endLatLng], {
                color: color,
                weight: 4,
                opacity: 0.9,
                lineJoin: 'round',
                dashArray: '6 6'
            }).addTo(overviewLayerGroup);

            polyline.bindPopup(`<b>${formatStageNumber(stage.name)}</b><br>${stage.distance_km.toFixed(1)} km`);
            polyline.on('click', () => showStageDetail(index));

            const startMarkerNum = L.marker(startLatLng, {
                icon: L.divIcon({
                    html: `<div style="
                        background:${color};
                        color:#fff;
                        border:2px solid #fff;
                        border-radius:50%;
                        width:24px;
                        height:24px;
                        display:flex;
                        align-items:center;
                        justify-content:center;
                        font-weight:bold;
                        font-size:12px;
                        box-shadow:0 2px 6px rgba(0,0,0,0.4);
                        font-family:inherit;
                    ">${index}</div>`,
                    className: 'stage-number-icon',
                    iconSize: [24, 24],
                    iconAnchor: [12, 12]
                })
            }).addTo(overviewLayerGroup);
            startMarkerNum.on('click', () => showStageDetail(index));

            const endMarkerNum = L.marker(endLatLng, {
                icon: L.divIcon({
                    html: `<div style="
                        background:${color};
                        color:#fff;
                        border:2px solid #fff;
                        border-radius:50%;
                        width:24px;
                        height:24px;
                        display:flex;
                        align-items:center;
                        justify-content:center;
                        font-weight:bold;
                        font-size:12px;
                        box-shadow:0 2px 6px rgba(0,0,0,0.4);
                        font-family:inherit;
                    ">${index}</div>`,
                    className: 'stage-number-icon',
                    iconSize: [24, 24],
                    iconAnchor: [12, 12]
                })
            }).addTo(overviewLayerGroup);
            endMarkerNum.on('click', () => showStageDetail(index));

            allBounds.push(startLatLng, endLatLng);
        });

        if (allBounds.length > 0) {
            map.fitBounds(allBounds, { padding: [40, 40] });
        }

        mapOverlay.classList.add('hidden');
        setTimeout(() => { if (map) map.invalidateSize(); }, 100);

        stopWindAnimation();
        const windWidget = document.getElementById('wind-widget');
        if (windWidget) {
            windWidget.classList.add('hidden');
        }
    }

    function loadStageMap(stage) {
        mapOverlay.classList.remove('hidden');

        const elevationContainer = document.querySelector('.elevation-container');
        if (elevationContainer) {
            elevationContainer.classList.remove('hidden');
        }

        const mapLegend = document.getElementById('map-legend');
        if (mapLegend) {
            mapLegend.classList.remove('hidden');
        }

        if (map) {
            profileHoverMarker = null;
            map.remove();
            map = null;
            routeLayer = null;
            startMarker = null;
            endMarker = null;
            overviewLayerGroup = null;
        }

        const gpxUrl = `${GPX_DIR}/${encodeURIComponent(stage.filename)}`;

        fetch(gpxUrl)
            .then(res => {
                if (!res.ok) throw new Error('Error al cargar GPX');
                return res.text();
            })
            .then(gpxText => {
                const coords = parseGpx(gpxText);
                if (coords.length === 0) throw new Error('No se encontraron puntos del recorrido');

                renderStageMap(coords, stage);
                renderElevationProfile(coords, stage);

                const maxElev = Math.round(d3Max(coords, c => c[2]) || 0);
                const minElev = Math.round(d3Min(coords, c => c[2]) || 0);
                const gain = Math.round(stage.elevation_gain_m);
                elevationStats.innerHTML = `
                    <span class="elevation-stat">Máx: <strong>${maxElev}m</strong></span>
                    <span class="elevation-stat">Mín: <strong>${minElev}m</strong></span>
                    <span class="elevation-stat">Ganancia: <strong>+${gain}m</strong></span>
                `;

                mapOverlay.classList.add('hidden');
            })
            .catch(err => {
                console.error('Error al cargar GPX:', err);
                mapOverlay.innerHTML = `
                    <div style="color: var(--red); text-align: center; padding: 2rem;">
                        <p style="font-size: 1.2rem; margin-bottom: 0.5rem;">⚠️ Error al cargar la ruta</p>
                        <p style="color: var(--text-muted); font-size: 0.9rem;">${err.message}</p>
                    </div>
                `;
            });
    }

    function getGradientColor(slope) {
        if (slope <= 2) return '#ffffff';      // Llano y Bajada (blanco)
        if (slope <= 5) return '#eab308';      // 2% - 5% (amarillo)
        if (slope <= 8) return '#f97316';      // 5% - 8% (naranja)
        if (slope <= 11) return '#ef4444';     // 8% - 11% (rojo)
        return '#881337';                      // > 11% (rojo oscuro)
    }

    function getGradientFillColor(slope) {
        if (slope <= 2) return 'rgba(255, 255, 255, 0.12)';
        if (slope <= 5) return 'rgba(234, 179, 8, 0.25)';
        if (slope <= 8) return 'rgba(249, 115, 22, 0.32)';
        if (slope <= 11) return 'rgba(239, 68, 68, 0.40)';
        return 'rgba(136, 19, 55, 0.55)';
    }

    function getCategoryColor(cat) {
        const c = (cat || '').toUpperCase();
        if (c === 'HC') return '#7c2d12';
        if (c === '1C' || c === '1ª' || c === '1') return '#991b1b';
        if (c === '2C' || c === '2ª' || c === '2') return '#b91c1c';
        if (c === '3C' || c === '3ª' || c === '3') return '#ea580c';
        return '#65a30d';
    }

    function formatCatLabel(cat) {
        const c = (cat || '').toUpperCase();
        if (c === '1C') return '1ª';
        if (c === '2C') return '2ª';
        if (c === '3C') return '3ª';
        if (c === '4C') return '4ª';
        return c;
    }

    function computePointSlopes(coords) {
        const n = coords.length;
        const distM = new Array(n).fill(0);
        let cum = 0;
        for (let i = 1; i < n; i++) {
            const p1 = coords[i - 1];
            const p2 = coords[i];
            const d = Math.sqrt(
                Math.pow((p2[0] - p1[0]) * 111000, 2) +
                Math.pow((p2[1] - p1[1]) * 111000 * Math.cos(p1[0] * Math.PI / 180), 2)
            );
            cum += d;
            distM[i] = cum;
        }

        const windowSize = 5;
        const slopes = new Array(n).fill(0);
        for (let i = 0; i < n; i++) {
            const iStart = Math.max(0, i - windowSize);
            const iEnd = Math.min(n - 1, i + windowSize);
            const dDist = distM[iEnd] - distM[iStart];
            const eStart = coords[iStart][2];
            const eEnd = coords[iEnd][2];
            if (dDist > 0 && eStart !== null && eEnd !== null && !isNaN(eStart) && !isNaN(eEnd)) {
                slopes[i] = ((eEnd - eStart) / dDist) * 100;
            } else {
                slopes[i] = 0;
            }
        }
        return { distM, slopes };
    }

    function renderStageMap(coords, stage) {
        map = L.map('map', {
            zoomControl: true,
            attributionControl: true
        }).setView([coords[0][0], coords[0][1]], 10);

        L.tileLayer('https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png', {
            attribution: '\u00A9 <a href="https://www.openstreetmap.org/copyright">OSM</a> \u00A9 <a href="https://carto.com/attributions">CARTO</a>',
            subdomains: 'abcd',
            maxZoom: 20
        }).addTo(map);

        const { slopes } = computePointSlopes(coords);
        const latLngs = coords.map(c => [c[0], c[1]]);

        // Dark background outline for high contrast
        L.polyline(latLngs, {
            color: '#0a0e17',
            weight: 7,
            opacity: 0.8,
            lineJoin: 'round',
            lineCap: 'round'
        }).addTo(map);

        // Segmented colored route
        let currentSegment = [latLngs[0]];
        let currentSlope = slopes[0];

        for (let i = 1; i < coords.length; i++) {
            const slope = slopes[i];
            const colorCurrent = getGradientColor(currentSlope);
            const colorNext = getGradientColor(slope);

            currentSegment.push(latLngs[i]);

            if (colorCurrent !== colorNext || i === coords.length - 1) {
                L.polyline(currentSegment, {
                    color: colorCurrent,
                    weight: 4.5,
                    opacity: 0.95,
                    lineJoin: 'round',
                    lineCap: 'round'
                }).addTo(map);

                currentSegment = [latLngs[i]];
                currentSlope = slope;
            }
        }

        // Climbs Markers on Map
        const climbs = stage.climbs || [];
        climbs.forEach((climb) => {
            const catLabel = formatCatLabel(climb.category) + (climb.is_finish ? ' 🏁' : '');
            const catColor = getCategoryColor(climb.category);

            const badgeW = climb.is_finish ? 42 : 26;
            const climbMarker = L.marker([climb.lat, climb.lon], {
                icon: L.divIcon({
                    html: `<div class="climb-map-badge" style="background:${catColor}; width:${badgeW}px; border-radius:${climb.is_finish ? '12px' : '50%'};">${catLabel}</div>`,
                    className: 'climb-map-icon',
                    iconSize: [badgeW, 26],
                    iconAnchor: [badgeW / 2, 13]
                })
            }).addTo(map);

            const climbTitle = climb.is_finish ? `⛰️ Puerto ${formatCatLabel(climb.category)} — FINAL EN ALTO 🏁` : `⛰️ Puerto ${formatCatLabel(climb.category)}`;
            const climbName = climb.name ? `<div><b>Nombre:</b> ${climb.name}</div>` : '';

            climbMarker.bindPopup(`
                <div class="climb-popup">
                    <div class="climb-popup-title">${climbTitle}</div>
                    ${climbName}
                    <div><b>Desnivel:</b> +${Math.round(climb.elevation_gain_m)} m</div>
                    <div><b>Longitud:</b> ${(climb.distance_m / 1000).toFixed(1)} km</div>
                    <div><b>Pendiente Media:</b> ${climb.avg_gradient_pct}%</div>
                    <div><b>Altitud Cumbre:</b> ${climb.max_ele_m} m</div>
                </div>
            `);
        });

        startMarker = L.circleMarker([coords[0][0], coords[0][1]], {
            radius: 8,
            fillColor: '#10b981',
            color: '#fff',
            weight: 3,
            opacity: 1,
            fillOpacity: 0.9
        }).addTo(map);
        startMarker.bindPopup('<b>Inicio</b>');

        endMarker = L.circleMarker([coords[coords.length - 1][0], coords[coords.length - 1][1]], {
            radius: 8,
            fillColor: '#ef4444',
            color: '#fff',
            weight: 3,
            opacity: 1,
            fillOpacity: 0.9
        }).addTo(map);
        endMarker.bindPopup('<b>Meta</b>');

        const fullPolyline = L.polyline(latLngs);
        map.fitBounds(fullPolyline.getBounds(), { padding: [30, 30] });

        updateStageWind(stage);
        if (map) map.on('moveend zoomend', resizeWindCanvas);
    }

    function parseGpx(gpxText) {
        const parser = new DOMParser();
        const xml = parser.parseFromString(gpxText, 'text/xml');
        const trkpts = xml.querySelectorAll('trkpt');
        const coords = [];
        trkpts.forEach(pt => {
            const lat = parseFloat(pt.getAttribute('lat'));
            const lon = parseFloat(pt.getAttribute('lon'));
            const ele = pt.querySelector('ele');
            const eleVal = ele ? parseFloat(ele.textContent) : null;
            if (!isNaN(lat) && !isNaN(lon)) {
                coords.push([lat, lon, eleVal]);
            }
        });
        return coords;
    }

    function getTrackHeading(coords, origIdx) {
        if (!coords || coords.length < 2) return 0;
        const idx = Math.max(0, Math.min(coords.length - 1, origIdx || 0));
        const iStart = Math.max(0, idx - 6);
        const iEnd = Math.min(coords.length - 1, idx + 6);
        const p1 = coords[iStart];
        const p2 = coords[iEnd];
        const dLat = p2[0] - p1[0];
        const dLon = (p2[1] - p1[1]) * Math.cos(p1[0] * Math.PI / 180);
        let angle = Math.atan2(dLon, dLat) * (180 / Math.PI);
        return (angle + 360) % 360;
    }

    function getRelativeWindAnalysis(coords, origIdx, wind) {
        if (!wind || !coords || origIdx === undefined || !coords[origIdx]) return null;
        const trackHeading = getTrackHeading(coords, origIdx);
        const windTo = (wind.dir + 180) % 360;
        let diff = (windTo - trackHeading + 180) % 360;
        if (diff < 0) diff += 360;
        diff -= 180;
        const relAngle = Math.abs(diff);

        let labelText = 'Viento de costado';
        let emoji = '🟪';
        let colorHex = '#a855f7'; // purple

        if (relAngle <= 45) {
            labelText = 'Viento a favor';
            emoji = '🟩';
            colorHex = '#10b981'; // green
        } else if (relAngle >= 135) {
            labelText = 'Viento en contra';
            emoji = '🟥';
            colorHex = '#ef4444'; // red
        }

        return { labelText, emoji, colorHex, relAngle };
    }

    function renderElevationProfile(coords, stage) {
        const ctx = document.getElementById('elevation-chart').getContext('2d');
        
        if (elevationChart) {
            elevationChart.destroy();
        }

        const { distM, slopes } = computePointSlopes(coords);

        const maxPoints = 600;
        let step = 1;
        if (coords.length > maxPoints) {
            step = Math.ceil(coords.length / maxPoints);
        }
        
        const filtered = [];
        for (let i = 0; i < coords.length; i += step) {
            filtered.push({
                origIndex: i,
                dist: distM[i] / 1000,
                elev: coords[i][2],
                slope: slopes[i]
            });
        }

        // Clean elevation nulls
        for (let i = 0; i < filtered.length; i++) {
            if (filtered[i].elev === null || isNaN(filtered[i].elev)) {
                let j = i - 1;
                let k = i + 1;
                while (j >= 0 && (filtered[j].elev === null || isNaN(filtered[j].elev))) j--;
                while (k < filtered.length && (filtered[k].elev === null || isNaN(filtered[k].elev))) k++;
                if (j >= 0 && k < filtered.length) {
                    filtered[i].elev = filtered[j].elev + (filtered[k].elev - filtered[j].elev) * (i - j) / (k - j);
                } else if (j >= 0) {
                    filtered[i].elev = filtered[j].elev;
                } else if (k < filtered.length) {
                    filtered[i].elev = filtered[k].elev;
                }
            }
        }

        const labels = filtered.map(f => f.dist.toFixed(1));
        const data = filtered.map(f => f.elev);

        const climbMarkersPlugin = {
            id: 'climbMarkers',
            afterDraw(chart) {
                if (!stage || !stage.climbs || stage.climbs.length === 0) return;
                const { ctx, chartArea: { top, bottom, left, right }, scales: { x, y } } = chart;
                ctx.save();

                stage.climbs.forEach((climb) => {
                    let summitFilteredIdx = -1;
                    if (climb.is_finish) {
                        summitFilteredIdx = filtered.length - 1;
                    } else if (climb.summit_index !== undefined) {
                        summitFilteredIdx = filtered.findIndex(f => f.origIndex >= climb.summit_index);
                    }
                    if (summitFilteredIdx === -1) {
                        const climbDistKm = (climb.distance_m || 0) / 1000;
                        summitFilteredIdx = filtered.findIndex(f => f.dist >= climbDistKm);
                    }
                    if (summitFilteredIdx === -1) return;

                    const xPos = x.getPixelForValue(summitFilteredIdx);
                    const yVal = filtered[summitFilteredIdx] ? filtered[summitFilteredIdx].elev : (climb.max_ele_m || 0);
                    const yPos = y.getPixelForValue(yVal);

                    if (xPos < left || xPos > right + 10) return;

                    // Dashed line down to axis
                    ctx.beginPath();
                    ctx.setLineDash([4, 4]);
                    ctx.strokeStyle = climb.is_finish ? 'rgba(239, 68, 68, 0.8)' : 'rgba(255, 255, 255, 0.45)';
                    ctx.lineWidth = climb.is_finish ? 2 : 1.5;
                    ctx.moveTo(xPos, yPos);
                    ctx.lineTo(xPos, bottom);
                    ctx.stroke();
                    ctx.setLineDash([]);

                    // Summit point dot
                    ctx.beginPath();
                    ctx.arc(xPos, yPos, climb.is_finish ? 5 : 4, 0, Math.PI * 2);
                    ctx.fillStyle = climb.is_finish ? '#ef4444' : '#ffffff';
                    ctx.fill();

                    // Category Badge
                    const label = formatCatLabel(climb.category) + (climb.is_finish ? ' 🏁' : '');
                    const badgeColor = getCategoryColor(climb.category);

                    ctx.font = 'bold 11px Inter, sans-serif';
                    const textWidth = ctx.measureText(label).width;
                    const badgeW = Math.max(textWidth + 12, 26);
                    const badgeH = 20;
                    let badgeX = xPos - badgeW / 2;
                    if (badgeX + badgeW > right) badgeX = right - badgeW - 2;
                    if (badgeX < left) badgeX = left + 2;
                    const badgeY = Math.max(top + 4, yPos - 26);

                    // Shadow
                    ctx.shadowColor = 'rgba(0, 0, 0, 0.6)';
                    ctx.shadowBlur = 4;
                    ctx.shadowOffsetY = 2;

                    // Background pill
                    ctx.fillStyle = badgeColor;
                    ctx.beginPath();
                    if (typeof ctx.roundRect === 'function') {
                        ctx.roundRect(badgeX, badgeY, badgeW, badgeH, 10);
                    } else {
                        ctx.rect(badgeX, badgeY, badgeW, badgeH);
                    }
                    ctx.fill();

                    // Border
                    ctx.strokeStyle = '#ffffff';
                    ctx.lineWidth = 1.5;
                    ctx.stroke();

                    // Text
                    ctx.shadowColor = 'transparent';
                    ctx.fillStyle = '#ffffff';
                    ctx.textAlign = 'center';
                    ctx.textBaseline = 'middle';
                    ctx.fillText(label, xPos, badgeY + badgeH / 2);
                });

                ctx.restore();
            }
        };

        const canvas = document.getElementById('elevation-chart');
        if (canvas) {
            const clearHoverMarker = () => {
                if (profileHoverMarker && map) {
                    map.removeLayer(profileHoverMarker);
                    profileHoverMarker = null;
                }
            };
            canvas.onmouseleave = clearHoverMarker;
        }

        elevationChart = new Chart(ctx, {
            type: 'line',
            data: {
                labels: labels,
                datasets: [{
                    label: 'Elevación (m)',
                    data: data,
                    borderColor: '#ffffff',
                    borderWidth: 2,
                    fill: true,
                    tension: 0.2,
                    pointRadius: 0,
                    pointHoverRadius: 5,
                    segment: {
                        borderColor: ctx => {
                            const slope = filtered[ctx.p0DataIndex]?.slope ?? 0;
                            return getGradientColor(slope);
                        },
                        backgroundColor: ctx => {
                            const slope = filtered[ctx.p0DataIndex]?.slope ?? 0;
                            return getGradientFillColor(slope);
                        }
                    }
                }]
            },
            plugins: [climbMarkersPlugin],
            options: {
                responsive: true,
                maintainAspectRatio: false,
                onHover: (event, activeElements) => {
                    if (!map || !coords || coords.length === 0) return;
                    if (activeElements && activeElements.length > 0) {
                        const dataIdx = activeElements[0].index;
                        const item = filtered[dataIdx];
                        if (item && item.origIndex !== undefined && coords[item.origIndex]) {
                            const pt = coords[item.origIndex];
                            const latLng = [pt[0], pt[1]];
                            const windAnalysis = getRelativeWindAnalysis(coords, item.origIndex, currentStageWind);
                            const markerColor = windAnalysis ? windAnalysis.colorHex : '#38bdf8';

                            if (!profileHoverMarker) {
                                profileHoverMarker = L.circleMarker(latLng, {
                                    radius: 7,
                                    fillColor: markerColor,
                                    color: '#ffffff',
                                    weight: 3,
                                    opacity: 1,
                                    fillOpacity: 1,
                                    className: 'profile-hover-marker'
                                }).addTo(map);
                            } else {
                                profileHoverMarker.setLatLng(latLng);
                                profileHoverMarker.setStyle({ fillColor: markerColor });
                            }
                        }
                    } else {
                        if (profileHoverMarker && map) {
                            map.removeLayer(profileHoverMarker);
                            profileHoverMarker = null;
                        }
                    }
                },
                interaction: {
                    intersect: false,
                    mode: 'index'
                },
                plugins: {
                    legend: { display: false },
                    tooltip: {
                        backgroundColor: '#1f2937',
                        titleColor: '#f9fafb',
                        bodyColor: '#d1d5db',
                        borderColor: '#374151',
                        borderWidth: 1,
                        padding: 10,
                        callbacks: {
                            title: (items) => {
                                const idx = items[0].dataIndex;
                                const item = filtered[idx];
                                if (!item) return '';
                                const totalDist = stage ? stage.distance_km : (filtered[filtered.length - 1]?.dist || 0);
                                const distStart = item.dist.toFixed(1);
                                const distFinish = Math.max(0, totalDist - item.dist).toFixed(1);
                                return `📍 Salida: ${distStart} km  |  🏁 A Meta: ${distFinish} km`;
                            },
                            label: (item) => {
                                const idx = item.dataIndex;
                                const val = item.raw;
                                const sl = filtered[idx]?.slope;
                                const slopeTxt = sl !== undefined ? ` (Pendiente: ${sl >= 0 ? '+' : ''}${sl.toFixed(1)}%)` : '';

                                const lines = [
                                    `📈 Altitud: ${Math.round(val)} m${slopeTxt}`
                                ];

                                if (currentStageWind && filtered[idx]?.origIndex !== undefined) {
                                    const windAnalysis = getRelativeWindAnalysis(coords, filtered[idx].origIndex, currentStageWind);
                                    const cardDir = getCardinalDirection(currentStageWind.dir);
                                    if (windAnalysis) {
                                        lines.push(`${windAnalysis.emoji} ${windAnalysis.labelText}: ${currentStageWind.speed.toFixed(1)} km/h ${cardDir} (${Math.round(currentStageWind.dir)}°)`);
                                    } else {
                                        lines.push(`💨 Viento: ${currentStageWind.speed.toFixed(1)} km/h ${cardDir} (${Math.round(currentStageWind.dir)}°)`);
                                    }
                                }

                                const climbs = stage?.climbs || [];
                                const totalDist = stage ? stage.distance_km : 0;
                                const currentDist = filtered[idx]?.dist || 0;
                                const nearbyClimb = climbs.find(c => {
                                    if (c.is_finish && (totalDist - currentDist) <= 4.0) {
                                        return true;
                                    }
                                    if (c.summit_index !== undefined) {
                                        return Math.abs((filtered[idx]?.origIndex || 0) - c.summit_index) < 40;
                                    }
                                    return false;
                                });

                                if (nearbyClimb) {
                                    const isMetaTag = nearbyClimb.is_finish ? ' (Final en Alto 🏁)' : '';
                                    const climbName = nearbyClimb.name ? ` - ${nearbyClimb.name}` : '';
                                    lines.push(`⛰️ Puerto ${formatCatLabel(nearbyClimb.category)}${isMetaTag}${climbName} (+${Math.round(nearbyClimb.elevation_gain_m)}m, ${(nearbyClimb.distance_m/1000).toFixed(1)}km, ${nearbyClimb.avg_gradient_pct}%)`);
                                }

                                return lines;
                            },
                            labelColor: (context) => {
                                const idx = context.dataIndex;
                                const item = filtered[idx];
                                if (item && currentStageWind && coords) {
                                    const windAnalysis = getRelativeWindAnalysis(coords, item.origIndex, currentStageWind);
                                    if (windAnalysis) {
                                        return {
                                            borderColor: windAnalysis.colorHex,
                                            backgroundColor: windAnalysis.colorHex,
                                            borderWidth: 2,
                                            borderRadius: 2
                                        };
                                    }
                                }
                                return {
                                    borderColor: '#38bdf8',
                                    backgroundColor: '#38bdf8'
                                };
                            }
                        }
                    }
                },
                scales: {
                    x: {
                        type: 'category',
                        display: true,
                        grid: { color: 'rgba(255,255,255,0.05)' },
                        ticks: {
                            color: '#9ca3af',
                            maxTicksLimit: 10,
                            callback: function(val, idx) {
                                const d = filtered[idx];
                                return d ? 'km ' + d.dist.toFixed(0) : '';
                            }
                        },
                        title: {
                            display: true,
                            text: 'Distancia',
                            color: '#9ca3af',
                            font: { size: 11 }
                        }
                    },
                    y: {
                        display: true,
                        grid: { color: 'rgba(255,255,255,0.05)' },
                        ticks: {
                            color: '#9ca3af',
                            callback: (val) => val + ' m'
                        },
                        title: {
                            display: true,
                            text: 'Elevación (m)',
                            color: '#9ca3af',
                            font: { size: 11 }
                        }
                    }
                }
            }
        });
    }

    function d3Max(arr, accessor) {
        return Math.max(...arr.map(accessor));
    }

    function d3Min(arr, accessor) {
        return Math.min(...arr.map(accessor));
    }

    function getStageTypeClass(stage, index) {
        if (stage.name.includes('PRO')) return 'prelude';
        if (index === 0) return 'prelude';
        if (stage.elevation_gain_m > 4000) return 'mountain';
        return 'flat';
    }

    function getStageType(stage, index) {
        if (stage.name.includes('PRO')) return 'Prólogo';
        if (index === 0) return 'Prólogo';
        if (stage.elevation_gain_m > 4000) return 'Montaña';
        if (stage.elevation_gain_m > 2500) return 'Media-Montaña';
        return 'Llano';
    }

    function formatStageNumber(name) {
        const match = name.match(/^(\d+)/);
        if (match) {
            const num = parseInt(match[1]);
            if (name.includes('PRO')) return 'PRÓLOGO';
            return 'ETAPA ' + num;
        }
        return name;
    }

    function extractRouteFromName(name) {
        let clean = name.replace(/^\d+_(?:ET\d+_|CRI_|PRO_)/, '');
        clean = clean.replace(/_/g, ' ');
        
        if (clean.includes(' - ')) {
            const parts = clean.split(' - ');
            return { from: parts[0].trim(), to: parts[1].trim() };
        }
        
        const dashIdx = clean.lastIndexOf('-');
        if (dashIdx !== -1) {
            const from = clean.substring(0, dashIdx).trim();
            const to = clean.substring(dashIdx + 1).trim();
            return { from, to };
        }
        
        return { from: clean.trim(), to: 'Fin' };
    }

    function escapeHtml(text) {
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }

    // === WIND CANVAS ANIMATION & WEATHER API ENGINE ===
    let windCanvas = null;
    let windCtx = null;
    let windAnimId = null;
    let windParticles = [];

    function initWindCanvas() {
        const mapContainer = document.querySelector('.map-container');
        if (!mapContainer) return;

        if (!windCanvas || !mapContainer.contains(windCanvas)) {
            if (windCanvas && windCanvas.parentNode) {
                windCanvas.parentNode.removeChild(windCanvas);
            }
            windCanvas = document.createElement('canvas');
            windCanvas.className = 'wind-canvas';
            windCanvas.style.position = 'absolute';
            windCanvas.style.inset = '0';
            windCanvas.style.width = '100%';
            windCanvas.style.height = '100%';
            windCanvas.style.pointerEvents = 'none';
            windCanvas.style.zIndex = '400';
            mapContainer.appendChild(windCanvas);
        }

        windCtx = windCanvas.getContext('2d');
        resizeWindCanvas();
    }

    function resizeWindCanvas() {
        if (!windCanvas) return;
        windCanvas.width = windCanvas.clientWidth || windCanvas.offsetWidth || 800;
        windCanvas.height = windCanvas.clientHeight || windCanvas.offsetHeight || 600;
        createWindParticles();
    }

    function createWindParticles() {
        if (!windCanvas) return;
        const numParticles = 110;
        windParticles = [];
        for (let i = 0; i < numParticles; i++) {
            windParticles.push({
                x: Math.random() * windCanvas.width,
                y: Math.random() * windCanvas.height,
                age: Math.floor(Math.random() * 60),
                maxAge: 40 + Math.floor(Math.random() * 60),
                speedScale: 0.7 + Math.random() * 0.6
            });
        }
    }

    function startWindAnimation(speedKmH, directionDeg) {
        initWindCanvas();

        if (windAnimId) {
            cancelAnimationFrame(windAnimId);
            windAnimId = null;
        }

        const rad = (directionDeg + 90) * (Math.PI / 180);
        const dx = Math.cos(rad);
        const dy = Math.sin(rad);

        const baseSpeed = Math.max(0.8, Math.min(5.5, speedKmH / 5.5));

        function animate() {
            if (!windCanvas || !windCtx) return;
            const w = windCanvas.width;
            const h = windCanvas.height;

            // Clear canvas completely on every frame to keep map & route track 100% transparent and visible
            windCtx.clearRect(0, 0, w, h);

            windCtx.lineWidth = 1.3;
            windCtx.lineCap = 'round';

            windParticles.forEach(p => {
                const pSpeed = baseSpeed * p.speedScale;
                const nextX = p.x + dx * pSpeed * 2.5;
                const nextY = p.y + dy * pSpeed * 2.5;

                const alpha = Math.sin((p.age / p.maxAge) * Math.PI) * 0.45;
                windCtx.strokeStyle = `rgba(56, 189, 248, ${alpha.toFixed(2)})`;

                windCtx.beginPath();
                windCtx.moveTo(p.x, p.y);
                windCtx.lineTo(nextX, nextY);
                windCtx.stroke();

                p.x += dx * pSpeed;
                p.y += dy * pSpeed;
                p.age++;

                if (p.age > p.maxAge || p.x < -20 || p.x > w + 20 || p.y < -20 || p.y > h + 20) {
                    p.x = Math.random() * w;
                    p.y = Math.random() * h;
                    p.age = 0;
                    p.maxAge = 50 + Math.floor(Math.random() * 70);
                }
            });

            windAnimId = requestAnimationFrame(animate);
        }

        animate();
    }

    function stopWindAnimation() {
        if (windAnimId) {
            cancelAnimationFrame(windAnimId);
            windAnimId = null;
        }
        if (windCtx && windCanvas) {
            windCtx.clearRect(0, 0, windCanvas.width, windCanvas.height);
        }
    }

    function getCardinalDirection(deg) {
        const directions = ['N', 'NE', 'E', 'SE', 'S', 'SO', 'O', 'NO'];
        const idx = Math.round(((deg % 360) / 45)) % 8;
        return directions[(idx + 8) % 8];
    }

    function formatDateSpanish(fechaStr) {
        if (!fechaStr) return '';
        const parts = fechaStr.split('-');
        if (parts.length === 3) {
            return `${parts[2]}/${parts[1]}/${parts[0]}`;
        }
        return fechaStr;
    }

    function fetchWindData(lat, lon, fechaString) {
        if (!fechaString) fechaString = '2026-08-05';
        const url = `https://api.open-meteo.com/v1/forecast?latitude=${lat.toFixed(4)}&longitude=${lon.toFixed(4)}&hourly=wind_speed_10m,wind_direction_10m&start_date=${fechaString}&end_date=${fechaString}`;

        return fetch(url)
            .then(res => {
                if (!res.ok) throw new Error('Error al obtener meteo');
                return res.json();
            })
            .then(data => {
                if (data && data.hourly && data.hourly.wind_speed_10m && data.hourly.wind_direction_10m) {
                    const idx = 14;
                    const speed = data.hourly.wind_speed_10m[idx] ?? data.hourly.wind_speed_10m[12] ?? 15;
                    const dir = data.hourly.wind_direction_10m[idx] ?? data.hourly.wind_direction_10m[12] ?? 270;
                    return { speed, dir };
                }
                throw new Error('Sin datos de viento');
            })
            .catch(err => {
                console.warn('Fallback viento:', err);
                const dateNum = parseInt(fechaString.replace(/-/g, '')) || 20260805;
                const speed = 12 + (dateNum % 12);
                const dir = (240 + (dateNum % 90)) % 360;
                return { speed, dir };
            });
    }

    function updateStageWind(stage) {
        let lat = 38.72;
        let lon = -9.13;
        let fecha = '2026-08-05';

        if (stage) {
            lat = (stage.start_lat + stage.end_lat) / 2;
            lon = (stage.start_lon + stage.end_lon) / 2;
            if (stage.fecha) fecha = stage.fecha;
        }

        const windWidget = document.getElementById('wind-widget');
        if (windWidget) {
            windWidget.classList.remove('hidden');
        }

        const windTitle = document.getElementById('wind-title');
        const windDetails = document.getElementById('wind-details');
        const windArrow = document.getElementById('wind-compass-arrow');

        if (windTitle) windTitle.textContent = 'Viento: Cargando...';

        fetchWindData(lat, lon, fecha).then(wind => {
            currentStageWind = wind;
            if (windTitle) windTitle.textContent = `Viento: ${wind.speed.toFixed(1)} km/h`;
            const cardDir = getCardinalDirection(wind.dir);
            const fmtDate = formatDateSpanish(fecha);
            if (windDetails) windDetails.textContent = `${fmtDate} • ${cardDir} (${Math.round(wind.dir)}°)`;
            if (windArrow) windArrow.style.transform = `rotate(${wind.dir + 180}deg)`;

            startWindAnimation(wind.speed, wind.dir);
        });
    }

    window.addEventListener('resize', resizeWindCanvas);

    document.addEventListener('DOMContentLoaded', init);
})();
