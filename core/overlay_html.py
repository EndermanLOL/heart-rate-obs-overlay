"""
overlay_html.py

Contiene la pagina HTML/CSS/JS que se sirve como overlay para OBS
(Fuente de Navegador). No tiene dependencias externas: todo el estilo y
la logica de refresco viven en este mismo archivo.
"""

OVERLAY_HTML = """<!DOCTYPE html>
<html lang="es">
<head>
<meta charset="UTF-8">
<title>Heart Rate Overlay</title>
<style>
    html, body {
        margin: 0;
        padding: 0;
        background: transparent;
        overflow: hidden;
        width: 100%;
        height: 100%;
    }
    body.bg-black {
        background: #000000 !important;
    }
    body.chroma-key {
        background: #00ff00 !important;
    }
    #wrap {
        display: flex;
        flex-direction: column;
        align-items: center;
        justify-content: center;
        gap: 14px;
        width: 100vw;
        height: 100vh;
        font-family: 'Segoe UI', Arial, sans-serif;
        box-sizing: border-box;
        padding: 16px;
    }
    #card {
        display: flex;
        align-items: center;
        gap: 12px;
        padding: 10px 22px;
        border-radius: 999px;
        background: rgba(0, 0, 0, 0.0);
    }
    #heart {
        font-size: 42px;
        color: #ff2d55;
        text-shadow: 0 0 8px rgba(255, 45, 85, 0.9);
        animation: beat 1s infinite ease-in-out;
        transform-origin: center;
        display: inline-block;
    }
    #heart.paused { animation: none; opacity: 0.35; }
    /* Intensidad del latido segun la zona de BPM: mas alto -> laton mas grande/brusco */
    #heart.zone-low    { --beat-scale: 1.15; }
    #heart.zone-mid    { --beat-scale: 1.28; }
    #heart.zone-high   { --beat-scale: 1.42; }
    #heart.zone-max    { --beat-scale: 1.55; }
    #bpm {
        font-size: 42px;
        font-weight: 700;
        color: #ffffff;
        text-shadow: 0 0 6px rgba(0,0,0,0.85), 0 0 2px rgba(0,0,0,0.9);
    }
    #unit {
        font-size: 20px;
        font-weight: 600;
        color: #ffffff;
        text-shadow: 0 0 6px rgba(0,0,0,0.85);
        align-self: flex-end;
        margin-bottom: 8px;
    }
    @keyframes beat {
        0%   { transform: scale(1); }
        15%  { transform: scale(var(--beat-scale, 1.25)); }
        30%  { transform: scale(1); }
        45%  { transform: scale(calc(1 + (var(--beat-scale, 1.25) - 1) * 0.6)); }
        60%  { transform: scale(1); }
        100% { transform: scale(1); }
    }

    /* ---------------- Controles (esquina superior derecha) ---------------- */
    #controls {
        position: fixed;
        top: 10px;
        right: 10px;
        z-index: 10;
        display: flex;
        flex-direction: column;
        align-items: flex-end;
        gap: 6px;
    }
    #controls button {
        background: rgba(255, 255, 255, 0.08);
        color: #ffffff;
        border: 1px solid rgba(255, 255, 255, 0.25);
        border-radius: 6px;
        font-size: 12px;
        font-family: 'Segoe UI', Arial, sans-serif;
        padding: 4px 8px;
        cursor: pointer;
    }
    #controls button:hover { background: rgba(255, 255, 255, 0.18); }
    #bg-toggle.mode-black {
        background: #000000;
        color: #ffffff;
        border-color: #555;
    }
    #bg-toggle.mode-chroma {
        background: #00ff00;
        color: #000000;
        border-color: #00ff00;
        font-weight: 700;
    }

    /* ---------------- Panel de estadisticas ---------------- */
    #stats-panel {
        display: none;
        width: 280px;
        max-width: 90vw;
        background: rgba(20, 20, 20, 0.85);
        border: 1px solid rgba(255, 255, 255, 0.15);
        border-radius: 10px;
        padding: 12px 14px;
        color: #ffffff;
        font-family: 'Segoe UI', Arial, sans-serif;
        box-sizing: border-box;
    }
    #stats-panel.visible { display: block; }

    #stats-clock {
        font-size: 14px;
        font-weight: 600;
        color: #cfcfcf;
        margin-bottom: 8px;
        text-align: center;
        letter-spacing: 0.5px;
    }
    #stats-summary {
        display: flex;
        justify-content: space-between;
        font-size: 12px;
        color: #cfcfcf;
        margin-bottom: 8px;
        padding-bottom: 8px;
        border-bottom: 1px solid rgba(255,255,255,0.15);
    }
    #stats-summary div { text-align: center; flex: 1; }
    #stats-summary span.label { display: block; font-size: 10px; color: #888; text-transform: uppercase; }
    #stats-summary span.value { display: block; font-size: 16px; font-weight: 700; color: #fff; }

    #stats-chart-wrap {
        margin-bottom: 10px;
        padding-bottom: 10px;
        border-bottom: 1px solid rgba(255,255,255,0.15);
    }
    #stats-chart { width: 100%; height: 70px; display: block; overflow: visible; }
    #stats-chart .grid-line { stroke: rgba(255,255,255,0.12); stroke-width: 1; }
    #stats-chart .bpm-line {
        fill: none;
        stroke: #ff2d55;
        stroke-width: 2;
        stroke-linejoin: round;
        stroke-linecap: round;
    }
    #stats-chart .bpm-fill { fill: rgba(255, 45, 85, 0.15); stroke: none; }
    #stats-chart .bpm-dot { fill: #ff2d55; }
    #stats-chart .chart-label { fill: #888; font-size: 8px; font-family: 'Segoe UI', Arial, sans-serif; }
    #stats-chart-empty { font-size: 11px; color: #666; text-align: center; padding: 20px 0; }

    #stats-log {
        max-height: 160px;
        overflow-y: auto;
        font-size: 12px;
    }
    #stats-log table { width: 100%; border-collapse: collapse; }
    #stats-log td { padding: 2px 4px; }
    #stats-log td.time { color: #888; width: 45%; }
    #stats-log td.bpm { text-align: right; font-weight: 600; color: #ff6b81; }
    #stats-log tr:first-child td { color: #fff; }
    #stats-log tr:first-child td.bpm { color: #ff2d55; }
</style>
</head>
<body>
<div id="controls">
    <button id="bg-toggle">Fondo: Transparente</button>
    <button id="stats-toggle">Mostrar estadisticas</button>
</div>
<div id="wrap">
    <div id="card">
        <span id="heart" class="zone-low">&#9829;</span>
        <span id="bpm">--</span>
        <span id="unit">BPM</span>
    </div>
    <div id="stats-panel">
        <div id="stats-clock">--:--:--</div>
        <div id="stats-summary">
            <div><span class="label">Min</span><span class="value" id="stat-min">--</span></div>
            <div><span class="label">Prom</span><span class="value" id="stat-avg">--</span></div>
            <div><span class="label">Max</span><span class="value" id="stat-max">--</span></div>
        </div>
        <div id="stats-chart-wrap">
            <svg id="stats-chart" viewBox="0 0 260 70" preserveAspectRatio="none"></svg>
            <div id="stats-chart-empty">Esperando datos para graficar...</div>
        </div>
        <div id="stats-log">
            <table id="stats-table"><tbody></tbody></table>
        </div>
    </div>
</div>
<script>
    // Mostrar el panel de estadisticas por defecto si la URL trae ?stats=1
    // (util para incrustarlo directamente en OBS sin tener que hacer clic).
    const urlParams = new URLSearchParams(window.location.search);
    let statsVisible = urlParams.get('stats') === '1';

    // Modo de fondo: 'transparent' (recomendado para OBS Browser Source, que
    // soporta transparencia real), 'black' o 'chroma' (verde, por si necesitas
    // chroma key en un programa que no soporte canal alfa).
    const BG_MODES = ['transparent', 'black', 'chroma'];
    const BG_LABELS = {
        transparent: 'Fondo: Transparente',
        black: 'Fondo: Negro',
        chroma: 'Fondo: Verde (Chroma Key)',
    };
    let bgMode = BG_MODES.includes(urlParams.get('bg')) ? urlParams.get('bg') : 'transparent';

    const bgBtn = document.getElementById('bg-toggle');

    function applyBgMode() {
        document.body.classList.remove('bg-black', 'chroma-key');
        if (bgMode === 'black') document.body.classList.add('bg-black');
        if (bgMode === 'chroma') document.body.classList.add('chroma-key');

        bgBtn.classList.remove('mode-black', 'mode-chroma');
        if (bgMode === 'black') bgBtn.classList.add('mode-black');
        if (bgMode === 'chroma') bgBtn.classList.add('mode-chroma');

        bgBtn.textContent = BG_LABELS[bgMode];
    }
    applyBgMode();

    bgBtn.addEventListener('click', () => {
        const idx = BG_MODES.indexOf(bgMode);
        bgMode = BG_MODES[(idx + 1) % BG_MODES.length];
        applyBgMode();
    });

    const toggleBtn = document.getElementById('stats-toggle');
    const statsPanel = document.getElementById('stats-panel');
    const statsTableBody = document.querySelector('#stats-table tbody');
    const chartSvg = document.getElementById('stats-chart');
    const chartEmpty = document.getElementById('stats-chart-empty');
    const SVG_NS = 'http://www.w3.org/2000/svg';
    const CHART_W = 260;
    const CHART_H = 70;
    const CHART_PAD = 6;

    const history = [];       // { time: Date, bpm: number }
    const MAX_HISTORY = 30;    // cuantas lecturas guardar en el panel
    let lastLoggedBpm = null;

    function applyStatsVisibility() {
        statsPanel.classList.toggle('visible', statsVisible);
        toggleBtn.textContent = statsVisible ? 'Ocultar estadisticas' : 'Mostrar estadisticas';
    }
    applyStatsVisibility();

    toggleBtn.addEventListener('click', () => {
        statsVisible = !statsVisible;
        applyStatsVisibility();
    });

    function formatTime(d) {
        return d.toLocaleTimeString('es-MX', { hour12: false });
    }

    function renderStats() {
        document.getElementById('stats-clock').textContent = formatTime(new Date());

        if (history.length === 0) {
            document.getElementById('stat-min').textContent = '--';
            document.getElementById('stat-avg').textContent = '--';
            document.getElementById('stat-max').textContent = '--';
            statsTableBody.innerHTML = '';
            renderChart([], 0, 0);
            return;
        }

        const values = history.map(h => h.bpm);
        const min = Math.min(...values);
        const max = Math.max(...values);
        const avg = Math.round(values.reduce((a, b) => a + b, 0) / values.length);

        document.getElementById('stat-min').textContent = min;
        document.getElementById('stat-avg').textContent = avg;
        document.getElementById('stat-max').textContent = max;

        statsTableBody.innerHTML = history
            .slice()
            .reverse()
            .map(h => `<tr><td class="time">${formatTime(h.time)}</td><td class="bpm">${h.bpm}</td></tr>`)
            .join('');

        renderChart(values, min, max);
    }

    function renderChart(values, min, max) {
        chartSvg.innerHTML = '';

        if (values.length < 2) {
            chartEmpty.style.display = 'block';
            chartSvg.style.display = 'none';
            return;
        }
        chartEmpty.style.display = 'none';
        chartSvg.style.display = 'block';

        const range = Math.max(1, max - min);
        const yMin = min - range * 0.15;
        const yMax = max + range * 0.15;
        const yRange = Math.max(1, yMax - yMin);

        const innerW = CHART_W - CHART_PAD * 2;
        const innerH = CHART_H - CHART_PAD * 2;

        const points = values.map((v, i) => {
            const x = CHART_PAD + (i / (values.length - 1)) * innerW;
            const y = CHART_PAD + innerH - ((v - yMin) / yRange) * innerH;
            return [x, y];
        });

        for (let i = 0; i <= 2; i++) {
            const gy = CHART_PAD + (innerH / 2) * i;
            const line = document.createElementNS(SVG_NS, 'line');
            line.setAttribute('x1', CHART_PAD);
            line.setAttribute('x2', CHART_W - CHART_PAD);
            line.setAttribute('y1', gy);
            line.setAttribute('y2', gy);
            line.setAttribute('class', 'grid-line');
            chartSvg.appendChild(line);
        }

        const areaPath = 'M' + points.map(p => p.join(',')).join(' L')
            + ` L${points[points.length - 1][0]},${CHART_PAD + innerH}`
            + ` L${points[0][0]},${CHART_PAD + innerH} Z`;
        const area = document.createElementNS(SVG_NS, 'path');
        area.setAttribute('d', areaPath);
        area.setAttribute('class', 'bpm-fill');
        chartSvg.appendChild(area);

        const linePath = 'M' + points.map(p => p.join(',')).join(' L');
        const line = document.createElementNS(SVG_NS, 'path');
        line.setAttribute('d', linePath);
        line.setAttribute('class', 'bpm-line');
        chartSvg.appendChild(line);

        const [lastX, lastY] = points[points.length - 1];
        const dot = document.createElementNS(SVG_NS, 'circle');
        dot.setAttribute('cx', lastX);
        dot.setAttribute('cy', lastY);
        dot.setAttribute('r', 2.6);
        dot.setAttribute('class', 'bpm-dot');
        chartSvg.appendChild(dot);

        const maxLabel = document.createElementNS(SVG_NS, 'text');
        maxLabel.setAttribute('x', CHART_PAD);
        maxLabel.setAttribute('y', CHART_PAD + 7);
        maxLabel.setAttribute('class', 'chart-label');
        maxLabel.textContent = max;
        chartSvg.appendChild(maxLabel);

        const minLabel = document.createElementNS(SVG_NS, 'text');
        minLabel.setAttribute('x', CHART_PAD);
        minLabel.setAttribute('y', CHART_H - 2);
        minLabel.setAttribute('class', 'chart-label');
        minLabel.textContent = min;
        chartSvg.appendChild(minLabel);
    }

    function zoneForBpm(bpm) {
        if (bpm < 90) return 'zone-low';
        if (bpm < 120) return 'zone-mid';
        if (bpm < 150) return 'zone-high';
        return 'zone-max';
    }

    async function updateBpm() {
        try {
            const res = await fetch('/bpm', { cache: 'no-store' });
            const data = await res.json();
            const bpmEl = document.getElementById('bpm');
            const heartEl = document.getElementById('heart');

            if (data.live && data.bpm > 0) {
                bpmEl.textContent = data.bpm;
                heartEl.classList.remove('paused');
                heartEl.style.animationDuration = Math.max(0.35, 60 / data.bpm) + 's';
                heartEl.classList.remove('zone-low', 'zone-mid', 'zone-high', 'zone-max');
                heartEl.classList.add(zoneForBpm(data.bpm));

                if (data.bpm !== lastLoggedBpm) {
                    history.push({ time: new Date(), bpm: data.bpm });
                    if (history.length > MAX_HISTORY) history.shift();
                    lastLoggedBpm = data.bpm;
                }
            } else {
                bpmEl.textContent = '--';
                heartEl.classList.add('paused');
            }
        } catch (err) {
            // Si el servidor aun no responde, no hacemos nada; se reintenta en el proximo ciclo.
        }
        renderStats();
    }
    updateBpm();
    setInterval(updateBpm, 1000);
</script>
</body>
</html>
"""
