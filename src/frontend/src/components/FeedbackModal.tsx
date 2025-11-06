"use client";

import React, { useEffect, useMemo, useState } from "react";

type WantShape = {
  label?: "positive" | "negative" | "neutral";
  translation?: string | null;
  analysis?: any;
};

export type FeedbackModalProps = {
  open: boolean;
  onClose: () => void;
  apiBase: string;
  modelId: string;
  text: string;
  got: any;
};

export default function FeedbackModal({
  open,
  onClose,
  apiBase,
  modelId,
  text,
  got,
}: FeedbackModalProps) {
  const existing = useMemo(() => {
    const label = got?.label ?? null;
    const translation = got?.translation ?? null;
    const analysis = got?.analysis ?? null;
    return { label, translation, analysis };
  }, [got]);

  const [label, setLabel] = useState<"positive" | "negative" | "neutral" | "">("");
  const [translation, setTranslation] = useState<string>("");
  const [analysisStr, setAnalysisStr] = useState<string>("");
  const [notes, setNotes] = useState<string>("");
  const [tagsStr, setTagsStr] = useState<string>("");
  const [submitting, setSubmitting] = useState(false);
  const [err, setErr] = useState<string>("");

  useEffect(() => {
    if (!open) return;
    setErr("");
    setSubmitting(false);
    const initLabel =
      existing.label && ["positive", "negative", "neutral"].includes(String(existing.label).toLowerCase())
        ? (String(existing.label).toLowerCase() as "positive" | "negative" | "neutral")
        : "";
    setLabel(initLabel);
    setTranslation(typeof existing.translation === "string" ? existing.translation : "");
    try {
      setAnalysisStr(
        existing.analysis && typeof existing.analysis === "object"
          ? JSON.stringify(existing.analysis, null, 2)
          : ""
      );
    } catch {
      setAnalysisStr("");
    }
    setNotes("");
    setTagsStr("");
  }, [open, existing]);

  function parseAnalysisSafe(s: string) {
    const trimmed = s.trim();
    if (!trimmed) return undefined;
    try {
      return JSON.parse(trimmed);
    } catch (e: any) {
      throw new Error("Analysis must be valid JSON.");
    }
  }

  async function handleSubmit() {
    setErr("");
    let want: WantShape = {};
    if (label) want.label = label;
    if (translation) want.translation = translation;
    if (analysisStr.trim()) {
      want.analysis = parseAnalysisSafe(analysisStr);
    }

    const tags = tagsStr
      .split(",")
      .map((t) => t.trim())
      .filter((t) => t.length > 0);

    const payload = {
      model_id: modelId,
      text,
      got,
      want,
      notes: notes || undefined,
      tags,
    };

    setSubmitting(true);
    try {
      const r = await fetch(`${apiBase}/feedback`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });
      if (!r.ok) throw new Error(`Submit failed: ${r.status}`);
      onClose();
    } catch (e: any) {
      setErr(e?.message || "Failed to submit feedback");
    } finally {
      setSubmitting(false);
    }
  }

  if (!open) return null;

  return (
    <div className="modal" onClick={onClose}>
      <div className="modal-inner" onClick={(e) => e.stopPropagation()}>
        <div className="modal-bar">
          <div className="modal-title">Send Feedback</div>
          <div className="modal-actions">
            <button className="modal-close" onClick={onClose} disabled={submitting}>
              Close
            </button>
          </div>
        </div>

        <div style={{ padding: 14, display: "grid", gap: 12 }}>
          {err ? <div className="error">{err}</div> : null}

          <div className="model-settings-grid">
            <div className="model-settings-label">Original Model</div>
            <div>{modelId || "—"}</div>

            <div className="model-settings-label">Label</div>
            <div>
              <select
                value={label}
                onChange={(e) =>
                  setLabel(e.target.value as "positive" | "negative" | "neutral" | "")
                }
              >
                <option value="">(no change)</option>
                <option value="positive">positive</option>
                <option value="neutral">neutral</option>
                <option value="negative">negative</option>
              </select>
            </div>

            <div className="model-settings-label">Translation</div>
            <div>
              <textarea
                value={translation}
                onChange={(e) => setTranslation(e.target.value)}
                rows={3}
                style={{ width: "100%" }}
                placeholder="Optional corrected translation"
              />
            </div>

            <div className="model-settings-label">Analysis JSON</div>
            <div>
              <textarea
                value={analysisStr}
                onChange={(e) => setAnalysisStr(e.target.value)}
                rows={6}
                style={{ width: "100%", fontFamily: "monospace" }}
                placeholder='Optional analysis JSON, e.g. {"entities":["Cicero"],"sentiment":{"positive":0.2,"negative":0.7,"neutral":0.1}}'
              />
            </div>

            <div className="model-settings-label">Notes</div>
            <div>
              <textarea
                value={notes}
                onChange={(e) => setNotes(e.target.value)}
                rows={2}
                style={{ width: "100%" }}
                placeholder="Optional notes for this feedback"
              />
            </div>

            <div className="model-settings-label">Tags</div>
            <div>
              <input
                type="text"
                value={tagsStr}
                onChange={(e) => setTagsStr(e.target.value)}
                placeholder="comma,separated,tags"
                style={{ width: "100%" }}
              />
            </div>
          </div>

          <div style={{ display: "flex", gap: 10, justifyContent: "flex-end" }}>
            <button className="tool-cta" onClick={handleSubmit} disabled={submitting}>
              {submitting ? "Submitting…" : "Submit Feedback"}
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
