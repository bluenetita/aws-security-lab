"use strict";

// Presentation only: this is a snapshot-health check, NOT a live sensor probe.
(() => {
  const byId = (id) => document.getElementById(id);
  const panel = byId("telemetry-health");
  if (!panel) return;

  const state = byId("telemetry-health-state");
  const labels = {
    fresh: "Dati recenti",
    stale: "Dati non recenti",
    unavailable: "Dati non disponibili",
  };

  let pending = false;

  function ageText(value) {
    if (!Number.isFinite(value) || value < 0) return "n/d";
    const seconds = Math.floor(value);
    if (seconds < 60) return `${seconds} s`;
    const minutes = Math.floor(seconds / 60);
    if (minutes < 60) return `${minutes} min`;
    const hours = Math.floor(minutes / 60);
    if (hours < 24) return `${hours} h ${minutes % 60} min`;
    return `${Math.floor(hours / 24)} g ${hours % 24} h`;
  }

  function utcText(value) {
    if (!value) return "n/d";
    const date = new Date(value);
    if (!Number.isFinite(date.getTime())) return "n/d";
    return new Intl.DateTimeFormat("it-IT", {
      dateStyle: "short",
      timeStyle: "medium",
      timeZone: "UTC",
    }).format(date) + " UTC";
  }

  function showStatus(code, note) {
    state.dataset.state = code;
    state.textContent = labels[code];
    byId("telemetry-health-note").textContent = note;
  }

  function showHealth(data) {
    if (!Object.prototype.hasOwnProperty.call(labels, data.data_status) ||
        data.source !== "zeek_snapshot" ||
        data.ingestion_mode !== "periodic_snapshot") {
      throw new Error("Risposta inattesa dal servizio di telemetria");
    }

    byId("telemetry-records").textContent =
      Number.isInteger(data.records) ? data.records.toLocaleString("it-IT") : "n/d";
    byId("telemetry-snapshot-updated").textContent = utcText(data.snapshot_updated_at_utc);
    byId("telemetry-snapshot-age").textContent = ageText(data.snapshot_age_seconds);
    byId("telemetry-last-event").textContent = utcText(data.latest_event_at_utc);
    byId("telemetry-event-age").textContent = ageText(data.latest_event_age_seconds);
    byId("telemetry-capture").textContent =
      data.missed_bytes_complete === true && Number.isInteger(data.missed_bytes_total)
        ? `${data.missed_bytes_total.toLocaleString("it-IT")} missed bytes (record disponibili)`
        : "Dato incompleto / non disponibile";

    const note = data.data_status === "fresh"
      ? "Snapshot ed eventi recenti; la connettivita del sensore non e verificata."
      : data.data_status === "stale"
        ? "Ultimo snapshot o ultimo evento non recente. Non indica necessariamente un guasto del sensore."
        : "Snapshot assente o non valido. Nessuna verifica della connettivita del sensore.";
    showStatus(data.data_status, note);
  }

  async function refresh() {
    if (pending) return;
    pending = true;
    try {
      const response = await fetch("/api/v1/telemetry/health", { cache: "no-store" });
      if (!response.ok) throw new Error(`HTTP ${response.status}`);
      showHealth(await response.json());
    } catch (error) {
      showStatus("unavailable", "Controllo dell'API non riuscito; lo stato del sensore resta sconosciuto.");
    } finally {
      pending = false;
    }
  }

  byId("telemetry-health-refresh").addEventListener("click", () => void refresh());
  document.addEventListener("visibilitychange", () => {
    if (!document.hidden) void refresh();
  });
  window.setInterval(() => {
    if (!document.hidden) void refresh();
  }, 60_000);
  void refresh();
})();
