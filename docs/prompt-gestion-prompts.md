# Prompts used to build the "Gestion des Prompts" module

> Technique: structured prompt (Role → Context → Task → Specifications → Constraints → Acceptance criteria → Output format).
> Each section has one job, so the AI cannot guess wrong about scope, stack, or what "done" means.
>
> The work was done in 4 prompts, one per step:
> 1. **Prompt 1**: build the CRUD module "Gestion des Prompts"
> 2. **Prompt 2 (Atelier 4)**: integrate an AI API with a local fallback
> 3. **Prompt 3 (Atelier 5, part 1)**: unit tests + code coverage
> 4. **Prompt 4 (Atelier 5, part 2)**: User Story → Gherkin scenarios

---

## Prompt 1: Build the CRUD module

**# ROLE**
You are a senior full-stack developer who is fluent in FastAPI (Python) and Angular 17 (standalone components, Tailwind CSS). You write simple, readable code that matches the style of the existing project.

**# CONTEXT**
I am working on an existing project called **UML Architecture Analyzer**:
- The user uploads an image of a UML use case diagram.
- The backend (FastAPI) extracts the text with PaddleOCR (`services/ocr.py`), then sends it to Google Gemini (`services/llm_service.py`), which returns JSON: `system_title`, `detected_actors`, `documentation_markdown`.
- The frontend (Angular 17 + Tailwind) has one page: a drag-and-drop uploader and a Markdown viewer.
- Problem: the instructions sent to Gemini (`SYSTEM_PROMPT`) are **hard-coded** in `llm_service.py`. To test another prompt, you have to edit the code and restart the server. Nothing is saved, and there is no database.

**# TASK**
Add a CRUD module called **"Gestion des Prompts"**, which lets users manage the prompt templates sent to Gemini and choose which one to use for each analysis.

**# FUNCTIONAL SPECIFICATIONS**

1. **Data (SQLite, Python's built-in `sqlite3` module, no new dependency)**
   Table `prompts`: `id`, `name` (unique), `description` (optional), `content` (the instructions sent to the LLM), `is_default` (exactly one prompt is the default), `created_at`, `updated_at`.
   On first launch, create the table and insert one default prompt, "Architecte Sénior", containing the current instructions from `SYSTEM_PROMPT`, so the app keeps working exactly as before.

2. **Backend: REST API under `/api/prompts`**
   - `GET /api/prompts`: list all prompts (default first)
   - `GET /api/prompts/{id}`: get one prompt
   - `POST /api/prompts`: create a prompt
   - `PUT /api/prompts/{id}`: update a prompt
   - `DELETE /api/prompts/{id}`: delete a prompt
   - `PUT /api/prompts/{id}/default`: make this prompt the default
   - Validation with Pydantic: `name` 3–100 characters, `content` at least 20 characters, `description` max 255.
   - Errors: `404` if the prompt does not exist, `409` if the name is already used, `400` if the user tries to delete the default prompt.

3. **Connect to the analysis**
   - `POST /api/upload-diagram` accepts an optional form field `prompt_id`. If it is missing, use the default prompt. If it doesn't exist, return `404`.
   - Gemini receives the chosen prompt's `content`, followed by a **fixed JSON format block that the user cannot edit**, so the response is always parseable whatever prompt is written.
   - The response also returns `prompt_name` (the name of the prompt used).

4. **Frontend (Angular)**
   - Two simple tabs at the top of the page: **"Analyser un diagramme"** and **"Gestion des Prompts"** (no router needed).
   - "Gestion des Prompts" page: a list of prompts as cards (name, description, "Par défaut" badge, preview of the content), with **Modifier**, **Supprimer** (with confirmation), and **Définir par défaut** buttons, plus a **"+ Nouveau prompt"** button that opens a form (name, description, content) used for both create and edit.
   - In the analyzer: a dropdown above the button to choose the prompt (the default is preselected), and the name of the prompt used is shown in the result.
   - A new `PromptService` handles the HTTP calls, following the style of the existing `DiagramService`.

**# CONSTRAINTS**
- Keep it **simple**. This is a university project, so no ORM, no authentication, no new library.
- **Do not break** the existing functionality: an upload with no `prompt_id` must behave exactly as before.
- Follow the existing project structure: `api/endpoints/`, `schemas/`, `services/`, `core/`, and on the frontend `components/` and `services/`.
- Same visual style as the existing UI (Tailwind, rounded cards, blue/indigo gradient).
- User interface text in **French**.
- Do not modify unrelated files.

**# ACCEPTANCE CRITERIA**
- [ ] On first launch, the database is created with one default prompt.
- [ ] I can create, view, edit, and delete a prompt from the interface.
- [ ] I cannot delete the default prompt, and an error message explains why.
- [ ] I cannot create two prompts with the same name.
- [ ] I can change the default prompt.
- [ ] When I analyze a diagram with a chosen prompt, that prompt is the one sent to Gemini, and its name appears in the result.
- [ ] The Angular build (`npm run build`) compiles without errors.

**# OUTPUT FORMAT**
1. A short plan listing the files to create and modify.
2. The code for each file.
3. A short explanation of how to test the feature (curl commands + UI steps).

---

## Prompt 2 (Atelier 4): AI analysis of a prompt's quality, with a local fallback

**# ROLE**
You are a senior Python developer who specializes in integrating AI APIs into existing software and handling errors robustly.

**# CONTEXT**
The "Gestion des Prompts" module (FastAPI + SQLite + Angular) is working: users can create, edit, and delete the prompts sent to Gemini. But they get no help writing a *good* prompt. The project already uses the `google-genai` SDK and the `GEMINI_API_KEY` key (see `services/llm_service.py`).

**# TASK**
Add a feature called **"Analyser la qualité du prompt"**: the user writes a prompt in the form, clicks a button, and gets a score, a verdict, strengths, and improvement suggestions.

**# SPECIFICATION (write it in `docs/specification-analyse-prompt.md` before coding)**
- **Input:** the text of the prompt (`content`, minimum 20 characters).
- **Output:** JSON `{ score: 0-100, verdict: "Excellent" | "Correct" | "À améliorer", strengths: [..], suggestions: [..], source: "ia" | "local", fallback_reason: string | null }`.
- **Normal behavior:** the analysis is done by **Gemini** (`source = "ia"`).
- **Error behavior (fallback):** if the API key is missing, the SDK is not installed, the API call fails, or Gemini returns an invalid response, **do not crash**. Run a **local rule-based analysis** instead (`source = "local"`) and explain why in `fallback_reason`.
- **Local rules (7 criteria, 100 points):** role defined (15), clear task (20), context (15), structure as a list/steps (15), constraints (15), output format (10), sufficient length (10). Verdict: ≥ 80 Excellent, ≥ 50 Correct, otherwise À améliorer.

**# IMPLEMENTATION**
- `services/prompt_analyzer.py`: `analyze_prompt(content)` tries `_analyze_with_ai()`, and on any exception calls `_analyze_locally()`. Import the Gemini SDK *inside* the AI function so that a missing SDK also triggers the fallback.
- Endpoint `POST /api/prompts/analyze` (body: `{ "content": "..." }`).
- Angular: an **"Analyser la qualité"** button in the prompt form. Show the score as a colored bar, the verdict, the strengths (✓), and the suggestions (→), with a badge **"Analyse IA (Gemini)"** or **"Analyse locale (fallback)"** + the reason.

**# CONSTRAINTS**
- Clear comments, exceptions handled, no new dependency (the local fallback uses only regular expressions).
- Do not modify the generation of the documentation itself.

**# OUTPUT FORMAT**
Specification → code → test examples (one with the API, one without the key, to prove the fallback works).

---

## Prompt 3 (Atelier 5, part 1): Unit tests and code coverage

**# ROLE**
You are a QA engineer and Python developer who is an expert in `pytest`.

**# CONTEXT**
The "Gestion des Prompts" module contains business logic with no tests:
- `services/prompt_service.py` (CRUD, unique name, single default prompt, protection of the default prompt),
- `services/prompt_analyzer.py` (Gemini analysis + local fallback),
- `api/endpoints/prompts.py` (REST routes and HTTP codes),
- `core/database.py` (table creation + seed).

**# TASK**
Generate a unit test suite in the `tests/` folder and measure coverage with `pytest --cov`.

**# CASES TO COVER**
- **Nominal cases:** create, list (default first), read, update, delete, change the default prompt.
- **Complex case:** a full scenario that chains create → set as default → delete the old default.
- **Error cases:** prompt not found (404), duplicate name on create and on update (409), deleting the default prompt (400), invalid data (422).
- **Analyzer:** an excellent prompt / a weak prompt (local rules); Gemini OK; missing key, Gemini error, and invalid JSON → fallback.

**# CONSTRAINTS**
- Each test uses a **temporary SQLite database** (`tmp_path` fixture), never the real database.
- **Mock** Gemini (no real network call during the tests).
- Do not import `main.py` (it loads PaddleOCR): test the router inside a minimal FastAPI app.
- Clear test names in the form `test_<action>_<expected_result>`.
- Goal: **100% coverage** of the 4 files above.

**# OUTPUT FORMAT**
The test files, the commands (`pip install -r requirements-dev.txt`, `pytest --cov=...`), and the coverage table before/after.

---

## Prompt 4 (Atelier 5, part 2): User Story → Gherkin

> Transform the following User Story into a complete Gherkin file (`Feature`, `Background`, `Scenario`, `Given`, `When`, `Then`). Write the step text in French. Include scenarios for: displaying the list with the default prompt, creating a valid prompt, creating a prompt with a name that already exists, creating a prompt that is too short, editing a prompt, deleting a prompt with confirmation, trying to delete the default prompt, changing the default prompt, analyzing quality with the AI, analyzing quality when the AI is unavailable (fallback), and analyzing a diagram with a chosen prompt. Use a `Scenario Outline` with an `Examples` table for the validation errors. The file must be understandable by a non-technical person.
>
> **Title:** Gestion des prompts de génération
> **As a:** software architect who uses the UML Architecture Analyzer
> **I want to:** create, view, edit, and delete the prompts sent to the AI, and choose the prompt used for an analysis
> **So that:** I can compare different prompts and get the documentation best suited to my needs
> **Acceptance criteria:**
> - The list shows all prompts, with the default prompt first.
> - A prompt must have a unique name (3–100 characters) and content of at least 20 characters.
> - The default prompt cannot be deleted.
> - Exactly one prompt is the default.
> - Deletion asks for confirmation.
> - The quality analysis works even when the AI is unavailable (local analysis).
> - The analysis of a diagram uses the selected prompt and shows its name.

---

## Why these prompts are written this way (prompt-engineering techniques used)

| Technique | Where | Why |
|---|---|---|
| **Role prompting** | `# ROLE` | Sets the expertise level and the coding style expected. |
| **Context grounding** | `# CONTEXT` | Gives the real file names and the real problem, so the AI builds *on* the project instead of inventing a new one. |
| **Precise specifications** | Routes, fields, HTTP codes | Removes ambiguity: the AI doesn't have to guess the API design. |
| **Negative constraints** | `# CONSTRAINTS` ("no ORM", "do not break…") | Prevents over-engineering and regressions. |
| **Acceptance criteria** | Checklist | Defines "done" in a way that can be verified. |
| **Output format** | Plan → code → tests | Makes the answer structured and easy to review. |
