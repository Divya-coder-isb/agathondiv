# Mockscreen to Code Agent

A no-code AI tool that converts UI mockups and wireframes into fully functional code templates using Google Gemini's multimodal capabilities.

## 🌟 Impact
This project bridges the gap between design and development. By allowing users to upload static images and instantly receive working Streamlit, React, or Flask code, it accelerates rapid prototyping, empowers non-technical product teams, and significantly reduces boilerplate coding time for engineers.

## 🎨 Workflow Design
The user experience is designed to be frictionless and intuitive:
1. **Configuration:** The user opens the Streamlit web app and selects their desired target tech stack (Streamlit, React, or Flask).
2. **Input:** The user uploads 1 to 3 images of their UI mockups (PNG, JPG, WEBP).
3. **Processing:** The user clicks "Generate Code." The app displays a loading spinner while the AI analyzes the visual components.
4. **Output:** The generated code is displayed in expandable sections for easy review.
5. **Export:** A "Download ZIP" button allows the user to immediately download the fully structured project repository to their local machine.

## ⚙️ Logic Flow
1. **Frontend (app.py):** Streamlit handles the UI, file uploads, and user inputs.
2. **Validation (validators.py):** Uploaded files are checked for correct MIME types, file sizes, and quantity limits (1-3 images).
3. **AI Generation (code_generator.py):** 
   - The images and system prompts are packaged and sent to the Google Gemini API (`gemini-2.5-flash`).
   - The prompt strictly enforces a JSON-only response containing file paths and code content.
   - *Error Handling:* Includes graceful catch blocks for API limits (429 Quota Exhausted) and server overloads (503 Unavailable).
4. **Parsing & Packaging (file_builder.py):** The JSON response is parsed. The file paths and contents are mapped into an in-memory ZIP file.
5. **Delivery:** The ZIP file is passed back to the Streamlit UI as a downloadable artifact.
