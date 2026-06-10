"""
code_generator.py

Screen-to-Code AI Agent module powered by Google Gemini.

Exposes two top-level functions:
    - analyze_screens(images, api_key): plain-English breakdown of mock screens.
    - generate_code(images, framework, api_key): complete, runnable UI code
      in Streamlit, React, or Flask based on the supplied screens.

Dependencies (see requirements.txt):
    - google-genai
    - Pillow
"""

from __future__ import annotations

import logging
from typing import List

from google import genai
from google.genai import types
from PIL import Image


# ---------------------------------------------------------------------------
# Logging setup
# ---------------------------------------------------------------------------
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
MODEL_NAME           = "gemini-2.0-flash"   # ✅ Updated from gemini-1.5-pro
SUPPORTED_FRAMEWORKS = ("Streamlit", "React", "Flask")
MAX_IMAGES           = 3
MIN_IMAGES           = 1


# ---------------------------------------------------------------------------
# Generation config
# ---------------------------------------------------------------------------
_GENERATION_CONFIG = types.GenerateContentConfig(
    temperature=0.4,
    top_p=0.95,
    max_output_tokens=8192,
)


# ---------------------------------------------------------------------------
# System Prompts
# ---------------------------------------------------------------------------
ANALYSIS_SYSTEM_PROMPT = """You are an expert UI/UX analyst.
You will be given between 1 and 3 mock screen images.

For the uploaded screen(s), produce a clean, plain-English breakdown that covers:
1. Overall layout of each screen (header, sidebar, main content, footer, grids, etc.).
2. Every UI component visible — buttons, tables, forms, input fields, charts,
   navbars, sidebars, cards, dropdowns, tabs, modals, icons, images, etc.
3. The color scheme (primary, secondary, accent, background, text colors).
4. Any visible text, labels, headings, placeholder text, or menu items.

Rules:
- Return ONLY a plain-English breakdown. No code. No markdown fences.
- Be concise but complete. Use short bullet points grouped by screen.
- If multiple screens are provided, label them as Screen 1, Screen 2, etc.
"""


FRAMEWORK_INSTRUCTIONS = {
    "Streamlit": """Streamlit-specific requirements:
- Produce a SINGLE file named app.py.
- Put all required imports at the top of app.py.
- Use st.sidebar for any sidebar / navigation.
- Use st.columns for multi-column layouts.
- Use st.dataframe for tables.
- Use st.plotly_chart for charts.
- The file must be runnable directly with: streamlit run app.py
""",
    "React": """React-specific requirements:
- Produce App.js, one component file per major screen section, and App.css.
- Use functional components and React hooks.
- Keep imports/exports correct between files.
- Clearly delimit each file with a header comment in this exact format:
      // ===== File: src/App.js =====
      // ===== File: src/components/<ComponentName>.js =====
      /* ===== File: src/App.css ===== */
- Assume a standard Create-React-App project layout.
""",
    "Flask": """Flask-specific requirements:
- Produce app.py, templates/index.html, and static/style.css.
- app.py must define the Flask app and at least one route rendering
  index.html via render_template, passing placeholder data where useful.
- Clearly delimit each file with a header comment in this exact format:
      # ===== File: app.py =====
      <!-- ===== File: templates/index.html ===== -->
      /* ===== File: static/style.css ===== */
- The app must be runnable with: python app.py
""",
}


CODE_SYSTEM_PROMPT_TEMPLATE = """You are an expert front-end engineer.
You will be given between 1 and 3 mock screen images and a target framework.

Target framework: {framework}

Your job:
1. Carefully analyze the layout of every screen.
2. Identify every UI component visible (buttons, tables, forms, charts,
   navbars, sidebars, cards, dropdowns, tabs, etc.).
3. Generate a COMPLETE, RUNNABLE application in the target framework that
   visually reproduces the screens as closely as possible.
4. Where real data is not visible in the mock, use sensible placeholder data
   (sample rows for tables, dummy series for charts, lorem-ipsum text, etc.).
5. Add clear comments for every major section of the code.

{framework_instructions}

Output rules (CRITICAL):
- Return ONLY raw code. No prose, no explanations, no markdown code fences,
  no leading or trailing commentary.
- All explanations must live INSIDE code comments.
- The code must be runnable as-is once placed in the documented file paths.
"""


# ---------------------------------------------------------------------------
# Internal Helpers
# ---------------------------------------------------------------------------

def _validate_images(images: List[Image.Image]) -> None:
    """Raise ValueError if the images list is missing, empty, or out of bounds."""
    if not isinstance(images, list) or len(images) < MIN_IMAGES:
        raise ValueError(
            f"`images` must be a non-empty list of PIL Image objects "
            f"(minimum {MIN_IMAGES})."
        )
    if len(images) > MAX_IMAGES:
        raise ValueError(
            f"At most {MAX_IMAGES} images are supported; "
            f"you supplied {len(images)}."
        )
    for idx, img in enumerate(images):
        if not isinstance(img, Image.Image):
            raise ValueError(
                f"Item at index {idx} is not a PIL Image object "
                f"(got {type(img).__name__}). "
                "Open your files with PIL.Image.open() before passing them in."
            )


def _build_client(api_key: str) -> genai.Client:
    """Validate the API key and return a configured Gemini client."""
    if not isinstance(api_key, str) or not api_key.strip():
        raise ValueError(
            "A non-empty Gemini API key string is required. "
            "Obtain one at https://aistudio.google.com/app/apikey"
        )
    logger.info("Gemini client created successfully.")
    return genai.Client(api_key=api_key.strip())


def _strip_outer_code_fence(text: str) -> str:
    """Unwrap a single outer ```...``` fence if the entire response is wrapped."""
    if not text:
        return text
    stripped = text.strip()
    if not stripped.startswith("```"):
        return text
    first_newline = stripped.find("\n")
    if first_newline == -1:
        return text
    if not stripped.endswith("```"):
        return text
    inner = stripped[first_newline + 1: -3]
    if "```" in inner:
        return text
    return inner.rstrip()


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def analyze_screens(images: List[Image.Image], api_key: str) -> str:
    """
    Send 1-3 PIL images to Gemini and return a plain-English UI breakdown.
    Always returns a str, even on error.
    """
    try:
        _validate_images(images)
        client = _build_client(api_key)

        user_text = (
            f"Analyze these {len(images)} mock screen image(s) and provide "
            "the plain-English breakdown as instructed."
        )

        contents = [ANALYSIS_SYSTEM_PROMPT, user_text, *images]

        logger.info("Sending %d image(s) to Gemini for analysis...", len(images))

        response = client.models.generate_content(
            model=MODEL_NAME,
            contents=contents,
            config=_GENERATION_CONFIG,
        )

        result = (response.text or "").strip()

        if not result:
            return "[analyze_screens] Gemini returned an empty response. Please retry."

        return result

    except Exception as exc:
        logger.error("analyze_screens failed: %s: %s", type(exc).__name__, exc)
        return f"[analyze_screens error] {type(exc).__name__}: {exc}"


def generate_code(
    images: List[Image.Image],
    framework: str,
    api_key: str,
) -> str:
    """
    Send 1-3 PIL images + framework choice to Gemini and return raw UI code.
    Always returns a str, even on error.
    """
    try:
        _validate_images(images)

        if framework not in SUPPORTED_FRAMEWORKS:
            raise ValueError(
                f"Unsupported framework '{framework}'. "
                f"Choose one of: {list(SUPPORTED_FRAMEWORKS)}."
            )

        client = _build_client(api_key)

        system_prompt = CODE_SYSTEM_PROMPT_TEMPLATE.format(
            framework=framework,
            framework_instructions=FRAMEWORK_INSTRUCTIONS[framework],
        )

        user_text = (
            f"Generate a complete, runnable {framework} app that reproduces "
            f"these {len(images)} mock screen(s). Return ONLY raw code."
        )

        contents = [system_prompt, user_text, *images]

        logger.info(
            "Sending %d image(s) to Gemini for %s code generation...",
            len(images),
            framework,
        )

        response = client.models.generate_content(
            model=MODEL_NAME,
            contents=contents,
            config=_GENERATION_CONFIG,
        )

        result = (response.text or "").strip()

        if not result:
            return "[generate_code] Gemini returned an empty response. Please retry."

        return _strip_outer_code_fence(result)

    except Exception as exc:
        logger.error("generate_code failed: %s: %s", type(exc).__name__, exc)
        return f"[generate_code error] {type(exc).__name__}: {exc}"
