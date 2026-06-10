"""
app.py

Screen-to-Code Agent — Streamlit UI.

Upload up to 3 mock screen images, choose a target framework
(Streamlit / React / Flask), and Gemini Vision will generate
production-ready UI code for you.
"""

import io
import time

import streamlit as st
from PIL import Image

try:
    from code_generator import analyze_screens, generate_code
    import_error = None
except Exception as e:
    import_error = str(e)


# ---------------------------------------------------------------------------
# Page configuration (must be the first Streamlit call)
# ---------------------------------------------------------------------------
st.set_page_config(
    page_title="Screen-to-Code Agent",
    page_icon="🖥️",
    layout="wide",
)

# Show import error immediately if code_generator failed to load
if import_error:
    st.error(f"❌ Failed to import code_generator: {import_error}")
    st.stop()


# ---------------------------------------------------------------------------
# Custom CSS
# ---------------------------------------------------------------------------
st.markdown(
    """
    <style>
        .app-header {
            background-color: #0A2342;
            color: #FFFFFF;
            padding: 1.75rem 2rem;
            border-radius: 12px;
            margin-bottom: 1.5rem;
            box-shadow: 0 6px 18px rgba(10, 35, 66, 0.18);
        }
        .app-header h1 {
            color: #FFFFFF !important;
            margin: 0;
            font-size: 2.2rem;
            font-weight: 700;
        }
        .app-header p {
            color: #D9E1F2;
            margin: 0.5rem 0 0 0;
            font-size: 1.05rem;
            line-height: 1.5;
        }

        .stButton > button[kind="primary"] {
            background-color: #1E6FEB;
            border: none;
            color: #FFFFFF;
            font-size: 1.05rem;
            font-weight: 600;
            padding: 0.85rem 1.25rem;
            border-radius: 10px;
            transition: all 0.2s ease;
            box-shadow: 0 4px 12px rgba(30, 111, 235, 0.25);
        }
        .stButton > button[kind="primary"]:hover:not(:disabled) {
            background-color: #1558C2;
            transform: translateY(-1px);
            box-shadow: 0 6px 16px rgba(30, 111, 235, 0.35);
        }
        .stButton > button[kind="primary"]:disabled {
            background-color: #B0B7C2;
            color: #F1F2F4;
            box-shadow: none;
        }
        [data-testid="stCode"] {
            box-shadow: 0 6px 20px rgba(10, 35, 66, 0.12);
            border-radius: 10px;
            overflow: hidden;
        }
        [data-testid="stImage"] img {
            border-radius: 12px;
            box-shadow: 0 2px 8px rgba(0, 0, 0, 0.08);
        }
    </style>
    """,
    unsafe_allow_html=True,
)


# ---------------------------------------------------------------------------
# Session-state defaults
# ---------------------------------------------------------------------------
def _init_state() -> None:
    defaults = {
        "generated_code": "",
        "framework": "",
        "analysis_text": "",
    }
    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value


_init_state()

WIDGET_KEYS = ("api_key", "framework_choice", "screen1", "screen2", "screen3", "analyze_first")
RESULT_KEYS = ("generated_code", "framework", "analysis_text")


def _reset_all() -> None:
    for key in WIDGET_KEYS + RESULT_KEYS:
        if key in st.session_state:
            del st.session_state[key]
    st.rerun()


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
FRAMEWORK_DESCRIPTIONS = {
    "Streamlit": "⚡ Python-based. Best for data apps & internal tools.",
    "React":     "⚛️ JavaScript. Best for modern web applications.",
    "Flask":     "🌶️ Python web framework with HTML templates.",
}

FRAMEWORK_DOWNLOAD_META = {
    "Streamlit": {"filename": "app.py",  "mime": "text/plain", "language": "python"},
    "React":     {"filename": "App.js",  "mime": "text/plain", "language": "javascript"},
    "Flask":     {"filename": "app.py",  "mime": "text/plain", "language": "python"},
}


def _uploaded_to_pil(uploaded_file) -> Image.Image:
    """Convert a Streamlit uploaded file to a PIL RGB image."""
    img = Image.open(io.BytesIO(uploaded_file.getvalue()))
    if img.mode != "RGB":
        img = img.convert("RGB")
    return img


# ---------------------------------------------------------------------------
# Sidebar
# ---------------------------------------------------------------------------
with st.sidebar:
    st.header("⚙️ Configuration")

    # Safely read secret — works in both Streamlit Cloud and local/Colab
    try:
        default_key = st.secrets.get("GEMINI_API_KEY", "")
    except Exception:
        default_key = ""

    # ✅ NEW — Hide input field if key is already loaded from secrets
    if default_key:
        api_key = default_key
        st.success("🔐 API Key loaded securely")
    else:
        api_key = st.text_input(
            "Gemini API Key",
            value="",
            type="password",
            key="api_key",
            help="Obtain your key at https://aistudio.google.com/app/apikey",
            placeholder="Paste your Gemini API key here...",
        )
        if not api_key:
            st.caption("🔑 Enter your Gemini API key to get started.")

    st.divider()

    framework_choice = st.selectbox(
        "🎨 Choose UI Framework",
        options=["Select a framework...", "Streamlit", "React", "Flask"],
        key="framework_choice",
    )

    if framework_choice in FRAMEWORK_DESCRIPTIONS:
        st.caption(FRAMEWORK_DESCRIPTIONS[framework_choice])

    st.divider()

    st.header("📤 Upload Mock Screens")
    screen1 = st.file_uploader("📱 Screen 1 (Required)", type=["png", "jpg", "jpeg"], key="screen1")
    screen2 = st.file_uploader("📱 Screen 2 (Optional)", type=["png", "jpg", "jpeg"], key="screen2")
    screen3 = st.file_uploader("📱 Screen 3 (Optional)", type=["png", "jpg", "jpeg"], key="screen3")

    st.divider()

    if st.button("🔄 Reset All", use_container_width=True):
        _reset_all()



uploaded_screens = [s for s in (screen1, screen2, screen3) if s is not None]

is_screen1_uploaded   = screen1 is not None
is_framework_selected = framework_choice in FRAMEWORK_DESCRIPTIONS
is_api_key_provided   = bool(api_key and api_key.strip())
is_code_generated     = bool(st.session_state.get("generated_code"))


# ---------------------------------------------------------------------------
# Header banner
# ---------------------------------------------------------------------------
st.markdown(
    """
    <div class="app-header">
        <h1>🖥️ Screen-to-Code Agent</h1>
        <p>Upload your mock screens, select a framework, and get production-ready UI code instantly</p>
    </div>
    """,
    unsafe_allow_html=True,
)


# ---------------------------------------------------------------------------
# Progress tiles
# ---------------------------------------------------------------------------
status_cols = st.columns(4)
with status_cols[0]: st.metric("Screens",   "✅" if is_screen1_uploaded   else "⏳")
with status_cols[1]: st.metric("Framework", "✅" if is_framework_selected  else "⏳")
with status_cols[2]: st.metric("API Key",   "✅" if is_api_key_provided    else "⏳")
with status_cols[3]: st.metric("Code",      "✅" if is_code_generated      else "⏳")


# ---------------------------------------------------------------------------
# Empty-state hint
# ---------------------------------------------------------------------------
if not uploaded_screens:
    st.info("👆 Upload at least one mock screen and select a framework from the sidebar to get started.")


# ---------------------------------------------------------------------------
# Screen preview
# ---------------------------------------------------------------------------
if uploaded_screens:
    st.subheader("🖼️ Uploaded Screens")
    preview_cols = st.columns(len(uploaded_screens))
    for col, screen in zip(preview_cols, uploaded_screens):
        with col:
            st.image(screen, use_container_width=True)
            st.caption(screen.name)

analyze_first = st.checkbox("🔍 Analyze screens before generating code", key="analyze_first")


# ---------------------------------------------------------------------------
# Generate button
# ---------------------------------------------------------------------------
generate_disabled = not (is_screen1_uploaded and is_framework_selected and is_api_key_provided)

generate_clicked = st.button(
    "🚀 Generate Code",
    type="primary",
    disabled=generate_disabled,
    use_container_width=True,
)

if generate_clicked:
    pil_images = [_uploaded_to_pil(s) for s in uploaded_screens]

    if analyze_first:
        with st.spinner("🔍 Analyzing your screens..."):
            analysis_text = analyze_screens(pil_images, api_key)
            st.session_state["analysis_text"] = analysis_text
            time.sleep(0.2)
        with st.expander("🔍 Screen Analysis", expanded=True):
            st.write(st.session_state["analysis_text"])
    else:
        st.session_state["analysis_text"] = ""

    with st.spinner(f"⚙️ Generating {framework_choice} code..."):
        generated = generate_code(pil_images, framework_choice, api_key)
        st.session_state["generated_code"] = generated
        st.session_state["framework"] = framework_choice


# ---------------------------------------------------------------------------
# Output section
# ---------------------------------------------------------------------------
if st.session_state.get("generated_code") and st.session_state.get("framework"):
    fw        = st.session_state["framework"]
    code_text = st.session_state["generated_code"]
    meta      = FRAMEWORK_DOWNLOAD_META[fw]

    if st.session_state.get("analysis_text") and not generate_clicked:
        with st.expander("🔍 Screen Analysis", expanded=False):
            st.write(st.session_state["analysis_text"])

    st.success(f"✅ Code generated for {fw}! Copy from below or download the file.")
    st.code(code_text, language=meta["language"])
    st.caption("💡 Click the copy icon at the top right of the code block to copy all code")

    st.download_button(
        label="⬇️ Download Code",
        data=code_text,
        file_name=meta["filename"],
        mime=meta["mime"],
        use_container_width=True,
    )


# ---------------------------------------------------------------------------
# Footer
# ---------------------------------------------------------------------------
st.markdown("---")
st.markdown("Powered by Gemini Vision | Built for Ford Agathon 🚗")
