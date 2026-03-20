import { useEffect, useMemo, useState } from "react";

import ComposerShell from "./components/ComposerShell.jsx";
import StatusRail from "./components/StatusRail.jsx";

const API_BASE = "http://127.0.0.1:8010";

const initialMessages = [
  {
    id: "system-presence",
    role: "system",
    label: "Jarvis Presence",
    body: "Vedvarende identitet, vaerktoejer og Mission Control-observability samles her."
  }
];

export default function App() {
  const [draft, setDraft] = useState("");
  const [messages, setMessages] = useState(initialMessages);
  const [isRunning, setIsRunning] = useState(false);
  const [activeRunId, setActiveRunId] = useState(null);
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");
  const [wsState, setWsState] = useState("connecting");
  const [activityEvents, setActivityEvents] = useState([]);
  const [visibleControl, setVisibleControl] = useState(null);
  const [visibleControlState, setVisibleControlState] = useState("loading");
  const [visibleControlError, setVisibleControlError] = useState("");
  const [visibleControlNotice, setVisibleControlNotice] = useState("");
  const [capabilityInvokeBusy, setCapabilityInvokeBusy] = useState("");
  const [capabilityInvokeResult, setCapabilityInvokeResult] = useState(null);

  useEffect(() => {
    const ws = new WebSocket("ws://127.0.0.1:8010/ws");

    ws.onopen = () => {
      setWsState("live");
    };

    ws.onmessage = (event) => {
      const item = JSON.parse(event.data);
      setActivityEvents((prev) => [item, ...prev].slice(0, 6));
      if (item.kind?.startsWith("runtime.visible_run_")) {
        loadVisibleControl({ quiet: true });
      }
    };

    ws.onerror = () => {
      setWsState("offline");
    };

    ws.onclose = () => {
      setWsState("offline");
    };

    return () => ws.close();
  }, []);

  useEffect(() => {
    loadVisibleControl();
  }, []);

  const currentActivity = useMemo(() => {
    const visibleRun = visibleControl?.visible_run;
    if (visibleRun?.active_run?.run_id) {
      return `Visible run ${visibleRun.active_run.run_id} er aktiv via runtime-truth.`;
    }
    if (!activityEvents.length) {
      return "Afventer runtime-aktivitet fra control-plane.";
    }

    const latest = activityEvents[0];
    if (latest.kind === "runtime.visible_run_started") {
      return `Visible run ${latest.payload.run_id} er startet via runtime-truth.`;
    }
    if (latest.kind === "runtime.visible_run_completed") {
      return `Visible run ${latest.payload.run_id} er afsluttet i control-plane.`;
    }
    return `Seneste runtime-event: ${latest.kind}.`;
  }, [activityEvents]);

  async function handleSubmit(event) {
    event.preventDefault();
    const message = draft.trim();
    if (!message || isRunning) {
      return;
    }

    setError("");
    setNotice("");
    setDraft("");
    setIsRunning(true);
    setMessages((prev) => [
      ...prev,
      {
        id: `user-${Date.now()}`,
        role: "user",
        label: "Du",
        body: message
      }
    ]);

    try {
      const response = await fetch(`${API_BASE}/chat/stream`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json"
        },
        body: JSON.stringify({ message })
      });

      if (!response.ok || !response.body) {
        throw new Error("Visible chat stream kunne ikke startes.");
      }

      await consumeSseStream(response.body, {
        onRun(data) {
          setActiveRunId(data.run_id);
          setMessages((prev) => [
            ...prev,
            {
              id: data.run_id,
              role: "assistant",
              label: "Jarvis",
              body: ""
            }
          ]);
        },
        onDelta(data) {
          setMessages((prev) =>
            prev.map((item) =>
              item.id === data.run_id
                ? { ...item, body: `${item.body}${data.delta}` }
                : item
            )
          );
        },
        onDone(data) {
          if (data.status === "failed") {
            setError(data.error || "Visible run fejlede.");
          } else if (data.status === "cancelled") {
            setNotice("Visible run annulleret.");
          }
          setActiveRunId(data.run_id);
        },
        onFailed(data) {
          setError(data.error || "Visible run fejlede.");
        },
        onCancelled() {
          setNotice("Visible run annulleret.");
        }
      });
    } catch (streamError) {
      setError(streamError instanceof Error ? streamError.message : "Ukendt stream-fejl.");
    } finally {
      setIsRunning(false);
      setActiveRunId(null);
    }
  }

  async function handleCancel() {
    if (!activeRunId || !isRunning) {
      return;
    }

    setError("");
    setNotice("");

    try {
      const response = await fetch(`${API_BASE}/chat/runs/${activeRunId}/cancel`, {
        method: "POST"
      });
      const data = await response.json();
      if (!response.ok) {
        throw new Error(data.detail || "Visible run kunne ikke annulleres.");
      }
    } catch (cancelError) {
      setError(
        cancelError instanceof Error ? cancelError.message : "Ukendt cancel-fejl."
      );
    }
  }

  async function loadVisibleControl(options = {}) {
    const quiet = options.quiet === true;
    if (!quiet) {
      setVisibleControlState("loading");
      setVisibleControlError("");
    }

    try {
      const response = await fetch(`${API_BASE}/mc/visible-execution`);
      if (!response.ok) {
        throw new Error("Visible lane authority kunne ikke hentes.");
      }
      const data = await response.json();
      setVisibleControl(data);
      setVisibleControlState("ready");
    } catch (fetchError) {
      if (!quiet) {
        setVisibleControlState("error");
        setVisibleControlError(
          fetchError instanceof Error ? fetchError.message : "Ukendt authority-fejl."
        );
      }
    }
  }

  async function handleVisibleControlSave(nextAuthority) {
    setVisibleControlState("saving");
    setVisibleControlError("");
    setVisibleControlNotice("");

    try {
      const response = await fetch(`${API_BASE}/mc/visible-execution`, {
        method: "PUT",
        headers: {
          "Content-Type": "application/json"
        },
        body: JSON.stringify(nextAuthority)
      });
      const data = await response.json();
      if (!response.ok) {
        throw new Error(data.detail || "Visible lane authority kunne ikke gemmes.");
      }
      setVisibleControl(data);
      setVisibleControlState("ready");
      setVisibleControlNotice("Visible lane authority opdateret.");
    } catch (saveError) {
      setVisibleControlState("error");
      setVisibleControlError(
        saveError instanceof Error ? saveError.message : "Ukendt save-fejl."
      );
    }
  }

  async function handleInvokeCapability(capabilityId) {
    setCapabilityInvokeBusy(capabilityId);
    setCapabilityInvokeResult(null);

    try {
      const response = await fetch(
        `${API_BASE}/mc/workspace-capabilities/${encodeURIComponent(capabilityId)}/invoke`,
        {
          method: "POST"
        }
      );
      const data = await response.json();
      setCapabilityInvokeResult(data);
    } catch (invokeError) {
      setCapabilityInvokeResult({
        ok: false,
        capability: null,
        status: "not-found",
        execution_mode: "unsupported",
        result: null,
        detail:
          invokeError instanceof Error ? invokeError.message : "Ukendt capability-fejl."
      });
    } finally {
      setCapabilityInvokeBusy("");
    }
  }

  return (
    <div className="webchat-shell">
      <header className="topbar">
        <div>
          <span className="eyebrow">Primary Chat</span>
          <h1>Jarvis V2</h1>
        </div>
        <div className="topbar-meta">
          <span>Visible lane</span>
          <span>Mission Control sidecar</span>
        </div>
      </header>
      <main className="layout">
        <section className="chat-column">
          <section className="panel chat-panel">
            <div className="chat-panel-header">
              <div>
                <span className="eyebrow">Conversation</span>
                <h2>Primary Chat Shell</h2>
              </div>
              <span className={`status-pill${isRunning ? "" : " muted"}`}>
                {isRunning ? "Working" : "Idle"}
              </span>
            </div>
            <div className="transcript">
              {messages.map((item) => (
                <article key={item.id} className={`message ${item.role}`}>
                  <span className="message-label">{item.label}</span>
                  <p>{item.body || "..."}</p>
                </article>
              ))}
            </div>
            {notice ? <p className="chat-notice">{notice}</p> : null}
            {error ? <p className="chat-error">{error}</p> : null}
          </section>
          <ComposerShell
            draft={draft}
            isRunning={isRunning}
            onCancel={handleCancel}
            onChange={setDraft}
            onSubmit={handleSubmit}
          />
        </section>
        <section className="work-column">
          <section className="panel work-panel">
            <div className="chat-panel-header">
              <div>
                <span className="eyebrow">Work Area</span>
                <h2>Activity and Output</h2>
              </div>
              <span className={`status-pill${wsState === "live" ? "" : " muted"}`}>
                {wsState === "live" ? "Control-plane live" : "Control-plane offline"}
              </span>
            </div>
            <div className="work-grid">
              <article className="work-card">
                <strong>Live arbejde</strong>
                <p>{currentActivity}</p>
              </article>
              <article className="work-card">
                <strong>Visible lane truth</strong>
                {visibleControl?.visible_run ? (
                  <div className="truth-sections">
                    <section className="truth-section">
                      <h3>Authority og readiness</h3>
                      <ul className="runtime-event-list compact">
                        <li>
                          <span>
                            Provider:{" "}
                            {visibleControl.authority?.visible_model_provider || "ingen"}
                          </span>
                        </li>
                        <li>
                          <span>
                            Model: {visibleControl.authority?.visible_model_name || "ingen"}
                          </span>
                        </li>
                        <li>
                          <span>
                            Profil:{" "}
                            {visibleControl.authority?.visible_auth_profile || "ingen"}
                          </span>
                        </li>
                        <li>
                          <span>
                            Readiness: {visibleControl.readiness?.provider_status || "ukendt"}
                          </span>
                          <small>
                            <span
                              className={`status-chip ${statusTone(
                                visibleControl.readiness?.provider_status
                              )}`}
                            >
                              {visibleControl.readiness?.provider_status || "ukendt"}
                            </span>
                          </small>
                        </li>
                      </ul>
                    </section>
                    <section className="truth-section">
                      <h3>Aktivt run</h3>
                      <ul className="runtime-event-list compact">
                        <li>
                          <span>Aktiv: {visibleControl.visible_run.active ? "ja" : "nej"}</span>
                          <small>
                            <span
                              className={`status-chip ${
                                visibleControl.visible_run.active ? "status-live" : "status-idle"
                              }`}
                            >
                              {visibleControl.visible_run.active ? "aktiv" : "inaktiv"}
                            </span>
                          </small>
                        </li>
                        <li>
                          <span>
                            Run: {visibleControl.visible_run.active_run?.run_id || "ingen"}
                          </span>
                        </li>
                        <li>
                          <span>
                            Lane: {visibleControl.visible_run.active_run?.lane || "ingen"}
                          </span>
                        </li>
                        <li>
                          <span>
                            Provider:{" "}
                            {visibleControl.visible_run.active_run?.provider || "ingen"}
                          </span>
                        </li>
                        <li>
                          <span>
                            Model: {visibleControl.visible_run.active_run?.model || "ingen"}
                          </span>
                        </li>
                        <li>
                          <span>
                            Startet:{" "}
                            {visibleControl.visible_run.active_run?.started_at || "ingen"}
                          </span>
                        </li>
                      </ul>
                    </section>
                    <section className="truth-section">
                      <h3>Sidste udfald</h3>
                      <ul className="runtime-event-list compact">
                        <li>
                          <span>
                            Status:{" "}
                            {visibleControl.visible_run.last_outcome?.status || "ingen"}
                          </span>
                          <small>
                            <span
                              className={`status-chip ${statusTone(
                                visibleControl.visible_run.last_outcome?.status
                              )}`}
                            >
                              {visibleControl.visible_run.last_outcome?.status || "ingen"}
                            </span>
                            {visibleControl.visible_run.last_outcome?.run_id
                              ? ` · ${visibleControl.visible_run.last_outcome.run_id}`
                              : ""}
                          </small>
                        </li>
                        <li>
                          <span>
                            Afsluttet:{" "}
                            {visibleControl.visible_run.last_outcome?.finished_at || "ingen"}
                          </span>
                        </li>
                        <li>
                          <span>
                            Preview:{" "}
                            {visibleControl.visible_run.last_outcome?.text_preview || "ingen"}
                          </span>
                        </li>
                      </ul>
                    </section>
                    <section className="truth-section">
                      <h3>Recent events</h3>
                      {visibleControl.visible_run.recent_events?.length ? (
                        <ul className="runtime-event-list compact">
                          {visibleControl.visible_run.recent_events.map((item) => (
                            <li key={item.id}>
                              <span>{item.kind}</span>
                              <small>
                                <span
                                  className={`status-chip ${statusTone(
                                    item.payload?.status
                                  )}`}
                                >
                                  {item.payload?.status || "ukendt"}
                                </span>{" "}
                                ·{" "}
                                {item.payload?.run_id || "ingen"} · {item.created_at}
                              </small>
                            </li>
                          ))}
                        </ul>
                      ) : (
                        <p>Ingen visible run-events endnu.</p>
                      )}
                    </section>
                    <section className="truth-section">
                      <h3>Workspace capabilities</h3>
                      {visibleControl.workspace_capabilities?.declared_capabilities?.length ? (
                        <div className="capability-list">
                          {visibleControl.workspace_capabilities.declared_capabilities.map(
                            (capability) => (
                              <article
                                key={capability.capability_id}
                                className="capability-item"
                              >
                                <div className="capability-header">
                                  <strong>{capability.name}</strong>
                                  <span
                                    className={`status-chip ${statusTone(
                                      capability.status
                                    )}`}
                                  >
                                    {capability.status}
                                  </span>
                                </div>
                                <p className="capability-meta">
                                  {capability.capability_id} · {capability.kind} ·{" "}
                                  {capability.source_doc}
                                </p>
                                <p className="capability-meta">
                                  Runnable: {capability.runnable ? "ja" : "nej"}
                                </p>
                                {capability.runnable ? (
                                  <button
                                    className="ghost-button capability-action"
                                    type="button"
                                    disabled={capabilityInvokeBusy === capability.capability_id}
                                    onClick={() =>
                                      handleInvokeCapability(capability.capability_id)
                                    }
                                  >
                                    {capabilityInvokeBusy === capability.capability_id
                                      ? "Kører..."
                                      : "Invoke"}
                                  </button>
                                ) : null}
                              </article>
                            )
                          )}
                          {capabilityInvokeResult ? (
                            <div className="capability-result">
                              <strong>Seneste capability-resultat</strong>
                              <p>
                                Status:{" "}
                                <span
                                  className={`status-chip ${statusTone(
                                    capabilityInvokeResult.status
                                  )}`}
                                >
                                  {capabilityInvokeResult.status}
                                </span>
                              </p>
                              <p>
                                Capability:{" "}
                                {capabilityInvokeResult.capability?.capability_id || "ingen"}
                              </p>
                              <p>
                                Mode: {capabilityInvokeResult.execution_mode || "ukendt"}
                              </p>
                              <p>
                                Resultat:{" "}
                                {capabilityInvokeResult.result?.text ||
                                  capabilityInvokeResult.detail ||
                                  "ingen"}
                              </p>
                            </div>
                          ) : null}
                        </div>
                      ) : (
                        <p>Ingen deklarerede workspace capabilities endnu.</p>
                      )}
                    </section>
                  </div>
                ) : (
                  <p>Ingen visible run truth endnu.</p>
                )}
              </article>
              <article className="work-card">
                <strong>Seneste runtime-events</strong>
                <ul className="runtime-event-list">
                  {activityEvents.length ? (
                    activityEvents.map((item) => (
                      <li key={item.id}>
                        <span>{item.kind}</span>
                        <small>{item.created_at}</small>
                      </li>
                    ))
                  ) : (
                    <li>
                      <span>Ingen runtime-events endnu.</span>
                    </li>
                  )}
                </ul>
              </article>
            </div>
          </section>
          <StatusRail
            visibleControl={visibleControl}
            visibleControlState={visibleControlState}
            visibleControlError={visibleControlError}
            visibleControlNotice={visibleControlNotice}
            onRefresh={loadVisibleControl}
            onSave={handleVisibleControlSave}
          />
        </section>
      </main>
    </div>
  );
}

function statusTone(status) {
  if (status === "completed" || status === "reachable" || status === "ready") {
    return "status-ok";
  }
  if (status === "started" || status === "active" || status === "cancelled") {
    return "status-live";
  }
  if (
    status === "failed" ||
    status === "auth-rejected" ||
    status === "missing-credentials" ||
    status === "missing-profile" ||
    status === "unsupported-provider" ||
    status === "model-not-found" ||
    status === "unreachable"
  ) {
    return "status-bad";
  }
  return "status-idle";
}

async function consumeSseStream(stream, handlers) {
  const reader = stream.getReader();
  const decoder = new TextDecoder();
  let buffer = "";

  while (true) {
    const { value, done } = await reader.read();
    if (done) {
      break;
    }

    buffer += decoder.decode(value, { stream: true });
    const parts = buffer.split("\n\n");
    buffer = parts.pop() || "";

    for (const part of parts) {
      const parsed = parseSseChunk(part);
      if (!parsed) {
        continue;
      }
      if (parsed.event === "run") {
        handlers.onRun?.(parsed.data);
      } else if (parsed.event === "delta") {
        handlers.onDelta?.(parsed.data);
      } else if (parsed.event === "cancelled") {
        handlers.onCancelled?.(parsed.data);
      } else if (parsed.event === "failed") {
        handlers.onFailed?.(parsed.data);
      } else if (parsed.event === "done") {
        handlers.onDone?.(parsed.data);
      }
    }
  }
}

function parseSseChunk(chunk) {
  const lines = chunk.split("\n");
  let event = "message";
  const dataLines = [];

  for (const line of lines) {
    if (line.startsWith("event:")) {
      event = line.slice(6).trim();
    } else if (line.startsWith("data:")) {
      dataLines.push(line.slice(5).trim());
    }
  }

  if (!dataLines.length) {
    return null;
  }

  return {
    event,
    data: JSON.parse(dataLines.join("\n"))
  };
}
