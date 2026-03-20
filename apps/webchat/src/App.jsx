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
  const [wsState, setWsState] = useState("connecting");
  const [activityEvents, setActivityEvents] = useState([]);
  const [visibleControl, setVisibleControl] = useState(null);
  const [visibleControlState, setVisibleControlState] = useState("loading");
  const [visibleControlError, setVisibleControlError] = useState("");
  const [visibleControlNotice, setVisibleControlNotice] = useState("");

  useEffect(() => {
    const ws = new WebSocket("ws://127.0.0.1:8010/ws");

    ws.onopen = () => {
      setWsState("live");
    };

    ws.onmessage = (event) => {
      const item = JSON.parse(event.data);
      setActivityEvents((prev) => [item, ...prev].slice(0, 6));
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
          setActiveRunId(data.run_id);
        }
      });
    } catch (streamError) {
      setError(streamError instanceof Error ? streamError.message : "Ukendt stream-fejl.");
    } finally {
      setIsRunning(false);
      setActiveRunId(null);
    }
  }

  async function loadVisibleControl() {
    setVisibleControlState("loading");
    setVisibleControlError("");

    try {
      const response = await fetch(`${API_BASE}/mc/visible-execution`);
      if (!response.ok) {
        throw new Error("Visible lane authority kunne ikke hentes.");
      }
      const data = await response.json();
      setVisibleControl(data);
      setVisibleControlState("ready");
    } catch (fetchError) {
      setVisibleControlState("error");
      setVisibleControlError(
        fetchError instanceof Error ? fetchError.message : "Ukendt authority-fejl."
      );
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
            {error ? <p className="chat-error">{error}</p> : null}
          </section>
          <ComposerShell
            draft={draft}
            isRunning={isRunning}
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
