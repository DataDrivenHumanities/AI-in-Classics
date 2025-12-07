"use client";

import { useEffect, useState } from "react";

export type ModelOptions = {
  temperature: number;
  top_p: number;
  repeat_penalty: number;
  num_predict: number;
  stop: string[];
  raw: boolean;
  format: "json" | "text";
};

type Preset = {
  name: string;
  temperature?: number;
  top_p?: number;
  repeat_penalty?: number;
  num_predict?: number;
  stop?: string[];
  raw?: boolean;
  format?: "json" | "text";
};

type Props = {
  open: boolean;
  onClose: () => void;
  initial: (ModelOptions & { name?: string }) | undefined;
  onSave: (opts: ModelOptions & { name?: string }) => void;
  onApplyPreset?: (name: string, opts: ModelOptions) => void;
};

const API_BASE = process.env.NEXT_PUBLIC_API_BASE || "http://localhost:5050/api";

export default function ModelSettingsModal({
  open,
  onClose,
  initial,
  onSave,
  onApplyPreset,
}: Props) {
  const [working, setWorking] = useState<ModelOptions>({
    temperature: 0.0,
    top_p: 0.9,
    repeat_penalty: 1.0,
    num_predict: 1024,
    stop: [],
    raw: true,
    format: "json",
  });
  const [name, setName] = useState<string>("Default");
  const [presets, setPresets] = useState<Preset[]>([]);
  const [selectedPreset, setSelectedPreset] = useState<string>("");

  useEffect(() => {
    if (!open) return;
    fetch(`${API_BASE}/presets`)
      .then((r) => r.json())
      .then((data) => {
        const list = Array.isArray(data?.presets) ? data.presets : [];
        setPresets(list);
        if (list.length > 0 && !selectedPreset) {
          setSelectedPreset(list[0].name);
        }
      })
      .catch(() => {});
  }, [open]); // eslint-disable-line

  useEffect(() => {
    if (!open) return;
    if (initial) {
      setWorking({
        temperature: initial.temperature,
        top_p: initial.top_p,
        repeat_penalty: initial.repeat_penalty,
        num_predict: initial.num_predict,
        stop: initial.stop,
        raw: initial.raw,
        format: initial.format,
      });
      setName(initial.name || "Default");
    }
  }, [open, initial]);

  function applySelectedPreset() {
    const p = presets.find((x) => x.name === selectedPreset);
    if (!p) return;
    const merged: ModelOptions = {
      temperature: p.temperature ?? working.temperature,
      top_p: p.top_p ?? working.top_p,
      repeat_penalty: p.repeat_penalty ?? working.repeat_penalty,
      num_predict: p.num_predict ?? working.num_predict,
      stop: p.stop ?? working.stop,
      raw: p.raw ?? working.raw,
      format: p.format ?? working.format,
    };
    setWorking(merged);
    setName(p.name);
    if (onApplyPreset) onApplyPreset(p.name, merged);
  }

  function save() {
    onSave({ ...working, name });
  }

  if (!open) return null;

  return (
    <div className="modal" onClick={onClose}>
      <div
        className="modal-inner modal-inner--small"
        onClick={(e) => e.stopPropagation()}
        role="dialog"
        aria-modal="true"
        aria-labelledby="model-settings-title"
      >
        <div className="modal-bar">
          <div className="modal-title" id="model-settings-title">
            Model Settings
          </div>
          <div className="modal-actions">
            <button className="modal-close" onClick={onClose}>
              Close
            </button>
          </div>
        </div>

        <div className="settings-body">
          <div className="settings-row">
            <div className="field">
              <label>Preset</label>
              <div className="preset-row">
                <select
                  value={selectedPreset}
                  onChange={(e) => setSelectedPreset(e.target.value)}
                >
                  {presets.map((p) => (
                    <option key={p.name} value={p.name}>
                      {p.name}
                    </option>
                  ))}
                </select>
                <button className="tool-cta" onClick={applySelectedPreset}>
                  Apply
                </button>
              </div>
            </div>

            <div className="field">
              <label>Preset Name</label>
              <input
                type="text"
                value={name}
                onChange={(e) => setName(e.target.value)}
                placeholder="e.g., Deterministic JSON"
              />
            </div>
          </div>

          <div className="settings-grid">
            <div className="field">
              <label>Format</label>
              <select
                value={working.format}
                onChange={(e) =>
                  setWorking({ ...working, format: e.target.value as "json" | "text" })
                }
              >
                <option value="json">json</option>
                <option value="text">text</option>
              </select>
            </div>

            <div className="field">
              <label>Bypass Modelfile (raw)</label>
              <select
                value={String(working.raw)}
                onChange={(e) =>
                  setWorking({ ...working, raw: e.target.value === "true" })
                }
              >
                <option value="true">true</option>
                <option value="false">false</option>
              </select>
            </div>

            <div className="field">
              <label>Temperature</label>
              <input
                type="number"
                step="0.01"
                value={working.temperature}
                onChange={(e) =>
                  setWorking({ ...working, temperature: Number(e.target.value) })
                }
              />
            </div>

            <div className="field">
              <label>Top-p</label>
              <input
                type="number"
                step="0.01"
                value={working.top_p}
                onChange={(e) =>
                  setWorking({ ...working, top_p: Number(e.target.value) })
                }
              />
            </div>

            <div className="field">
              <label>Repeat Penalty</label>
              <input
                type="number"
                step="0.01"
                value={working.repeat_penalty}
                onChange={(e) =>
                  setWorking({ ...working, repeat_penalty: Number(e.target.value) })
                }
              />
            </div>

            <div className="field">
              <label>Max Tokens</label>
              <input
                type="number"
                value={working.num_predict}
                onChange={(e) =>
                  setWorking({ ...working, num_predict: Number(e.target.value) })
                }
              />
            </div>

            <div className="field field--full">
              <label>Stop Tokens (comma-separated)</label>
              <input
                type="text"
                value={working.stop.join(",")}
                onChange={(e) =>
                  setWorking({
                    ...working,
                    stop: e.target.value
                      .split(",")
                      .map((s) => s.trim())
                      .filter((s) => s.length > 0),
                  })
                }
                placeholder="e.g., <|eot_id|>, </s>"
              />
            </div>
          </div>

          <div className="settings-actions">
            <button className="tool-cta" onClick={save}>
              Save
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
