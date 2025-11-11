"use client";

import { useEffect, useMemo, useRef, useState } from "react";
import ModelModal from "@/components/ModelModal";

const API_BASE = process.env.NEXT_PUBLIC_API_BASE || "http://localhost:5050/api";
const JUPYTERLITE_LAB = "/jlite/lab/index.html";

type AnalyzeResponse = unknown;

export default function Analyzer() {
  const [model, setModel] = useState<string>("");
  const [modelsOpen, setModelsOpen] = useState<boolean>(false);
  const [text, setText] = useState<string>("");
  const [resp, setResp] = useState<AnalyzeResponse | null>(null);
  const [error, setError] = useState<string>("");
  const [loading, setLoading] = useState<boolean>(false);

  const [drawerOpen, setDrawerOpen] = useState<boolean>(false);
  const [notebookOpen, setNotebookOpen] = useState<boolean>(false);

  const [progress, setProgress] = useState<number>(0);
  const fileRef = useRef<HTMLInputElement | null>(null);
  const hasResp = !!resp;

  const r: any = resp ?? {};
  const translation = r?.translation ?? r?.data?.translation ?? null;
  const analysis = r?.analysis ?? r?.data?.analysis ?? null;

  useEffect(() => {
    if (!loading) {
      setProgress(0);
      return;
    }
    let p = 10;
    setProgress(p);
    const id = setInterval(() => {
      p = Math.min(p + Math.random() * 10 + 5, 90);
      setProgress(p);
    }, 200);
    return () => clearInterval(id);
  }, [loading]);

  const controllerRef = useRef<AbortController | null>(null);
  

  async function handleSubmit(e: React.FormEvent<HTMLFormElement>) {
    e.preventDefault();
    if (!model || !text.trim()) return;
    controllerRef.current?.abort();
    controllerRef.current = new AbortController();

    setLoading(true);
    setError("");
    setResp(null);

    try {
      const r = await fetch(`${API_BASE}/analyze`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ text, engine: "model", model_id: model }),
        signal: controllerRef.current.signal,
      });
      if (!r.ok) throw new Error(`Request failed: ${r.status}`);
      const data: AnalyzeResponse = await r.json();
      setResp(data);
      setProgress(100);
    } catch (err: any) {
      if (err?.name !== "AbortError") {
        setError(err?.message || "Request failed");
      }
    } finally {
      setLoading(false);
    }
  }

  function triggerUpload() {
    fileRef.current?.click();
  }

  async function onPickFile(e: React.ChangeEvent<HTMLInputElement>) {
    const f = e.target.files?.[0] || null;
    e.target.value = "";
    if (!f) return;
    if (!model) {
      setError("Please select a model before uploading a file.");
      return;
    }
    controllerRef.current?.abort();
    controllerRef.current = new AbortController();

    setLoading(true);
    setError("");
    setResp(null);

    try {
      const form = new FormData();
      form.append("file", f);
      form.append("engine", "model");
      form.append("model_id", model);

      const r = await fetch(`${API_BASE}/analyze/upload`, {
        method: "POST",
        body: form,
        signal: controllerRef.current.signal,
      });
      if (!r.ok) throw new Error(`Upload failed: ${r.status}`);
      const data: any = await r.json();
      if (data?.text) setText(String(data.text));
      setResp(data as AnalyzeResponse);
      setProgress(100);
    } catch (err: any) {
      if (err?.name !== "AbortError") {
        setError(err?.message || "Upload failed");
      }
    } finally {
      setLoading(false);
    }
  }

  function exportJSON() {
    const payload = JSON.stringify(resp ?? { model, text }, null, 2);
    const blob = new Blob([payload], { type: "application/json" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = "trojan-parse-result.json";
    a.click();
    URL.revokeObjectURL(url);
  }

  return (
    <div className="app">
      <header className="header">
        <img className="logo" src="/uf_logo.png" alt="Trojan Parse" />
        <h1 className="title">AI in Classics</h1>
        <div className="subtitle">Latin &amp; Greek Analysis</div>
      </header>

      <div className="bar-row">
        <form className="bar" onSubmit={handleSubmit}>
          <select
            value={model}
            onChange={(e) => {
              setModel(e.target.value);
              if (resp || error) {
                setResp(null);
                setError("");
              }
            }}
          >
            <option value="">Select a model…</option>
            <option value="latin_model:1.0.0">latin_model:1.0.0</option>
            <option value="greek_model:1.0.0">greek_model:1.0.0</option>
            <option value="auto">auto</option>
          </select>

          <div style={{ flex: 1, display: "flex", flexDirection: "column", gap: 6 }}>
            <input
              type="text"
              placeholder="Paste or type text to analyze…"
              value={text}
              onChange={(e) => {
                setText(e.target.value);
                if (resp || error) {
                  setResp(null);
                  setError("");
                }
              }}
            />
          </div>

          <button type="submit" disabled={loading}>
            {loading ? "Analyzing…" : "Submit"}
          </button>

          <button type="button" onClick={triggerUpload} disabled={loading}>
            Upload
          </button>

          <input
            ref={fileRef}
            type="file"
            accept=".txt,.md,.rtf,.html,.pdf,.doc,.docx"
            onChange={onPickFile}
            style={{ display: "none" }}
          />
        </form>

        <div className="bar-tools">
          <button
            type="button"
            className={`hamburger ${drawerOpen ? "active" : ""}`}
            onClick={() => setDrawerOpen((v) => !v)}
            aria-label="Toggle menu"
          >
            <span />
            <span />
            <span />
          </button>

          {drawerOpen && (
            <div className="tool-drawer inline" role="menu">
              <div className="tool-carousel">
                <div className="tool-card">
                  <div className="tool-title">Open Notebook</div>
                  <button className="tool-cta" onClick={() => setNotebookOpen(true)}>
                    Open
                  </button>
                </div>
                <div className="tool-card">
                  <div className="tool-title">Export JSON</div>
                  <button className="tool-cta" onClick={exportJSON} disabled={!resp}>
                    Export
                  </button>
                </div>
                <div className="tool-card">
                  <div className="tool-title">LLM Status</div>
                  <button className="tool-cta" onClick={() => setModelsOpen(true)}>
                    View
                  </button>
                </div>
                <div className="tool-card">
                  <div className="tool-title">Reset</div>
                  <button
                    className="tool-cta"
                    onClick={() => {
                      controllerRef.current?.abort();
                      setText("");
                      setResp(null);
                      setError("");
                      setLoading(false);
                      setProgress(0);
                    }}
                  >
                    Clear
                  </button>
                </div>
              </div>
            </div>
          )}
        </div>
      </div>
      {loading && (
        <div className="progress progress-mid">
          <div className="progress-bar" style={{ width: `${progress}%` }} />
        </div>
      )}
      {!!error && <div className="error">{error}</div>}

      {hasResp ? (
        <div className="panels">
          <div className="panel">
            <h3>Results</h3>
            <pre>{JSON.stringify(resp, null, 2)}</pre>
          </div>
          <div className="panel">
            <h3>Translation</h3>
            <pre>{translation ? String(translation) : "—"}</pre>
          </div>
          <div className="panel">
            <h3>Analysis</h3>
            <pre>{analysis ? JSON.stringify(analysis, null, 2) : "—"}</pre>
          </div>
        </div>
      ) : (
        <div className="panels">
          <div className="panel">
            <h3>Debug</h3>
            <pre>{JSON.stringify({ model, textLen: text.length, loading }, null, 2)}</pre>
          </div>
        </div>
      )}
<ModelModal open={modelsOpen} onClose={() => setModelsOpen(false)} />

  
      {notebookOpen && (
        <div className="modal" onClick={() => setNotebookOpen(false)}>
          <div className="modal-inner" onClick={(e) => e.stopPropagation()}>
            <div className="modal-bar">
              <div className="modal-title">JupyterLite</div>
              <div className="modal-actions">
                <a className="modal-link" href={JUPYTERLITE_LAB} target="_blank" rel="noreferrer">
                  Open in new tab
                </a>
                <button className="modal-close" onClick={() => setNotebookOpen(false)}>
                  Close
                </button>
              </div>
            </div>
            <iframe className="modal-iframe" title="JupyterLite" src={`${JUPYTERLITE_LAB}?reset=1`} />
          </div>
        </div>
      )}
    </div>
  );
}
