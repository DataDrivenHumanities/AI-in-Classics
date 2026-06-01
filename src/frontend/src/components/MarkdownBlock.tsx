"use client";

import React from "react";

type Props = {
    content: string;
    className?: string;
};

type InlineNode =
    | {t: "text"; v: string}
    | {t: "br"}
    | {t: "code"; v: string}
    | {t: "strong"; c: InlineNode[]}
    | {t: "em"; c: InlineNode[]}
    | {t: "link"; href: string; c: InlineNode[]};

type BlockNode =
    | {t: "h"; level: 1 | 2 | 3; c: InlineNode[]}
    | {t: "p"; c: InlineNode[]}
    | {t: "ul"; items: InlineNode[][]}
    | {t: "ol"; items: InlineNode[][]}
    | {t: "quote"; c: InlineNode[]}
    | {t: "hr"}
    | {t: "codeblock"; lang?: string; v: string};

function parseInline(input: string): InlineNode[] {
    const s = String(input || "");
    const out: InlineNode[] = [];
    let i = 0;

    const pushText = (v: string) => {
        if (!v) return;
        const last = out[out.length - 1];
        if (last && last.t === "text") last.v += v;
        else out.push({t: "text", v});
    };

    const findNext = (needle: string, from: number) => s.indexOf(needle, from);

    while (i < s.length) {
        const ch = s[i];
        if (ch === "\n") {
            out.push({t: "br"});
            i += 1;
            continue;
        }

        if (s.startsWith("**", i)) {
            const j = findNext("**", i + 2);
            if (j !== -1) {
                const inner = s.slice(i + 2, j);
                out.push({t: "strong", c: parseInline(inner)});
                i = j + 2;
                continue;
            }
        }

        if (ch === "*") {
            const j = findNext("*", i + 1);
            // Avoid treating list markers like "* " as italics.
            const nextCh = s[i + 1] || "";
            if (j !== -1 && nextCh && nextCh !== " ") {
                const inner = s.slice(i + 1, j);
                out.push({t: "em", c: parseInline(inner)});
                i = j + 1;
                continue;
            }
        }

        if (ch === "`") {
            const j = findNext("`", i + 1);
            if (j !== -1) {
                out.push({t: "code", v: s.slice(i + 1, j)});
                i = j + 1;
                continue;
            }
        }

        if (s.startsWith("[", i)) {
            const endText = findNext("]", i + 1);
            const hasParen = endText !== -1 && s[endText + 1] === "(";
            if (hasParen) {
                const endHref = findNext(")", endText + 2);
                if (endHref !== -1) {
                    const label = s.slice(i + 1, endText);
                    const href = s.slice(endText + 2, endHref);
                    out.push({t: "link", href, c: parseInline(label)});
                    i = endHref + 1;
                    continue;
                }
            }
        }

        // Plain text: consume until next special character.
        let j = i + 1;
        while (j < s.length) {
            const c = s[j];
            if (c === "\n" || c === "`" || c === "*") break;
            if (s.startsWith("**", j) || s.startsWith("[", j)) break;
            j += 1;
        }
        pushText(s.slice(i, j));
        i = j;
    }

    return out;
}

function parseBlocks(input: string): BlockNode[] {
    const lines = String(input || "").replace(/\r\n?/g, "\n").split("\n");
    const blocks: BlockNode[] = [];
    let i = 0;

    const isBlank = (ln: string) => !ln.trim();

    while (i < lines.length) {
        const line = lines[i] ?? "";

        if (isBlank(line)) {
            i += 1;
            continue;
        }

        // Fenced code block
        const fence = line.match(/^```(\w+)?\s*$/);
        if (fence) {
            const lang = fence[1] || undefined;
            i += 1;
            const body: string[] = [];
            while (i < lines.length && !(lines[i] ?? "").startsWith("```")) {
                body.push(lines[i] ?? "");
                i += 1;
            }
            if (i < lines.length && (lines[i] ?? "").startsWith("```")) i += 1;
            blocks.push({t: "codeblock", lang, v: body.join("\n")});
            continue;
        }

        // Horizontal rule
        if (/^\s*---\s*$/.test(line)) {
            blocks.push({t: "hr"});
            i += 1;
            continue;
        }

        // Heading
        const h = line.match(/^(#{1,6})\s+(.*)$/);
        if (h) {
            const levelRaw = h[1].length;
            const level: 1 | 2 | 3 = levelRaw <= 1 ? 1 : levelRaw === 2 ? 2 : 3;
            blocks.push({t: "h", level, c: parseInline(h[2] || "")});
            i += 1;
            continue;
        }

        // Blockquote (single block; keep hard breaks)
        if (/^\s*>\s?/.test(line)) {
            const q: string[] = [];
            while (i < lines.length && /^\s*>\s?/.test(lines[i] ?? "")) {
                q.push(String(lines[i] ?? "").replace(/^\s*>\s?/, ""));
                i += 1;
            }
            blocks.push({t: "quote", c: parseInline(q.join("\n"))});
            continue;
        }

        // Unordered list
        if (/^\s*[-*]\s+/.test(line)) {
            const items: InlineNode[][] = [];
            while (i < lines.length && /^\s*[-*]\s+/.test(lines[i] ?? "")) {
                const itemText = String(lines[i] ?? "").replace(/^\s*[-*]\s+/, "");
                items.push(parseInline(itemText));
                i += 1;
            }
            blocks.push({t: "ul", items});
            continue;
        }

        // Ordered list
        if (/^\s*\d+\.\s+/.test(line)) {
            const items: InlineNode[][] = [];
            while (i < lines.length && /^\s*\d+\.\s+/.test(lines[i] ?? "")) {
                const itemText = String(lines[i] ?? "").replace(/^\s*\d+\.\s+/, "");
                items.push(parseInline(itemText));
                i += 1;
            }
            blocks.push({t: "ol", items});
            continue;
        }

        // Paragraph: collect until blank or block boundary
        const p: string[] = [];
        while (i < lines.length) {
            const ln = lines[i] ?? "";
            if (isBlank(ln)) break;
            if (/^```/.test(ln)) break;
            if (/^\s*---\s*$/.test(ln)) break;
            if (/^(#{1,6})\s+/.test(ln)) break;
            if (/^\s*>\s?/.test(ln)) break;
            if (/^\s*[-*]\s+/.test(ln)) break;
            if (/^\s*\d+\.\s+/.test(ln)) break;
            p.push(ln);
            i += 1;
        }
        blocks.push({t: "p", c: parseInline(p.join("\n"))});
    }

    return blocks;
}

function renderInline(nodes: InlineNode[], keyPrefix: string): React.ReactNode[] {
    return nodes.map((n, idx) => {
        const k = `${keyPrefix}-${idx}`;
        if (n.t === "text") return <React.Fragment key={k}>{n.v}</React.Fragment>;
        if (n.t === "br") return <br key={k} />;
        if (n.t === "code") return <code key={k}>{n.v}</code>;
        if (n.t === "strong") return <strong key={k}>{renderInline(n.c, k)}</strong>;
        if (n.t === "em") return <em key={k}>{renderInline(n.c, k)}</em>;
        if (n.t === "link") {
            const href = n.href || "#";
            return (
                <a key={k} href={href} target="_blank" rel="noreferrer noopener">
                    {renderInline(n.c, k)}
                </a>
            );
        }
        return null;
    });
}

export default function MarkdownBlock({content, className}: Props) {
    const blocks = parseBlocks(String(content || ""));
    return (
        <div className={className ? `markdown ${className}` : "markdown"}>
            {blocks.map((b, idx) => {
                const k = `b-${idx}`;
                if (b.t === "hr") return <hr key={k} />;
                if (b.t === "codeblock") {
                    return (
                        <pre key={k} className="md-pre">
                            <code>{b.v}</code>
                        </pre>
                    );
                }
                if (b.t === "quote") return <blockquote key={k}>{renderInline(b.c, k)}</blockquote>;
                if (b.t === "ul") {
                    return (
                        <ul key={k}>
                            {b.items.map((it, j) => (
                                <li key={`${k}-i-${j}`}>{renderInline(it, `${k}-i-${j}`)}</li>
                            ))}
                        </ul>
                    );
                }
                if (b.t === "ol") {
                    return (
                        <ol key={k}>
                            {b.items.map((it, j) => (
                                <li key={`${k}-i-${j}`}>{renderInline(it, `${k}-i-${j}`)}</li>
                            ))}
                        </ol>
                    );
                }
                if (b.t === "h") {
                    if (b.level === 1) return <h1 key={k}>{renderInline(b.c, k)}</h1>;
                    if (b.level === 2) return <h2 key={k}>{renderInline(b.c, k)}</h2>;
                    return <h3 key={k}>{renderInline(b.c, k)}</h3>;
                }
                return <p key={k}>{renderInline(b.c, k)}</p>;
            })}
        </div>
    );
}
