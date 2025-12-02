"use client";

import React, {Fragment, useEffect, useRef, useState} from "react";
import ModelModal from "@/components/ModelModal";
import ModelSettingsModal, {ModelOptions} from "@/components/ModelSettingsModal";
import FeedbackModal from "@/components/FeedbackModal";
import ModelShopModal from "@/components/ModelShopModal";


const API_BASE = process.env.NEXT_PUBLIC_API_BASE || "http://localhost:5050/api";
const JUPYTERLITE_LAB = "/jlite/lab/index.html";

type AnalyzeResponse = any;

type ModelEntry = {
    id: string;
    label?: string;
};

export default function Analyzer() {
    const [model, setModel] = useState<string>("");
    const [modelsOpen, setModelsOpen] = useState<boolean>(false);
    const [settingsOpen, setSettingsOpen] = useState<boolean>(false);
    const [notebookOpen, setNotebookOpen] = useState<boolean>(false);
    const [drawerOpen, setDrawerOpen] = useState<boolean>(false);
    const [feedbackOpen, setFeedbackOpen] = useState<boolean>(false);
    const [shopOpen, setShopOpen] = useState(false);
    const [isHuggingFaceModel, setIsHuggingFaceModel] = useState(false)

    const [text, setText] = useState<string>("");
    const [resp, setResp] = useState<AnalyzeResponse | null>(null);
    const [error, setError] = useState<string>("");
    const [loading, setLoading] = useState<boolean>(false);
    const [progress, setProgress] = useState<number>(0);
    const [presetName, setPresetName] = useState<string>("Default");

    const fileRef = useRef<HTMLInputElement | null>(null);
    const controllerRef = useRef<AbortController | null>(null);

    const [modelOpts, setModelOpts] = useState<ModelOptions>({
        temperature: 0.0,
        top_p: 0.9,
        repeat_penalty: 1.0,
        num_predict: 1024,
        stop: [],
        raw: true,
        format: "json",
    });

    const [availableModels, setAvailableModels] = useState<ModelEntry[]>([
        {id: "latin_ollama_model:1.0.0"},
        {id: "greek_ollama_model:1.0.0"},
        {id: "greek_hf_model:1.0.0"},
    ]);

    useEffect(() => {
        let mounted = true;
        (async () => {
            try {
                const rr = await fetch(`${API_BASE}/model_registry`);
                if (!mounted) return;
                if (!rr.ok) throw new Error(`Failed to load model registry: ${rr.status}`);
                const data: any = await rr.json();
                let models: ModelEntry[] = [];
                console.log(data)
                if (Array.isArray(data)) {
                    models = data.map((m: any) =>
                        typeof m === "string" ? {id: m} : {
                            id: String(m.id ?? m.model_id ?? ""),
                            label: m.label ?? m.name
                        }
                    );
                } else if (Array.isArray(data?.models)) {
                    models = data.models.map((m: any) =>
                        typeof m === "string" ? {id: m} : {
                            id: String(m.id ?? m.model_id ?? ""),
                            label: m.label ?? m.name
                        }
                    );
                } else if (data && typeof data === "object") {
                    // If models is an object map (like src/app/model_registry.json), use its values
                    if (data.models && typeof data.models === "object" && !Array.isArray(data.models)) {
                        models = Object.values(data.models).map((m: any) =>
                            typeof m === "string" ? {id: String(m)} : {
                                id: String(m.id ?? m.model_id ?? m?.id ?? ""),
                                label: (m as any)?.name ?? (m as any)?.label
                            }
                        );
                    } else {
                        // fallback: convert object entries -> values that look like model entries
                        models = Object.entries(data)
                            .map(([k, v]) =>
                                typeof v === "object" && v !== null
                                    ? {id: String((v as any).id ?? k), label: (v as any).name ?? (v as any).label}
                                    : {id: String(v)}
                            );
                    }
                }

                models = models.filter((m) => m.id);
                if (models.length > 0) setAvailableModels(models);
                console.log(models)
            } catch (e) {
                // keep fallback list on error
            }
        })();
        return () => {
            mounted = false;
        };
    }, []);


    const hasResp = !!resp;
    const r: any = resp ?? {};
    const engine = r?.engine ?? r?.data?.engine ?? null;
    const label = r?.label ?? r?.data?.label ?? null;
    const confidence = r?.confidence ?? r?.data?.confidence ?? null;
    const scores = r?.scores ?? r?.data?.scores ?? null;
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

    useEffect(() => {
        setIsHuggingFaceModel(engine === "hugging face")
    }, [engine])

    async function handleSubmit(e: React.FormEvent<HTMLFormElement>) {
        e.preventDefault();
        if (!model || !text.trim()) return;

        controllerRef.current?.abort();
        controllerRef.current = new AbortController();

        setLoading(true);
        setError("");
        setResp(null);

        try {
            const payload = {
                text,
                model_id: model,
                options: {
                    temperature: modelOpts.temperature,
                    top_p: modelOpts.top_p,
                    repeat_penalty: modelOpts.repeat_penalty,
                    num_predict: modelOpts.num_predict,
                    stop: modelOpts.stop,
                },
                raw: modelOpts.raw,
                format: modelOpts.format,
            };
            const rr = await fetch(`${API_BASE}/analyze`, {
                method: "POST",
                headers: {"Content-Type": "application/json"},
                body: JSON.stringify(payload),
                signal: controllerRef.current.signal,
            });
            if (!rr.ok) throw new Error(`Request failed: ${rr.status}`);
            const data: AnalyzeResponse = await rr.json();
            console.log(data)
            setResp(data);
            setProgress(100);
        } catch (err: any) {
            if (err?.name !== "AbortError") setError(err?.message || "Request failed");
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
            form.append("raw", String(modelOpts.raw));
            form.append("format", modelOpts.format);
            form.append(
                "options",
                JSON.stringify({
                    temperature: modelOpts.temperature,
                    top_p: modelOpts.top_p,
                    repeat_penalty: modelOpts.repeat_penalty,
                    num_predict: modelOpts.num_predict,
                    stop: modelOpts.stop,
                })
            );

            const rr = await fetch(`${API_BASE}/analyze/upload`, {
                method: "POST",
                body: form,
                signal: controllerRef.current.signal,
            });
            if (!rr.ok) throw new Error(`Upload failed: ${rr.status}`);
            const data: any = await rr.json();
            if (data?.text) setText(String(data.text));
            setResp(data as AnalyzeResponse);
            setProgress(100);
        } catch (err: any) {
            if (err?.name !== "AbortError") setError(err?.message || "Upload failed");
        } finally {
            setLoading(false);
        }
    }

    function exportJSON() {
        const payload = JSON.stringify(resp ?? {model, text}, null, 2);
        const blob = new Blob([payload], {type: "application/json"});
        const url = URL.createObjectURL(blob);
        const a = document.createElement("a");
        a.href = url;
        a.download = "trojan-parse-result.json";
        a.click();
        URL.revokeObjectURL(url);
    }

    const miniDebug = {
        model: model || null,
        textLen: text.length,
        loading,
    };

    function isPlainObject(v: any) {
        return v && typeof v === "object" && !Array.isArray(v);
    }

    function toPercent(n: any) {
        const x = Number(n);
        if (Number.isFinite(x)) return `${(x * 100).toFixed(1)}%`;
        return String(n);
    }

    function renderValue(val: any) {
        if (Array.isArray(val)) {
            const allPrimitive = val.every((x) => typeof x !== "object" || x === null);
            if (allPrimitive) {
                return (
                    <ul style={{margin: 0, paddingLeft: 16}}>
                        {val.map((item, i) => (
                            <li key={i}>{String(item)}</li>
                        ))}
                    </ul>
                );
            }
            return (
                <ul style={{margin: 0, paddingLeft: 16}}>
                    {val.map((obj, i) => (
                        <li key={i}>
                            {isPlainObject(obj)
                                ? Object.entries(obj)
                                    .map(([k, v]) => `${k}: ${String(v)}`)
                                    .join(" · ")
                                : String(obj)}
                        </li>
                    ))}
                </ul>
            );
        }
        if (isPlainObject(val)) {
            const looksLikeScores =
                Object.values(val).length > 0 &&
                Object.values(val).every((v) => typeof v === "number" && v >= 0 && v <= 1);
            if (looksLikeScores) {
                return (
                    <div className="model-settings-grid">
                        {Object.entries(val).map(([k, v]) => (
                            <Fragment key={k}>
                                <div className="model-settings-label">{k}</div>
                                <div>{toPercent(v)}</div>
                            </Fragment>
                        ))}
                    </div>
                );
            }
            return (
                <div className="model-settings-grid">
                    {Object.entries(val).map(([k, v]) => (
                        <Fragment key={k}>
                            <div className="model-settings-label">{k}</div>
                            <div>{typeof v === "object" ? JSON.stringify(v) : String(v)}</div>
                        </Fragment>
                    ))}
                </div>
            );
        }
        return <span>{String(val)}</span>;
    }

    return (
        <div className="app">
            <header className="header">
                <img className="logo" src="/uf_logo.png" alt="Trojan Parse"/>
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
                        {availableModels.map((m) => (
                            <option key={m.id} value={m.id}>
                                {m.label ?? m.id}
                            </option>
                        ))}
                    </select>

                    <div style={{flex: 1, display: "flex", flexDirection: "column", gap: 6}}>
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
                        style={{display: "none"}}
                    />
                </form>

                <div className="bar-tools">
                    <button
                        type="button"
                        className={`hamburger ${drawerOpen ? "active" : ""}`}
                        onClick={() => setDrawerOpen((v) => !v)}
                        aria-label="Toggle menu"
                    >
                        <span/>
                        <span/>
                        <span/>
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
                                    <button
                                        className="tool-cta"
                                        onClick={() => {
                                            setModelsOpen(true);
                                            setDrawerOpen(false);
                                        }}
                                    >
                                        View
                                    </button>
                                </div>
                                <div className="tool-card">
                                    <div className="tool-title">Model Settings</div>
                                    <button
                                        className="tool-cta"
                                        onClick={() => {
                                            setSettingsOpen(true);
                                            setDrawerOpen(false);
                                        }}
                                    >
                                        Edit
                                    </button>
                                </div>
                                <div className="tool-card">
                                    <div className="tool-title">Model Shop</div>
                                    <button
                                        className="tool-cta"
                                        onClick={() => {
                                            setShopOpen(true);
                                            setDrawerOpen(false);
                                        }}
                                    >
                                        Open
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
                    <div className="progress-bar" style={{width: `${progress}%`}}/>
                </div>
            )}

            {!!error && <div className="error">{error}</div>}

            {hasResp && (
                <div className="floating-actions">
                    <button
                        className="ghost-btn"
                        onClick={() => setFeedbackOpen(true)}
                        disabled={!resp || !model || !text}
                    >
                        Send Feedback
                    </button>
                    <button
                        className="ghost-btn"
                        onClick={exportJSON}
                        disabled={!resp}
                    >
                        Export JSON
                    </button>
                </div>
            )}

            {hasResp ? (
                <div className="panels">
                    <div className="panel">
                        <div style={{display: "flex", justifyContent: "space-between", alignItems: "center"}}>
                            <h3 style={{margin: 0}}>Results</h3>
                            <div style={{display: "flex", gap: 8}}>
                            </div>
                        </div>

                        <div className="model-settings-grid" style={{marginTop: 10}}>
                            <div className="model-settings-label">Engine</div>
                            <div>{engine || "—"}</div>

                            <div className="model-settings-label">Label</div>
                            <div>{label ? String(label).toUpperCase() : "—"}</div>

                            <div className="model-settings-label">Confidence</div>
                            <div>{typeof confidence === "number" ? `${(confidence * 100).toFixed(1)}%` : "—"}</div>

                            {!isHuggingFaceModel && scores && typeof scores === "object" ? (
                                <>
                                    <div className="model-settings-label">Positive</div>
                                    <div>{(Number(scores.positive) * 100).toFixed(1)}%</div>

                                    <div className="model-settings-label">Neutral</div>
                                    <div>{(Number(scores.neutral) * 100).toFixed(1)}%</div>

                                    <div className="model-settings-label">Negative</div>
                                    <div>{(Number(scores.negative) * 100).toFixed(1)}%</div>
                                </>
                            ) : null}
                        </div>
                    </div>

                    {!isHuggingFaceModel && (<div className="panel">
                        <h3>Translation</h3>
                        <pre>{translation ? String(translation) : "—"}</pre>
                    </div>)}

                    {!isHuggingFaceModel && (<div className="panel">
                        <h3>Analysis</h3>
                        {analysis && typeof analysis === "object" && Object.keys(analysis).length > 0 ? (
                            <div className="analysis-grid">
                                {Object.entries(analysis).map(([key, val]) => (
                                    <Fragment key={key}>
                                        <div className="analysis-label">{key}</div>
                                        <div className="analysis-value">{renderValue(val)}</div>
                                    </Fragment>
                                ))}
                            </div>
                        ) : (
                            <div>—</div>
                        )}
                    </div>)}
                </div>
            ) : (
                <div className="panels debug-grid">
                    <div className="panel debug-snippet">
                        <h3>Debug</h3>
                        <pre>{JSON.stringify(miniDebug, null, 2)}</pre>
                    </div>

                    <div className="panel model-settings">
                        <div className="model-settings-header">
                            <h3>Model Settings</h3>
                            <div className="model-preset-badge">Preset: {presetName}</div>
                        </div>

                        <div className="model-settings-grid">
                            <div className="model-settings-label">Format</div>
                            <div>{modelOpts.format.toUpperCase()}</div>

                            <div className="model-settings-label">Bypass Modelfile (raw)</div>
                            <div>{modelOpts.raw ? "Enabled" : "Disabled"}</div>

                            <div className="model-settings-label">Temperature</div>
                            <div>{modelOpts.temperature}</div>

                            <div className="model-settings-label">Top-p</div>
                            <div>{modelOpts.top_p}</div>

                            <div className="model-settings-label">Repeat Penalty</div>
                            <div>{modelOpts.repeat_penalty}</div>

                            <div className="model-settings-label">Max Tokens</div>
                            <div>{modelOpts.num_predict}</div>

                            <div className="model-settings-label" style={{alignSelf: "start"}}>
                                Stop Tokens
                            </div>
                            <div>
                                {modelOpts.stop.length === 0 ? (
                                    <span className="model-stop-chip none">None</span>
                                ) : (
                                    modelOpts.stop.map((s) => (
                                        <span key={s} className="model-stop-chip">
                      {s}
                    </span>
                                    ))
                                )}
                            </div>
                        </div>
                    </div>
                </div>
            )}

            <ModelModal open={modelsOpen} onClose={() => setModelsOpen(false)}/>

            <ModelSettingsModal
                open={settingsOpen}
                onClose={() => setSettingsOpen(false)}
                initial={{...modelOpts, name: presetName} as ModelOptions & { name?: string }}
                onSave={(opts: ModelOptions & { name?: string }) => {
                    setModelOpts({
                        temperature: opts.temperature,
                        top_p: opts.top_p,
                        repeat_penalty: opts.repeat_penalty,
                        num_predict: opts.num_predict,
                        stop: opts.stop,
                        raw: opts.raw,
                        format: opts.format,
                    });
                    setPresetName(opts.name || "Custom");
                    setSettingsOpen(false);
                }}
                onApplyPreset={(name: string, opts: ModelOptions) => {
                    setModelOpts(opts);
                    setPresetName(name || "Custom");
                }}
            />

            <FeedbackModal
                open={feedbackOpen}
                onClose={() => setFeedbackOpen(false)}
                apiBase={API_BASE}
                modelId={model}
                text={text}
                got={resp}
            />

            <ModelShopModal open={shopOpen} onClose={() => setShopOpen(false)} apiBase={API_BASE}/>


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
                        <iframe className="modal-iframe" title="JupyterLite" src={`${JUPYTERLITE_LAB}?reset=1`}/>
                    </div>
                </div>
            )}
        </div>
    );
}
