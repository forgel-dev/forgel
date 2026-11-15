import React, { useCallback, useEffect, useState } from "react";

const CHECKING = "checking";

/**
 * Render the health status of the api service.
 *
 * The request goes to the same origin (``/healthz``) and nginx proxies it to
 * the ``api`` service, so the browser needs neither a published API port nor
 * CORS. The ``data-testid`` markers are stable hooks for qa/scenario.js.
 */
export default function App() {
  const [health, setHealth] = useState({
    state: CHECKING,
    status: "",
    code: 0,
    error: "",
  });

  const load = useCallback(async (signal) => {
    try {
      const response = await fetch("/healthz", {
        headers: { Accept: "application/json" },
        signal,
      });
      const body = await response.json().catch(() => ({}));
      setHealth({
        state: response.ok ? "ok" : "error",
        status: body.status || "",
        code: response.status,
        error: "",
      });
    } catch (error) {
      if (error.name === "AbortError") {
        return;
      }
      setHealth({ state: "error", status: "", code: 0, error: String(error) });
    }
  }, []);

  useEffect(() => {
    const controller = new AbortController();
    load(controller.signal);
    return () => controller.abort();
  }, [load]);

  const label =
    health.state === CHECKING ? CHECKING : health.status || health.state;
  const code = health.code || "-";

  return (
    <main>
      <h1>__PROJECT_NAME__</h1>
      <p
        className={health.state === "error" ? "health is-error" : "health"}
        data-testid="health"
      >
        Health: <strong data-testid="health-status">{label}</strong> (HTTP{" "}
        <span data-testid="health-code">{code}</span>)
      </p>
      {health.error ? <p data-testid="health-error">{health.error}</p> : null}
      <button type="button" onClick={() => load()}>Re-check</button>
    </main>
  );
}
