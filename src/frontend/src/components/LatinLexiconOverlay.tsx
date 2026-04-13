"use client";

import React, {useEffect, useMemo, useRef, useState} from "react";

type LexSpan = {
    start: number;
    end: number;
    surface?: string;
    lemma_key?: string | null;
    polarity_score?: number | null;
    pos_bucket?: string | null;
    provenance?: string | null;
    has_polarity?: any;
    pos_match?: any;
};

type LemmaDetails = Record<string, any>;

function sentimentBg(score: number) {
    const s = Math.max(-1, Math.min(1, Number(score) || 0));
    if (s === 0 && score === 0) return 'transparent';
    const t = Math.min(1, Math.abs(s));
    const [r, g, b] = s < 0 ? [239, 68, 68] : [20, 184, 166];
    const a = 0.14 + 0.28 * t;
    return `rgba(${r},${g},${b},${a.toFixed(3)})`;
}

function clamp(n: number, lo: number, hi: number) {
    return Math.max(lo, Math.min(hi, n));
}

export default function LatinLexiconOverlay(props: {
    text: string;
    spans: LexSpan[];
    lemmaDetails?: LemmaDetails;
}) {
    const {text, spans, lemmaDetails = {}} = props;
    const rootRef = useRef<HTMLDivElement | null>(null);

    const [popup, setPopup] = useState<null | {
        lemma: string;
        scoreText: string;
        scoreValue: number | null;
        label: string;
        pos: string;
        count: string;
        source: string;
        posMatch: string;
        x: number;
        y: number;
        definition?: string;
    }>(null);

    const parts = useMemo(() => {
        if (!text) return [];
        if (!Array.isArray(spans) || spans.length === 0) {
            return [{k: "t", text, kind: "plain"} as const];
        }

        const out: Array<
            | {k: string; kind: "plain"; text: string}
            | {
            k: string;
            kind: "hit";
            text: string;
            lemma: string;
            score: number;
            isNeutral: boolean;
        }
        > = [];

        let last = 0;
        for (let i = 0; i < spans.length; i++) {
            const sp = spans[i] || ({} as any);
            const start = clamp(Number(sp.start) || 0, 0, text.length);
            const end = clamp(Number(sp.end) || 0, 0, text.length);
            if (end < start) continue;
            if (start > last) out.push({k: `p-${i}-${last}`, kind: "plain", text: text.slice(last, start)});

            const surface = text.slice(start, end);
            const lemma = (sp.lemma_key ?? null) ? String(sp.lemma_key) : "";
            const score = sp.polarity_score != null ? Number(sp.polarity_score) : 0;
            const det = lemma ? (lemmaDetails?.[lemma] || {}) : {};
            const hasDefinition = !!det.definition;

            if (lemma && ((Number.isFinite(score) && score !== 0) || hasDefinition)) {
                out.push({
                    k: `h-${i}-${start}`,
                    kind: "hit",
                    text: surface,
                    lemma,
                    score: Number.isFinite(score) ? score : 0,
                    isNeutral: !(Number.isFinite(score) && score !== 0) && hasDefinition,
                });
            } else {
                out.push({k: `s-${i}-${start}`, kind: "plain", text: surface});
            }
            last = end;
        }
        if (last < text.length) out.push({k: `tail-${last}`, kind: "plain", text: text.slice(last)});
        return out;
    }, [text, spans, lemmaDetails]);

    useEffect(() => {
        function onKeyDown(e: KeyboardEvent) {
            if (e.key === "Escape") setPopup(null);
        }
        function onDocDown(e: MouseEvent) {
            const root = rootRef.current;
            if (!root) return;
            if (!root.contains(e.target as any)) setPopup(null);
        }
        document.addEventListener("keydown", onKeyDown);
        document.addEventListener("mousedown", onDocDown);
        return () => {
            document.removeEventListener("keydown", onKeyDown);
            document.removeEventListener("mousedown", onDocDown);
        };
    }, []);

    function openPopup(lemma: string, score: number, anchor: HTMLElement) {
        const det = lemmaDetails?.[lemma] || {};
        const rect = anchor.getBoundingClientRect();

        const pos = String(det.scraped_pos_bucket ?? det.pos_bucket ?? "");
        const prov = String(det.provenance ?? "");
        const pol = det.has_polarity ?? "";
        const cnt = det.count ?? "";
        const pm = det.pos_match;
        const pm_s = pm == null ? "" : pm ? "yes" : "no";

        const pad = 10;
        const x = clamp(rect.left + rect.width / 2, pad, window.innerWidth - pad);
        const y = clamp(rect.bottom + 8, pad, window.innerHeight - pad);

        const scoreValue = Number.isFinite(score) && score !== 0 ? score : null;
        const scoreText = scoreValue == null ? "" : `${scoreValue >= 0 ? "+" : ""}${scoreValue.toFixed(2)}`;

        setPopup({
            lemma,
            scoreText,
            scoreValue,
            label: String(pol),
            pos,
            count: String(cnt),
            source: prov,
            posMatch: pm_s,
            x,
            y,
            definition: det.definition || "",
        });
    }

    return (
        <div className="latin-overlay-wrap" ref={rootRef}>
            <div className="latin-overlay" aria-label="Latin text with lexicon highlights">
                {parts.map((p) => {
                    if (p.kind === "plain") return <React.Fragment key={p.k}>{p.text}</React.Fragment>;
                    const bg = sentimentBg(p.score);
                    const isNeutral = p.isNeutral;
                    return (
                        <span
                            key={p.k}
                            className={`lex-chip ${isNeutral ? "lex-chip-neutral" : ""}`}
                            role="button"
                            tabIndex={0}
                            style={{background: bg, borderColor: isNeutral ? 'transparent' : bg}}
                            onClick={(e) => openPopup(p.lemma, p.score, e.currentTarget)}
                            onKeyDown={(e) => {
                                if (e.key === "Enter" || e.key === " ") {
                                    e.preventDefault();
                                    openPopup(p.lemma, p.score, e.currentTarget as any);
                                }
                            }}
                            title={`${p.lemma}${p.score !== 0 ? ` ${p.score >= 0 ? "+" : ""}${p.score.toFixed(2)}` : ""}`}
                        >
                            {p.text}
                        </span>
                    );
                })}
            </div>

            {popup && (
                <div className="lex-popup" style={{left: popup.x, top: popup.y}}>
                    <div className="lex-popup-title">{popup.lemma}</div>
                    {popup.definition && (
                        <div className="lex-popup-row" style={{marginBottom: "6px"}}>
                            <span>{popup.definition}</span>
                        </div>
                    )}
                    {popup.scoreValue != null && (
                        <div className="lex-popup-row">
                            <span className="k">score</span> <span>{popup.scoreText}</span>
                        </div>
                    )}
                    {popup.scoreValue != null && popup.label && (
                        <div className="lex-popup-row">
                            <span className="k">label</span> <span>{popup.label}</span>
                        </div>
                    )}
                    <div className="lex-popup-row"><span className="k">pos</span> <span>{popup.pos || "—"}</span></div>
                    <div className="lex-popup-row"><span className="k">count</span> <span>{popup.count || "—"}</span></div>
                    {popup.source && (
                        <div className="lex-popup-row">
                            <span className="k">source</span> <span>{popup.source}</span>
                        </div>
                    )}
                    {popup.posMatch && (
                        <div className="lex-popup-row">
                            <span className="k">pos match</span> <span>{popup.posMatch}</span>
                        </div>
                    )}
                </div>
            )}
        </div>
    );
}
