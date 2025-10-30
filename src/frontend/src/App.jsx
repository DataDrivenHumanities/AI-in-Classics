import { useRef, useState } from "react";
import "./App.css";

const API_BASE = "/api";
const JUPYTERLITE_LAB = "/jlite/lab/index.html"; // if you haven't built Lite yet, use the demo:

export default function App() {
  // main state
  const [model, setModel] = useState("");
  const [text, setText] = useState("");
  const [resp, setResp] = useState(null);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  // tools / modal
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
    const response = await fetch(`${API_BASE}/analyze`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ model, text }),
    });

    if (!response.ok) {
      throw new Error(`Server error: ${response.status}`);
    }

    const data = await response.json();
    setResp(data); // will show in your panels
  } catch (err) {
    setError(err.message || "Something went wrong");
  } finally {
    setLoading(false);
  }
}

  // tool actions
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
    e.target.value = "";
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

  function onKeyDown(e) {
    if (e.key === "Escape") {
      setMenuOpen(false);
      setNotebookOpen(false);
    }
  }


  return (
    <div className="app" onKeyDown={onKeyDown} tabIndex={-1}>
      {/* Header: top-center logo + title */}
      <div className="header">
        <img src="src/assets/uf_logo.png" alt="Trojan Parse Logo" className="logo" />
        <h1 className="title">AI in Classics</h1>
      </div>

      {/* Left-aligned main content */}
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


        <button disabled={loading}>{loading ? "Analyzing..." : "Submit"}</button>

        {/* Inline hamburger + drawer */}
        <div className="bar-tools">
          <button
            className={`hamburger ${menuOpen ? "active" : ""}`}
            onClick={(e) => {
              e.preventDefault();
              setMenuOpen((v) => !v);
            }}
            aria-expanded={menuOpen}
            aria-label="Open tools"
            type="button"
          >
            <span />
            <span />
            <span />
          </button>

          {menuOpen && (
            <div className="tool-drawer inline">
              <div className="tool-carousel" role="list">
                <div className="tool-card" role="listitem">
                  <div className="tool-title">Interactive Notebook</div>
                  <button className="tool-cta" type="button" onClick={openNotebook}>
                    Open
                  </button>
                </div>

                <div className="tool-card" role="listitem">
                  <div className="tool-title">Upload .txt</div>
                  <button className="tool-cta" type="button" onClick={triggerUpload}>
                    Choose
                  </button>
                </div>

                <div className="tool-card" role="listitem">
                  <div className="tool-title">Export JSON</div>
                  <button
                    className="tool-cta"
                    type="button"
                    onClick={exportJSON}
                    disabled={!resp && !text}
                  >
                    Download
                  </button>
                </div>
              </div>
            </div>
          )}
        </div>
      </form>

      {/* hidden file input */}
      <input ref={fileRef} type="file" accept=".txt" onChange={onPickFile} style={{ display: "none" }} />

      {/* Results */}
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

      {/* Modal: JupyterLite Lab (simple, no file list) */}
      {notebookOpen && (
        <div className="modal" onClick={() => setNotebookOpen(false)}>
          <div className="modal-inner" onClick={(e) => e.stopPropagation()}>
            <div className="modal-bar">
              <div className="modal-title">Interactive Notebook</div>
              <div className="modal-actions">
                <a
                  className="modal-link"
                  href={`${JUPYTERLITE_LAB}?reset=1`}
                  target="_blank"
                  rel="noreferrer"
                >
                  Open in new tab ↗
                </a>
                <button className="modal-close" onClick={() => setNotebookOpen(false)} aria-label="Close">
                  ✕
                </button>
              </div>
            </div>
            <iframe
              className="modal-iframe"
              title="JupyterLite"
              src={`${JUPYTERLITE_LAB}?reset=1`}
              referrerPolicy="no-referrer"
            />
          </div>
        </div>
      )}
    </div>
  );
}
