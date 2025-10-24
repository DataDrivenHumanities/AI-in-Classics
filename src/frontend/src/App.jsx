import { useRef, useState } from "react";
import "./App.css";

const API_BASE = "/api";
const NOTEBOOK_URL = "https://jupyterlite.github.io/demo/lab/index.html"; 
// ↑ Change to your own Jupyter/JupyterLite/Binder URL when ready

export default function App() {
  const [model, setModel] = useState("");
  const [text, setText] = useState("");
  const [resp, setResp] = useState(null);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  // Tool drawer + notebook modal
  const [menuOpen, setMenuOpen] = useState(false);
  const [notebookOpen, setNotebookOpen] = useState(false);

  const fileRef = useRef(null);

  async function handleSubmit(e) {
    e.preventDefault();
    if (!model || !text.trim()) return;
    setLoading(true);
    setError("");
    setResp(null);

    try {
      const r = await fetch(`${API_BASE}/analyze`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ model, text }),
      });
      if (!r.ok) throw new Error(`Server responded ${r.status}`);
      const data = await r.json();
      setResp(data);
    } catch (err) {
      setError(err.message || "Something went wrong");
    } finally {
      setLoading(false);
    }
  }

  // ===== Tool actions =====
  function openNotebook() {
    setNotebookOpen(true);
  }

  function triggerUpload() {
    fileRef.current?.click();
  }

  function onPickFile(e) {
    const f = e.target.files?.[0];
    if (!f) return;
    const reader = new FileReader();
    reader.onload = () => setText(String(reader.result || ""));
    reader.readAsText(f);
    e.target.value = ""; // reset for next pick
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

  // Close drawers on ESC
  function onKeyDown(e) {
    if (e.key === "Escape") {
      setMenuOpen(false);
      setNotebookOpen(false);
    }
  }

  return (
    <div className="app" onKeyDown={onKeyDown} tabIndex={-1}>
      <div className="header">
      <img src="public/uf_logo.png" alt="Trojan Parse Logo" className="logo" />
      </div>
      <h1>AI in Classics</h1>
      <p className="subtitle">
        Paste or upload text, choose a model, and get instant analysis.
      </p>

      <form className="bar" onSubmit={handleSubmit}>
        <select value={model} onChange={(e) => setModel(e.target.value)}>
          <option value="">Select a Model</option>
          <option value="greek-ollama">Greek Ollama</option>
          <option value="greek-vator">Greek Vator</option>
          <option value="latin-ollama">Latin Ollama</option>
          <option value="latin-vator">Latin Vator</option>
        </select>

        <input
          type="text"
          placeholder="Enter Greek or Latin text..."
          value={text}
          onChange={(e) => setText(e.target.value)}
        />

        <button disabled={loading}>
          {loading ? "Analyzing..." : "Submit"}
        </button>
      </form>

      {error && <p className="error">{error}</p>}

      {resp && (
        <div className="panels">
          <div className="panel">
            <h3>Result</h3>
            <pre>{JSON.stringify(resp.result || resp, null, 2)}</pre>
          </div>
          <div className="panel">
            <h3>Translation</h3>
            <p>{resp.translation || "(none)"}</p>
          </div>
          <div className="panel">
            <h3>Analysis</h3>
            <pre>{JSON.stringify(resp.analysis || {}, null, 2)}</pre>
          </div>
        </div>
      )}

      {/* Hidden file input for the Upload tool */}
      <input ref={fileRef} type="file" accept=".txt" onChange={onPickFile} style={{ display: "none" }} />


      <button
        className={`hamburger ${menuOpen ? "active" : ""}`}
        onClick={() => setMenuOpen((v) => !v)}
        aria-expanded={menuOpen}
        aria-label="Open tools"
      >
        <span />
        <span />
        <span />
      </button>

      <div className={`tool-drawer ${menuOpen ? "open" : ""}`}>
        <div className="tool-carousel" role="list">

          <div className="tool-card" role="listitem">
            <div className="tool-icon">
              {/* laptop/code icon */}
              <svg viewBox="0 0 24 24" width="22" height="22" fill="none">
                <path d="M4 6h16v9H4z" stroke="currentColor" strokeWidth="1.5" />
                <path d="M2 17h20" stroke="currentColor" strokeWidth="1.5" />
                <path d="M9 9l-2 2 2 2M15 9l2 2-2 2" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round"/>
              </svg>
            </div>
            <div className="tool-title">Interactive Notebook</div>
            <div className="tool-desc">Open a Python notebook session.</div>
            <button className="tool-cta" onClick={openNotebook}>Open</button>
          </div>

          {/* Tool Card 2: Upload .txt */}
          <div className="tool-card" role="listitem">
            <div className="tool-icon">
              {/* upload icon */}
              <svg viewBox="0 0 24 24" width="22" height="22" fill="none">
                <path d="M12 16V6" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round"/>
                <path d="M8 9l4-4 4 4" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round"/>
                <path d="M4 18h16" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round"/>
              </svg>
            </div>
            <div className="tool-title">Upload .txt</div>
            <div className="tool-desc">Load a local text file into the input.</div>
            <button className="tool-cta" onClick={triggerUpload}>Choose File</button>
          </div>

          {/* Tool Card 3: Export JSON */}
          <div className="tool-card" role="listitem">
            <div className="tool-icon">
              {/* download icon */}
              <svg viewBox="0 0 24 24" width="22" height="22" fill="none">
                <path d="M12 8v10" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round"/>
                <path d="M8 15l4 4 4-4" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round"/>
                <path d="M4 6h16" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round"/>
              </svg>
            </div>
            <div className="tool-title">Export JSON</div>
            <div className="tool-desc">Download the current result or input.</div>
            <button className="tool-cta" onClick={exportJSON} disabled={!resp && !text}>Download</button>
          </div>
        </div>
      </div>



      {/* ===== Notebook Modal ===== */}
      {notebookOpen && (
        <div className="modal" onClick={() => setNotebookOpen(false)}>
          <div className="modal-inner" onClick={(e) => e.stopPropagation()}>
            <div className="modal-bar">
              <div className="modal-title">Interactive Notebook</div>
              <button className="modal-close" onClick={() => setNotebookOpen(false)} aria-label="Close">✕</button>
            </div>
            <iframe
              className="modal-iframe"
              title="Notebook"
              src={NOTEBOOK_URL}
              referrerPolicy="no-referrer"
            />
          </div>
        </div>
      )}
    </div>
  );
}
