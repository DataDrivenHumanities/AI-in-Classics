from __future__ import annotations
import base64
import html as _html
import mimetypes
from pathlib import Path
import textwrap
from urllib.parse import quote as _urlquote
import streamlit as st

# ==============================
# Page / Theme
# ==============================


def set_page(
    layout: str = "wide",
    title: str = "App",
    icon: str = "✨",
    sidebar: str = "expanded",
):
    """Configure base page layout and sidebar state."""
    st.set_page_config(
        page_title=title,
        page_icon=icon,
        layout=layout,  # "wide" or "centered"
        initial_sidebar_state="expanded" if sidebar == "expanded" else "collapsed",
    )


def inject_css(raw_css: str):
    """Inject arbitrary CSS (dedented for readability)."""
    st.markdown(f"<style>{textwrap.dedent(raw_css)}</style>", unsafe_allow_html=True)


def _apply_shell_css(
    bg: str,
    text: str,
    surface: str,
    primary: str,
    radius: str,
    compact: bool,
    centered: bool,
    max_width_px: int,
):
    """
    Internal: keeps selectors stable and light.

    """
    padding_y = "0.75rem" if compact else "1.25rem"
    padding_x = "0.9rem" if compact else "1.2rem"
    control_height = "2.1rem" if compact else "2.5rem"
    df_radius = radius

    main_width_css = ""
    if centered:
        main_width_css = f"""
        [data-testid="stAppViewContainer"] > .main .block-container {{
            max-width: {max_width_px}px;
            margin: 0 auto;
        }}
        """

    css = f"""
    /* App background & body text */
    .stApp {{
        background: {bg} !important;
        color: {text} !important;
    }}

    /* Sidebar background */
    section[data-testid="stSidebar"] > div:first-child {{
        background: {surface} !important;
        color: {text} !important;
    }}

    /* Basic typography tweaks */
    .stMarkdown, .stText, .stHeader, p, li {{
        line-height: 1.45;
    }}

    /* Buttons */
    .stButton > button {{
        background: {primary} !important;
        color: white !important;
        border: none !important;
        border-radius: {radius} !important;
        padding: {padding_y} {padding_x} !important;
        font-weight: 600 !important;
        transition: transform .06s ease, opacity .15s ease;
    }}
    .stButton > button:hover {{ transform: translateY(-1px); opacity:.95; }}

    /* Common inputs (robust selectors) */
    input[type="text"], input[type="number"], input[type="search"], textarea, select {{
        background: {surface} !important;
        color: {text} !important;
        border-radius: {radius} !important;
        border: 1px solid rgba(255,255,255,.10) !important;
        height: {control_height};
    }}

    /* Streamlit wraps inputs inside divs; soften those too */
    .stTextInput, .stNumberInput, .stSelectbox, .stDateInput, .stTextArea {{
        border-radius: {radius} !important;
    }}

    /* Dataframe / Table / Metric rounding */
    .stDataFrame, .stTable, .stMetric {{
        border-radius: {df_radius} !important;
        overflow: hidden;
    }}

    /* Tabs: underline active without loud colors */
    .stTabs [aria-selected="true"] {{
        border-bottom: 2px solid {primary} !important;
    }}

    /* Cards */
    .webui-card {{
        background: transparent;
        border: 1px solid rgba(0,0,0,.08);
        border-radius: {radius};
        padding: 0.85rem 1rem;
        box-shadow: none;
        margin-bottom: 0.75rem;
    }}

    /* Callouts */
    .webui-callout {{
        border-radius: {radius};
        padding: 0.85rem 1rem;
        border: 1px solid rgba(255,255,255,.12);
        margin: 0.25rem 0 0.9rem 0;
        background: {surface};
    }}
    .webui-callout-title {{
        font-weight: 700;
        margin-bottom: 0.35rem;
    }}

    /* Headers */
    .webui-h1 {{ font-size: 1.6rem; font-weight: 700; margin: .2rem 0 .6rem; }}
    .webui-h2 {{ font-size: 1.1rem; font-weight: 600; opacity: .9; margin: 0 0 .5rem; }}

    /* Dividers */
    .webui-divider {{
        height: 1px;
        width: 100%;
        background: rgba(255,255,255,.12);
        margin: 1rem 0;
    }}

    {main_width_css}
    """
    inject_css(css)


def base_theme(
    *,
    primary: str = "#7C3AED",
    bg: str = "#0E1117",
    surface: str = "#161A22",
    text: str = "#E6E6E6",
    radius: str = "12px",
    compact: bool = True,
    centered: bool = False,
    max_width_px: int = 1100,
):
    """
    Minimal dark theme. Keeps things readable and consistent.
    Set compact=False for roomier controls.
    Set centered=True to cap width and center main content.
    """
    key = "_WEBUI_BASE_THEME_APPLIED"
    if st.session_state.get(key):
        return
    st.session_state[key] = True

    _apply_shell_css(
        bg=bg,
        text=text,
        surface=surface,
        primary=primary,
        radius=radius,
        compact=compact,
        centered=centered,
        max_width_px=max_width_px,
    )


def use_dark_preset(
    compact: bool = True, centered: bool = False, max_width_px: int = 1100
):
    base_theme(
        primary="#6D28D9",  # muted purple
        bg="#0E1117",
        surface="#141821",
        text="#E5E7EB",
        radius="12px",
        compact=compact,
        centered=centered,
        max_width_px=max_width_px,
    )


def use_light_preset(
    compact: bool = True, centered: bool = False, max_width_px: int = 1100
):
    base_theme(
        primary="#2563EB",  # blue-600
        bg="#F7F7FB",
        surface="#FFFFFF",
        text="#1F2937",
        radius="10px",
        compact=compact,
        centered=centered,
        max_width_px=max_width_px,
    )


# ==============================
# extra Components
# ==============================


def hero_header(title: str, subtitle: str | None = None):
    """
    Centered, large header for top of page.
    """
    html = f"""
    <div style="text-align:center; margin-top:0.5rem; margin-bottom:1.5rem;">
        <h1 style="font-size:2.5rem; font-weight:800; margin-bottom:0.3rem;">
            {title}
        </h1>
        {f'<p style="font-size:1.25rem; font-weight:400; opacity:0.85; margin-top:0;">{subtitle}</p>' if subtitle else ""}
    </div>
    """
    st.markdown(html, unsafe_allow_html=True)


def header(title: str, subtitle: str | None = None):
    st.markdown(f'<div class="webui-h1">{title}</div>', unsafe_allow_html=True)
    if subtitle:
        st.markdown(f'<div class="webui-h2">{subtitle}</div>', unsafe_allow_html=True)


def subheader(text: str):
    st.markdown(f'<div class="webui-h2">{text}</div>', unsafe_allow_html=True)


def card(markdown: str = "", *, title: str | None = None):
    """A simple card with optional title; content can be Markdown."""
    st.markdown('<div class="webui-card">', unsafe_allow_html=True)
    if title:
        st.markdown(f"**{title}**")
    if markdown:
        st.markdown(markdown)
    st.markdown("</div>", unsafe_allow_html=True)


def callout(body: str, *, title: str | None = None, kind: str = "info"):
    """
    Lightweight callout box. kind ∈ {"info","success","warn","danger"} controls the border.
    these are stock colors
    """
    accents = {
        "info": "#60A5FA",
        "success": "#34D399",
        "warn": "#FBBF24",
        "danger": "#F87171",
    }
    color = accents.get(kind, "#60A5FA")
    st.markdown(
        f"""
        <div class="webui-callout" style="border-left: 4px solid {color}">
            {'<div class="webui-callout-title">'+title+'</div>' if title else ''}
            <div>{body}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def row(*ratios):
    """
    Convenience wrapper for columns; default equals widths if none given.
    Example: left, right = row(1, 2)
    """
    ratios = ratios or (1, 1)
    return st.columns(ratios)


def vspace(rem: float = 0.6):
    st.markdown(f"<div style='height:{rem}rem'></div>", unsafe_allow_html=True)


def divider():
    st.markdown('<div class="webui-divider"></div>', unsafe_allow_html=True)


# ==============================
# Latin sentiment overlay
# ==============================


def use_lexicon_overlay_css() -> None:
    key = "_WEBUI_LEXICON_OVERLAY_CSS"
    if st.session_state.get(key):
        return
    st.session_state[key] = True
    inject_css(
        """
        .latin-overlay {
            line-height: 2.05;
            font-size: 1.04rem;
            white-space: pre-wrap;
            word-wrap: break-word;
        }
        a.lex-hit {
            color: inherit !important;
            text-decoration: none !important;
            border-radius: 6px;
            padding: 0.05rem 0.18rem;
            margin: 0 0.02rem;
            transition: outline-color .08s ease;
        }
        a.lex-hit:hover { outline: 2px solid rgba(37, 99, 235, 0.45); }
        a.lex-hit.lex-selected { outline: 2px solid rgba(37, 99, 235, 0.85); }
        """
    )


def _sentiment_bg(score: float) -> str:
    """
    Map a polarity score to a readable background color.
    Negative -> red, positive -> teal/blue, intensity by abs(score).
    """
    try:
        s = float(score)
    except Exception:
        s = 0.0
    s = max(-1.0, min(1.0, s))
    t = min(1.0, abs(s))
    # Base colors (Tailwind-ish): red-500, teal-500
    r, g, b = (239, 68, 68) if s < 0 else (20, 184, 166)
    a = 0.14 + 0.28 * t
    return f"rgba({r},{g},{b},{a:.3f})"


def latin_sentiment_overlay_html(
    text: str,
    spans: list[dict],
    *,
    selected_lemma: str | None = None,
) -> str:
    """
    Render the original text with sentiment-bearing lemmas highlighted.

    `spans` is expected to be in the shape returned by
    `LatinLexiconAnnotator.annotate_spans()`.
    """
    if not text:
        return ""
    if not spans:
        return f'<div class="latin-overlay">{_html.escape(text)}</div>'

    parts: list[str] = []
    last = 0
    for sp in spans:
        try:
            start = int(sp.get("start", 0))
            end = int(sp.get("end", 0))
        except Exception:
            continue
        start = max(0, min(len(text), start))
        end = max(0, min(len(text), end))
        if end < start:
            continue

        parts.append(_html.escape(text[last:start]))
        surface = _html.escape(text[start:end])

        lemma = sp.get("lemma_key")
        score = sp.get("polarity_score")
        try:
            sc = float(score) if score is not None else None
        except Exception:
            sc = None

        if lemma and sc is not None and sc != 0.0:
            lemma_s = str(lemma)
            pos = sp.get("pos_bucket") or ""
            prov = sp.get("provenance") or ""
            title = f"lemma={lemma_s} score={sc:+.2f} pos={pos} src={prov}"
            bg = _sentiment_bg(sc)
            cls = "lex-hit" + (" lex-selected" if selected_lemma == lemma_s else "")
            href = f"?lemma={_urlquote(lemma_s)}"
            parts.append(
                f'<a class="{cls}" href="{href}" title="{_html.escape(title)}" '
                f'style="background:{bg}">{surface}</a>'
            )
        else:
            parts.append(surface)

        last = end
    parts.append(_html.escape(text[last:]))
    return '<div class="latin-overlay">' + "".join(parts) + "</div>"


def latin_sentiment_overlay_popup_html(
    text: str,
    spans: list[dict],
    lemma_details: dict[str, dict] | None = None,
) -> str:
    """
    Render the text as clickable "chips" (rounded rectangles) for sentiment hits.
    Clicking a chip opens a small in-place popup (no query params / no navigation).

    Intended for `streamlit.components.v1.html(...)`.
    """
    lemma_details = lemma_details or {}
    if not text:
        return "<div></div>"

    parts: list[str] = []
    last = 0
    for sp in spans or []:
        try:
            start = int(sp.get("start", 0))
            end = int(sp.get("end", 0))
        except Exception:
            continue
        start = max(0, min(len(text), start))
        end = max(0, min(len(text), end))
        if end < start:
            continue

        parts.append(_html.escape(text[last:start]))
        surface = _html.escape(text[start:end])

        lemma = sp.get("lemma_key")
        score = sp.get("polarity_score")
        try:
            sc = float(score) if score is not None else None
        except Exception:
            sc = None

        if lemma and sc is not None and sc != 0.0:
            lemma_s = str(lemma)
            det = lemma_details.get(lemma_s) or {}
            pos = det.get("scraped_pos_bucket") or sp.get("pos_bucket") or ""
            prov = det.get("provenance") or sp.get("provenance") or ""
            pol = det.get("has_polarity") or sp.get("has_polarity") or ""
            cnt = det.get("count") or ""
            pm = det.get("pos_match")
            pm_s = "" if pm is None else ("yes" if pm else "no")

            bg = _sentiment_bg(sc)
            parts.append(
                "<span "
                'class="lex-chip" role="button" tabindex="0" '
                f'data-lemma="{_html.escape(lemma_s)}" '
                f'data-score="{sc:+.2f}" '
                f'data-label="{_html.escape(str(pol))}" '
                f'data-pos="{_html.escape(str(pos))}" '
                f'data-source="{_html.escape(str(prov))}" '
                f'data-count="{_html.escape(str(cnt))}" '
                f'data-posmatch="{_html.escape(str(pm_s))}" '
                f'style="background:{bg}; border-color:{bg};"'
                f">{surface}</span>"
            )
        else:
            parts.append(surface)

        last = end
    parts.append(_html.escape(text[last:]))

    body = "".join(parts)

    # Inline HTML with minimal CSS + JS (runs inside the component iframe).
    return f"""
    <div class="latin-overlay-wrap">
      <div id="latinText" class="latin-overlay">{body}</div>
      <div id="lexPopup" class="lex-popup" style="display:none;">
        <div class="lex-popup-title" id="lexTitle"></div>
        <div class="lex-popup-row"><span class="k">score</span> <span id="lexScore"></span></div>
        <div class="lex-popup-row"><span class="k">label</span> <span id="lexLabel"></span></div>
        <div class="lex-popup-row"><span class="k">pos</span> <span id="lexPos"></span></div>
        <div class="lex-popup-row"><span class="k">count</span> <span id="lexCount"></span></div>
        <div class="lex-popup-row"><span class="k">source</span> <span id="lexSource"></span></div>
        <div class="lex-popup-row"><span class="k">pos match</span> <span id="lexPosMatch"></span></div>
      </div>
    </div>

    <style>
      :root {{
        --chip-radius: 10px;
        --chip-pad-y: 2px;
        --chip-pad-x: 8px;
        --popup-bg: rgba(17, 24, 39, 0.96);
        --popup-fg: #F9FAFB;
        --popup-muted: rgba(249,250,251,0.75);
        --popup-border: rgba(255,255,255,0.16);
      }}

      body {{ margin: 0; padding: 0; }}

      .latin-overlay-wrap {{
        font-family: ui-sans-serif, system-ui, -apple-system, Segoe UI, Roboto, Helvetica, Arial, "Apple Color Emoji", "Segoe UI Emoji";
        color: inherit;
      }}

      .latin-overlay {{
        line-height: 2.15;
        font-size: 1.05rem;
        white-space: pre-wrap;
        word-wrap: break-word;
        padding: 0.25rem 0.1rem;
      }}

      .lex-chip {{
        display: inline-block;
        border: 1px solid transparent;
        border-radius: var(--chip-radius);
        padding: var(--chip-pad-y) var(--chip-pad-x);
        margin: 0 2px;
        cursor: pointer;
        user-select: none;
        box-shadow: 0 0 0 0 rgba(0,0,0,0);
        transition: transform .05s ease, box-shadow .12s ease, outline-color .12s ease;
      }}
      .lex-chip:hover {{
        transform: translateY(-1px);
        box-shadow: 0 6px 20px rgba(0,0,0,0.08);
        outline: 2px solid rgba(37, 99, 235, 0.40);
        outline-offset: 2px;
      }}
      .lex-chip:focus {{
        outline: 2px solid rgba(37, 99, 235, 0.55);
        outline-offset: 2px;
      }}

      .lex-popup {{
        position: fixed;
        z-index: 9999;
        min-width: 220px;
        max-width: 320px;
        padding: 10px 12px;
        border-radius: 12px;
        background: var(--popup-bg);
        color: var(--popup-fg);
        border: 1px solid var(--popup-border);
        box-shadow: 0 16px 40px rgba(0,0,0,0.22);
        backdrop-filter: blur(8px);
      }}
      .lex-popup-title {{
        font-weight: 700;
        margin-bottom: 6px;
      }}
      .lex-popup-row {{
        display: flex;
        justify-content: space-between;
        gap: 10px;
        font-size: 0.92rem;
        padding: 2px 0;
      }}
      .lex-popup-row .k {{
        color: var(--popup-muted);
        white-space: nowrap;
      }}
    </style>

    <script>
      (function () {{
        const popup = document.getElementById('lexPopup');
        const titleEl = document.getElementById('lexTitle');
        const scoreEl = document.getElementById('lexScore');
        const labelEl = document.getElementById('lexLabel');
        const posEl = document.getElementById('lexPos');
        const countEl = document.getElementById('lexCount');
        const sourceEl = document.getElementById('lexSource');
        const posMatchEl = document.getElementById('lexPosMatch');

        function hide() {{
          popup.style.display = 'none';
        }}

        function clamp(v, lo, hi) {{
          return Math.max(lo, Math.min(hi, v));
        }}

        function showForChip(chip) {{
          const lemma = chip.dataset.lemma || '';
          const score = chip.dataset.score || '';
          const label = chip.dataset.label || '';
          const pos = chip.dataset.pos || '';
          const source = chip.dataset.source || '';
          const count = chip.dataset.count || '';
          const posmatch = chip.dataset.posmatch || '';

          titleEl.textContent = lemma;
          scoreEl.textContent = score;
          labelEl.textContent = label || '—';
          posEl.textContent = pos || '—';
          countEl.textContent = (count !== '' ? count : '—');
          sourceEl.textContent = source || '—';
          posMatchEl.textContent = posmatch || '—';

          popup.style.display = 'block';

          const r = chip.getBoundingClientRect();
          const margin = 10;
          const pw = popup.offsetWidth;
          const ph = popup.offsetHeight;

          // Prefer above the chip; fallback below if needed.
          let top = r.top - ph - 10;
          if (top < margin) top = r.bottom + 10;
          let left = r.left + (r.width / 2) - (pw / 2);
          left = clamp(left, margin, window.innerWidth - pw - margin);
          top = clamp(top, margin, window.innerHeight - ph - margin);

          popup.style.left = left + 'px';
          popup.style.top = top + 'px';
        }}

        document.addEventListener('click', (e) => {{
          const chip = e.target && e.target.closest ? e.target.closest('.lex-chip') : null;
          if (chip) {{
            e.preventDefault();
            e.stopPropagation();
            showForChip(chip);
            return;
          }}
          // click outside -> hide
          hide();
        }});

        document.addEventListener('keydown', (e) => {{
          if (e.key === 'Escape') hide();
          if ((e.key === 'Enter' || e.key === ' ') && document.activeElement && document.activeElement.classList && document.activeElement.classList.contains('lex-chip')) {{
            e.preventDefault();
            showForChip(document.activeElement);
          }}
        }});

        window.addEventListener('resize', hide);
        window.addEventListener('scroll', hide, true);
      }})();
    </script>
    """


def section(title: str, body_md: str):
    header(title)
    card(body_md)


# ==============================
# sidebar logo
# ==============================


def _data_uri_from_file(path: str | Path) -> str | None:
    """Return a data: URI for a local image file, or None if not found/invalid."""
    p = Path(path)
    if not p.exists() or not p.is_file():
        return None
    mime, _ = mimetypes.guess_type(str(p))
    if mime is None or not mime.startswith(("image/",)):
        return None
    data = p.read_bytes()
    b64 = base64.b64encode(data).decode("ascii")
    return f"data:{mime};base64,{b64}"


def sidebar_logo(
    path_or_url: str,
    *,
    link: str | None = None,
    height_px: int = 56,
    alt: str = "Logo",
    top_pad: str = "0.5rem",
    align: str = "center",  # "left" | "center" | "right"
):
    """
    Renders a logo at the very top of the left sidebar.

    """
    src = path_or_url
    if not (path_or_url.startswith("http://") or path_or_url.startswith("https://")):
        src = (
            _data_uri_from_file(path_or_url)
            or _data_uri_from_file(Path(__file__).parent / path_or_url)
            or _data_uri_from_file(Path.cwd() / path_or_url)
        )

    justify = {"left": "flex-start", "center": "center", "right": "flex-end"}.get(
        align, "center"
    )
    if not src:
        # Fallback: subtle placeholder
        st.sidebar.markdown(
            f"""
            <div style="display:flex; justify-content:{justify}; padding-top: {top_pad} !important; opacity:.6; font-size:.9rem;">
                (logo not found: {path_or_url})
            </div>
            """,
            unsafe_allow_html=True,
        )
        return

    tag = f'<img src="{src}" alt="{alt}" style="height:{height_px}px; display:block;">'
    if link:
        tag = f'<a href="{link}" target="_blank" style="line-height:0;">{tag}</a>'

    st.sidebar.markdown(
        f"""
        <div class="webui-sb-logo" style="display:flex; justify-content:{justify}; padding-top: {top_pad} !important;">
            {tag}
        </div>
        """,
        unsafe_allow_html=True,
    )
