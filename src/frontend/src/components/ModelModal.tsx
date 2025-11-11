"use client";

import { useEffect, useMemo, useRef, useState } from "react";

const API_BASE = process.env.NEXT_PUBLIC_API_BASE || "http://localhost:5050/api";

type StatusItem = {
  id?: string;
  name?: string;
  provider?: string;
  available?: boolean;
  latency_ms?: number | null;
  host?: string | null;
  meta?: Record<string, unknown>;
};

type StatusPayload =
  | { models: StatusItem[] }
  | StatusItem[]
  | Record<string, any>;

function normalize(payload: StatusPayload): StatusItem[] {
  if (Array.isArray(payload)) return payload;
  if ("models" in payload && Array.isArray(payload.models)) return payload.models;
  const arr: StatusItem[] = [];
  Object.entries(payload).forEach(([k, v]) => {
    if (v && typeof v === "object") {
      const o = v as any;
      arr.push({
        id: o.id ?? k,
        name: o.name ?? k,
        provider: o.provider ?? o.type ?? "ollama",
        available: Boolean(o.available ?? o.up ?? o.ok ?? false),
        latency_ms: typeof o.latency_ms === "number" ? o.latency_ms : null,
        host: o.host ?? null,
        meta: o,
      });
    }
  });
  return arr;
}

export default function ModelModal({
  open,
  onClose,
  pollMs = 10000,
}: {
  open: boolean;
  onClose: () => void;
  pollMs?: number;
}) {
  const [items, setItems] = useState<StatusItem[]>([]);
  const [loading, setLoading] = useState(false);
  const [err, setErr] = useState<string>("");

  const load = async () => {
    setLoading(true);
    setErr("");
    try {
      const r1 = await fetch(`${API_BASE}/models/status`, { cache: "no-store" });
      if (r1.ok) {
        const j = await r1.json();
        setItems(normalize(j));
      } else {
        const r2 = await fetch(`${API_BASE}/models/registry`, { cache: "no-store" });
        if (r2.ok) {
          const j2 = await r2.json();
          setItems(normalize(j2));
        } else {
          setErr(`Status endpoint error ${r1.status} and registry ${r2.status}`);
        }
      }
    } catch (e: any) {
      setErr(e?.message || "Failed to load model status");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    if (!open) return;
    load();
    const id = setInterval(load, pollMs);
    return () => clearInterval(id);
  }, [open, pollMs]);

  const anyUp = useMemo(() => items.some(i => i.available), [items]);

  if (!open) return null;

  return (
    <div className="float-root">
      <div className="float-card">
        <div className="float-head">
          <div className="float-title">Model Status</div>
          <div className="float-actions">
            <span className={`dot ${anyUp ? "ok" : "down"}`} />
            <button className="tool-cta" onClick={load} disabled={loading}>
              {loading ? "Refreshing…" : "Refresh"}
            </button>
            <button className="modal-close" onClick={onClose}>Close</button>
          </div>
        </div>

        {err && <div className="error" style={{ margin: "10px" }}>{err}</div>}

        <div className="status-list">
          {items.length === 0 && !err && (
            <div className="status-empty">No models found.</div>
          )}
          {items.map((m, idx) => {
            const up = !!m.available;
            const latency =
              typeof m.latency_ms === "number" && m.latency_ms >= 0
                ? `${Math.round(m.latency_ms)} ms`
                : "—";
            return (
              <div className="status-row" key={(m.id ?? m.name ?? "m") + idx}>
                <div className="status-main">
                  <span className={`dot ${up ? "ok" : "down"}`} />
                  <div className="status-texts">
                    <div className="status-name">
                      {m.name || m.id || "model"}
                    </div>
                    <div className="status-sub">
                      {(m.provider || "provider")} · {(m.host || "local")}
                    </div>
                  </div>
                </div>
                <div className="status-meta">
                  <div className={`badge ${up ? "up" : "down"}`}>
                    {up ? "Connected" : "Offline"}
                  </div>
                  <div className="latency">{latency}</div>
                </div>
              </div>
            );
          })}
        </div>
      </div>
    </div>
  );
}
