# Engineering Guide: Article Validation System

## 1. What This Automation Does
This system automates the process of verifying whether a list of web URLs contains relevant content for a specific topic.

Instead of manually checking thousands of links, this tool:
1.  **Reads** a list of URLs and Titles from an Excel file.
2.  **Pre-filters** them based on "Metadata" (URL and Title) to instantly reject obvious mismatches (e.g., matching "Golf" when looking for "Laundry").
3.  **Scrapes** the full article content from the remaining candidates, handling anti-bot protections.
4.  **Reads** the article text using a Machine Learning model (Zero-Shot Classification).
5.  **Decides** if the article is "Relevant" or "Not Relevant" based on user-defined categories.

## 2. What Is It For?
**Business Goal:** To quickly curate high-quality datasets of articles for specific niche topics without human labor.

**Use Cases:**
*   **Content Aggregation:** Finding top news stories for a specific industry.
*   **QA Dataset Creation:** verifying that a list of "gold standard" URLs actually matches the intended topic before feeding them into an LLM or RAG system.
*   **Competitor Analysis:** Monitoring specific topics across many domains.

## 3. How Does It Work?
The system is built as a **Two-Stage Pipeline** to optimize for speed and cost.

### Architecture
*   **Core Engine**: Python + Transformers (Hugging Face) + Playwright.
*   **Model**: `cross-encoder-nli-deberta-v3-base` (runs locally, no API costs).

### Workflow
1.  **Step 1: The Gatekeeper (`step1_prefilter.py`)**
    *   **Input**: `input_urls.xlsx`
    *   **Logic**: It looks *only* at the **Title** and **URL string**.
    *   **Why?**: Scraping is slow (3-10 seconds per page). Checking a string is fast (0.01 seconds).
    *   **Mechanism**:
        *   It uses a "Keyword Boost" system (configurable in `config.json`). If a title contains "Best Laundry Detergent", it gets a score boost (+0.3).
        *   It calculates a "Relevance Score". If Score < 0.30, it is discarded immediately.
    *   **Output**: Filters the list down to only "Promising Candidates".

2.  **Step 2: The Validator (`step2_validate.py`)**
    *   **Input**: The filtered list from Step 1.
    *   **Logic**: It performs the heavy lifting.
    *   **Mechanism**:
        *   **Smart Scraping (`core_validator.py`)**: It attempts to download the page using 3 methods in order:
            1.  `Requests` (Fast, standard).
            2.  `Cloudscraper` (Bypasses Cloudflare checks).
            3.  `Playwright` (Launches a headless browser for complex JavaScript sites).
        *   **Analysis**: It extracts the main text (removing ads/menus) and feeds it into the NLI Model to see if it matches the `positive_labels` defined in `config.json`.

## 4. How Engineers Can Improve It
Here are the key areas for future optimization:

### A. Performance & Scaling
*   **Parallel Processing**: Step 2 currently uses `ThreadPoolExecutor`. For truly massive scale (100k+ URLs), migrate to an async queue system (like Celery or just pure `asyncio` with `aiohttp` where possible).
*   **API Deployment**: The project structure is ready for `FastAPI`. Deploying this as a microservice would allow multiple users to validate lists simultaneously. `core_validator.py` can be wrapped in a simple API endpoint.

### B. Scraping Robustness
*   **Proxy Integration**: Currently, it runs from the local IP. Integrating a rotating proxy service (e.g., BrightData, IPRoyal) into `core_validator.py` would significantly reduce blocking rates on strict sites.
*   **DOM Parsing**: The current `BeautifulSoup` text extraction is generic. Implementing `readability-lxml` or a dedicated article extractor would improve content quality.

### C. Model Accuracy
*   **Fine-Tuning**: The current model is "Zero-Shot" (general purpose). If the business focuses on one specific niche (e.g., only Medical Journals), fine-tuning a small BERT model on that specific data would be faster and more accurate.
*   **LLM Verification**: For "Edge Cases" (where score is 0.5 - 0.7), you could add a "Step 3" that sends *only* those confusing articles to GPT-4o-mini for a final "Human-Level" check.
