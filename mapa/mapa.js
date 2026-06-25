(function () {
  "use strict";

  const DATA_BASE = "data/";
  const svg = d3.select("#map");
  const mapWrap = document.getElementById("map-wrap");
  const tooltip = document.getElementById("tooltip");
  const subtitle = document.getElementById("subtitle");
  const btnBack = document.getElementById("btn-back");
  const loadingEl = document.getElementById("loading");
  const loadingText = document.getElementById("loading-text");

  const projection = d3.geoMercator();
  const path = d3.geoPath().projection(projection);
  const color = d3.scaleOrdinal(d3.schemeTableau10);

  let width = 960;
  let height = 560;
  let estadosFc = null;
  let slugByName = new Map();
  let view = "nacional";
  let activeState = null;

  const g = svg.append("g").attr("class", "map-layer");

  function resize() {
    const rect = mapWrap.getBoundingClientRect();
    width = Math.max(320, rect.width);
    height = Math.round(width * 0.58);
    svg.attr("viewBox", `0 0 ${width} ${height}`);
    if (estadosFc) fitAndDraw(getCurrentFc());
  }

  function getCurrentFc() {
    if (view === "nacional") return estadosFc;
    const sel = g.selectAll("path.region--municipio");
    if (sel.empty()) return estadosFc;
    return {
      type: "FeatureCollection",
      features: sel.data(),
    };
  }

  function fitProjection(geojson) {
    projection.fitSize([width, height], geojson);
    path.projection(projection);
  }

  function regionName(d) {
    return d.properties.NAME_2 || d.properties.NAME_1 || "";
  }

  function showTooltip(event, name) {
    if (!name) return;
    tooltip.hidden = false;
    tooltip.textContent = name;
    const bounds = mapWrap.getBoundingClientRect();
    tooltip.style.left = `${event.clientX - bounds.left}px`;
    tooltip.style.top = `${event.clientY - bounds.top}px`;
  }

  function hideTooltip() {
    tooltip.hidden = true;
  }

  function setLoading(on) {
    loadingEl.hidden = !on;
  }

  function bindInteractions(selection, clickable) {
    selection
      .on("mouseenter", function (event, d) {
        d3.select(this).classed("is-hovered", true);
        showTooltip(event, regionName(d));
      })
      .on("mousemove", (event, d) => showTooltip(event, regionName(d)))
      .on("mouseleave", function () {
        d3.select(this).classed("is-hovered", false);
        hideTooltip();
      });

    if (clickable) {
      selection.on("click", (event, d) => {
        event.stopPropagation();
        if (view === "nacional") enterState(d);
      });
    }
  }

  function drawRegions(features, layerClass, keyFn, clickable) {
    const joined = g
      .selectAll(`path.${layerClass}`)
      .data(features, keyFn);

    joined.exit().remove();

    const enter = joined
      .enter()
      .append("path")
      .attr("class", `region ${layerClass}`)
      .attr("fill", (d) =>
        layerClass === "region--municipio" ? color(keyFn(d)) : null
      );

    joined
      .merge(enter)
      .attr("d", path)
      .style("opacity", 1)
      .call((sel) => bindInteractions(sel, clickable));
  }

  function fitAndDraw(geojson) {
    fitProjection(geojson);
    if (view === "nacional") {
      svg.classed("view--estados", true);
      drawRegions(
        geojson.features,
        "region--estado",
        (d) => d.properties.NAME_1,
        true
      );
      g.selectAll("path.region--municipio").remove();
    } else {
      svg.classed("view--estados", false);
      g.selectAll("path.region--estado").remove();
      drawRegions(
        geojson.features,
        "region--municipio",
        (d) => d.properties.NAME_2,
        false
      );
    }
  }

  function renderNacional() {
    view = "nacional";
    activeState = null;
    btnBack.hidden = true;
    subtitle.textContent = "Divisiones estatales — haz clic en un estado";
    document.querySelector(".header__title").textContent = "México";
    fitAndDraw(estadosFc);
  }

  async function enterState(estadoFeature) {
    const name = estadoFeature.properties.NAME_1;
    const entry = slugByName.get(name);
    if (!entry) {
      console.warn("Sin datos municipales para:", name);
      return;
    }

    loadingText.textContent = "Cargando municipios…";
    setLoading(true);
    try {
      const resp = await fetch(DATA_BASE + entry.file);
      if (!resp.ok) throw new Error(resp.statusText);
      const municipiosFc = await resp.json();

      view = "estatal";
      activeState = name;
      btnBack.hidden = false;
      subtitle.textContent = `${municipiosFc.features.length} municipios`;
      document.querySelector(".header__title").textContent = name;

      fitAndDraw(municipiosFc);
    } catch (err) {
      console.error(err);
      subtitle.textContent = `Error al cargar municipios de ${name}`;
    } finally {
      setLoading(false);
    }
  }

  async function init() {
    loadingText.textContent = "Cargando mapa…";
    setLoading(true);

    window.addEventListener("resize", resize);
    btnBack.addEventListener("click", renderNacional);

    const [estadosResp, indexResp] = await Promise.all([
      fetch(DATA_BASE + "estados.geojson"),
      fetch(DATA_BASE + "index.json"),
    ]);

    if (!estadosResp.ok) throw new Error("No se pudo cargar estados.geojson");
    estadosFc = await estadosResp.json();

    const index = await indexResp.json();
    slugByName = new Map(index.map((e) => [e.name, e]));

    resize();
    renderNacional();
    setLoading(false);
  }

  init().catch((err) => {
    console.error(err);
    setLoading(false);
    subtitle.textContent =
      "Error al cargar el mapa. Usa un servidor local (ver README en mapa/).";
  });
})();
