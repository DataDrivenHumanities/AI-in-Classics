from __future__ import annotations
import base64
import mimetypes
from pathlib import Path
import textwrap
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


def _apply_shell_css(bg: str, text: str, surface: str, primary: str, radius: str,
                     compact: bool, centered: bool, max_width_px: int):
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


def use_dark_preset(compact: bool = True, centered: bool = False, max_width_px: int = 1100):
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


def use_light_preset(compact: bool = True, centered: bool = False, max_width_px: int = 1100):
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
        "info":   "#60A5FA",
        "success": "#34D399",
        "warn":   "#FBBF24",
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
        src = _data_uri_from_file(path_or_url) or _data_uri_from_file(
            Path(__file__).parent / path_or_url
        ) or _data_uri_from_file(Path.cwd() / path_or_url)

    justify = {"left": "flex-start", "center": "center", "right": "flex-end"}.get(align, "center")
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
