(function () {
  "use strict";

  const INEGI_URL = "https://gaia.inegi.org.mx/wscatgeo/v2/geo/mgee/";
  const DATA = "data/";
  const PLAY_MS = 900;

  const PARTIDO_COLOR = {
    "Partido Revolucionario Institucional": "#006847",
    "Partido Acción Nacional": "#053689",
    "Partido de la Revolución Democrática": "#f4c430",
    "Movimiento de Regeneración Nacional": "#7b0323",
    "Movimiento Regeneración Nacional": "#7b0323",
    "Movimiento Ciudadano": "#ff7f27",
    "Partido Verde Ecologista de México": "#1e7140",
    "Partido Encuentro Social": "#621054",
    Independiente: "#6b7280",
    Desconocido: "#b8b4ac",
  };

  const svg = d3.select("#map");
  const mapWrap = document.getElementById("map-wrap");
  const tooltip = document.getElementById("tooltip");
  const loading = document.getElementById("loading");
  const loadingText = document.getElementById("loading-text");
  const dateDisplay = document.getElementById("date-display");
  const slider = document.getElementById("time-slider");
  const changesList = document.getElementById("changes-list");
  const legendList = document.getElementById("legend-list");
  const btnPlay = document.getElementById("btn-play");
  const btnStep = document.getElementById("btn-step");

  const projection = d3.geoMercator();
  const path = d3.geoPath().projection(projection);
  const parseDate = d3.utcParse("%Y-%m-%d");
  const formatDate = d3.utcFormat("%d %b %Y");
  const formatYear = d3.utcFormat("%Y");

  let width = 900;
  let height = 520;
  let geojson = null;
  let mandatosByEstado = new Map();
  let fechasClave = [];
  let dateMin = null;
  let dateMax = null;
  let currentDate = null;
  let sliderIndex = 0;
  let playing = false;
  let playTimer = null;

  const g = svg.append("g");

  function setLoading(on, text) {
    if (text) loadingText.textContent = text;
    loading.hidden = !on;
  }

  function colorPartido(partido) {
    return PARTIDO_COLOR[partido] || PARTIDO_COLOR.Desconocido;
  }

  function normalizePartido(p) {
    if (!p) return "Desconocido";
    if (p === "Movimiento Regeneración Nacional") return "Movimiento de Regeneración Nacional";
    return p;
  }

  function resize() {
    const rect = mapWrap.getBoundingClientRect();
    width = Math.max(300, rect.width);
    height = Math.round(width * 0.56);
    svg.attr("viewBox", `0 0 ${width} ${height}`);
    if (geojson) {
      projection.fitSize([width, height], geojson);
      g.selectAll("path.estado").attr("d", path);
    }
  }

  function mandatoEnFecha(estado, when) {
    const lista = mandatosByEstado.get(estado);
    if (!lista) return null;
    const t = when.getTime();
    for (const m of lista) {
      const ini = parseDate(m.inicio).getTime();
      const fin = m.fin ? parseDate(m.fin).getTime() : Infinity;
      if (t >= ini && t <= fin) return m;
    }
    return null;
  }

  function cambiosEnFecha(when) {
    const iso = d3.utcFormat("%Y-%m-%d")(when);
    const entran = [];
    const salen = [];

    for (const [estado, lista] of mandatosByEstado) {
      for (const m of lista) {
        if (m.inicio === iso) entran.push({ estado, ...m, tipo: "entra" });
        if (m.fin === iso) salen.push({ estado, ...m, tipo: "sale" });
      }
    }
    return { entran, salen, iso };
  }

  function updateChangesPanel(when) {
    const { entran, salen } = cambiosEnFecha(when);
    changesList.innerHTML = "";

    if (!entran.length && !salen.length) {
      changesList.innerHTML = '<li class="empty">Sin cambios de gobernador en esta fecha</li>';
      return;
    }

    for (const c of entran) {
      const li = document.createElement("li");
      li.innerHTML = `<strong>${c.estado}</strong> → ${c.nombre.replace(/\s*\([^)]*\)/g, "")}<br><span style="color:${colorPartido(c.partido)}">${c.partido}</span>`;
      changesList.appendChild(li);
    }
    for (const c of salen) {
      const li = document.createElement("li");
      li.innerHTML = `<strong>${c.estado}</strong> ← termina mandato de ${c.nombre.replace(/\s*\([^)]*\)/g, "")}`;
      li.style.opacity = "0.75";
      changesList.appendChild(li);
    }
  }

  function renderLegend(partidos) {
    legendList.innerHTML = "";
    const orden = [
      "Partido Revolucionario Institucional",
      "Partido Acción Nacional",
      "Partido de la Revolución Democrática",
      "Movimiento de Regeneración Nacional",
      "Movimiento Ciudadano",
      "Partido Verde Ecologista de México",
      "Partido Encuentro Social",
      "Independiente",
      "Desconocido",
    ];
    const mostrar = orden.filter((p) => partidos.includes(p));
    for (const p of partidos) {
      if (!mostrar.includes(p)) mostrar.push(p);
    }
    mostrar.push("Sin datos");

    for (const p of mostrar) {
      const li = document.createElement("li");
      const sw = document.createElement("span");
      sw.className = "legend-swatch";
      sw.style.background = p === "Sin datos" ? "var(--sin-datos)" : colorPartido(p);
      li.appendChild(sw);
      li.appendChild(document.createTextNode(p === "Sin datos" ? "Sin datos en CSV" : p));
      legendList.appendChild(li);
    }
  }

  function showTooltip(event, d, info) {
    tooltip.hidden = false;
    const bounds = mapWrap.getBoundingClientRect();
    if (!info) {
      tooltip.innerHTML = `<strong>${d.properties.estado_csv || d.properties.nomgeo_inegi}</strong>Sin datos de gobernador`;
    } else {
      tooltip.innerHTML = `<strong>${info.estado}</strong>${info.nombre}<br>${info.partido}<br><em>${info.periodo}</em>`;
    }
    tooltip.style.left = `${event.clientX - bounds.left}px`;
    tooltip.style.top = `${event.clientY - bounds.top}px`;
  }

  function hideTooltip() {
    tooltip.hidden = true;
  }

  function renderMap(when) {
    currentDate = when;
    dateDisplay.textContent = formatDate(when);
    updateChangesPanel(when);

    const iso = d3.utcFormat("%Y-%m-%d")(when);
    const cambioEstados = new Set([
      ...cambiosEnFecha(when).entran.map((c) => c.estado),
      ...cambiosEnFecha(when).salen.map((c) => c.estado),
    ]);

    g.selectAll("path.estado")
      .attr("fill", (d) => {
        const estado = d.properties.estado_csv;
        if (!estado) return "var(--sin-datos)";
        const m = mandatoEnFecha(estado, when);
        return m ? colorPartido(m.partido) : "var(--sin-datos)";
      })
      .classed("is-changing", (d) => cambioEstados.has(d.properties.estado_csv));
  }

  function setDateFromSlider(index) {
    sliderIndex = Math.max(0, Math.min(fechasClave.length - 1, index));
    slider.value = sliderIndex;
    renderMap(parseDate(fechasClave[sliderIndex]));
  }

  function stepForward() {
    if (sliderIndex >= fechasClave.length - 1) {
      setDateFromSlider(0);
    } else {
      setDateFromSlider(sliderIndex + 1);
    }
  }

  function togglePlay() {
    playing = !playing;
    btnPlay.textContent = playing ? "⏸ Pausar" : "▶ Reproducir";
    if (playing) {
      playTimer = setInterval(() => {
        if (sliderIndex >= fechasClave.length - 1) {
          togglePlay();
          return;
        }
        stepForward();
      }, PLAY_MS);
    } else {
      clearInterval(playTimer);
    }
  }

  function indexForDate(when) {
    const iso = d3.utcFormat("%Y-%m-%d")(when);
    let idx = fechasClave.indexOf(iso);
    if (idx >= 0) return idx;
    const t = when.getTime();
    for (let i = fechasClave.length - 1; i >= 0; i--) {
      if (parseDate(fechasClave[i]).getTime() <= t) return i;
    }
    return 0;
  }

  async function loadGeojson() {
    const local = await fetch(DATA + "estados_inegi.geojson");
    if (local.ok) return local.json();

    loadingText.textContent = "Descargando INEGI…";
    const remote = await fetch(INEGI_URL);
    if (!remote.ok) throw new Error("No se pudo cargar geometría INEGI");
    const raw = await remote.json();
    raw.features.forEach((f) => {
      f.properties.estado_csv = f.properties.nomgeo;
    });
    return raw;
  }

  function buildMandatosIndex(mandatos) {
    mandatosByEstado = d3.group(mandatos, (d) => d.estado);
    for (const [k, v] of mandatosByEstado) {
      mandatosByEstado.set(
        k,
        v.sort((a, b) => a.inicio.localeCompare(b.inicio))
      );
    }
  }

  async function init() {
    setLoading(true);
    window.addEventListener("resize", resize);

    slider.addEventListener("input", () => setDateFromSlider(+slider.value));
    btnPlay.addEventListener("click", togglePlay);
    btnStep.addEventListener("click", stepForward);

    const [geo, mandatosResp] = await Promise.all([
      loadGeojson(),
      fetch(DATA + "mandatos.json"),
    ]);

    if (!mandatosResp.ok) throw new Error("No se pudo cargar mandatos.json");
    const mandatosData = await mandatosResp.json();

    geojson = geo;
    buildMandatosIndex(mandatosData.mandatos);

    fechasClave = mandatosData.fechas_clave.length
      ? mandatosData.fechas_clave
      : [mandatosData.rango.min, mandatosData.rango.max];

    dateMin = parseDate(mandatosData.rango.min);
    dateMax = parseDate(mandatosData.rango.max);

    document.getElementById("label-min").textContent = formatYear(dateMin);
    document.getElementById("label-max").textContent = formatYear(dateMax);

    slider.min = 0;
    slider.max = fechasClave.length - 1;
    slider.step = 1;

    renderLegend(mandatosData.partidos.map(normalizePartido));

    projection.fitSize([width, height], geojson);

    g.selectAll("path.estado")
      .data(geojson.features, (d) => d.properties.cvegeo)
      .join("path")
      .attr("class", "estado")
      .attr("d", path)
      .on("mouseenter", function (event, d) {
        d3.select(this).classed("is-hovered", true);
        const info = mandatoEnFecha(d.properties.estado_csv, currentDate);
        showTooltip(event, d, info);
      })
      .on("mousemove", function (event, d) {
        const info = mandatoEnFecha(d.properties.estado_csv, currentDate);
        showTooltip(event, d, info);
      })
      .on("mouseleave", function () {
        d3.select(this).classed("is-hovered", false);
        hideTooltip();
      });

    resize();
    setDateFromSlider(indexForDate(parseDate("1992-12-01")));
    setLoading(false);
  }

  init().catch((err) => {
    console.error(err);
    setLoading(false);
    dateDisplay.textContent = "Error";
    loadingText.textContent = "Error al cargar. Usa servidor local en mapa/gobernadores/.";
    loading.hidden = false;
  });
})();
