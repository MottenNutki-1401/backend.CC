# CopyCatch Backend Code Review

This review describes the backend source in this repository. It does not assess the frontend, hosting environment, external controls, or live dependency advisories unless explicitly stated.

## 1. Architecture Review

### Verified strengths

- The FastAPI application is split into route modules and service modules.
- `main.py` centralizes app creation, CORS middleware, and route registration.

### Issues that need fixing

- **Severity: Medium** — **File:** `routes/*.py`; **Function:** route handlers. **Current behavior:** Handlers use generic dictionaries and directly call service functions; there is no common request schema or application-level error mapping. **Why it matters:** Validation behavior and error responses differ by route, and malformed input can fail inside service code. **Recommended action:** Define typed request models, validate related arrays and values, and standardize error responses.

### Potential improvements

- Add a shared application/service boundary for validated input, processing, and error translation if the API grows.

### Could not be verified

- The frontend’s own architecture, state management, and whether it consistently follows the backend workflow are outside this repository.

## 2. API Review

### Verified behavior

| Route | Method | Behavior |
|---|---|---|
| `/` | GET | Returns a fixed backend-running message. |
| `/upload` | POST | Accepts multipart `files`; returns filenames and extracted texts. Unsupported extensions raise HTTP 400. |
| `/similarity` | POST | Reads `texts` and `files` from JSON and returns similarity results. |
| `/grading` | POST | Reads `texts`, `files`, and optional `weights`; returns grade results. |
| `/grammar` | POST | Reads `texts`/`files` with empty-list defaults and returns grammar results. |
| `/spelling` | POST | Reads `texts` and `files` from JSON and returns spelling results. |

### Issues that need fixing

- **Severity: Medium** — **File:** `routes/similarity.py`, `routes/spelling.py`, `routes/grammar.py`, `routes/grading.py`; **Functions:** `get_similarity`, `get_spelling`, `grammar_endpoint`, `grading_endpoint`. **Current behavior:** Required keys are accessed directly in some routes, defaults are used in others, and array lengths/types are not consistently checked. **Why it matters:** Missing fields and mismatched arrays can produce inconsistent responses or runtime exceptions. **Recommended action:** Apply shared schemas and length/type validation.
- **Severity: Medium** — **File:** `services/similarity.py`; **Function:** `compute_all_similarities`. **Current behavior:** Inputs are passed to vectorization and indexed without validating nonempty input, empty vocabulary, or matching text/filename counts. **Why it matters:** Empty or inconsistent requests can fail or produce incorrect associations. **Recommended action:** Validate these cases and define controlled responses.

### Could not be verified

- The frontend’s expected request schemas and handling of non-2xx responses are not present in this backend repository.

## 3. Document Processing Review

### Verified strengths

- `routes/upload.py` restricts filename extensions to `.pdf`, `.docx`, and `.txt`.
- TXT extraction tries UTF-8, then CP1252 on a Unicode decode error.
- PDF resources are opened through a context manager (`pdfplumber.open`).

### Issues that need fixing

- **Severity: High** — **File:** `routes/upload.py`; **Function:** `upload_files`. **Current behavior:** The route joins the client-provided filename into a local path and writes with mode `wb`; it does not constrain the path to a safe basename or generate a unique name. **Why it matters:** Path components can escape the intended upload folder where accepted by the runtime path semantics; duplicate names overwrite existing files. **Recommended action:** Generate server-side names and enforce resolved path containment.
- **Severity: High** — **File:** `routes/upload.py`; **Function:** `upload_files`. **Current behavior:** Reads each entire file into memory and has no visible size, file-count, or extracted-text limit. **Why it matters:** Large uploads or batches can consume memory, disk, and parser time. **Recommended action:** Add bounded streaming and request/file/text limits.
- **Severity: Medium** — **File:** `services/text_extractor.py`; **Functions:** `extract_docx`, `extract_pdf`, `extract_text`. **Current behavior:** DOCX extraction reads paragraphs only; PDF text from pages is concatenated without separators; parser exceptions are uncaught; there is no OCR. **Why it matters:** Table content and scanned-page text can be omitted; malformed documents can result in unhandled errors. **Recommended action:** Define extraction coverage, handle parser errors, and add OCR only if required.
- **Severity: Medium** — **File:** `routes/upload.py`; **Function:** `upload_files`. **Current behavior:** Files remain under relative `uploads/`; no cleanup is implemented. The route prints the first 200 extracted characters. **Why it matters:** Documents may persist unexpectedly, and excerpts may enter logs. **Recommended action:** Establish retention/cleanup and remove content logging.

## 4. Text Preprocessing Review

### Verified behavior

- **File:** `services/preprocess.py`; **Function:** `clean_text`. It lowercases, removes characters outside `\w` and whitespace, collapses whitespace, and trims.
- `compute_all_similarities` applies this same preprocessing function to each supplied text before both cosine and Jaccard calculations.
- Grammar and spelling use raw text or their own handling; the similarity preprocessing does not govern those features.

### Potential improvements

- Test Unicode, punctuation, contractions, numbers, and documents whose content becomes empty after cleaning. The current cleaning also removes apostrophes and punctuation, which can merge or alter token forms.

## 5. Similarity Engine Review

### Verified behavior

- **Cosine:** `services/similarity.py`, `compute_all_similarities` builds a TF-IDF matrix using scikit-learn `TfidfVectorizer(ngram_range=(1, 2))`, then calls `cosine_similarity` for pairwise scores.
- **Jaccard:** `jaccard_similarity` uses sets of whitespace-split cleaned words and returns intersection/union, or 0 when union is empty.
- **N-grams:** Unigrams and bigrams are dimensions in the TF-IDF representation. There is no independent n-gram metric or n-gram result field.
- **Selection:** Each document’s maximum combined score against a different index in the submitted set is selected.

### Issues that need fixing

- **Severity: High** — **File:** `services/similarity.py`; **Function:** `compute_all_similarities`. **Current behavior:** TF-IDF is fitted to the batch; empty input/all-empty vocabulary and mismatched list lengths are not handled. **Why it matters:** Some valid-looking edge requests fail and score values are batch-dependent. **Recommended action:** Validate inputs, define edge behavior, and document batch-relative scoring.
- **Severity: Medium** — **File:** `services/similarity.py`; **Function:** `compute_all_similarities`. **Current behavior:** For one filename, no other candidate is visited; index `-1` is then used for `most_similar`, reporting the same filename at 0%. **Why it matters:** The result implies a comparison where none exists. **Recommended action:** Return an explicit no-candidate value or require at least two documents.

## 6. Scoring Review

### Verified behavior

- Similarity score for a candidate is `0.7 * cosine + 0.3 * Jaccard`. The largest candidate score is multiplied by 100 and rounded to two decimals.
- Status thresholds are `High Risk` at 0.7+, `Moderate` at 0.4+, and otherwise `Safe`.
- `services/grading.py`, `compute_grades` defaults weights to grammar 40, spelling 30, originality 30. It calculates originality as `100 - similarity percentage`, then sums each score multiplied by its weight divided by 100.

### Issues that need fixing

- **Severity: Medium** — **File:** `services/grading.py`; **Function:** `compute_grades`. **Current behavior:** Caller-provided weights are accepted without checking ranges, numeric types, or sum-to-100. Defaults sum to 100, but custom weights need not. **Why it matters:** `final_score` can be outside an expected 0–100 interpretation or behave inconsistently. **Recommended action:** Validate and document weight semantics.
- **Severity: Medium** — **File:** `services/grammar.py`, `services/spelling.py`; **Functions:** `analyze_grammar`, `analyze_spelling`. **Current behavior:** Grammar subtracts count of LanguageTool matches from regex word count; spelling subtracts unique misspelled token count from total token count. **Why it matters:** These are heuristics; grammar matches need not map one-to-one to words, and repeated misspellings count once in the unknown-word set. **Recommended action:** Present scores as heuristic indicators and validate the scoring model before treating it as an academic grade.

## 7. Report Generation Review

### Verified behavior

- **Severity: Low** — **File:** `main.py`; **Function:** route registration. **Current behavior:** The app registers JSON-returning upload and analysis routes; no report creation, report persistence, or download route appears. **Why it matters:** A claim that this backend generates a downloadable report is unsupported by the reviewed code. **Recommended action:** Describe the current response as JSON output, or implement report generation as separate work.

### Could not be verified

- A frontend may format JSON into a display or downloadable artifact, but no such frontend source was reviewed here.

## 8. Additional Features Review

- Grammar is implemented by `services/grammar.py` using a module-level `language_tool_python.LanguageTool('en-US')`, returning match count, heuristic score, issue messages/suggestions/offsets, and original text.
- Spelling is implemented by `services/spelling.py` using a module-level `SpellChecker`, returning unknown-word count, score, unique misspelled words, and original text.
- The grading endpoint invokes grammar, spelling, and similarity, but these checks are not the similarity algorithm itself.

### Issues that need fixing

- **Severity: Medium** — **File:** `services/grammar.py`; **Function/module initialization and `analyze_grammar`. Current behavior:** LanguageTool is constructed at import time and checked synchronously. **Why it matters:** Runtime availability and startup behavior are coupled to the external tool/runtime. **Recommended action:** Verify runtime requirements in deployment and handle tool failure with a controlled service error.
- **Severity: Low** — **File:** `services/spelling.py`; **Function:** `analyze_spelling`. **Current behavior:** Prints the misspelled-word set and returns the original text. **Why it matters:** This creates potentially sensitive logs and responses. **Recommended action:** Avoid printing document-derived content and return only fields needed by the client.

## 9. Security Review

### Verified mechanisms

- CORS uses an explicit three-origin list in `main.py`.
- Upload filename extensions are restricted to three values.

### Issues that need fixing

- **Severity: High** — **File:** `routes/upload.py`; **Function:** `upload_files`. **Current behavior:** Client filename is used in the filesystem path, and file bytes are persisted without signature validation, size limits, or parser isolation. **Why it matters:** Unsafe paths, overwrites, resource exhaustion, and malicious parser input are not mitigated by the visible implementation. **Recommended action:** Safe generated names, containment checks, resource bounds, and content/parser safeguards.
- **Severity: Medium** — **File:** `main.py` and route modules; **Functions:** app configuration and handlers. **Current behavior:** No authentication, authorization, or rate limiting is visible. CORS is a browser policy and does not authenticate callers. **Why it matters:** Any network-accessible API requires perimeter or application access controls appropriate to its deployment. **Recommended action:** Add access controls if the service is not intended to be public and apply request throttling where appropriate.
- **Severity: Medium** — **File:** `routes/upload.py`, `services/grammar.py`, `services/spelling.py`. **Current behavior:** Extracted excerpts are printed, and original text is returned from grammar/spelling. Uploaded files remain on local disk. **Why it matters:** Document data may be exposed through logs, API responses, or retained storage. **Recommended action:** Minimize logged/returned content and define secure retention and access policies.

### Could not be verified

- Real secrets, hosting network restrictions, TLS, reverse proxy limits, persistent volumes, and deployment access controls are not specified by this backend source. `requirements.txt` pins packages, but no dependency vulnerability audit was performed.

## 10. Performance Review

- **Severity: Medium** — **File:** `routes/upload.py`; **Function:** `upload_files`. **Current behavior:** Full uploads are read into memory; extraction runs in the request. **Why it matters:** Large files/batches increase memory use and request time. **Recommended action:** Bound uploads and consider streaming or background processing for larger workloads.
- **Severity: Medium** — **File:** `services/similarity.py`; **Function:** `compute_all_similarities`. **Current behavior:** Pairwise comparison is quadratic in document count; pair results include a dense cosine matrix. **Why it matters:** Large batches increase computation and memory. **Recommended action:** Limit batch size or use an architecture suitable for the expected corpus/workload.
- **Severity: Medium** — **File:** `routes/*.py`, `services/grading.py`. **Current behavior:** Async handlers invoke synchronous extraction, sklearn, LanguageTool, and spelling work. Grading repeats similarity and both text checks. **Why it matters:** Synchronous operations can occupy request workers and repeated requests redo work. **Recommended action:** Measure workload; consider worker/background execution and safe result reuse.

## 11. Code Quality Review

- **Severity: Low** — **File:** `services/preprocess.py`, `services/spelling.py`; **Functions:** both named `clean_text`. **Current behavior:** Two different functions share the same name: similarity cleaning returns a string; spelling cleaning returns a word list. **Why it matters:** The names obscure different behavior. **Recommended action:** Use purpose-specific names if the implementation is revised.
- **Severity: Medium** — **File:** `routes/upload.py`, `services/spelling.py`; **Functions:** `upload_files`, `analyze_spelling`. **Current behavior:** Uses `print` for extracted excerpts and misspelled words. **Why it matters:** Not configurable, structured application logging and can disclose data. **Recommended action:** Use safe, configurable logging without document content.
- **Severity: Low** — **File:** `services/similarity.py`, `services/grading.py`; **Functions:** `compute_all_similarities`, `compute_grades`. **Current behavior:** Similarity weights, risk thresholds, and grade default weights are hardcoded. **Why it matters:** Behavior is less discoverable/configurable and may diverge from presentation material. **Recommended action:** Document the values and centralize configuration if configurability is required.

No dead code or definitely unused dependency was established by this review; dependency usage was not exhaustively audited.

## 12. Deployment Readiness

- **Severity: Medium** — **File:** `Dockerfile`; **Build/run configuration:** Uses mutable `python:3.10`, installs `openjdk-21-jdk`, and runs Uvicorn on hardcoded port 8080. **Why it matters:** Runtime availability, image reproducibility, and platform port expectations require verification. **Recommended action:** Verify the target platform and pin/parameterize deployment settings as needed.
- **Severity: Medium** — **File:** `services/grammar.py`; **Module initialization:** Starts/configures LanguageTool at import. **Why it matters:** Startup depends on Java/LanguageTool behavior. **Recommended action:** Exercise container startup and grammar route in the actual deployment image.
- **Severity: Medium** — **File:** `routes/upload.py`; **Configuration:** Relative local `uploads` storage. **Why it matters:** Persistence across restarts/replicas and cleanup are not configured. **Recommended action:** Define volume/storage and retention requirements.
- **Severity: Low** — **File:** `main.py`. **Current behavior:** CORS origins are hardcoded; root endpoint is the only visible health-style endpoint. **Recommended action:** Verify origin list per environment and add deployment-specific readiness checks if needed.

## 13. Testing

No repository-owned test files were found outside the virtual environment in the inspected file listing. External CI tests cannot be verified.

Recommended tests:

- Extraction of valid, malformed, empty, and unsupported files; TXT encodings; DOCX tables; scanned PDFs.
- Upload traversal, duplicate filenames, size/count limits, and cleanup behavior.
- Similarity for identical, dissimilar, empty, one-document, and mismatched-array inputs; verify weighting and status boundary values.
- Grading defaults, custom/invalid weights, and component scores.
- Grammar/spelling with empty input, repeated errors, and unavailable LanguageTool.
- API request validation, status codes, and consistent error response structure.
- Docker startup, Java/LanguageTool availability, and expected port/storage behavior.

## 14. Defense Presentation Risks

- **Severity: Medium** — **File:** `services/similarity.py`; **Function:** `compute_all_similarities`. **Current behavior:** Two final measures are combined: TF-IDF cosine (with unigram/bigram features) and word-set Jaccard. **Why it matters:** Describing this as three separately calculated and reported algorithms would not match source. **Recommended action:** Describe n-grams as TF-IDF features, not a separate score.
- **Severity: Medium** — **File:** `services/similarity.py`; **Function:** `compute_all_similarities`. **Current behavior:** Fixed 70/30 weighted sum, best match within submitted batch. **Why it matters:** Claims of equal averaging or comparison against a stored corpus would be inaccurate. **Recommended action:** Present the exact formula and batch scope.
- **Severity: Medium** — **File:** `services/grading.py`; **Function:** `compute_grades`. **Current behavior:** “Originality” is 100 minus batch-relative maximum similarity and combines with heuristic grammar/spelling scores. **Why it matters:** This is not a globally calibrated originality or writing-quality measure. **Recommended action:** Explain its operational definition and heuristic nature.
- **Severity: Low** — **File:** `main.py`; **Function:** route registration. **Current behavior:** No report-generation/download route, database, OCR flow, or background queue is registered/implemented. **Why it matters:** Claims of those capabilities are not supported by the backend source. **Recommended action:** Keep the presentation architecture aligned with verified implementation, or label planned features as future work.

### Verified strengths

- The code has distinct route and service modules.
- It supports PDF, DOCX, and TXT extraction and computes two combined similarity measures.
- The similarity preprocessing is consistently applied to each input within a comparison request.

### Fix before defense

Prioritize documenting the algorithm accurately and resolving upload path/resource risks, input validation and edge cases, and document-content logging. Verify runtime/deployment behavior before making operational claims.
