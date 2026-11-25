(() => {
  "use strict";

  const byId = (id) => document.getElementById(id);

  const elements = {
    status: byId("ingestion-health-status"),
    lastBatch: byId("ingestion-last-batch"),
    age: byId("ingestion-batch-age"),
    newRecords: byId("ingestion-new-records"),
    duplicates: byId("ingestion-duplicates"),
    total: byId("ingestion-total-records"),
    storeUpdated: byId("ingestion-store-updated"),
    note: byId("ingestion-health-note")
  };

  if (Object.values(elements).some((element) => !element)) {
    return;
  }

  const labels = {
    recent: "Recent",
    stale: "Stale",
    unavailable: "Unavailable"
  };

  const placeholders = [
    elements.lastBatch,
    elements.age,
    elements.newRecords,
    elements.duplicates,
    elements.total,
    elements.storeUpdated
  ];

  function formatUtc(value) {
    if (!value) return "—";

    const date = new Date(value);

    if (Number.isNaN(date.getTime())) {
      return "—";
    }

    return date.toLocaleString("it-IT", {
      timeZone: "UTC",
      dateStyle: "short",
      timeStyle: "medium"
    }) + " UTC";
  }

  function formatAge(seconds) {
    if (!Number.isSafeInteger(seconds) || seconds < 0) {
      return "—";
    }

    if (seconds < 60) return `${seconds} s`;

    if (seconds < 3600) {
      return `${Math.floor(seconds / 60)} min`;
    }

    if (seconds < 86400) {
      const hours = Math.floor(seconds / 3600);
      const minutes = Math.floor((seconds % 3600) / 60);
      return `${hours} h ${minutes} min`;
    }

    const days = Math.floor(seconds / 86400);
    const hours = Math.floor((seconds % 86400) / 3600);

    return `${days} g ${hours} h`;
  }

  function formatCount(value) {
    if (!Number.isSafeInteger(value) || value < 0) {
      return "—";
    }

    return value.toLocaleString("it-IT");
  }

  function setStatus(status) {
    elements.status.dataset.state = status;
    elements.status.textContent = labels[status];
  }

  function renderUnavailable(reason) {
    setStatus("unavailable");

    for (const element of placeholders) {
      element.textContent = "—";
    }

    elements.note.textContent =
      reason === "timestamp_clock_skew"
        ? "Timestamp non coerente: verificare la sincronizzazione degli orologi."
        : "Receipt di ingestion assente, non valido o non leggibile.";
  }

  function render(data) {
    const status = data.ingestion_status;

    if (!Object.prototype.hasOwnProperty.call(labels, status)) {
      throw new Error("Invalid ingestion status");
    }

    if (status === "unavailable") {
      renderUnavailable(data.reason);
      return;
    }

    setStatus(status);

    elements.lastBatch.textContent =
      formatUtc(data.last_valid_batch_at_utc);

    elements.age.textContent =
      formatAge(data.last_valid_batch_age_seconds);

    elements.newRecords.textContent =
      formatCount(data.last_batch_new_records);

    elements.duplicates.textContent =
      formatCount(data.last_batch_duplicate_records);

    elements.total.textContent =
      formatCount(data.total_records_after_batch);

    elements.storeUpdated.textContent =
      formatUtc(data.store_updated_at_utc);

    if (status === "stale") {
      elements.note.textContent =
        "Nessun batch valido recente. Questo non dimostra che il sensore sia guasto.";
    } else if (data.last_batch_new_records === 0) {
      elements.note.textContent =
        "Ricezione recente riuscita, ma senza nuovi record. Archivio ed eventi sono monitorati separatamente.";
    } else {
      elements.note.textContent =
        "Batch valido ricevuto con nuovi record. La connettività del sensore non è verificata da questo indicatore.";
    }
  }

  let loading = false;

  async function refresh() {
    if (loading) return;

    loading = true;

    try {
      const response = await fetch(
        "/api/v1/telemetry/ingestion",
        { cache: "no-store" }
      );

      if (!response.ok) {
        throw new Error("Ingestion health request failed");
      }

      const data = await response.json();

      render(data);

    } catch (_error) {
      renderUnavailable("receipt_missing_or_invalid");
      elements.note.textContent =
        "Impossibile recuperare lo stato dell'ingestion.";
    } finally {
      loading = false;
    }
  }

  const refreshButton = byId("telemetry-health-refresh");

  if (refreshButton) {
    refreshButton.addEventListener("click", () => {
      void refresh();
    });
  }

  document.addEventListener("visibilitychange", () => {
    if (!document.hidden) {
      void refresh();
    }
  });

  window.setInterval(() => {
    if (!document.hidden) {
      void refresh();
    }
  }, 60000);

  void refresh();
})();
