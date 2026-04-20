"use client";

import React, {Fragment, useEffect, useRef, useState} from "react";
import ModelModal from "@/components/ModelModal";
import ModelSettingsModal, {ModelOptions} from "@/components/ModelSettingsModal";
import FeedbackModal from "@/components/FeedbackModal";
import ModelShopModal from "@/components/ModelShopModal";
import LatinLexiconOverlay from "@/components/LatinLexiconOverlay";
import MarkdownBlock from "@/components/MarkdownBlock";


const API_BASE = process.env.NEXT_PUBLIC_API_BASE || "http://localhost:5050/api";
const JUPYTERLITE_LAB = "/jlite/lab/index.html";

type AnalyzeResponse = any;

type ModelEntry = {
    id: string;
    label?: string;
    provider?: string;
};

export default function Analyzer() {
    const [language, setLanguage] = useState<"latin" | "greek">("latin");
    const [model, setModel] = useState<string>("");
    const [modelsOpen, setModelsOpen] = useState<boolean>(false);
    const [settingsOpen, setSettingsOpen] = useState<boolean>(false);
    const [notebookOpen, setNotebookOpen] = useState<boolean>(false);
    const [drawerOpen, setDrawerOpen] = useState<boolean>(false);
    const [feedbackOpen, setFeedbackOpen] = useState<boolean>(false);
    const [shopOpen, setShopOpen] = useState(false);
    const [isHuggingFaceModel, setIsHuggingFaceModel] = useState(false);

    const [providerMode, setProviderMode] = useState<"registry" | "openrouter">(
        "registry"
    );
    const [openrouterKey, setOpenrouterKey] = useState<string>("");
    const [openrouterModel, setOpenrouterModel] = useState<string>("");
    const [rememberOpenrouterKey, setRememberOpenrouterKey] = useState<boolean>(false);

    const [activeText, setActiveText] = useState<string>("");
    const [pasteDraft, setPasteDraft] = useState<string>("");
    const [workspaceTab, setWorkspaceTab] = useState<
        "paste" | "upload" | "sample"
    >("paste");
    const [editMode, setEditMode] = useState<boolean>(true);
    const [textView, setTextView] = useState<"plain" | "lexicon">("plain");
    const [extractWarnings, setExtractWarnings] = useState<string[]>([]);

    const [samples, setSamples] = useState<
        Array<{id: string; name: string; bytes: number}>
    >([]);
    const [samplesLoaded, setSamplesLoaded] = useState<boolean>(false);
    const [pickedSampleId, setPickedSampleId] = useState<string>("");
    const [resp, setResp] = useState<AnalyzeResponse | null>(null);
    const [error, setError] = useState<string>("");
    const [loading, setLoading] = useState<boolean>(false);
    const [progress, setProgress] = useState<number>(0);
    const [presetName, setPresetName] = useState<string>("Default");

    const fileRef = useRef<HTMLInputElement | null>(null);
    const controllerRef = useRef<AbortController | null>(null);
    const lexControllerRef = useRef<AbortController | null>(null);
    const outputRef = useRef<HTMLDivElement | null>(null);

    const [lexLoading, setLexLoading] = useState(false);
    const [lexError, setLexError] = useState<string>("");
    const [lexAuto, setLexAuto] = useState<boolean>(true);
    const [lexRes, setLexRes] = useState<any | null>(null);

    const [analyzeIncludePriors, setAnalyzeIncludePriors] = useState<boolean>(true);

    const [chatMessages, setChatMessages] = useState<Array<{role: "user" | "assistant"; content: string}>>([]);
    const [chatDraft, setChatDraft] = useState<string>("");
    const [chatLoading, setChatLoading] = useState<boolean>(false);
    const [chatError, setChatError] = useState<string>("");
    const [chatPeriod, setChatPeriod] = useState<string>("");
    const [chatGenre, setChatGenre] = useState<string>("");
    const [chatIncludePriors, setChatIncludePriors] = useState<boolean>(true);
    const [chatPriorsWarning, setChatPriorsWarning] = useState<string>("");
    const [outputTab, setOutputTab] = useState<"sentiment" | "llm" | "chat">(
        "sentiment"
    );

    const [llmMode, setLlmMode] = useState<number>(6);
    const [llmPeriod, setLlmPeriod] = useState<string>("");
    const [llmGenre, setLlmGenre] = useState<string>("");
    const [llmOutputLength, setLlmOutputLength] = useState<"short" | "medium" | "long">("medium");
    const [llmIncludePriors, setLlmIncludePriors] = useState<boolean>(true);
    const [llmContent, setLlmContent] = useState<string>("");
    const [llmLoading, setLlmLoading] = useState<boolean>(false);
    const [llmError, setLlmError] = useState<string>("");

    function focusOutput(tab?: "sentiment" | "llm" | "chat") {
        if (tab) setOutputTab(tab);
        try {
            window.setTimeout(() => {
                outputRef.current?.scrollIntoView({behavior: "smooth", block: "start"});
            }, 50);
        } catch {
            // ignore
        }
    }

    const [modelOpts, setModelOpts] = useState<ModelOptions>({
        temperature: 0.0,
        top_p: 0.9,
        repeat_penalty: 1.0,
        num_predict: 1024,
        stop: [],
        raw: false,
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
                if (Array.isArray(data)) {
                    models = data.map((m: any) =>
                        typeof m === "string" ? {id: m} : {
                            id: String(m.id ?? m.model_id ?? ""),
                            label: m.label ?? m.name ?? m.display_label,
                            provider: m.provider ?? m.engine
                        }
                    );
                } else if (Array.isArray(data?.models)) {
                    models = data.models.map((m: any) =>
                        typeof m === "string" ? {id: m} : {
                            id: String(m.id ?? m.model_id ?? ""),
                            label: m.label ?? m.name ?? m.display_label,
                            provider: m.provider ?? m.engine
                        }
                    );
                } else if (data && typeof data === "object") {
                    // If models is an object map (like src/app/model_registry.json), use its values
                    if (data.models && typeof data.models === "object" && !Array.isArray(data.models)) {
                        models = Object.values(data.models).map((m: any) =>
                            typeof m === "string" ? {id: String(m)} : {
                                id: String(m.id ?? m.model_id ?? m?.id ?? ""),
                                label: (m as any)?.name ?? (m as any)?.label ?? (m as any)?.display_label,
                                provider: (m as any)?.provider ?? (m as any)?.engine
                            }
                        );
                    } else {
                        // fallback: convert object entries -> values that look like model entries
                        models = Object.entries(data)
                            .map(([k, v]) =>
                                typeof v === "object" && v !== null
                                    ? {id: String((v as any).id ?? k), label: (v as any).name ?? (v as any).label, provider: (v as any).provider ?? (v as any).engine}
                                    : {id: String(v)}
                            );
                    }
                }

                models = models.filter((m) => m.id);
                if (models.length > 0) setAvailableModels(models);
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
        setIsHuggingFaceModel(engine === "hugging face");
    }, [engine])

    useEffect(() => {
        // Greek is supported for model calls, but lexicon highlight is Latin-only.
        if (language !== "latin") {
            setTextView("plain");
            lexControllerRef.current?.abort();
            setLexRes(null);
            setLexError("");
        }
        if (language !== "latin") {
            setChatIncludePriors(false);
        }
        // eslint-disable-next-line react-hooks/exhaustive-deps
    }, [language]);

    function commitActiveText(next: string) {
        setActiveText(next || "");
        setEditMode(false);
        lexControllerRef.current?.abort();
        setLexRes(null);
        setLexError("");
        setExtractWarnings([]);
        setLlmContent("");
        setLlmError("");
        setChatMessages([]);
        setChatError("");
        if (resp || error) {
            setResp(null);
            setError("");
        }
    }

    function selectedModelEntry() {
        return availableModels.find((m) => m.id === model) || null;
    }

    function isRegistryLlmCapable() {
        const m = selectedModelEntry();
        const p = (m?.provider || "").toLowerCase();
        if (!p) return true; // unknown -> allow and let backend error if needed
        return p !== "hugging face";
    }

    useEffect(() => {
        if (typeof window === "undefined") return;
        try {
            const kLocal = window.localStorage.getItem("openrouter_api_key") || "";
            const kSession = window.sessionStorage.getItem("openrouter_api_key") || "";
            const mLocal = window.localStorage.getItem("openrouter_model") || "";
            const mSession = window.sessionStorage.getItem("openrouter_model") || "";
            if (kLocal) {
                setOpenrouterKey(kLocal);
                setRememberOpenrouterKey(true);
            } else if (kSession) {
                setOpenrouterKey(kSession);
                setRememberOpenrouterKey(false);
            }
            // If a model is remembered but no key is present, still restore the checkbox state.
            if (!kLocal && !kSession) {
                if (mLocal) setRememberOpenrouterKey(true);
                else if (mSession) setRememberOpenrouterKey(false);
            }
            const m = mLocal || mSession;
            if (m) setOpenrouterModel(m);
        } catch {
            // ignore
        }
    }, []);

    useEffect(() => {
        if (typeof window === "undefined") return;
        try {
            const key = openrouterKey || "";
            if (rememberOpenrouterKey) {
                if (key) window.localStorage.setItem("openrouter_api_key", key);
                else window.localStorage.removeItem("openrouter_api_key");
                window.sessionStorage.removeItem("openrouter_api_key");
            } else {
                if (key) window.sessionStorage.setItem("openrouter_api_key", key);
                else window.sessionStorage.removeItem("openrouter_api_key");
                window.localStorage.removeItem("openrouter_api_key");
            }
        } catch {
            // ignore
        }
    }, [openrouterKey, rememberOpenrouterKey]);

    useEffect(() => {
        if (typeof window === "undefined") return;
        try {
            const modelId = (openrouterModel || "").trim();
            if (rememberOpenrouterKey) {
                if (modelId) window.localStorage.setItem("openrouter_model", modelId);
                else window.localStorage.removeItem("openrouter_model");
                window.sessionStorage.removeItem("openrouter_model");
            } else {
                if (modelId) window.sessionStorage.setItem("openrouter_model", modelId);
                else window.sessionStorage.removeItem("openrouter_model");
                window.localStorage.removeItem("openrouter_model");
            }
        } catch {
            // ignore
        }
    }, [openrouterModel, rememberOpenrouterKey]);

    async function handleSubmit(e: React.FormEvent<HTMLFormElement>) {
        e.preventDefault();
        const text = activeText || "";
        if (!text.trim()) {
            setError("Load or paste text first.");
            return;
        }
        if (providerMode === "registry" && !model) {
            setError("Please select a model.");
            return;
        }
        if (providerMode === "openrouter") {
            if (!openrouterKey.trim()) {
                setError("Enter an OpenRouter API key.");
                return;
            }
            if (!openrouterModel.trim()) {
                setError("Enter an OpenRouter model id.");
                return;
            }
        }

        controllerRef.current?.abort();
        controllerRef.current = new AbortController();

        setLoading(true);
        setError("");
        setResp(null);

        try {
            const payload: any = {
                text,
                model_id: providerMode === "registry" ? model : undefined,
                provider: providerMode === "openrouter" ? "openrouter" : undefined,
                openrouter_model: providerMode === "openrouter" ? openrouterModel : undefined,
                include_lexicon_priors: language === "latin" ? !!analyzeIncludePriors : false,
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
            const headers: any = {"Content-Type": "application/json"};
            if (providerMode === "openrouter") headers["Authorization"] = `Bearer ${openrouterKey}`;
            const rr = await fetch(`${API_BASE}/analyze`, {
                method: "POST",
                headers,
                body: JSON.stringify(payload),
                signal: controllerRef.current.signal,
            });
            if (!rr.ok) throw new Error(`Request failed: ${rr.status}`);
            const data: AnalyzeResponse = await rr.json();
            console.log(data)
            setResp(data);
            setProgress(100);
            focusOutput("sentiment");
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

        controllerRef.current?.abort();
        controllerRef.current = new AbortController();

        setLoading(true);
        setError("");
        setResp(null);
        setExtractWarnings([]);

        try {
            const form = new FormData();
            form.append("file", f);
            const rr = await fetch(`${API_BASE}/text/extract`, {
                method: "POST",
                body: form,
                signal: controllerRef.current.signal,
            });
            if (!rr.ok) throw new Error(`Upload failed: ${rr.status}`);
            const data: any = await rr.json();
            const nextText = data?.text ? String(data.text) : "";
            commitActiveText(nextText);
            setPasteDraft(nextText);
            setWorkspaceTab("paste");
            setEditMode(false);
            if (Array.isArray(data?.warnings)) setExtractWarnings(data.warnings.map((w: any) => String(w)));
        } catch (err: any) {
            if (err?.name !== "AbortError") setError(err?.message || "Upload failed");
        } finally {
            setLoading(false);
        }
    }

    function exportJSON() {
        const payload = JSON.stringify(
            resp ?? {model, providerMode, openrouterModel: openrouterModel || null, text: activeText},
            null,
            2
        );
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
        providerMode,
        textLen: activeText.length,
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

    async function ensureSamplesLoaded() {
        if (language !== "latin") {
            setSamples([]);
            setSamplesLoaded(true);
            return;
        }
        if (samplesLoaded) return;
        try {
            const rr = await fetch(`${API_BASE}/samples/latin`);
            if (!rr.ok) throw new Error(`Failed to load samples: ${rr.status}`);
            const data: any = await rr.json();
            const list = Array.isArray(data?.samples) ? data.samples : [];
            const normalized = list
                .map((s: any) => ({
                    id: String(s.id || ""),
                    name: String(s.name || s.id || ""),
                    bytes: Number(s.bytes || 0),
                }))
                .filter((s: any) => s.id);
            setSamples(normalized);
            if (!pickedSampleId && normalized.length > 0) setPickedSampleId(normalized[0].id);
        } catch {
            setSamples([]);
        } finally {
            setSamplesLoaded(true);
        }
    }

    async function loadPickedSample() {
        if (!pickedSampleId) return;
        setLoading(true);
        setError("");
        setResp(null);
        try {
            const rr = await fetch(`${API_BASE}/samples/latin/${encodeURIComponent(pickedSampleId)}`);
            if (!rr.ok) throw new Error(`Failed to load sample: ${rr.status}`);
            const data: any = await rr.json();
            const nextText = data?.text ? String(data.text) : "";
            commitActiveText(nextText);
            setPasteDraft(nextText);
            setWorkspaceTab("paste");
            setEditMode(false);
        } catch (err: any) {
            setError(err?.message || "Failed to load sample");
        } finally {
            setLoading(false);
        }
    }

    async function computeLexicon(text: string) {
        if (language !== "latin") return;
        if (!text.trim()) return;
        lexControllerRef.current?.abort();
        lexControllerRef.current = new AbortController();
        setLexLoading(true);
        setLexError("");
        try {
            const rr = await fetch(`${API_BASE}/latin/lexicon/annotate`, {
                method: "POST",
                headers: {"Content-Type": "application/json"},
                body: JSON.stringify({text, max_chars: 12000}),
                signal: lexControllerRef.current.signal,
            });
            if (!rr.ok) {
                let msg = `Lexicon request failed: ${rr.status}`;
                try {
                    const j = await rr.json();
                    if (j?.detail) msg = String(j.detail);
                } catch {
                    // ignore
                }
                throw new Error(msg);
            }
            const data: any = await rr.json();
            setLexRes(data);
        } catch (err: any) {
            if (err?.name !== "AbortError") setLexError(err?.message || "Lexicon failed");
        } finally {
            setLexLoading(false);
        }
    }

    useEffect(() => {
        if (editMode) return;
        if (textView !== "lexicon") return;
        if (language !== "latin") return;
        if (!lexAuto) return;
        if (!activeText.trim()) return;
        const id = setTimeout(() => {
            computeLexicon(activeText);
        }, 650);
        return () => clearTimeout(id);
        // eslint-disable-next-line react-hooks/exhaustive-deps
    }, [activeText, lexAuto, textView, editMode, language]);

    async function tryFetchLatinPriorsJson(): Promise<string> {
        if (language !== "latin") return "";
        if (!chatIncludePriors) return "";
        try {
            const rr = await fetch(`${API_BASE}/latin/lexicon/priors`, {
                method: "POST",
                headers: {"Content-Type": "application/json"},
                body: JSON.stringify({text: activeText, max_chars: 6000}),
            });
            if (!rr.ok) {
                let msg = `Priors unavailable (${rr.status})`;
                try {
                    const j = await rr.json();
                    if (j?.detail) msg = String(j.detail);
                } catch {
                    // ignore
                }
                setChatPriorsWarning(msg);
                return "";
            }
            const data: any = await rr.json();
            const priors = data?.priors;
            if (!priors || typeof priors !== "object") return "";
            setChatPriorsWarning("");
            return JSON.stringify(priors) + "\n\n";
        } catch {
            setChatPriorsWarning("Priors unavailable (network error)");
            return "";
        }
    }

    async function buildChatSystemPrompt() {
        const clip = (activeText || "").slice(0, 6000);
        const meta: string[] = [];
        if ((chatPeriod || "").trim()) meta.push(`Period: ${chatPeriod.trim()}`);
        if ((chatGenre || "").trim()) meta.push(`Genre/Context: ${chatGenre.trim()}`);
        const metaBlock = meta.length ? meta.join("\n") + "\n\n" : "";

        const priorsJson = await tryFetchLatinPriorsJson();

        if (language === "greek") {
            return (
                "You are an Ancient Greek text analysis assistant.\n" +
                "The user will ask questions about the provided Greek text.\n" +
                "Do not ask the user to paste the text; it is included below.\n" +
                "If the question cannot be answered from the text, say what is missing.\n\n" +
                metaBlock +
                `Greek text:\n${clip}\n`
            );
        }
        return (
            "You are a Latin text analysis assistant.\n" +
            "The user will ask questions about the provided Latin text.\n" +
            "Do not ask the user to paste the text; it is included below.\n" +
            "If the question cannot be answered from the text, say what is missing.\n" +
            (priorsJson ? "If lexicon priors are included, treat them as weak evidence.\n\n" : "\n") +
            priorsJson +
            metaBlock +
            `Latin text:\n${clip}\n`
        );
    }

    async function sendChatMessage() {
        const q = (chatDraft || "").trim();
        if (!q) return;
        if (!(activeText || "").trim()) {
            setChatError("Load text above first.");
            return;
        }
        if (providerMode === "registry" && !model) {
            setChatError("Select a model to chat.");
            return;
        }
        if (providerMode === "registry" && !isRegistryLlmCapable()) {
            setChatError("Selected registry model is not an LLM (Hugging Face). Pick a local Ollama model to chat.");
            return;
        }
        if (providerMode === "openrouter" && (!openrouterKey.trim() || !openrouterModel.trim())) {
            setChatError("Enter OpenRouter model id and API key to chat.");
            return;
        }

        setChatError("");
        setChatLoading(true);

        const nextMessages = [...chatMessages, {role: "user" as const, content: q}];
        setChatMessages(nextMessages);
        setChatDraft("");

        try {
            const system = await buildChatSystemPrompt();
            const history = nextMessages.slice(-12);
            const payload: any = {
                model_id: providerMode === "registry" ? model : openrouterModel,
                provider: providerMode === "openrouter" ? "openrouter" : undefined,
                openrouter_model: providerMode === "openrouter" ? openrouterModel : undefined,
                messages: [{role: "system", content: system}, ...history],
                temperature: modelOpts.temperature,
                max_tokens: modelOpts.num_predict,
                stream: false,
                extra: {},
            };
            const headers: any = {"Content-Type": "application/json"};
            if (providerMode === "openrouter") headers["Authorization"] = `Bearer ${openrouterKey}`;
            const rr = await fetch(`${API_BASE}/chat`, {
                method: "POST",
                headers,
                body: JSON.stringify(payload),
            });
            if (!rr.ok) {
                let msg = `Chat failed: ${rr.status}`;
                try {
                    const j = await rr.json();
                    if (j?.detail) msg = String(j.detail);
                } catch {
                    // ignore
                }
                throw new Error(msg);
            }
            const data: any = await rr.json();
            const content = String(data?.content || "");
            setChatMessages((prev) => [...prev, {role: "assistant", content}]);
            focusOutput("chat");
        } catch (e: any) {
            setChatError(e?.message || "Chat failed");
        } finally {
            setChatLoading(false);
        }
    }

    async function runLlmAnalysis() {
        if (!(activeText || "").trim()) {
            setLlmError("Load text above first.");
            return;
        }
        if (providerMode === "registry" && !model) {
            setLlmError("Select a local model to run analysis.");
            return;
        }
        if (providerMode === "registry" && !isRegistryLlmCapable()) {
            setLlmError("Selected registry model is not an LLM (Hugging Face). Pick a local Ollama model to run analysis.");
            return;
        }
        if (providerMode === "openrouter") {
            if (!openrouterModel.trim()) {
                setLlmError("Enter an OpenRouter model id.");
                return;
            }
            if (!openrouterKey.trim()) {
                setLlmError("Enter an OpenRouter API key.");
                return;
            }
        }

        setLlmLoading(true);
        setLlmError("");
        setLlmContent("");
        try {
            const payload: any = {
                text: activeText,
                language,
                mode: llmMode,
                period: llmPeriod,
                genre: llmGenre,
                output_length: llmOutputLength,
                include_lexicon_priors: language === "latin" ? !!llmIncludePriors : false,
                provider: providerMode === "openrouter" ? "openrouter" : "ollama",
                model_id: providerMode === "registry" ? model : undefined,
                openrouter_model: providerMode === "openrouter" ? openrouterModel : undefined,
                options: {
                    temperature: modelOpts.temperature,
                },
            };
            const headers: any = {"Content-Type": "application/json"};
            if (providerMode === "openrouter") headers["Authorization"] = `Bearer ${openrouterKey}`;
            const rr = await fetch(`${API_BASE}/llm/analyze`, {
                method: "POST",
                headers,
                body: JSON.stringify(payload),
            });
            if (!rr.ok) {
                let msg = `Run analysis failed: ${rr.status}`;
                try {
                    const j = await rr.json();
                    if (j?.detail) msg = String(j.detail);
                } catch {
                    // ignore
                }
                throw new Error(msg);
            }
            const data: any = await rr.json();
            setLlmContent(String(data?.content || ""));
            focusOutput("llm");
        } catch (e: any) {
            setLlmError(e?.message || "Run analysis failed");
        } finally {
            setLlmLoading(false);
        }
    }

// typescript
// Insert this inside the Analyzer component (e.g. after renderValue) and replace the existing HF panel JSX with the usage shown below.

    function extractHfList(respObj: any): any[] | null {
        if (!respObj) return null;
        // try multiple common key variants
        const candidates = [
            "labels_and_scores_by_sentence",
            "labels and scores by sentence",
            "labels_and_scores",
            "labels_by_sentence",
            "labels",
            "scores_by_sentence",
        ];
        for (const k of candidates) {
            const v = respObj[k] ?? respObj?.data?.[k];
            if (Array.isArray(v) && v.length > 0) return v;
        }
        // maybe top-level is already an array
        if (Array.isArray(respObj)) return respObj;
        return null;
    }

    function renderHfTable(respObj: any) {
        const list = extractHfList(respObj);
        if (!list) {
            // fallback to raw JSON display
            return (
                <div className="panel">
                    <h3>Raw Response (Hugging Face)</h3>
                    <pre style={{whiteSpace: "pre-wrap", wordBreak: "break-word", maxHeight: 400, overflow: "auto"}}>
                    {JSON.stringify(respObj, null, 2)}
                </pre>
                </div>
            );
        }
        const rows = list.map((item: any, i: number) => {
            if (Array.isArray(item) && item.length > 0) {
                const top = item[0];
                return {
                    index: i + 1,
                    label: top?.label ?? top?.name ?? JSON.stringify(item),
                    score: top?.score ?? top?.confidence ?? null,
                    sentence: (top?.sentence ?? top?.text ?? null),
                    raw: item,
                };
            }
            if (item && typeof item === "object") {
                // item may be { label, score, sentence } or { sentence: "...", labels: [...] }
                const label = item.label ?? item.predicted_label ?? (Array.isArray(item.labels) ? String(item.labels[0]?.label ?? item.labels[0]) : undefined);
                const score = item.score ?? item.confidence ?? item.probability ?? (Array.isArray(item.labels) ? item.labels[0]?.score : undefined);
                const sentence = item.sentence ?? item.text ?? item.input ?? null;
                return {
                    index: i + 1,
                    label: label ?? JSON.stringify(item),
                    score: score ?? null,
                    sentence,
                    raw: item,
                };
            }
            // primitive fallback
            return {index: i + 1, label: String(item), score: null, sentence: null, raw: item};
        });

        const showSentenceColumn = rows.some((r) => r.sentence);

        return (
            <div className="panels">
                <div className="panel width=100%">
                    <h3>Hugging Face — Results by Sentence</h3>
                    <div style={{overflowX: "auto", maxHeight: 420}}>
                        <table className="hf-table" style={{width: "100%", borderCollapse: "collapse"}}>
                            <thead>
                            <tr>
                                <th style={{textAlign: "left", padding: 8, borderBottom: "1px solid #ddd"}}>#</th>
                                <th style={{textAlign: "left", padding: 8, borderBottom: "1px solid #ddd"}}>Label</th>
                                <th style={{textAlign: "left", padding: 8, borderBottom: "1px solid #ddd"}}>Score</th>
                                {showSentenceColumn && <th style={{
                                    textAlign: "left",
                                    padding: 8,
                                    borderBottom: "1px solid #ddd"
                                }}>Sentence</th>}
                            </tr>
                            </thead>
                            <tbody>
                            {rows.map((r) => (
                                <tr key={r.index} style={{borderBottom: "1px solid #f3f3f3"}}>
                                    <td style={{padding: 8}}>{r.index}</td>
                                    <td style={{padding: 8, whiteSpace: "nowrap"}}>{String(r.label)}</td>
                                    <td style={{padding: 8}}>{r.score != null ? toPercent(r.score) : "—"}</td>
                                    {showSentenceColumn && <td style={{
                                        padding: 8,
                                        whiteSpace: "normal",
                                        maxWidth: 420
                                    }}>{r.sentence ?? JSON.stringify(r.raw)}</td>}
                                </tr>
                            ))}
                            </tbody>
                        </table>
                    </div>
                </div>
            </div>
        );
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
                    {providerMode === "openrouter" ? (
                        <div className="bar-stack">
                            <div className="bar-line">
                                <select
                                    value={language}
                                    onChange={(e) => setLanguage((e.target.value as any) || "latin")}
                                    title="Language"
                                >
                                    <option value="latin">Latin</option>
                                    <option value="greek">Greek</option>
                                </select>

                                <select
                                    value={providerMode}
                                    onChange={(e) => {
                                        setProviderMode((e.target.value as any) || "registry");
                                        setError("");
                                        setResp(null);
                                    }}
                                    title="Provider"
                                >
                                    <option value="registry">Local Model</option>
                                    <option value="openrouter">OpenRouter</option>
                                </select>

                                <label style={{display: "flex", gap: 8, alignItems: "center"}}>
                                    <input
                                        type="checkbox"
                                        checked={analyzeIncludePriors}
                                        onChange={(e) => setAnalyzeIncludePriors(e.target.checked)}
                                        disabled={language !== "latin"}
                                    />
                                    RAG priors
                                </label>

                            <button type="submit" disabled={loading}>
                                    {loading ? "Analyzing…" : "Run sentiment"}
                            </button>

                                <button type="button" onClick={triggerUpload} disabled={loading}>
                                    Upload
                                </button>
                            </div>

                            <div className="bar-line bar-two-col">
                                <input
                                    className="bar-input-large"
                                    type="text"
                                    placeholder="OpenRouter model id…"
                                    value={openrouterModel}
                                    onChange={(e) => setOpenrouterModel(e.target.value)}
                                />
                                <input
                                    className="bar-input-large"
                                    type="password"
                                    placeholder="OpenRouter API key…"
                                    value={openrouterKey}
                                    onChange={(e) => setOpenrouterKey(e.target.value)}
                                />
                            </div>

                            <div className="bar-line" style={{justifyContent: "space-between"}}>
                                <label style={{display: "flex", gap: 8, alignItems: "center"}}>
                                    <input
                                        type="checkbox"
                                        checked={rememberOpenrouterKey}
                                        onChange={(e) => setRememberOpenrouterKey(e.target.checked)}
                                    />
                                    Remember key on this device
                                </label>
                                <button
                                    type="button"
                                    onClick={() => {
                                        setOpenrouterKey("");
                                        try {
                                            window.sessionStorage.removeItem("openrouter_api_key");
                                            window.localStorage.removeItem("openrouter_api_key");
                                        } catch {
                                            // ignore
                                        }
                                    }}
                                    disabled={!openrouterKey}
                                    title="Clear stored key"
                                >
                                    Clear key
                                </button>
                            </div>
                        </div>
                    ) : (
                        <>
                            <select
                                value={language}
                                onChange={(e) => setLanguage((e.target.value as any) || "latin")}
                                title="Language"
                            >
                                <option value="latin">Latin</option>
                                <option value="greek">Greek</option>
                            </select>

                            <select
                                value={providerMode}
                                onChange={(e) => {
                                    setProviderMode((e.target.value as any) || "registry");
                                    setError("");
                                    setResp(null);
                                }}
                                title="Provider"
                            >
                                <option value="registry">Local Model</option>
                                <option value="openrouter">OpenRouter</option>
                            </select>

                            <select
                                value={model}
                                onChange={(e) => {
                                    setModel(e.target.value);
                                    if (resp || error) {
                                        setResp(null);
                                        setError("");
                                    }
                                }}
                                title="Model"
                            >
                                <option value="">Select a model…</option>
                            {availableModels.map((m) => (
                                    <option key={m.id} value={m.id}>
                                        {(m.label ?? m.id) + (m.provider ? ` (${m.provider})` : "")}
                                    </option>
                                ))}
                            </select>

                            <label style={{display: "flex", gap: 8, alignItems: "center"}}>
                                <input
                                    type="checkbox"
                                    checked={analyzeIncludePriors}
                                    onChange={(e) => setAnalyzeIncludePriors(e.target.checked)}
                                    disabled={language !== "latin"}
                                />
                                RAG priors
                            </label>

                            <button type="submit" disabled={loading}>
                                {loading ? "Analyzing…" : "Run sentiment"}
                            </button>

                            <button type="button" onClick={triggerUpload} disabled={loading}>
                                Upload
                            </button>
                        </>
                    )}

                    <input
                        ref={fileRef}
                        type="file"
                        accept=".txt,.md,.csv,.tsv,.pdf"
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
                                            commitActiveText("");
                                            setPasteDraft("");
                                            setEditMode(true);
                                            setResp(null);
                                            setError("");
                                            setLoading(false);
                                            setProgress(0);
                                            setLexRes(null);
                                            setLexError("");
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

            <div className="workspace">
                <div className="workspace-header">
                    <h2 className="workspace-title">
                        {language === "latin" ? "Latin Text" : "Greek Text"}
                    </h2>
                    <div
                        className="workspace-tabs"
                        role="tablist"
                        aria-label="Text input modes"
                    >
                        <button
                            type="button"
                            className={`tab-btn ${workspaceTab === "paste" ? "active" : ""}`}
                            onClick={() => setWorkspaceTab("paste")}
                        >
                            Paste
                        </button>
                        <button
                            type="button"
                            className={`tab-btn ${workspaceTab === "upload" ? "active" : ""}`}
                            onClick={() => setWorkspaceTab("upload")}
                        >
                            Upload
                        </button>
                        <button
                            type="button"
                            className={`tab-btn ${workspaceTab === "sample" ? "active" : ""}`}
                            onClick={() => {
                                setWorkspaceTab("sample");
                                ensureSamplesLoaded();
                            }}
                            disabled={language !== "latin"}
                            title={language !== "latin" ? "Samples are currently Latin-only." : undefined}
                        >
                            Sample
                        </button>
                    </div>
                </div>

                <div className="workspace-card">
                    {workspaceTab === "paste" && editMode && (
                        <>
                            <textarea
                                className="workspace-textarea"
                                placeholder={language === "latin" ? "Paste Latin text here…" : "Paste Greek text here…"}
                                value={pasteDraft}
                                onChange={(e) => setPasteDraft(e.target.value)}
                            />
                            <div className="workspace-row">
                                <button
                                    type="button"
                                    onClick={() => commitActiveText(pasteDraft)}
                                    disabled={loading}
                                >
                                    Use pasted text
                                </button>
                            </div>
                        </>
                    )}

                    {workspaceTab === "upload" && (
                        <>
                            <div className="workspace-meta" style={{marginBottom: 10}}>
                                <span className="pill">Supported: txt, md, csv, tsv, pdf</span>
                                <span className="pill">Use Upload in the top bar</span>
                            </div>
                            <button type="button" onClick={triggerUpload} disabled={loading}>
                                Choose file…
                            </button>
                        </>
                    )}

                    {workspaceTab === "sample" && (
                        <>
                            {language !== "latin" ? (
                                <div className="workspace-meta">
                                    <span className="pill">Samples are currently available for Latin only.</span>
                                </div>
                            ) : (
                                samples.length === 0 ? (
                                    <div className="workspace-meta">
                                        <span className="pill">
                                            No samples found in `src/sample_text/latin/`.
                                        </span>
                                    </div>
                                ) : (
                                    <div className="workspace-row">
                                        <select
                                            value={pickedSampleId}
                                            onChange={(e) => setPickedSampleId(e.target.value)}
                                            style={{minWidth: 260}}
                                        >
                                            {samples.map((s) => (
                                                <option key={s.id} value={s.id}>
                                                    {s.name} ({Math.round((s.bytes || 0) / 1024)} KB)
                                                </option>
                                            ))}
                                        </select>
                                        <button
                                            type="button"
                                            onClick={loadPickedSample}
                                            disabled={!pickedSampleId || loading}
                                        >
                                            Load sample
                                        </button>
                                    </div>
                                )
                            )}
                        </>
                    )}

                    {extractWarnings.length > 0 && (
                        <div className="workspace-row">
                            <div className="error" style={{marginTop: 0}}>
                                {extractWarnings.map((w, i) => (
                                    <div key={i}>{w}</div>
                                ))}
                            </div>
                        </div>
                    )}

                    <div className="workspace-row" style={{justifyContent: "space-between", gap: 12}}>
                        <div className="workspace-meta">
                            <span className="pill">
                                Chars: {(activeText || "").length.toLocaleString()}
                            </span>
                            <span className="pill">
                                Words:{" "}
                                {(activeText || "").trim()
                                    ? activeText.trim().split(/\s+/).length.toLocaleString()
                                    : "0"}
                            </span>
                            {(activeText || "").length > 12000 && (
                                <span className="pill">Showing first 12k</span>
                            )}
                        </div>

                        <div className="workspace-tabs" aria-label="Text view" style={{justifyContent: "flex-end"}}>
                            <button
                                type="button"
                                className={`tab-btn ${textView === "plain" ? "active" : ""}`}
                                onClick={() => setTextView("plain")}
                                disabled={editMode}
                            >
                                Plain
                            </button>
                            <button
                                type="button"
                                className={`tab-btn ${textView === "lexicon" ? "active" : ""}`}
                                onClick={() => setTextView("lexicon")}
                                disabled={editMode || language !== "latin"}
                                title={language !== "latin" ? "Lexicon highlight is Latin-only." : undefined}
                            >
                                Lexicon highlight
                            </button>
                            <button
                                type="button"
                                className="tab-btn"
                                onClick={() => {
                                    setWorkspaceTab("paste");
                                    setPasteDraft(activeText || "");
                                    setEditMode(true);
                                }}
                                disabled={loading}
                                title="Edit the current text"
                            >
                                Edit
                            </button>
                        </div>
                    </div>

                    {!editMode && (
                        <>
                            {textView === "lexicon" && (
                                <div className="workspace-row" style={{justifyContent: "space-between", gap: 12}}>
                                    <div className="workspace-meta">
                                        <label style={{display: "flex", gap: 6, alignItems: "center"}}>
                                            <input
                                                type="checkbox"
                                                checked={lexAuto}
                                                onChange={(e) => setLexAuto(e.target.checked)}
                                            />
                                            Auto
                                        </label>
                                    </div>
                                    <div style={{display: "flex", gap: 10, alignItems: "center", flexWrap: "wrap"}}>
                                        <button
                                            type="button"
                                            onClick={() => computeLexicon(activeText)}
                                            disabled={lexLoading || !(activeText || "").trim()}
                                        >
                                            {lexLoading ? "Computing…" : "Compute highlights"}
                                        </button>
                                    </div>
                                </div>
                            )}

                            {textView === "lexicon" && lexError && (
                                <div className="error" style={{marginTop: 10}}>
                                    {lexError}
                                </div>
                            )}

                            {textView === "lexicon" && lexRes?.coverage && (
                                <div className="workspace-meta" style={{marginTop: 10}}>
                                    <span className="pill">
                                        Tokens: {Number(lexRes.coverage.token_count || 0).toLocaleString()}
                                    </span>
                                    <span className="pill">
                                        Hit rate: {Number(lexRes.coverage.affectus_hit_rate || 0).toFixed(3)}
                                    </span>
                                    <span className="pill">
                                        Sentiment lemmas: {Number(lexRes.coverage.sentiment_lemma_hits || 0).toLocaleString()}
                                    </span>
                                </div>
                            )}

                            <div className="text-view">
                                {!(activeText || "").trim() ? (
                                    <div style={{color: "rgba(255,255,255,0.85)"}}>
                                        No {language === "latin" ? "Latin" : "Greek"} text loaded yet. Paste, upload{language === "latin" ? ", or pick a sample" : ""} above.
                                    </div>
                                ) : textView === "lexicon" && lexRes?.spans && Array.isArray(lexRes.spans) ? (
                                    <>
                                        {lexRes?.truncated && (
                                            <div style={{marginBottom: 10, color: "rgba(255,255,255,0.85)"}}>
                                                Overlay shown on the first 12k characters for performance.
                                            </div>
                                        )}
                                        <LatinLexiconOverlay
                                            text={(activeText || "").slice(0, 12000)}
                                            spans={lexRes.spans}
                                            lemmaDetails={lexRes.lemma_details || {}}
                                        />
                                    </>
                                ) : (
                                    <pre className="plain-text">
                                        {(activeText || "").slice(0, 12000)}
                                        {(activeText || "").length > 12000 ? "\n\n[…truncated…]" : ""}
                                    </pre>
                                )}
                            </div>
                        </>
                    )}
                </div>
            </div>

            <div ref={outputRef} className="output-wrap">
                <div className="output-header">
                    <h3 className="output-title">Output</h3>
                    <div className="workspace-tabs" aria-label="Output tabs" style={{justifyContent: "flex-end"}}>
                        <button
                            type="button"
                            className={`tab-btn ${outputTab === "sentiment" ? "active" : ""}`}
                            onClick={() => setOutputTab("sentiment")}
                        >
                            Sentiment
                        </button>
                        <button
                            type="button"
                            className={`tab-btn ${outputTab === "llm" ? "active" : ""}`}
                            onClick={() => setOutputTab("llm")}
                        >
                            LLM Analysis
                        </button>
                        <button
                            type="button"
                            className={`tab-btn ${outputTab === "chat" ? "active" : ""}`}
                            onClick={() => setOutputTab("chat")}
                        >
                            Chat
                        </button>
                    </div>
                </div>

                {loading && (
                    <div className="output-loading" aria-live="polite" aria-busy="true">
                        <span className="loading-dots" aria-label="Loading">
                            <span />
                            <span />
                            <span />
                        </span>
                    </div>
                )}

                {outputTab === "sentiment" && (
                    <>
                        {!!error && <div className="error">{error}</div>}

                        {hasResp ? (
                            <>
                                {isHuggingFaceModel ? renderHfTable(resp) : (
                                    <div className="panels results-stack tight">
                                        <div className="panel">
                                            <div style={{display: "flex", justifyContent: "space-between", alignItems: "center"}}>
                                                <h3 style={{margin: 0}}>Results</h3>
                                                <div style={{display: "flex", gap: 8}}/>
                                            </div>
                                            <div className="results-two-col" style={{marginTop: 10}}>
                                                <div className="model-settings-grid">
                                                    <div className="model-settings-label">Engine</div>
                                                    <div>{engine || "—"}</div>

                                                    <div className="model-settings-label">Label</div>
                                                    <div>{label ? String(label).toUpperCase() : "—"}</div>

                                                    <div className="model-settings-label">Confidence</div>
                                                    <div>{typeof confidence === "number" ? `${(confidence * 100).toFixed(1)}%` : "—"}</div>

                                                    <div className="model-settings-label">RAG priors</div>
                                                    <div>{(r as any)?.lexicon_priors_included ? "Included" : "Not included"}</div>
                                                </div>

                                                <div className="model-settings-grid">
                                                    <div className="model-settings-label">Positive</div>
                                                    <div>{scores && typeof scores === "object" ? `${(Number(scores.positive) * 100).toFixed(1)}%` : "—"}</div>

                                                    <div className="model-settings-label">Neutral</div>
                                                    <div>{scores && typeof scores === "object" ? `${(Number(scores.neutral) * 100).toFixed(1)}%` : "—"}</div>

                                                    <div className="model-settings-label">Negative</div>
                                                    <div>{scores && typeof scores === "object" ? `${(Number(scores.negative) * 100).toFixed(1)}%` : "—"}</div>
                                                </div>
                                            </div>
                                        </div>
                                        <>
                                            <div className="panel">
                                                <h3>Translation</h3>
                                                <MarkdownBlock content={translation ? String(translation) : "—"} />
                                            </div>
                                            <div className="panel">
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
                                            </div>
                                        </>
                                    </div>
                                )}
                            </>
                        ) : (
                            <div className="panels debug-grid tight">
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
                                                    <span key={s} className="model-stop-chip">{s}</span>
                                                ))
                                            )}
                                        </div>
                                    </div>
                                </div>
                            </div>
                        )}

                        {hasResp && (
                            <div className="floating-actions">
                                <button
                                    className="ghost-btn"
                                    onClick={() => setFeedbackOpen(true)}
                                    disabled={!resp || !(activeText || "").trim()}
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
                    </>
                )}

                {outputTab === "llm" && (
                    <div className="panels tight">
                        <div className="panel" style={{gridColumn: "1 / -1"}}>
                            <div className="workspace-row" style={{marginTop: 0}}>
                                <select
                                    value={llmMode}
                                    onChange={(e) => setLlmMode(parseInt(e.target.value, 10) || 1)}
                                    title="Analysis mode"
                                >
                                    <option value={1}>1: Translation Only</option>
                                    <option value={2}>2: Word/Lemma Sentiment</option>
                                    <option value={3}>3: Document-Level Sentiment</option>
                                    <option value={4}>4: Aspect-Based Sentiment</option>
                                    <option value={5}>5: Sentence/Paragraph-Level</option>
                                    <option value={6}>6: All</option>
                                </select>

                                <select
                                    value={llmOutputLength}
                                    onChange={(e) => setLlmOutputLength((e.target.value as any) || "medium")}
                                    title="Output length"
                                >
                                    <option value="short">Short</option>
                                    <option value="medium">Medium</option>
                                    <option value="long">Long</option>
                                </select>

                                <label style={{display: "flex", gap: 8, alignItems: "center"}}>
                                    <input
                                        type="checkbox"
                                        checked={llmIncludePriors}
                                        onChange={(e) => setLlmIncludePriors(e.target.checked)}
                                        disabled={language !== "latin"}
                                    />
                                    Include lexicon priors
                                </label>

                                <button type="button" onClick={runLlmAnalysis} disabled={llmLoading}>
                                    {llmLoading ? "Running…" : "Run analysis"}
                                </button>
                            </div>

                            <div className="two-col-row" style={{marginTop: 10}}>
                                <input
                                    className="bar-input-large"
                                    type="text"
                                    placeholder="Period (optional)"
                                    value={llmPeriod}
                                    onChange={(e) => setLlmPeriod(e.target.value)}
                                />
                                <input
                                    className="bar-input-large"
                                    type="text"
                                    placeholder="Genre/Context (optional)"
                                    value={llmGenre}
                                    onChange={(e) => setLlmGenre(e.target.value)}
                                />
                            </div>

                            {llmError && <div className="error" style={{marginTop: 10}}>{llmError}</div>}

                            <div className="text-view" style={{minHeight: 320, maxHeight: 520}}>
                                {!llmContent ? (
                                    <div style={{color: "rgba(255,255,255,0.85)"}}>
                                        Run a structured analysis (modes 1–6) on the loaded {language === "latin" ? "Latin" : "Greek"} text.
                                    </div>
                                ) : (
                                    <MarkdownBlock content={llmContent} />
                                )}
                            </div>
                        </div>
                    </div>
                )}

                {outputTab === "chat" && (
                    <div className="panels tight">
                        <div className="panel" style={{gridColumn: "1 / -1"}}>
                            <div className="workspace-row" style={{marginTop: 0, justifyContent: "space-between"}}>
                                <label style={{display: "flex", gap: 8, alignItems: "center"}}>
                                    <input
                                        type="checkbox"
                                        checked={chatIncludePriors}
                                        onChange={(e) => setChatIncludePriors(e.target.checked)}
                                        disabled={language !== "latin"}
                                    />
                                    Include lexicon priors
                                </label>
                                <button
                                    type="button"
                                    onClick={() => {
                                        setChatMessages([]);
                                        setChatError("");
                                        setChatPriorsWarning("");
                                    }}
                                    disabled={chatLoading}
                                >
                                    Reset chat
                                </button>
                            </div>

                            <div className="two-col-row" style={{marginTop: 10}}>
                                <input
                                    className="bar-input-large"
                                    type="text"
                                    placeholder="Period (optional)"
                                    value={chatPeriod}
                                    onChange={(e) => setChatPeriod(e.target.value)}
                                />
                                <input
                                    className="bar-input-large"
                                    type="text"
                                    placeholder="Genre/Context (optional)"
                                    value={chatGenre}
                                    onChange={(e) => setChatGenre(e.target.value)}
                                />
                            </div>

                            {chatPriorsWarning && (
                                <div style={{marginTop: 10, color: "rgba(255,255,255,0.75)", fontSize: 13}}>
                                    {chatPriorsWarning}
                                </div>
                            )}

                            {chatError && <div className="error" style={{marginTop: 10}}>{chatError}</div>}

                            <div className="text-view" style={{minHeight: 260, maxHeight: 360}}>
                                {chatMessages.length === 0 ? null : (
                                    <div style={{display: "flex", flexDirection: "column", gap: 10}}>
                                        {chatMessages.map((m, i) => (
                                            <div key={i} style={{display: "flex", gap: 10}}>
                                                <div style={{width: 90, color: "rgba(255,255,255,0.75)", fontSize: 13}}>
                                                    {m.role === "user" ? "You" : "Assistant"}
                                                </div>
                                                {m.role === "assistant" ? (
                                                    <MarkdownBlock content={m.content} />
                                                ) : (
                                                    <div style={{whiteSpace: "pre-wrap", wordBreak: "break-word"}}>
                                                        {m.content}
                                                    </div>
                                                )}
                                            </div>
                                        ))}
                                    </div>
                                )}
                            </div>

                            <div className="workspace-row" style={{marginTop: 12, alignItems: "flex-end"}}>
                                <textarea
                                    className="workspace-textarea"
                                    style={{minHeight: 110}}
                                    placeholder="Ask a question about the text…"
                                    value={chatDraft}
                                    onChange={(e) => setChatDraft(e.target.value)}
                                    onKeyDown={(e) => {
                                        if ((e.metaKey || e.ctrlKey) && e.key === "Enter") {
                                            e.preventDefault();
                                            if (!chatLoading) sendChatMessage();
                                        }
                                    }}
                                />
                                <button
                                    type="button"
                                    onClick={sendChatMessage}
                                    disabled={chatLoading || !(chatDraft || "").trim()}
                                    style={{height: 44}}
                                >
                                    {chatLoading ? "Sending…" : "Send"}
                                </button>
                            </div>
                            <div style={{marginTop: 6, color: "rgba(255,255,255,0.7)", fontSize: 12}}>
                                Tip: press Ctrl+Enter (or Cmd+Enter) to send.
                            </div>
                        </div>
                    </div>
                )}
            </div>


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
                modelId={providerMode === "registry" ? model : openrouterModel}
                text={activeText}
                got={resp}
            />

            <ModelShopModal open={shopOpen} onClose={() => setShopOpen(false)} apiBase={API_BASE}/>


            {
                notebookOpen && (
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
                )
            }
        </div>
    )
        ;
}
