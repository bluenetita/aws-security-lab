"use strict";

// Zeek records are ingested periodically through the SSH collector: not a live stream.
(() => {
  const byId = (id) => document.getElementById(id);
  const AUTO_REFRESH_MS = 30_000;

  let requestNumber = 0;
  let requestInFlight = false;
  let autoRefreshTimer = null;
  let loadedOnce = false;
  let selectedUid = null;
  // Only submitted filters apply to background polling, not draft input values.
  let appliedFilters = { sourceIp: "", protocol: "" };

  function textCell(value, className = "") {
    const cell = document.createElement("td");
    cell.textContent = String(value);
    if (className) cell.className = className;
    return cell;
  }

  function formatBytes(value) {
    if (value === null || value === undefined) return "n/d";
    if (value >= 1048576) return `${(value / 1048576).toFixed(2)} MiB`;
    if (value >= 1024) return `${(value / 1024).toFixed(1)} KiB`;
    return `${value} B`;
  }

  function formatTime(value) {
    const date = new Date(value);
    if (!Number.isFinite(date.getTime())) return "n/d";
    return new Intl.DateTimeFormat("it-IT", {
      dateStyle: "short", timeStyle: "medium", timeZone: "UTC"
    }).format(date) + " UTC";
  }

  function endpoint(ip, port) {
    const host = String(ip).includes(":") ? `[${ip}]` : String(ip);
    return `${host}:${port}`;
  }

  function showMessage(message) {
    const body = byId("zeek-body");
    body.replaceChildren();
    const row = document.createElement("tr");
    const item = textCell(message, "loading");
    item.colSpan = 6;
    row.append(item);
    body.append(row);
  }

  function showDetail(event) {
    selectedUid = event.uid;
    const container = byId("zeek-detail");
    container.replaceChildren();
    const list = document.createElement("dl");
    list.className = "detail-list";

    const fields = [
      ["UID Zeek", event.uid],
      ["Timestamp", formatTime(event.timestamp_utc)],
      ["Origine", endpoint(event.source_ip, event.source_port)],
      ["Destinazione", endpoint(event.destination_ip, event.destination_port)],
      ["Protocollo", event.proto.toUpperCase()],
      ["Servizio", event.service ?? "n/d"],
      ["Stato connessione", event.conn_state ?? "n/d"],
      ["Durata", event.duration == null ? "n/d" : `${event.duration.toFixed(3)} s`],
      ["Bytes applicativi originator", formatBytes(event.orig_bytes)],
      ["Bytes applicativi responder", formatBytes(event.resp_bytes)],
      ["Missed bytes", event.missed_bytes ?? "n/d"],
      ["Pacchetti originator", event.orig_pkts ?? "n/d"],
      ["Pacchetti responder", event.resp_pkts ?? "n/d"],
      ["Provenienza", "Zeek — acquisizione periodica dei log (non live)"]
    ];

    for (const [label, value] of fields) {
      const row = document.createElement("div");
      row.className = "detail-row";
      const dt = document.createElement("dt");
      const dd = document.createElement("dd");
      dt.textContent = label;
      dd.textContent = String(value);
      row.append(dt, dd);
      list.append(row);
    }
    container.append(list);
  }

  function renderConnections(items) {
    const body = byId("zeek-body");
    body.replaceChildren();
    if (items.length === 0) {
      selectedUid = null;
      byId("zeek-detail").textContent = "Nessuna connessione selezionata.";
      showMessage("Nessuna connessione corrisponde ai filtri selezionati.");
      return;
    }

    for (const event of items) {
      const row = document.createElement("tr");
      row.tabIndex = 0;
      row.className = "zeek-row";
      row.setAttribute("aria-label", `Dettagli connessione ${event.uid}`);
      const direction = `${endpoint(event.source_ip, event.source_port)} → ${endpoint(event.destination_ip, event.destination_port)}`;
      const protocol = `${event.proto.toUpperCase()}${event.service ? ` / ${event.service}` : ""}`;
      row.append(
        textCell(formatTime(event.timestamp_utc)),
        textCell(direction),
        textCell(protocol),
        textCell(`${formatBytes(event.orig_bytes)} / ${formatBytes(event.resp_bytes)}`),
        textCell(event.missed_bytes ?? "n/d"),
        textCell(event.conn_state ?? "n/d")
      );
      row.addEventListener("click", () => showDetail(event));
      row.addEventListener("keydown", (keyEvent) => {
        if (keyEvent.key === "Enter" || keyEvent.key === " ") {
          keyEvent.preventDefault();
          showDetail(event);
        }
      });
      body.append(row);
    }

    // Preserve the open connection detail during background refreshes.
    const stillSelected = items.find((item) => item.uid === selectedUid);
    if (stillSelected) {
      showDetail(stillSelected);
    } else {
      selectedUid = null;
      byId("zeek-detail").textContent = "Seleziona una connessione per vedere i dettagli.";
    }
  }

  async function loadConnections({ background = false } = {}) {
    // One polling request at a time; explicit filter/refresh actions may supersede it.
    if (background && requestInFlight) return;
    const currentRequest = ++requestNumber;
    requestInFlight = true;
    if (!background || !loadedOnce) {
      byId("zeek-status").textContent = "Caricamento connessioni Zeek...";
    }

    const params = new URLSearchParams({ limit: "100", offset: "0" });
    if (appliedFilters.sourceIp) params.set("source_ip", appliedFilters.sourceIp);
    if (appliedFilters.protocol) params.set("proto", appliedFilters.protocol);

    try {
      const response = await fetch(`/api/v1/zeek/connections?${params}`, {
        cache: "no-store"
      });
      if (response.status === 422) {
        throw new Error("Filtro non valido: controlla l'indirizzo IP sorgente.");
      }
      if (!response.ok) throw new Error(`HTTP ${response.status}`);
      const payload = await response.json();
      if (currentRequest !== requestNumber) return;
      // Preserve the v0.4.0 API contract; the source is a published JSONL file,
      // not a direct, live connection to Zeek.
      if (payload.source !== "zeek_snapshot" || payload.live !== false ||
          !Array.isArray(payload.items) || !Number.isInteger(payload.total)) {
        throw new Error("Formato della risposta Zeek inatteso.");
      }

      renderConnections(payload.items);
      byId("zeek-count").textContent = String(payload.total);
      byId("zeek-total").textContent = String(payload.total);
      byId("zeek-tcp").textContent = String(
        payload.items.filter((item) => item.proto === "tcp").length
      );
      const allHaveMissedBytes = payload.items.every((item) => item.missed_bytes != null);
      byId("zeek-missed").textContent = allHaveMissedBytes
        ? payload.items.reduce((sum, item) => sum + item.missed_bytes, 0).toLocaleString("it-IT")
        : "n/d";
      byId("zeek-status").textContent =
        `Mostrate ${payload.items.length} di ${payload.total} connessioni filtrate · Ingestion periodica (non live)`;
      byId("zeek-last-updated").textContent =
        `Ultimo aggiornamento riuscito: ${new Date().toLocaleTimeString("it-IT")}`;
      loadedOnce = true;
    } catch (error) {
      if (currentRequest !== requestNumber) return;
      // Keep the last successful table and selected detail on transient failures.
      byId("zeek-status").textContent = loadedOnce
        ? `Aggiornamento non riuscito (${error.message}). Visualizzati gli ultimi dati disponibili.`
        : `Impossibile caricare le connessioni: ${error.message}`;
      if (!loadedOnce) {
        showMessage("Connessioni Zeek momentaneamente non disponibili.");
        for (const id of ["zeek-count", "zeek-total", "zeek-tcp", "zeek-missed"]) {
          byId(id).textContent = "—";
        }
      }
    } finally {
      if (currentRequest === requestNumber) requestInFlight = false;
    }
  }

  // The dashboard uses one scrolling page. A visible section is not always
  // represented by its URL fragment (the user may reach Zeek with the wheel).
  function zeekSectionOpen() {
    if (document.hidden) return false;
    const section = byId("zeek-connections");
    const rect = section.getBoundingClientRect();
    const viewportHeight = window.innerHeight || document.documentElement.clientHeight;
    if (!viewportHeight) return false;
    const center = viewportHeight / 2;
    return rect.top <= center && rect.bottom > center;
  }

  function updateNavActiveState(zeekVisible) {
    const links = [...document.querySelectorAll("a.nav-item")];
    const selectedHref = zeekVisible ? "#zeek-connections" : "/";
    const chosen = links.find((link) => link.getAttribute("href") === selectedHref);
    for (const link of links) {
      // styles.css uses .nav-item.selected, not .nav-item.active.
      link.classList.toggle("selected", link === chosen);
      link.classList.remove("active");
      if (link === chosen) link.setAttribute("aria-current", "location");
      else link.removeAttribute("aria-current");
    }
    const breadcrumb = document.querySelector(".crumb");
    if (breadcrumb?.lastChild?.nodeType === 3) {
      breadcrumb.lastChild.textContent = zeekVisible
        ? " Connessioni Zeek" : " Overview";
    }
  }

  function syncAutoRefresh() {
    const zeekVisible = zeekSectionOpen();
    updateNavActiveState(zeekVisible);
    if (zeekVisible) {
      if (autoRefreshTimer === null) {
        // Refresh once when entering the section, then every 30 seconds.
        if (!requestInFlight) void loadConnections({ background: loadedOnce });
        autoRefreshTimer = window.setInterval(() => {
          if (zeekSectionOpen()) void loadConnections({ background: true });
        }, AUTO_REFRESH_MS);
      }
    } else if (autoRefreshTimer !== null) {
      window.clearInterval(autoRefreshTimer);
      autoRefreshTimer = null;
    }
  }

  byId("zeek-filters").addEventListener("submit", (event) => {
    event.preventDefault();
    appliedFilters = {
      sourceIp: byId("zeek-source-ip").value.trim(),
      protocol: byId("zeek-proto").value
    };
    void loadConnections();
  });
  byId("zeek-reset").addEventListener("click", () => {
    byId("zeek-source-ip").value = "";
    byId("zeek-proto").value = "";
    appliedFilters = { sourceIp: "", protocol: "" };
    void loadConnections();
  });
  byId("refresh").addEventListener("click", () => void loadConnections());
  window.addEventListener("hashchange", syncAutoRefresh);
  window.addEventListener("resize", syncAutoRefresh);
  // Passive, requestAnimationFrame-throttled scroll tracking avoids a timer
  // that remains inactive when reaching Zeek through normal page scrolling.
  let scrollSyncPending = false;
  window.addEventListener("scroll", () => {
    if (scrollSyncPending) return;
    scrollSyncPending = true;
    window.requestAnimationFrame(() => {
      scrollSyncPending = false;
      syncAutoRefresh();
    });
  }, { passive: true });
  document.addEventListener("visibilitychange", syncAutoRefresh);
  void loadConnections();
  syncAutoRefresh();
})();
