(() => {
  "use strict";

  const byId = (id) => document.getElementById(id);

  if (!byId("telemetry-quality")) return;

  const elements = {
    status: byId("quality-status"),
    snapshot: byId("quality-snapshot"),
    publisher: byId("quality-publisher"),
    ingestion: byId("quality-ingestion"),
    capture: byId("quality-capture"),
    missed: byId("quality-missed"),
    sensor: byId("quality-sensor"),
    reasons: byId("quality-reasons"),
    note: byId("quality-note"),
    refresh: byId("quality-refresh")
  };

  if (Object.values(elements).some(element => !element)) {
    return;
  }

  const qualityLabels = {
    healthy: "Healthy",
    degraded: "Degraded",
    critical: "Critical",
    unknown: "Unknown"
  };

  const snapshotLabels = {
    fresh: "Fresh",
    stale: "Stale",
    unavailable: "Unavailable"
  };

  const publisherLabels = {
    healthy: "Healthy",
    stale: "Stale",
    unavailable: "Unavailable"
  };

  const ingestionLabels = {
    recent: "Recent",
    stale: "Stale",
    unavailable: "Unavailable"
  };

  const captureLabels = {
    no_observed_gaps: "No observed gaps",
    gaps_observed: "Gaps observed",
    unknown: "Unknown"
  };

  const reasonLabels = {
    snapshot_stale:
      "Snapshot o eventi Zeek non recenti.",

    snapshot_unavailable:
      "Snapshot Zeek assente o non valido.",

    snapshot_gaps_observed:
      "Gap TCP osservati nello snapshot disponibile.",

    capture_evidence_unavailable:
      "Evidenze insufficienti per valutare la qualità della cattura.",

    publisher_stale:
      "Ultimo successo del publisher non recente.",

    publisher_unavailable:
      "Heartbeat del publisher assente o non valido.",

    ingestion_stale:
      "Ultimo batch valido non recente.",

    ingestion_unavailable:
      "Ricevuta di acquisizione assente o non valida."
  };

  const owns = (object, key) =>
    typeof key === "string" &&
    Object.prototype.hasOwnProperty.call(object, key);

  let pending = false;

  function showMetric(element, labels, code) {
    element.textContent = labels[code];
    element.dataset.state = code;
  }

  function showReasons(messages) {
    const items = messages.map(message => {
      const item = document.createElement("li");
      item.textContent = message;
      return item;
    });

    elements.reasons.replaceChildren(...items);
  }

  function validateResponse(data) {
    if (
      !data ||
      data.policy_version !== 1 ||
      data.scope !== "available_zeek_snapshot" ||
      data.sensor_connectivity !== "unknown" ||
      !owns(qualityLabels, data.quality_status) ||
      !owns(captureLabels, data.capture_fidelity) ||
      !owns(snapshotLabels, data.snapshot?.data_status) ||
      !owns(publisherLabels, data.publisher?.publisher_status) ||
      !owns(ingestionLabels, data.ingestion?.ingestion_status) ||
      !Array.isArray(data.reasons) ||
      !data.reasons.every(reason => typeof reason === "string")
    ) {
      throw new Error("Unexpected Quality Gate response");
    }

    if (data.capture_fidelity !== "unknown") {
      const missed = data.snapshot.missed_bytes_total;

      if (
        data.snapshot.missed_bytes_complete !== true ||
        !Number.isSafeInteger(missed) ||
        missed < 0
      ) {
        throw new Error("Invalid capture evidence");
      }

      if (
        (data.capture_fidelity === "no_observed_gaps" && missed !== 0) ||
        (data.capture_fidelity === "gaps_observed" && missed === 0)
      ) {
        throw new Error("Inconsistent capture evidence");
      }
    }
  }

  function render(data) {
    validateResponse(data);

    showMetric(
      elements.status,
      qualityLabels,
      data.quality_status
    );

    showMetric(
      elements.snapshot,
      snapshotLabels,
      data.snapshot.data_status
    );

    showMetric(
      elements.publisher,
      publisherLabels,
      data.publisher.publisher_status
    );

    showMetric(
      elements.ingestion,
      ingestionLabels,
      data.ingestion.ingestion_status
    );

    showMetric(
      elements.capture,
      captureLabels,
      data.capture_fidelity
    );

    elements.missed.textContent =
      data.capture_fidelity !== "unknown"
        ? data.snapshot.missed_bytes_total.toLocaleString("it-IT")
        : "n/d";

    elements.missed.dataset.state =
      data.capture_fidelity;

    elements.sensor.textContent = "Non verificata";
    elements.sensor.dataset.state = "unknown";

    const messages = data.reasons.map(reason =>
      owns(reasonLabels, reason)
        ? reasonLabels[reason]
        : `Motivazione non riconosciuta: ${reason}`
    );

    if (messages.length === 0) {
      messages.push(
        data.quality_status === "healthy"
          ? "Nessuna anomalia osservata nei dati disponibili."
          : "Motivazione non disponibile."
      );
    }

    showReasons(messages);

    elements.note.textContent =
      "Valutazione dello snapshot disponibile. " +
      "Non misura direttamente la perdita di pacchetti in tempo reale " +
      "e non verifica la connettività del sensore.";
  }

  function showFailure() {
    elements.status.textContent = "Non disponibile";
    elements.status.dataset.state = "error";

    for (const name of [
      "snapshot", "publisher", "ingestion",
      "capture", "missed"
    ]) {
      elements[name].textContent = "n/d";
      elements[name].dataset.state = "unknown";
    }

    elements.sensor.textContent = "Non verificata";
    elements.sensor.dataset.state = "unknown";

    showReasons([
      "Impossibile ottenere una valutazione valida dall'API."
    ]);

    elements.note.textContent =
      "Qualità della telemetria non determinabile.";
  }

  async function refresh() {
    if (pending) return;

    pending = true;
    elements.refresh.disabled = true;

    const controller = new AbortController();

    const timeout = window.setTimeout(
      () => controller.abort(),
      10_000
    );

    try {
      const response = await fetch(
        "/api/v1/telemetry/quality",
        {
          cache: "no-store",
          credentials: "same-origin",
          signal: controller.signal
        }
      );

      if (!response.ok) {
        throw new Error(`HTTP ${response.status}`);
      }

      render(await response.json());

    } catch (error) {
      showFailure();

    } finally {
      window.clearTimeout(timeout);
      pending = false;
      elements.refresh.disabled = false;
    }
  }

  elements.refresh.addEventListener(
    "click",
    () => void refresh()
  );

  document.addEventListener("visibilitychange", () => {
    if (!document.hidden) void refresh();
  });

  window.setInterval(() => {
    if (!document.hidden) void refresh();
  }, 60_000);

  void refresh();
})();
