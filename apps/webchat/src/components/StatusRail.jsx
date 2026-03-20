import { useEffect, useState } from "react";

const activityItems = [
  {
    title: "Aktivitet",
    body: "Tool- og tankeaktivitet vises her, mens Jarvis arbejder."
  },
  {
    title: "Arbejdsflade",
    body: "Artifacts, previews og resultater faar et separat arbejdsomraade senere."
  },
  {
    title: "Mission Control",
    body: "Observability og kontrol bliver ved siden af chatten, ikke blandet ind i den."
  }
];

const initialAuthority = {
  visible_model_provider: "",
  visible_model_name: "",
  visible_auth_profile: ""
};

export default function StatusRail({
  visibleControl,
  visibleControlState,
  visibleControlError,
  visibleControlNotice,
  onRefresh,
  onSave
}) {
  const [authority, setAuthority] = useState(initialAuthority);

  useEffect(() => {
    if (!visibleControl?.authority) {
      return;
    }
    setAuthority(visibleControl.authority);
  }, [visibleControl]);

  function handleSubmit(event) {
    event.preventDefault();
    onSave({
      visible_model_provider: authority.visible_model_provider.trim(),
      visible_model_name: authority.visible_model_name.trim(),
      visible_auth_profile: authority.visible_auth_profile.trim()
    });
  }

  const readiness = visibleControl?.readiness;
  const supportedProviders = visibleControl?.supported_providers || [];
  const availableProfiles = visibleControl?.available_auth_profiles || [];
  const authProfileOptions = buildProfileOptions(availableProfiles, authority.visible_auth_profile);

  return (
    <aside className="status-rail">
      <section className="panel rail-panel">
        <span className="eyebrow">Jarvis V2</span>
        <h2>Primary Front Door</h2>
        <p>
          Den synlige chatflade er her. Mission Control forbliver et separat
          kontrolplan.
        </p>
        <a className="mc-link" href="http://127.0.0.1:5173" target="_blank" rel="noreferrer">
          Aabn Mission Control
        </a>
      </section>
      <section className="panel rail-panel">
        <div className="rail-header">
          <div>
            <span className="eyebrow">Visible Lane</span>
            <h2>Execution Authority</h2>
          </div>
          <button
            className="ghost-button"
            type="button"
            onClick={onRefresh}
            disabled={visibleControlState === "loading" || visibleControlState === "saving"}
          >
            Opdater
          </button>
        </div>
        <form className="visible-control-form" onSubmit={handleSubmit}>
          <label>
            <span>Provider</span>
            <select
              value={authority.visible_model_provider}
              onChange={(event) =>
                setAuthority((prev) => ({
                  ...prev,
                  visible_model_provider: event.target.value
                }))
              }
              disabled={visibleControlState === "loading" || visibleControlState === "saving"}
            >
              {supportedProviders.map((provider) => (
                <option key={provider} value={provider}>
                  {provider}
                </option>
              ))}
            </select>
          </label>
          <label>
            <span>Model</span>
            <input
              value={authority.visible_model_name}
              onChange={(event) =>
                setAuthority((prev) => ({
                  ...prev,
                  visible_model_name: event.target.value
                }))
              }
              disabled={visibleControlState === "loading" || visibleControlState === "saving"}
            />
          </label>
          <label>
            <span>Auth profile</span>
            <select
              value={authority.visible_auth_profile}
              onChange={(event) =>
                setAuthority((prev) => ({
                  ...prev,
                  visible_auth_profile: event.target.value
                }))
              }
              disabled={visibleControlState === "loading" || visibleControlState === "saving"}
            >
              <option value="">ingen</option>
              {authProfileOptions.map((item) => (
                <option key={item.profile} value={item.profile}>
                  {item.profile}
                  {item.auth_status === "active" ? "" : ` (${item.auth_status})`}
                </option>
              ))}
            </select>
          </label>
          <div className="visible-control-actions">
            <button
              className="primary"
              type="submit"
              disabled={visibleControlState === "loading" || visibleControlState === "saving"}
            >
              {visibleControlState === "saving" ? "Gemmer..." : "Gem authority"}
            </button>
          </div>
        </form>
        <div className="visible-readiness">
          <strong>Readiness</strong>
          {readiness ? (
            <ul className="readiness-list">
              <li>
                <span>Mode</span>
                <small>{readiness.mode}</small>
              </li>
              <li>
                <span>Provider</span>
                <small>{readiness.provider}</small>
              </li>
              <li>
                <span>Model</span>
                <small>{readiness.model}</small>
              </li>
              <li>
                <span>Auth status</span>
                <small>{readiness.auth_status}</small>
              </li>
              <li>
                <span>Auth profile</span>
                <small>{readiness.auth_profile || "ingen"}</small>
              </li>
              <li>
                <span>Provider status</span>
                <small>{readiness.provider_status}</small>
              </li>
              <li>
                <span>Provider reachable</span>
                <small>{readiness.provider_reachable ? "ja" : "nej"}</small>
              </li>
              <li>
                <span>Live verified</span>
                <small>{readiness.live_verified ? "ja" : "nej"}</small>
              </li>
              <li>
                <span>Probe cache</span>
                <small>{readiness.probe_cache || "ingen"}</small>
              </li>
              <li>
                <span>Checked at</span>
                <small>{readiness.checked_at || "ikke-probet"}</small>
              </li>
            </ul>
          ) : (
            <p>Ingen readiness-data endnu.</p>
          )}
        </div>
        {visibleControlNotice ? <p className="control-success">{visibleControlNotice}</p> : null}
        {visibleControlError ? <p className="control-error">{visibleControlError}</p> : null}
      </section>
      <section className="panel rail-panel">
        <span className="eyebrow">Phase 1</span>
        <ul className="activity-list">
          {activityItems.map((item) => (
            <li key={item.title}>
              <strong>{item.title}</strong>
              <p>{item.body}</p>
            </li>
          ))}
        </ul>
      </section>
    </aside>
  );
}

function buildProfileOptions(items, currentValue) {
  const seen = new Set();
  const next = [];

  for (const item of items) {
    if (!item.profile || seen.has(item.profile)) {
      continue;
    }
    seen.add(item.profile);
    next.push(item);
  }

  if (currentValue && !seen.has(currentValue)) {
    next.unshift({
      profile: currentValue,
      auth_status: "configured"
    });
  }

  return next;
}
