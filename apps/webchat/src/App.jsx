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
  const [approvalRequestBusy, setApprovalRequestBusy] = useState("");

  useEffect(() => {
    const ws = new WebSocket("ws://127.0.0.1:8010/ws");

    ws.onopen = () => {
      setWsState("live");
    };

    ws.onmessage = (event) => {
      const item = JSON.parse(event.data);
      setActivityEvents((prev) => [item, ...prev].slice(0, 6));
      if (
        item.kind?.startsWith("runtime.visible_run_") ||
        item.kind?.startsWith("runtime.capability_invocation_")
      ) {
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

  async function handleInvokeCapability(capabilityId, approvalRequired) {
    setVisibleControlNotice("");
    setVisibleControlError("");
    setCapabilityInvokeBusy(capabilityId);

    try {
      const response = await fetch(
        `${API_BASE}/mc/workspace-capabilities/${encodeURIComponent(capabilityId)}/invoke${
          approvalRequired ? "?approved=true" : ""
        }`,
        {
          method: "POST"
        }
      );
      const data = await response.json();
      if (!response.ok) {
        throw new Error(data.detail || "Capability kunne ikke invokes.");
      }
      await loadVisibleControl({ quiet: true });
      setVisibleControlNotice(
        approvalRequired
          ? `Capability ${capabilityId} godkendt og kørt via runtime-truth.`
          : `Capability ${capabilityId} kørt via runtime-truth.`
      );
    } catch (invokeError) {
      setVisibleControlError(
        invokeError instanceof Error ? invokeError.message : "Ukendt capability-fejl."
      );
    } finally {
      setCapabilityInvokeBusy("");
    }
  }

  async function handleApproveCapabilityRequest(requestId) {
    setVisibleControlNotice("");
    setVisibleControlError("");
    setApprovalRequestBusy(requestId);

    try {
      const response = await fetch(
        `${API_BASE}/mc/capability-approval-requests/${encodeURIComponent(requestId)}/approve`,
        {
          method: "POST"
        }
      );
      const data = await response.json();
      if (!response.ok) {
        throw new Error(data.detail || "Approval request kunne ikke godkendes.");
      }
      await loadVisibleControl({ quiet: true });
      setVisibleControlNotice(`Approval request ${requestId} markeret som approved.`);
    } catch (approveError) {
      setVisibleControlError(
        approveError instanceof Error ? approveError.message : "Ukendt approval-fejl."
      );
    } finally {
      setApprovalRequestBusy("");
    }
  }

  async function handleExecuteCapabilityRequest(requestId) {
    setVisibleControlNotice("");
    setVisibleControlError("");
    setApprovalRequestBusy(`execute:${requestId}`);

    try {
      const response = await fetch(
        `${API_BASE}/mc/capability-approval-requests/${encodeURIComponent(requestId)}/execute`,
        {
          method: "POST"
        }
      );
      const data = await response.json();
      if (!response.ok) {
        throw new Error(data.detail || "Approved request kunne ikke eksekveres.");
      }
      await loadVisibleControl({ quiet: true });
      setVisibleControlNotice(`Approved request ${requestId} eksekveret via runtime-truth.`);
    } catch (executeError) {
      setVisibleControlError(
        executeError instanceof Error ? executeError.message : "Ukendt execute-fejl."
      );
    } finally {
      setApprovalRequestBusy("");
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
                      <h3>Visible identity</h3>
                      {visibleControl.visible_identity ? (
                        <ul className="runtime-event-list compact">
                          <li>
                            <span>
                              Aktiv: {visibleControl.visible_identity.active ? "ja" : "nej"}
                            </span>
                            <small>
                              <span
                                className={`status-chip ${
                                  visibleControl.visible_identity.active
                                    ? "status-ok"
                                    : "status-idle"
                                }`}
                              >
                                {visibleControl.visible_identity.active
                                  ? "aktiv"
                                  : "inaktiv"}
                              </span>
                            </small>
                          </li>
                          <li>
                            <span>
                              Workspace: {visibleControl.visible_identity.name || "ingen"}
                            </span>
                          </li>
                          <li>
                            <span>
                              Kilder:{" "}
                              {visibleControl.visible_identity.source_files?.join(", ") ||
                                "ingen"}
                            </span>
                          </li>
                          <li>
                            <span>
                              Linjer:{" "}
                              {visibleControl.visible_identity.extracted_line_count ??
                                "ingen"}
                            </span>
                          </li>
                          <li>
                            <span>
                              Fingerprint:{" "}
                              {visibleControl.visible_identity.fingerprint || "ingen"}
                            </span>
                          </li>
                        </ul>
                      ) : (
                        <p>Ingen visible identity truth endnu.</p>
                      )}
                    </section>
                    <section className="truth-section">
                      <h3>Visible work</h3>
                      {visibleControl.visible_work ? (
                        <>
                          <ul className="runtime-event-list compact">
                            <li>
                              <span>
                                Aktiv: {visibleControl.visible_work.active ? "ja" : "nej"}
                              </span>
                              <small>
                                <span
                                  className={`status-chip ${
                                    visibleControl.visible_work.active
                                      ? "status-live"
                                      : "status-idle"
                                  }`}
                                >
                                  {visibleControl.visible_work.active ? "aktiv" : "idle"}
                                </span>
                              </small>
                            </li>
                            <li>
                              <span>Run: {visibleControl.visible_work.run_id || "ingen"}</span>
                            </li>
                            <li>
                              <span>
                                Status: {visibleControl.visible_work.status || "ingen"}
                              </span>
                            </li>
                            <li>
                              <span>Lane: {visibleControl.visible_work.lane || "ingen"}</span>
                            </li>
                            <li>
                              <span>
                                Provider/model:{" "}
                                {visibleControl.visible_work.provider || "ingen"} /{" "}
                                {visibleControl.visible_work.model || "ingen"}
                              </span>
                            </li>
                            <li>
                              <span>
                                Startet: {visibleControl.visible_work.started_at || "ingen"}
                              </span>
                            </li>
                            <li>
                              <span>
                                Work preview:{" "}
                                {visibleControl.visible_work.current_user_message_preview ||
                                  "ingen"}
                              </span>
                            </li>
                            <li>
                              <span>
                                Capability:{" "}
                                {visibleControl.visible_work.capability_id || "ingen"}
                              </span>
                            </li>
                          </ul>
                          <h4>Persisted visible work units</h4>
                          {visibleControl.visible_work.persisted_recent_units?.length ? (
                            <ul className="runtime-event-list compact">
                              {visibleControl.visible_work.persisted_recent_units.map(
                                (item) => (
                                  <li key={item.work_id || item.run_id}>
                                    <span>{item.work_id || item.run_id || "ingen"}</span>
                                    <small>
                                      <span
                                        className={`status-chip ${statusTone(item.status)}`}
                                      >
                                        {item.status || "ukendt"}
                                      </span>{" "}
                                      · {item.finished_at || "ingen"}
                                      {item.run_id ? ` · ${item.run_id}` : ""}
                                      {item.capability_id ? ` · ${item.capability_id}` : ""}
                                      {item.user_message_preview
                                        ? ` · ${item.user_message_preview}`
                                        : ""}
                                      {item.work_preview ? ` · ${item.work_preview}` : ""}
                                    </small>
                                  </li>
                                )
                              )}
                            </ul>
                          ) : (
                            <p>Ingen persisted visible work units endnu.</p>
                          )}
                        </>
                      ) : (
                        <p>Ingen visible work truth endnu.</p>
                      )}
                    </section>
                    <section className="truth-section">
                      <h3>Visible session continuity</h3>
                      {visibleControl.visible_session_continuity ? (
                        <ul className="runtime-event-list compact">
                          <li>
                            <span>
                              Aktiv:{" "}
                              {visibleControl.visible_session_continuity.active
                                ? "ja"
                                : "nej"}
                            </span>
                            <small>
                              <span
                                className={`status-chip ${
                                  visibleControl.visible_session_continuity.active
                                    ? "status-ok"
                                    : "status-idle"
                                }`}
                              >
                                {visibleControl.visible_session_continuity.active
                                  ? "aktiv"
                                  : "inaktiv"}
                              </span>
                            </small>
                          </li>
                          <li>
                            <span>
                              Seneste run:{" "}
                              {visibleControl.visible_session_continuity.latest_run_id ||
                                "ingen"}
                            </span>
                          </li>
                          <li>
                            <span>
                              Status:{" "}
                              {visibleControl.visible_session_continuity.latest_status ||
                                "ingen"}
                            </span>
                          </li>
                          <li>
                            <span>
                              Afsluttet:{" "}
                              {visibleControl.visible_session_continuity
                                .latest_finished_at || "ingen"}
                            </span>
                          </li>
                          <li>
                            <span>
                              Seneste capability:{" "}
                              {visibleControl.visible_session_continuity
                                .latest_capability_id || "ingen"}
                            </span>
                          </li>
                          <li>
                            <span>
                              Recent capabilities:{" "}
                              {visibleControl.visible_session_continuity.recent_capability_ids?.join(
                                ", "
                              ) || "ingen"}
                            </span>
                          </li>
                          <li>
                            <span>
                              Rows:{" "}
                              {visibleControl.visible_session_continuity
                                .included_run_rows ?? "ingen"}{" "}
                              /{" "}
                              {visibleControl.visible_session_continuity
                                .included_capability_rows ?? "ingen"}
                            </span>
                          </li>
                        </ul>
                      ) : (
                        <p>Ingen visible session continuity truth endnu.</p>
                      )}
                    </section>
                    <section className="truth-section">
                      <h3>Visible continuity</h3>
                      {visibleControl.visible_continuity ? (
                        <ul className="runtime-event-list compact">
                          <li>
                            <span>
                              Aktiv: {visibleControl.visible_continuity.active ? "ja" : "nej"}
                            </span>
                            <small>
                              <span
                                className={`status-chip ${
                                  visibleControl.visible_continuity.active
                                    ? "status-ok"
                                    : "status-idle"
                                }`}
                              >
                                {visibleControl.visible_continuity.active
                                  ? "aktiv"
                                  : "inaktiv"}
                              </span>
                            </small>
                          </li>
                          <li>
                            <span>
                              Kilde: {visibleControl.visible_continuity.source || "ingen"}
                            </span>
                          </li>
                          <li>
                            <span>
                              Runs:{" "}
                              {visibleControl.visible_continuity.included_run_ids?.join(
                                ", "
                              ) || "ingen"}
                            </span>
                          </li>
                          <li>
                            <span>
                              Statusser:{" "}
                              {visibleControl.visible_continuity.statuses?.join(", ") ||
                                "ingen"}
                            </span>
                          </li>
                          <li>
                            <span>
                              Rows/chars:{" "}
                              {visibleControl.visible_continuity.included_rows ?? "ingen"} /{" "}
                              {visibleControl.visible_continuity.chars ?? "ingen"}
                            </span>
                          </li>
                        </ul>
                      ) : (
                        <p>Ingen visible continuity truth endnu.</p>
                      )}
                    </section>
                    <section className="truth-section">
                      <h3>Visible capability continuity</h3>
                      {visibleControl.visible_capability_continuity ? (
                        <ul className="runtime-event-list compact">
                          <li>
                            <span>
                              Aktiv:{" "}
                              {visibleControl.visible_capability_continuity.active
                                ? "ja"
                                : "nej"}
                            </span>
                            <small>
                              <span
                                className={`status-chip ${
                                  visibleControl.visible_capability_continuity.active
                                    ? "status-ok"
                                    : "status-idle"
                                }`}
                              >
                                {visibleControl.visible_capability_continuity.active
                                  ? "aktiv"
                                  : "inaktiv"}
                              </span>
                            </small>
                          </li>
                          <li>
                            <span>
                              Kilde:{" "}
                              {visibleControl.visible_capability_continuity.source ||
                                "ingen"}
                            </span>
                          </li>
                          <li>
                            <span>
                              Capabilities:{" "}
                              {visibleControl.visible_capability_continuity.included_capability_ids?.join(
                                ", "
                              ) || "ingen"}
                            </span>
                          </li>
                          <li>
                            <span>
                              Statusser:{" "}
                              {visibleControl.visible_capability_continuity.statuses?.join(
                                ", "
                              ) || "ingen"}
                            </span>
                          </li>
                          <li>
                            <span>
                              Rows/chars:{" "}
                              {visibleControl.visible_capability_continuity.included_rows ??
                                "ingen"}{" "}
                              /{" "}
                              {visibleControl.visible_capability_continuity.chars ??
                                "ingen"}
                            </span>
                          </li>
                        </ul>
                      ) : (
                        <p>Ingen visible capability continuity truth endnu.</p>
                      )}
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
                      <h3>Sidste capability-brug i visible run</h3>
                      {visibleControl.visible_run.last_capability_use ? (
                        <ul className="runtime-event-list compact">
                          <li>
                            <span>
                              Capability:{" "}
                              {visibleControl.visible_run.last_capability_use
                                .capability_id || "ingen"}
                            </span>
                          </li>
                          <li>
                            <span>
                              Navn:{" "}
                              {visibleControl.visible_run.last_capability_use
                                .capability?.name || "ingen"}
                            </span>
                          </li>
                          <li>
                            <span>
                              Status:{" "}
                              {visibleControl.visible_run.last_capability_use.status ||
                                "ingen"}
                            </span>
                            <small>
                              <span
                                className={`status-chip ${statusTone(
                                  visibleControl.visible_run.last_capability_use.status
                                )}`}
                              >
                                {visibleControl.visible_run.last_capability_use.status ||
                                  "ingen"}
                              </span>
                            </small>
                          </li>
                          <li>
                            <span>
                              Mode:{" "}
                              {visibleControl.visible_run.last_capability_use
                                .execution_mode || "ingen"}
                            </span>
                          </li>
                          <li>
                            <span>
                              Brugt:{" "}
                              {visibleControl.visible_run.last_capability_use.used_at ||
                                "ingen"}
                            </span>
                          </li>
                          <li>
                            <span>
                              Preview/detail:{" "}
                              {visibleControl.visible_run.last_capability_use
                                .result_preview ||
                                visibleControl.visible_run.last_capability_use.detail ||
                                "ingen"}
                            </span>
                          </li>
                        </ul>
                      ) : (
                        <p>Ingen capability-brug i visible run endnu.</p>
                      )}
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
                      <h3>Persisted recent visible runs</h3>
                      {visibleControl.visible_run.persisted_recent_runs?.length ? (
                        <ul className="runtime-event-list compact">
                          {visibleControl.visible_run.persisted_recent_runs.map((item) => (
                            <li key={item.run_id}>
                              <span>{item.run_id}</span>
                              <small>
                                <span
                                  className={`status-chip ${statusTone(item.status)}`}
                                >
                                  {item.status || "ukendt"}
                                </span>{" "}
                                · {item.provider || "ingen"} / {item.model || "ingen"} ·{" "}
                                {item.finished_at || "ingen"}
                                {item.capability_id ? ` · ${item.capability_id}` : ""}
                                {item.text_preview ? ` · ${item.text_preview}` : ""}
                              </small>
                            </li>
                          ))}
                        </ul>
                      ) : (
                        <p>Ingen persisted visible runs endnu.</p>
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
                                <p className="capability-meta">
                                  Approval:{" "}
                                  {capability.approval_policy || "not-applicable"}
                                  {capability.approval_required ? " · required" : ""}
                                </p>
                                {capability.runnable ? (
                                  <button
                                    className="ghost-button capability-action"
                                    type="button"
                                    disabled={capabilityInvokeBusy === capability.capability_id}
                                    onClick={() =>
                                      handleInvokeCapability(
                                        capability.capability_id,
                                        capability.approval_required
                                      )
                                    }
                                  >
                                    {capabilityInvokeBusy === capability.capability_id
                                      ? "Kører..."
                                      : capability.approval_required
                                        ? "Approve + invoke"
                                        : "Invoke"}
                                  </button>
                                ) : null}
                              </article>
                            )
                          )}
                        </div>
                      ) : (
                        <p>Ingen deklarerede workspace capabilities endnu.</p>
                      )}
                    </section>
                    <section className="truth-section">
                      <h3>Sidste capability invocation</h3>
                      {visibleControl.capability_invocation?.last_invocation ? (
                        <ul className="runtime-event-list compact">
                          <li>
                            <span>
                              Aktiv:{" "}
                              {visibleControl.capability_invocation.active ? "ja" : "nej"}
                            </span>
                            <small>
                              <span
                                className={`status-chip ${
                                  visibleControl.capability_invocation.active
                                    ? "status-live"
                                    : "status-idle"
                                }`}
                              >
                                {visibleControl.capability_invocation.active
                                  ? "aktiv"
                                  : "inaktiv"}
                              </span>
                            </small>
                          </li>
                          <li>
                            <span>
                              Capability:{" "}
                              {visibleControl.capability_invocation.last_invocation
                                .capability_id || "ingen"}
                            </span>
                          </li>
                          <li>
                            <span>
                              Navn:{" "}
                              {visibleControl.capability_invocation.last_invocation
                                .capability?.name || "ingen"}
                            </span>
                          </li>
                          <li>
                            <span>
                              Status:{" "}
                              {visibleControl.capability_invocation.last_invocation.status ||
                                "ingen"}
                            </span>
                            <small>
                              <span
                                className={`status-chip ${statusTone(
                                  visibleControl.capability_invocation.last_invocation.status
                                )}`}
                              >
                                {visibleControl.capability_invocation.last_invocation.status ||
                                  "ingen"}
                              </span>
                            </small>
                          </li>
                          <li>
                            <span>
                              Mode:{" "}
                              {visibleControl.capability_invocation.last_invocation
                                .execution_mode || "ingen"}
                            </span>
                          </li>
                          <li>
                            <span>
                              Approval:{" "}
                              {visibleControl.capability_invocation.last_invocation
                                .approval?.policy || "ingen"}
                              {visibleControl.capability_invocation.last_invocation
                                .approval?.required
                                ? " · required"
                                : ""}
                              {visibleControl.capability_invocation.last_invocation
                                .approval?.approved
                                ? " · approved"
                                : ""}
                              {visibleControl.capability_invocation.last_invocation
                                .approval?.granted
                                ? " · granted"
                                : ""}
                            </span>
                          </li>
                          <li>
                            <span>
                              Invoked:{" "}
                              {visibleControl.capability_invocation.last_invocation
                                .invoked_at || "ingen"}
                            </span>
                          </li>
                          <li>
                            <span>
                              Finished:{" "}
                              {visibleControl.capability_invocation.last_invocation
                                .finished_at || "ingen"}
                            </span>
                          </li>
                          <li>
                            <span>
                              Preview/detail:{" "}
                              {visibleControl.capability_invocation.last_invocation
                                .result_preview ||
                                visibleControl.capability_invocation.last_invocation.detail ||
                                "ingen"}
                            </span>
                          </li>
                        </ul>
                      ) : (
                        <p>Ingen capability invocation endnu.</p>
                      )}
                    </section>
                    <section className="truth-section">
                      <h3>Capability invocation recent events</h3>
                      {visibleControl.capability_invocation?.recent_events?.length ? (
                        <ul className="runtime-event-list compact">
                          {visibleControl.capability_invocation.recent_events.map((item) => (
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
                                · {item.payload?.capability_id || "ingen"} · {item.created_at}
                              </small>
                            </li>
                          ))}
                        </ul>
                      ) : (
                        <p>Ingen capability invocation-events endnu.</p>
                      )}
                    </section>
                    <section className="truth-section">
                      <h3>Persisted recent capability invocations</h3>
                      {visibleControl.capability_invocation
                        ?.persisted_recent_invocations?.length ? (
                        <ul className="runtime-event-list compact">
                          {visibleControl.capability_invocation.persisted_recent_invocations.map(
                            (item, index) => (
                              <li key={`${item.capability_id || "capability"}-${index}`}>
                                <span>
                                  {item.capability_name || item.capability_id || "ingen"}
                                </span>
                                <small>
                                  <span
                                    className={`status-chip ${statusTone(item.status)}`}
                                  >
                                    {item.status || "ukendt"}
                                  </span>{" "}
                                  · {item.execution_mode || "ingen"} ·{" "}
                                  {item.finished_at || "ingen"}
                                  {item.approval?.policy
                                    ? ` · approval=${item.approval.policy}`
                                    : ""}
                                  {item.approval?.required ? " · required" : ""}
                                  {item.approval?.approved ? " · approved" : ""}
                                  {item.approval?.granted ? " · granted" : ""}
                                  {item.run_id ? ` · ${item.run_id}` : ""}
                                  {item.result_preview ? ` · ${item.result_preview}` : ""}
                                </small>
                              </li>
                            )
                          )}
                        </ul>
                      ) : (
                        <p>Ingen persisted capability invocations endnu.</p>
                      )}
                    </section>
                    <section className="truth-section">
                      <h3>Recent approval requests</h3>
                      {visibleControl.capability_invocation?.recent_approval_requests?.length ? (
                        <ul className="runtime-event-list compact">
                          {visibleControl.capability_invocation.recent_approval_requests.map(
                            (item) => (
                              <li key={item.request_id}>
                                <span>
                                  {item.capability_name || item.capability_id || "ingen"}
                                </span>
                                <small>
                                  <span
                                    className={`status-chip ${statusTone(item.status)}`}
                                  >
                                    {item.status || "ukendt"}
                                  </span>{" "}
                                  · {item.execution_mode || "ingen"} ·{" "}
                                  {item.approval_policy || "ingen"} ·{" "}
                                  {item.requested_at || "ingen"}
                                  {item.run_id ? ` · ${item.run_id}` : ""}
                                  {item.request_id ? ` · ${item.request_id}` : ""}
                                  {item.approved_at ? ` · ${item.approved_at}` : ""}
                                  {item.executed ? " · executed" : ""}
                                  {item.executed_at ? ` · ${item.executed_at}` : ""}
                                  {item.invocation_status
                                    ? ` · invoke=${item.invocation_status}`
                                    : ""}
                                  {item.invocation_execution_mode
                                    ? ` · ${item.invocation_execution_mode}`
                                    : ""}
                                </small>
                                {item.status === "pending" && item.request_id ? (
                                  <button
                                    className="ghost-button capability-action"
                                    type="button"
                                    disabled={approvalRequestBusy === item.request_id}
                                    onClick={() =>
                                      handleApproveCapabilityRequest(item.request_id)
                                    }
                                  >
                                    {approvalRequestBusy === item.request_id
                                      ? "Godkender..."
                                      : "Approve"}
                                  </button>
                                ) : null}
                                {item.status === "approved" && item.request_id ? (
                                  <button
                                    className="ghost-button capability-action"
                                    type="button"
                                    disabled={
                                      approvalRequestBusy === `execute:${item.request_id}`
                                    }
                                    onClick={() =>
                                      handleExecuteCapabilityRequest(item.request_id)
                                    }
                                  >
                                    {approvalRequestBusy === `execute:${item.request_id}`
                                      ? "Eksekverer..."
                                      : "Execute"}
                                  </button>
                                ) : null}
                              </li>
                            )
                          )}
                        </ul>
                      ) : (
                        <p>Ingen approval requests endnu.</p>
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
  if (
    status === "completed" ||
    status === "reachable" ||
    status === "ready" ||
    status === "executed"
  ) {
    return "status-ok";
  }
  if (status === "started" || status === "active" || status === "cancelled") {
    return "status-live";
  }
  if (
    status === "failed" ||
    status === "approval-required" ||
    status === "not-found" ||
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
