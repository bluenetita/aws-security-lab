(() => {
  "use strict";

  const byId = (id) => document.getElementById(id);

  const elements = {
    status: byId("publisher-health-status"),
    success: byId("publisher-last-success"),
    age: byId("publisher-success-age"),
    sensor: byId("publisher-sensor-state"),
    note: byId("publisher-health-note")
  };

  if (Object.values(elements).some((element) => !element)) {
    return;
  }

  const labels = {
    healthy: "Healthy",
    stale: "Stale",
    unavailable: "Unavailable"
  };

  const messages = {
    healthy:
      "Il publisher funziona. La freschezza degli eventi Zeek è verificata separatamente.",
    stale:
      "Nessun successo recente del publisher. Verificare il servizio systemd.",
    unavailable:
      "Heartbeat assente o non valido. Lo stato del publisher non è verificabile."
  };

  function formatUtc(value) {
    if (!value) return "—";

    const date = new Date(value);

    if (Number.isNaN(date.getTime())) return "—";

    return date.toLocaleString("it-IT", {
      timeZone: "UTC",
      dateStyle: "short",
      timeStyle: "medium"
    }) + " UTC";
  }

  function formatAge(seconds) {
    if (!Number.isInteger(seconds) || seconds < 0) {
      return "—";
    }

    if (seconds < 60) return `${seconds} s`;

    const minutes = Math.floor(seconds / 60);
    if (minutes < 60) return `${minutes} min`;

    const hours = Math.floor(minutes / 60);
    const remainingMinutes = minutes % 60;

    return `${hours} h ${remainingMinutes} min`;
  }

  function setStatus(status) {
    elements.status.dataset.state = status;
    elements.status.textContent = labels[status];
    elements.note.textContent = messages[status];
  }

  let loading = false;

  async function refresh() {
    if (loading) return;
    loading = true;

    try {
      const response = await fetch(
        "/api/v1/telemetry/publisher",
        { cache: "no-store" }
      );

      if (!response.ok) {
        throw new Error("Publisher health request failed");
      }

      const data = await response.json();

      if (!Object.prototype.hasOwnProperty.call(
        labels,
        data.publisher_status
      )) {
        throw new Error("Invalid publisher status");
      }

      setStatus(data.publisher_status);

      elements.success.textContent =
        formatUtc(data.last_success_at_utc);

      elements.age.textContent =
        formatAge(data.last_success_age_seconds);

      elements.sensor.textContent = "Non verificato";

    } catch (_error) {
      setStatus("unavailable");

      elements.success.textContent = "—";
      elements.age.textContent = "—";
      elements.sensor.textContent = "Non verificato";

      elements.note.textContent =
        "Impossibile recuperare lo stato del publisher.";
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
    if (!document.hidden) void refresh();
  });

  window.setInterval(() => {
    if (!document.hidden) void refresh();
  }, 60000);

  void refresh();
})();
