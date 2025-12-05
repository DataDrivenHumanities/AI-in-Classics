"use client";

import React, { useEffect, useMemo, useState } from "react";

type ModelStatus = {
  id: string;            // canonical id we’ll use for selection
  label: string;         // what we show in the UI (never empty)
  source?: string | null;
  ok: boolean;
  details?: string | null;
};

type TrainJob = {
  id: string;
  ts: string;
  model_id: string;
  preset_name?: string | null;
  strategy: string;
  filters: Record<string, any>;
  status: string;
  stats?: { feedback_count?: number; [k: string]: any };
};

type Props = {
  open: boolean;
  onClose: () => void;
  apiBase: string;
};

function coerceBool(v: any): boolean {
  if (typeof v === "boolean") return v;
  if (typeof v === "number") return v !== 0;
  if (typeof v === "string") {
    const s = v.toLowerCase().trim();
    return s === "true" || s === "online" || s === "ok" || s === "ready" || s === "available" || s === "up";
  }
  return false;
}

function pickId(m: any): string | null {
  const cands = [m?.id, m?.model, m?.name, m?.tag, m?.label, m?.slug];
  for (const c of cands) {
    if (typeof c === "string" && c.trim()) return c.trim();
  }
  return null;
}

function pickLabel(m: any): string {
  const cands = [m?.id, m?.model, m?.name, m?.label, m?.tag, m?.slug, m?.displayName];
  for (const c of cands) {
    if (typeof c === "string" && c.trim()) return c.trim();
  }
  // if absolutely nothing, show something debuggable
  try {
    return `(unnamed) ${JSON.stringify(m).slice(0, 80)}…`;
  } catch {
    return "(unnamed)";
  }
}

function normalizeOne(m: any): ModelStatus | null {
  const id = pickId(m);
  if (!id) return null;
  const ok =
    coerceBool(m?.ok) ||
    coerceBool(m?.online) ||
    coerceBool(m?.available) ||
    coerceBool(m?.status) ||
    coerceBool(m?.reachable);
  const source = m?.source || m?.origin || null;
  const details = m?.details ?? null;
  const label = pickLabel(m);
  return { id, label, ok, source, details };
}

function normalizeModels(raw: any): ModelStatus[] {
  // 1) { models: [...] }
  if (Array.isArray(raw?.models)) {
    const out: ModelStatus[] = [];
    for (const m of raw.models) {
      const n = normalizeOne(m);
      if (n) out.push(n);
    }
    return out;
  }
  // 2) { models: { online: [...], offline: [...] } }
  if (raw?.models && typeof raw.models === "object" && !Array.isArray(raw.models)) {
    const out: ModelStatus[] = [];
    const on = Array.isArray(raw.models.online) ? raw.models.online : [];
    const off = Array.isArray(raw.models.offline) ? raw.models.offline : [];
    for (const m of on) {
      const n = normalizeOne({ ...(m || {}), ok: true });
      if (n) out.push(n);
    }
    for (const m of off) {
      const n = normalizeOne({ ...(m || {}), ok: false });
      if (n) out.push(n);
    }
    return out;
  }
  // 3) raw is an array
  if (Array.isArray(raw)) {
    const out: ModelStatus[] = [];
    for (const m of raw) {
      const n = normalizeOne(m);
      if (n) out.push(n);
    }
    return out;
  }
  return [];
}

export default function ModelShopModal({ open, onClose, apiBase }: Props) {
  const [tab, setTab] = useState<"models" | "jobs">("models");

  const [loadingModels, setLoadingModels] = useState(false);
  const [models, setModels] = useState<ModelStatus[]>([]);
  const [selected, setSelected] = useState<string>("");

  const [strategy, setStrategy] = useState<"rag_refresh" | "prompt_update" | "lora">("rag_refresh");
  const [tags, setTags] = useState<string>("");
  const [limit, setLimit] = useState<string>("");
  const [presetName, setPresetName] = useState<string>("");

  const [loadingJobs, setLoadingJobs] = useState(false);
  const [jobs, setJobs] = useState<TrainJob[]>([]);
  const [jobError, setJobError] = useState<string>("");

  const [error, setError] = useState<string>("");
  const [msg, setMsg] = useState<string>("");

  useEffect(() => {
    if (!open) return;
    setTab("models");
    setError("");
    setMsg("");
    setJobError("");
    setSelected("");
    setStrategy("rag_refresh");
    setTags("");
    setLimit("");
    setPresetName("");

    let cancelled = false;
    (async () => {
      await refreshModels(cancelled);
      await refreshJobs(cancelled);
    })();
    return () => { cancelled = true; };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [open, apiBase]);

  async function refreshModels(cancelled = false) {
    setLoadingModels(true);
    try {
      const r = await fetch(`${apiBase}/models/status`);
      if (!r.ok) throw new Error(`Failed to load models: ${r.status}`);
      const data = await r.json();
      const list = normalizeModels(data);
      if (!cancelled) setModels(list);
    } catch (e: any) {
      if (!cancelled) setError(e?.message || "Failed to load models");
    } finally {
      if (!cancelled) setLoadingModels(false);
    }
  }

  async function refreshJobs(cancelled = false) {
    setLoadingJobs(true);
    setJobError("");
    try {
      const r = await fetch(`${apiBase}/train`);
      if (!r.ok) throw new Error(`Failed to load jobs: ${r.status}`);
      const data = await r.json();
      const list: TrainJob[] = Array.isArray(data?.jobs) ? data.jobs : [];
      if (!cancelled) setJobs(list);
    } catch (e: any) {
      if (!cancelled) setJobError(e?.message || "Failed to load jobs");
    } finally {
      if (!cancelled) setLoadingJobs(false);
    }
  }

  const online = useMemo(() => models.filter((m) => m.ok), [models]);
  const offline = useMemo(() => models.filter((m) => !m.ok), [models]);

  async function handleTrain() {
    setError("");
    setMsg("");
    if (!selected) {
      setError("Select a model to train.");
      return;
    }
    const payload: any = { model_id: selected, strategy };
    if (presetName.trim()) payload.preset_name = presetName.trim();
    const t = tags.split(",").map((s) => s.trim()).filter(Boolean);
    if (t.length) payload.tags = t;
    const lim = parseInt(limit, 10);
    if (!Number.isNaN(lim) && lim > 0) payload.limit = lim;

    try {
      const r = await fetch(`${apiBase}/train`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });
      if (!r.ok) throw new Error(`Train request failed: ${r.status}`);
      const data = await r.json();
      setMsg(`Queued job ${data.job_id} (${data.feedback_count} examples).`);
      await refreshJobs(false);
      setTab("jobs");
    } catch (e: any) {
      setError(e?.message || "Failed to start training");
    }
  }

  if (!open) return null;

  return (
    <div className="modal" onClick={onClose}>
      <div className="modal-inner compact" onClick={(e) => e.stopPropagation()}>
        <div className="modal-bar">
          <div className="modal-title">Model Shop</div>
          <div className="modal-actions">
            <button className="modal-close" onClick={onClose}>Close</button>
          </div>
        </div>

        <div className="shop-tabs">
          <button className={`tab-btn ${tab === "models" ? "active" : ""}`} onClick={() => setTab("models")}>
            Models
          </button>
          <button className={`tab-btn ${tab === "jobs" ? "active" : ""}`} onClick={() => setTab("jobs")}>
            Jobs
          </button>
          <div className="tabs-spacer" />
          {tab === "models" ? (
            <button className="ghost-btn small" onClick={() => refreshModels()}>
              Refresh
            </button>
          ) : (
            <button className="ghost-btn small" onClick={() => refreshJobs()}>
              Refresh
            </button>
          )}
        </div>

        <div className="shop-body">
          {tab === "models" ? (
            <div className="shop-section">
              {error ? <div className="error">{error}</div> : null}
              {msg ? <div className="panel" style={{ padding: 10 }}>{msg}</div> : null}

              <div className="model-settings-grid">
              <div className="model-settings-label">Online</div>
              <div className="models-col align-left">  
                {loadingModels && models.length === 0 ? (
                  <div>Loading…</div>
                ) : online.length === 0 ? (
                  <div>None</div>
                ) : (
                  <ul className="plain-list">
                    {online.map((m) => (
                      <li key={m.id}>
                        <label className="radio-row">
                          <span className="radio-label" title={m.id}>{m.label}</span>
                          <input
                            type="radio"
                            name="model"
                            value={m.id}
                            checked={selected === m.id}
                            onChange={() => setSelected(m.id)}
                          />
                        </label>
                      </li>
                    ))}
                  </ul>
                )}
              </div>

              <div className="model-settings-label">Offline</div>
              <div className="models-col"> 
                {offline.length === 0 ? (
                  <div>None</div>
                ) : (
                  <ul className="plain-list">
                    {offline.map((m) => (
                      <li key={m.id} style={{ opacity: 0.85 }}>
                        <span className="radio-label" title={m.id}>{m.label}</span>{" "}
                        <span style={{ opacity: 0.7 }}>(offline)</span>
                      </li>
                    ))}
                  </ul>
                )}
              </div>

                <div className="model-settings-label">Strategy</div>
                <div>
                  <select value={strategy} onChange={(e) => setStrategy(e.target.value as any)}>
                    <option value="rag_refresh">RAG Refresh</option>
                    <option value="prompt_update">Prompt Update</option>
                    <option value="lora">LoRA Fine-tune</option>
                  </select>
                </div>

                <div className="model-settings-label">Preset Name</div>
                <div>
                  <input
                    type="text"
                    value={presetName}
                    onChange={(e) => setPresetName(e.target.value)}
                    placeholder="Optional preset label"
                  />
                </div>

                <div className="model-settings-label">Tags Filter</div>
                <div>
                  <input
                    type="text"
                    value={tags}
                    onChange={(e) => setTags(e.target.value)}
                    placeholder="comma,separated,tags"
                  />
                </div>

                <div className="model-settings-label">Limit</div>
                <div>
                  <input
                    type="number"
                    min={1}
                    value={limit}
                    onChange={(e) => setLimit(e.target.value)}
                    placeholder="Optional max examples"
                  />
                </div>
              </div>

              <div className="shop-actions">
                <button className="ghost-btn" onClick={handleTrain} disabled={!selected}>
                  Train
                </button>
              </div>
            </div>
          ) : (
            <div className="shop-section">
              {jobError ? <div className="error">{jobError}</div> : null}
              {loadingJobs && jobs.length === 0 ? (
                <div>Loading…</div>
              ) : jobs.length === 0 ? (
                <div className="panel" style={{ padding: 10 }}>No jobs yet.</div>
              ) : (
                <div className="jobs-list">
                  {jobs.slice().reverse().map((j) => (
                    <div key={j.id} className="job-card">
                      <div className="job-row">
                        <div className="job-title">{j.model_id}</div>
                        <div className={`job-status ${j.status}`}>{j.status}</div>
                      </div>
                      <div className="job-grid">
                        <div className="job-label">Job ID</div>
                        <div className="job-val mono">{j.id}</div>
                        <div className="job-label">Created</div>
                        <div className="job-val">{j.ts}</div>
                        <div className="job-label">Strategy</div>
                        <div className="job-val">{j.strategy}</div>
                        <div className="job-label">Preset</div>
                        <div className="job-val">{j.preset_name || "—"}</div>
                        <div className="job-label">Feedback</div>
                        <div className="job-val">{j.stats?.feedback_count ?? "—"}</div>
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
