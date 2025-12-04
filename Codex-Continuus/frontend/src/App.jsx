import React from "react";
import { useState, useCallback } from "react";

/** Backend endpoint constants */
const API_URL = "http://127.0.0.1:8000/ocr";
const PAGE_SEP = "\n\n--- page break ---\n\n";

export default function App() {
  const [file, setFile] = useState(null);
  const [dragOver, setDragOver] = useState(false);
  const [status, setStatus] = useState("");
  const [result, setResult] = useState(null); 
  const [engine, setEngine] = useState("tesseract");
  const [psm, setPsm] = useState("");                

  // Drag & drop
  const onDrop = useCallback((e) => {
    e.preventDefault();
    setDragOver(false);
    const f = e.dataTransfer?.files?.[0];
    if (f) { setFile(f); setResult(null); setStatus(""); }
  }, []);

  // File chooser
  const onSelect = (e) => {
    const f = e.target.files?.[0];
    if (f) { setFile(f); setResult(null); setStatus(""); }
  };

  async function runOcrPipeline() {
    if (!file) return;
    setStatus("Processing …");
    setResult(null);

    try {
      const name = file.name.toLowerCase();
      const isPDF = name.endsWith(".pdf");
      const psmToUse = psm || (isPDF ? "6" : "7");

      const fd = new FormData();
      fd.append("file", file);
      fd.append("engine", engine);
      fd.append("psm", psmToUse);
      fd.append("lang", "lat");

      const res = await fetch(API_URL, { method: "POST", body: fd });
      if (!res.ok) {
        let detail = "";
        try { detail = (await res.json())?.detail || ""; } catch {}
        throw new Error(detail || `HTTP ${res.status}`);
      }

      const j = await res.json();
      const text = j?.text || "";
      const pages = text.split(PAGE_SEP);
      const meta = j?.meta || {};
      const english = j?.translation || "";

      setResult({
        latin_raw: text,
        english: english,
        pages,
        meta,
      });
      setStatus("Done");
    } catch (err) {
      setStatus(`Error: ${err.message}`);
    }
  }

  const isLoading = status.toLowerCase().startsWith("processing");

  return (
    <div className="container">
      <h1>Latin OCR → Translation (OCR)</h1>

      <div className="main-grid">
        {/* LEFT — Upload + Controls */}
        <div className="upload-panel">
          <div
            className={`dropzone ${dragOver ? "over" : ""}`}
            onDragOver={(e) => { e.preventDefault(); setDragOver(true); }}
            onDragLeave={() => setDragOver(false)}
            onDrop={onDrop}
          >
            <p>Drag & drop an image/PDF here</p>
            <p>or</p>
            <label className="btn">
              Choose file
              <input type="file" accept=".png,.jpg,.jpeg,.pdf" onChange={onSelect} hidden />
            </label>
          </div>

          {file && (
            <div className="filecard">
              <strong>Selected:</strong> {file.name} ({Math.round(file.size / 1024)} KB)
            </div>
          )}

          <div className="controls" style={{ marginTop: 12 }}>
            <label style={{ marginRight: 12 }}>
              Engine:
              <select value={engine} onChange={(e) => setEngine(e.target.value)} style={{ marginLeft: 8 }}>
                <option value="tesseract">tesseract</option>
              </select>
            </label>

            <label>
              PSM:
              <select value={psm} onChange={(e) => setPsm(e.target.value)} style={{ marginLeft: 8 }}>
                <option value="">auto</option>
                <option value="7">7 (single line)</option>
                <option value="6">6 (block/paragraph)</option>
              </select>
            </label>
          </div>

          <div className="actions">
            <button className="primary" disabled={!file || isLoading} onClick={runOcrPipeline}>
              {isLoading ? "Processing…" : "Run"}
            </button>
            <span className="status" style={{ marginLeft: 8 }}>{status}</span>
            {isLoading && (
              <div className="progress" role="status" aria-live="polite" aria-label="Processing">
                <div className="progress-bar" />
              </div>
            )}
          </div>
        </div>

        {/* RIGHT — Output */}
        <div className="output-panel">
          <h2>Results</h2>

          {!result && <p className="placeholder">Results will appear here.</p>}

          {result && (
            <div className="results">
              <p style={{ color: "#555", marginTop: 0 }}>
                Processed in <b>{result.meta?.duration_ms ?? "?"}</b> ms •{" "}
                Pages: <b>{result.meta?.pages ?? (result.pages?.length || 1)}</b>
              </p>

              {result.pages?.map((p, i) => (
                <div key={i} style={{ marginBottom: 16 }}>
                  {result.pages.length > 1 && <h3>Page {i + 1}</h3>}
                  <pre style={{ whiteSpace: "pre-wrap" }}>{p}</pre>
                </div>
              ))}

              <p><b>Latin (raw):</b> {result.latin_raw}</p>
              <p><b>English:</b> {result.english}</p>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
