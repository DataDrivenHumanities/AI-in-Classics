"use client";

import React, {useEffect, useLayoutEffect, useMemo, useRef, useState} from "react";

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

function splitNumberedDefinition(definition: string): string[] {
    const s = String(definition || "").trim();
    if (!s) return [];
    const hasNumbered = /\b\d+\.\s*/.test(s);
    if (!hasNumbered) return [s];

    // Prefer splitting on `;` boundaries when they precede a numbered sense.
    const semiParts = s
        .split(/;\s*(?=\d+\.\s*)/g)
        .map((p) => p.trim())
        .filter(Boolean);
    if (semiParts.length >= 2) return semiParts;

    // Fallback: slice by numbered markers.
    const matches = Array.from(s.matchAll(/\b\d+\.\s*/g));
    if (matches.length <= 1) return [s];
    const out: string[] = [];
    for (let i = 0; i < matches.length; i++) {
        const start = matches[i].index ?? 0;
        const end = (i + 1) < matches.length ? (matches[i + 1].index ?? s.length) : s.length;
        const chunk = s.slice(start, end).trim().replace(/;+\s*$/, "");
        if (chunk) out.push(chunk);
    }
    return out.length ? out : [s];
}

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
    const popupRef = useRef<HTMLDivElement | null>(null);

    const [popup, setPopup] = useState<null | {
        hitKey: string;
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
        definitions: string[];
    }>(null);

    useLayoutEffect(() => {
        const root = rootRef.current;
        const pop = popupRef.current;
        if (!popup || !root || !pop) return;

        const pad = 10;
        const rootW = root.clientWidth || 0;
        const popW = pop.offsetWidth || 0;
        if (rootW <= 0 || popW <= 0) return;

        // Keep popup fully within the visible overlay bounds horizontally.
        // (We use translateX(-50%), so `x` is the popup center.)
        const maxCenterHalf = Math.max(pad, (rootW - 2 * pad) / 2);
        const half = Math.min(popW / 2, maxCenterHalf);
        const minX = pad + half;
        const maxX = rootW - pad - half;
        const newX = clamp(popup.x, minX, maxX);
        if (Math.abs(newX - popup.x) > 0.5) {
            setPopup((prev) => (prev ? {...prev, x: newX} : prev));
        }
    }, [popup]);

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
            hasDefinition: boolean;
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
                    hasDefinition,
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

    function openPopup(hitKey: string, lemma: string, score: number, anchor: HTMLElement) {
        // Toggle off when clicking the same highlighted word again.
        if (popup?.hitKey && popup.hitKey === hitKey) {
            setPopup(null);
            return;
        }

        const det = lemmaDetails?.[lemma] || {};
        const rect = anchor.getBoundingClientRect();
        const root = rootRef.current;
        const rootRect = root?.getBoundingClientRect();

        const pos = String(det.scraped_pos_bucket ?? det.pos_bucket ?? "");
        const prov = String(det.provenance ?? "");
        const pol = det.has_polarity ?? "";
        const cnt = det.count ?? "";
        const pm = det.pos_match;
        const pm_s = pm == null ? "" : pm ? "yes" : "no";
        const definitions = splitNumberedDefinition(det.definition || "");

        const pad = 10;
        let x = rect.left + rect.width / 2;
        let y = rect.bottom + 8;

        // Prefer anchoring inside the overlay container so scrolling keeps the popup pinned to the word.
        if (root && rootRect) {
            x = x - rootRect.left;
            y = y - rootRect.top;

            // Best-effort: if we're near the bottom edge of the scroll viewport, open above the word.
            // (The popup is scroll-pinned regardless; this just improves first render.)
            const scroller = root.closest(".text-view") as HTMLElement | null;
            const scRect = scroller?.getBoundingClientRect();
            if (scRect) {
                const approxPopupH = 240;
                const belowBottom = rect.bottom + approxPopupH > scRect.bottom;
                if (belowBottom) {
                    y = (rect.top - rootRect.top) - 10; // above the word
                }
            }

            x = clamp(x, pad, rootRect.width - pad);
            y = Math.max(pad, y);
        } else {
            // Fallback (should be rare): keep within viewport.
            x = clamp(x, pad, window.innerWidth - pad);
            y = clamp(y, pad, window.innerHeight - pad);
        }

        const scoreValue = Number.isFinite(score) && score !== 0 ? score : null;
        const scoreText = scoreValue == null ? "" : `${scoreValue >= 0 ? "+" : ""}${scoreValue.toFixed(2)}`;

        setPopup({
            hitKey,
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
            definitions,
        });
    }

    return (
        <div className="latin-overlay-wrap" ref={rootRef}>
            <div className="latin-overlay" aria-label="Latin text with lexicon highlights">
                {parts.map((p) => {
                    if (p.kind === "plain") return <React.Fragment key={p.k}>{p.text}</React.Fragment>;
                    const bg = sentimentBg(p.score);
                    const isNeutral = p.isNeutral;
                    const hasDef = p.hasDefinition;
                    return (
                        <span
                            key={p.k}
                            className={`lex-chip ${isNeutral ? "lex-chip-neutral" : ""} ${hasDef ? "lex-has-def" : ""}`}
                            role="button"
                            tabIndex={0}
                            style={{background: bg, borderColor: isNeutral ? 'transparent' : bg}}
                            onClick={(e) => openPopup(p.k, p.lemma, p.score, e.currentTarget)}
                            onKeyDown={(e) => {
                                if (e.key === "Enter" || e.key === " ") {
                                    e.preventDefault();
                                    openPopup(p.k, p.lemma, p.score, e.currentTarget as any);
                                }
                            }}
                            title={
                                `${p.lemma}` +
                                `${p.score !== 0 ? ` ${p.score >= 0 ? "+" : ""}${p.score.toFixed(2)}` : ""}` +
                                `${hasDef ? " (click for definition)" : ""}`
                            }
                        >
                            {p.text}
                        </span>
                    );
                })}
            </div>

            {popup && (
                <div ref={popupRef} className="lex-popup" style={{left: popup.x, top: popup.y}}>
                    <div className="lex-popup-title">{popup.lemma}</div>
                    {popup.definitions.length > 0 && (
                        <div style={{marginBottom: "6px"}}>
                            {popup.definitions.map((d, i) => (
                                <div key={`${popup.lemma}-def-${i}`} className="lex-popup-row">
                                    <span>{d}</span>
                                </div>
                            ))}
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
