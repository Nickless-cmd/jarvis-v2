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
  provider: "",
  model: "",
  auth_profile: ""
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

  const mainAgentSelection = visibleControl?.provider_router?.main_agent_selection;
  const configuredTargets = mainAgentSelection?.available_configured_targets || [];
  const readiness = visibleControl?.readiness;

  useEffect(() => {
    if (!mainAgentSelection) {
      return;
    }
    setAuthority({
      provider: mainAgentSelection.current_provider || "",
      model: mainAgentSelection.current_model || "",
      auth_profile: mainAgentSelection.current_auth_profile || ""
    });
  }, [mainAgentSelection]);

  function handleSubmit(event) {
    event.preventDefault();
    onSave({
      provider: authority.provider.trim(),
      model: authority.model.trim(),
      auth_profile: authority.auth_profile.trim()
    });
  }

  const providerOptions = buildProviderOptions(configuredTargets, authority.provider);
  const modelOptions = buildModelOptions(configuredTargets, authority.provider, authority.model);
  const authProfileOptions = buildAuthProfileOptions(
    configuredTargets,
    authority.provider,
    authority.model,
    authority.auth_profile
  );
  const formDisabled =
    visibleControlState === "loading" ||
    visibleControlState === "saving" ||
    configuredTargets.length === 0;

  return (
    <aside className="status-rail">
      <section className="panel rail-panel">
        <span className="eyebrow">Jarvis V2</span>
        <h2>Primary Front Door</h2>
        <p>
          Den synlige chatflade er her. Mission Control forbliver et separat
          kontrolplan.
        </p>
        <a className="mc-link" href="/mc/runtime" target="_blank" rel="noreferrer">
          Aabn Mission Control
        </a>
      </section>
      <section className="panel rail-panel">
        <div className="rail-header">
          <div>
            <span className="eyebrow">Main Agent</span>
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
              value={authority.provider}
              onChange={(event) => {
                const provider = event.target.value;
                const model = firstMatchingModel(configuredTargets, provider, authority.model);
                const authProfile = firstMatchingAuthProfile(
                  configuredTargets,
                  provider,
                  model,
                  authority.auth_profile
                );
                setAuthority({
                  provider,
                  model,
                  auth_profile: authProfile
                });
              }}
              disabled={formDisabled}
            >
              {providerOptions.map((provider) => (
                <option key={provider} value={provider}>
                  {provider}
                </option>
              ))}
            </select>
          </label>
          <label>
            <span>Model</span>
            <select
              value={authority.model}
              onChange={(event) => {
                const model = event.target.value;
                setAuthority((prev) => ({
                  ...prev,
                  model,
                  auth_profile: firstMatchingAuthProfile(
                    configuredTargets,
                    prev.provider,
                    model,
                    prev.auth_profile
                  )
                }));
              }}
              disabled={formDisabled}
            >
              {modelOptions.map((model) => (
                <option key={model} value={model}>
                  {model}
                </option>
              ))}
            </select>
          </label>
          <label>
            <span>Auth profile</span>
            <select
              value={authority.auth_profile}
              onChange={(event) =>
                setAuthority((prev) => ({
                  ...prev,
                  auth_profile: event.target.value
                }))
              }
              disabled={formDisabled}
            >
              <option value="">ingen</option>
              {authProfileOptions.map((profile) => (
                <option key={profile} value={profile}>
                  {profile}
                </option>
              ))}
            </select>
          </label>
          <div className="visible-control-actions">
            <button className="primary" type="submit" disabled={formDisabled}>
              {visibleControlState === "saving" ? "Gemmer..." : "Gem main-agent target"}
            </button>
          </div>
        </form>
        {mainAgentSelection ? (
          <p>
            Current: {mainAgentSelection.current_provider || "ingen"} /{" "}
            {mainAgentSelection.current_model || "ingen"} /{" "}
            {mainAgentSelection.current_auth_profile || "ingen"}
          </p>
        ) : null}
        {!configuredTargets.length ? (
          <p>Ingen konfigurerede provider-router targets endnu.</p>
        ) : null}
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

function buildProviderOptions(targets, currentValue) {
  const seen = new Set();
  const next = [];

  for (const item of targets) {
    const provider = item.provider || "";
    if (!provider || seen.has(provider)) {
      continue;
    }
    seen.add(provider);
    next.push(provider);
  }

  if (currentValue && !seen.has(currentValue)) {
    next.unshift(currentValue);
  }

  return next;
}

function buildModelOptions(targets, provider, currentValue) {
  const seen = new Set();
  const next = [];

  for (const item of targets) {
    if ((item.provider || "") !== provider) {
      continue;
    }
    const model = item.model || "";
    if (!model || seen.has(model)) {
      continue;
    }
    seen.add(model);
    next.push(model);
  }

  if (currentValue && !seen.has(currentValue)) {
    next.unshift(currentValue);
  }

  return next;
}

function buildAuthProfileOptions(targets, provider, model, currentValue) {
  const seen = new Set();
  const next = [];

  for (const item of targets) {
    if ((item.provider || "") !== provider || (item.model || "") !== model) {
      continue;
    }
    const authProfile = item.auth_profile || "";
    if (!authProfile || seen.has(authProfile)) {
      continue;
    }
    seen.add(authProfile);
    next.push(authProfile);
  }

  if (currentValue && !seen.has(currentValue)) {
    next.unshift(currentValue);
  }

  return next;
}

function firstMatchingModel(targets, provider, currentValue) {
  const next = buildModelOptions(targets, provider, currentValue);
  return next[0] || "";
}

function firstMatchingAuthProfile(targets, provider, model, currentValue) {
  const next = buildAuthProfileOptions(targets, provider, model, currentValue);
  return next[0] || "";
}
