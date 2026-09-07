(() => {
  "use strict";
  const data = window.TRIP_DATA;
  const warning = document.getElementById("map-warning");
  function showWarning(message) {
    warning.hidden = false;
    warning.textContent = message;
  }
  if (!data || !window.L) {
    showWarning("地图数据或绘图库未能加载。请确保 data.js、app.js、leaflet.js 与 HTML 在同一文件夹，再刷新。");
    return;
  }
  const cityId = document.body.dataset.city;
  const city = data.cities[cityId];
  if (!city) {
    showWarning("未知城市，无法打开地图。");
    return;
  }
  const points = new Map(data.points.map(point => [point.id, point]));
  const params = new URLSearchParams(location.search);
  let activeDay = city.days.includes(params.get("day")) ? params.get("day") : "all";
  let showNames = true;
  let showRouteLabels = true;
  const visibleLegs = () => data.legs.filter(leg =>
    city.days.includes(leg.day) &&
    (points.get(leg.from).city === cityId || points.get(leg.to).city === cityId) &&
    (activeDay === "all" || leg.day === activeDay)
  );
  const modes = {walk: "🚶", transit: "🚋", rail: "🚆", intercity: "🚆"};
  const escape = value => String(value).replace(/[&<>"']/g, char =>
    ({"&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;"}[char]));
  const numberFor = new Map(data.points.map((point, index) => [point.id, index + 1]));
  const map = L.map("map", {scrollWheelZoom: true}).setView(city.center, city.zoom);
  const tiles = L.tileLayer("https://tile.openstreetmap.org/{z}/{x}/{y}.png", {
    maxZoom: 19,
    attribution: '&copy; <a href="https://www.openstreetmap.org/copyright" target="_blank" rel="noopener">OpenStreetMap</a> contributors',
    crossOrigin: true,
  }).addTo(map);
  let tileErrors = 0;
  tiles.on("tileerror", () => {
    tileErrors += 1;
    if (tileErrors >= 3) showWarning("部分底图未能加载，请检查网络。旗标和路线数据仍可查看；步行路线不是实时导航。");
  });
  const routeLayer = L.layerGroup().addTo(map);
  const markerLayer = L.layerGroup().addTo(map);
  const markers = new Map();
  const polylines = new Map();
  const labelPairs = [];

  function directions(leg) {
    const from = points.get(leg.from);
    const to = points.get(leg.to);
    const query = new URLSearchParams({
      api: "1",
      origin: from.coords.join(","),
      destination: to.coords.join(","),
      travelmode: leg.mode === "walk" ? "walking" : "transit",
    });
    return "https://www.google.com/maps/dir/?" + query;
  }
  function pointMap(point) {
    return "https://www.openstreetmap.org/?mlat=" + point.coords[0] + "&mlon=" +
      point.coords[1] + "#map=17/" + point.coords.join("/");
  }
  function distanceText(leg) {
    return leg.distance === null ? "" : `${(leg.distance / 1000).toFixed(2)} km · 约 ${leg.duration} 分钟`;
  }
  function labelText(leg) {
    return leg.mode === "walk" ? `🚶 ${distanceText(leg)}` : `${modes[leg.mode]} ${leg.label}`;
  }
  function mapLabel(leg) {
    if (leg.mode === "walk") return `🚶 ${(leg.distance / 1000).toFixed(2)} km`;
    if (leg.mode === "intercity") return "🚆 RE / RB · 30–60 分";
    if (leg.mode === "rail") return leg.from === "d-airport" ? "🚆 S11 · 约 15 分" : "🚆 S19 / 区域车 · 15–25 分";
    return "🚋 公交 / 地铁＋步行";
  }
  function routePopup(leg) {
    return `<h3>${escape(points.get(leg.from).name)} → ${escape(points.get(leg.to).name)}</h3>
      <div class="popup-day" style="--day-color:${data.days[leg.day].color}">${data.days[leg.day].label} · ${escape(leg.depart)} 出发</div>
      <p>${escape(labelText(leg))}</p><p>${escape(leg.note || (leg.mode === "walk" ? "沿街道路网估算；入口、红绿灯、施工可能改变用时。" : "这条线是交通方式示意，不是实际行驶路径或实时班次。"))}</p>
      <a href="${directions(leg)}" target="_blank" rel="noopener">打开此段步行 / 公交导航 ↗</a>`;
  }
  function pointPopup(point, legs) {
    const visits = legs.filter(leg => leg.to === point.id || leg.from === point.id);
    return `<h3>🚩 ${escape(point.name)}</h3>
      ${point.note ? `<p>${escape(point.note)}</p>` : ""}
      <a href="${pointMap(point)}" target="_blank" rel="noopener">在 OpenStreetMap 中查看 ↗</a>
      <div class="popup-stops">${visits.map(leg => `<div><span class="popup-day" style="--day-color:${data.days[leg.day].color}">${data.days[leg.day].label}</span>
      ${escape(leg.from === point.id ? leg.depart + " 出发 → " + points.get(leg.to).name : leg.arrival + " 抵达")}</div>`).join("")}</div>`;
  }
  function updateLabels() {
    const namesVisible = showNames && map.getZoom() >= 14;
    markers.forEach(marker => namesVisible ? marker.openTooltip() : marker.closeTooltip());
    labelPairs.forEach(({line}) => {
      if (showRouteLabels && map.getZoom() >= 13) line.openTooltip();
      else line.closeTooltip();
    });
  }
  function renderMap() {
    routeLayer.clearLayers();
    markerLayer.clearLayers();
    markers.clear();
    polylines.clear();
    labelPairs.length = 0;
    const legs = visibleLegs();
    const used = new Set(legs.flatMap(leg => [leg.from, leg.to]));
    for (const leg of legs) {
      const color = data.days[leg.day].color;
      const line = L.polyline(leg.geometry, {
        color, weight: leg.mode === "walk" ? 4 : 5, opacity: .8,
        dashArray: leg.mode === "walk" ? "3 7" : null,
      }).addTo(routeLayer);
      line.bindPopup(routePopup(leg));
      line.bindTooltip(`<span style="--route-color:${color}">${escape(mapLabel(leg))}</span>`, {
        permanent: true, direction: "center", className: "route-label", opacity: .96,
      });
      labelPairs.push({line});
      polylines.set(leg.id, line);
      const index = Math.max(0, Math.floor((leg.geometry.length - 1) * .58));
      const first = leg.geometry[index];
      const second = leg.geometry[Math.min(index + 1, leg.geometry.length - 1)];
      const mid = leg.geometry.length === 2
        ? [(first[0] + second[0]) / 2, (first[1] + second[1]) / 2] : first;
      const angle = Math.atan2(-(second[0] - first[0]),
        (second[1] - first[1]) * Math.cos(first[0] * Math.PI / 180)) * 180 / Math.PI;
      L.marker(mid, {
        interactive: false,
        icon: L.divIcon({
          className: "direction-icon", iconSize: [18, 18], iconAnchor: [9, 9],
          html: `<span style="color:${color};transform:rotate(${angle}deg)">➤</span>`,
        })
      }).addTo(routeLayer);
    }
    for (const id of used) {
      const point = points.get(id);
      const pointLeg = legs.find(leg => leg.from === id || leg.to === id);
      const color = point.kind === "hotel" ? "#64748b" : data.days[pointLeg.day].color;
      const marker = L.marker(point.coords, {
        title: point.name,
        icon: L.divIcon({
          className: "flag-shell", iconSize: [43, 35], iconAnchor: [9, 30],
          html: `<span class="flag-pin ${point.kind === "hotel" ? "flag-hotel" : ""}" style="--pin-color:${color}"><span class="flag-emoji">🚩</span><span class="flag-number">${numberFor.get(id)}</span></span>`,
        }),
      }).addTo(markerLayer);
      marker.bindTooltip(escape(point.name), {
        permanent: true, direction: "right", offset: [25, -10], className: "poi-label",
      });
      marker.bindPopup(pointPopup(point, legs));
      markers.set(id, marker);
    }
    updateLabels();
  }
  function fitAll() {
    const coordinates = visibleLegs().flatMap(leg => leg.geometry);
    if (coordinates.length) map.fitBounds(coordinates, {padding: [45, 45], maxZoom: 15});
  }
  function fitCenter() {
    const used = new Set(visibleLegs().flatMap(leg => [leg.from, leg.to]));
    const coordinates = [...used].map(id => points.get(id))
      .filter(point => point.city === cityId && point.kind !== "airport")
      .map(point => point.coords);
    if (coordinates.length) map.fitBounds(coordinates, {padding: [45, 50], maxZoom: 15});
  }
  function renderDetails() {
    const legs = visibleLegs();
    let content = `<section class="summary"><h2>交通预算 · 每人</h2>${data.budget.map((item, i) =>
      `<div class="budget-line ${i === data.budget.length - 1 ? "budget-total" : ""}"><span>${escape(item.label)}</span><strong>${escape(item.value)}</strong></div>`).join("")}
      <p class="note">按两城、一个背包、约 1 km 内步行估算；不含机票、景点门票、住宿。跨城票价尚未核实到具体起讫站，已留区间。</p></section>
      <section class="info-box notice"><h2>先看这里</h2>
      <p class="note">${escape(city.stay)} · ${escape(city.hotelNote)}</p>
      <p class="note">细虚线＝步行道路路线；粗线＝公共交通示意。点 🚩 看时间，点线路看乘车方式，右侧可打开导航。</p>
      <p class="note">所有时间为建议时段，不是实时班次。地图默认聚焦市中心；机场和跨城连接用上方按钮查看。</p></section>`;
    for (const day of city.days) {
      const dayLegs = legs.filter(leg => leg.day === day);
      if (!dayLegs.length) continue;
      const localWalks = dayLegs.filter(leg => leg.mode === "walk" && points.get(leg.from).city === cityId);
      const walkingKm = localWalks.reduce((sum, leg) => sum + leg.distance, 0) / 1000;
      content += `<section class="day-heading" style="--day-color:${data.days[day].color}">
        <h2>${data.days[day].label} · ${data.days[day].name}</h2>
        <p>图中步行约 ${walkingKm.toFixed(1)} km，另有馆内、站内和自由游览步行</p></section>`;
      for (const leg of dayLegs) {
        content += `<article class="route-card" style="--day-color:${data.days[day].color}">
          <div class="route-top"><span>${escape(leg.depart)}</span><span>${modes[leg.mode]} ${leg.mode === "walk" ? "步行" : "乘车"}</span></div>
          <div class="route-names">🚩${numberFor.get(leg.from)} ${escape(points.get(leg.from).name)}<br>↓ 🚩${numberFor.get(leg.to)} ${escape(points.get(leg.to).name)}</div>
          <div class="route-mode">${escape(labelText(leg))}</div>
          ${leg.note ? `<p class="note">${escape(leg.note)}</p>` : ""}
          <div class="route-actions"><button type="button" data-leg="${leg.id}">在地图上定位</button>
          <a href="${directions(leg)}" target="_blank" rel="noopener">打开导航 ↗</a></div>
        </article>`;
      }
    }
    content += `<section class="info-box"><h2>预算怎么用</h2>${data.budget.map(item =>
      `<p class="note"><strong>${escape(item.label)}</strong>：${escape(item.note)}</p>`).join("")}
      <p class="note">如果科隆同一 24 小时内需乘 3 次以上，可比较 €9.60 的 1b 24h 票；有效期内包括去 CGN 机场。不要与已有效的同范围票重复购买。</p></section>
      <section class="sources"><h2>来源与边界</h2>${data.notes.map(note => `<p class="note">${escape(note)}</p>`).join("")}
      ${data.sources.map(source => `<a href="${escape(source.url)}" target="_blank" rel="noopener">${escape(source.label)} ↗</a>`).join("")}</section>`;
    document.getElementById("details").innerHTML = content;
    document.querySelectorAll("[data-leg]").forEach(button => button.addEventListener("click", () => {
      const leg = legs.find(item => item.id === button.dataset.leg);
      map.fitBounds(leg.geometry, {padding: [65, 65], maxZoom: 16});
      polylines.get(leg.id).openPopup();
      if (matchMedia("(max-width: 690px)").matches) document.getElementById("map").scrollIntoView({behavior: "smooth"});
    }));
  }
  function renderToolbar() {
    document.getElementById("toolbar").innerHTML =
      `<button data-day="all" aria-pressed="${activeDay === "all"}">全部日期</button>` +
      city.days.map(day => `<button data-day="${day}" style="--day-color:${data.days[day].color}" aria-pressed="${activeDay === day}">${data.days[day].label}</button>`).join("") +
      `<span class="toolbar-divider"></span><button id="center-view">市中心</button><button id="full-view">含机场 / 跨城</button>
      <button id="toggle-names" aria-pressed="${showNames}">地点名称</button><button id="toggle-labels" aria-pressed="${showRouteLabels}">交通标注</button>
      <span class="mode-legend">🚩 地点 · 🚶 虚线步行 · 🚋 / 🚆 粗线乘车示意 · ➤ 前进方向</span>`;
    document.querySelectorAll("[data-day]").forEach(button => button.addEventListener("click", () => {
      activeDay = button.dataset.day;
      renderToolbar();
      renderMap();
      renderDetails();
      fitCenter();
    }));
    document.getElementById("center-view").addEventListener("click", fitCenter);
    document.getElementById("full-view").addEventListener("click", () => {
      activeDay = "all";
      renderToolbar();
      renderMap();
      renderDetails();
      fitAll();
    });
    document.getElementById("toggle-names").addEventListener("click", () => {
      showNames = !showNames;
      renderToolbar();
      updateLabels();
    });
    document.getElementById("toggle-labels").addEventListener("click", () => {
      showRouteLabels = !showRouteLabels;
      renderToolbar();
      updateLabels();
    });
  }
  document.getElementById("header").innerHTML =
    `<div class="heading-row"><div><h1>🚩 ${city.name} · 每日行程地图</h1>
      <div class="subtitle">${city.latin} · 2026 年 9 月 · 约 1 km 内步行 / 长距离乘车</div></div>
      <nav class="city-links"><a class="button ${cityId === "dusseldorf" ? "current" : ""}" href="dusseldorf.html">杜塞尔多夫</a>
      <a class="button ${cityId === "cologne" ? "current" : ""}" href="cologne.html">科隆</a>
      <a class="button" href="trip-maps.zip" download>下载两城地图</a></nav></div>`;
  renderToolbar();
  renderMap();
  renderDetails();
  map.on("zoomend", updateLabels);
  map.whenReady(() => {
    map.invalidateSize();
    fitCenter();
  });
  window.tripMap = {map, data, cityId, markers, polylines,
    get activeDay() {return activeDay;}, get visibleLegs() {return visibleLegs();}};
})();
