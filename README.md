# Article Validation System - Engineering Handover

This package contains the "2-Filtration System" for validating news articles. The system is designed to be efficient by filtering low-quality candidates early using metadata, before performing expensive content scraping on the remaining candidates.

## System Overview

1.  **Step 1: Metadata Pre-Filter (`step1_prefilter.py`)**
    *   **Input**: `input_urls.xlsx` (Requires "Title" and "URL" columns)
    *   **Logic**: Uses a Zero-Shot classification model on the URL and Title text. It checks if the title/url string matches the desired topics.
    *   **Features**: Includes a "Keyword Boost" system where specific keywords in the title can artificially boost the relevance score (configurable in `config.json`).
    *   **Output**: Excel file with "Meta-Label" and "Score".

2.  **Step 2: Content Scraping & Validation (`step2_validate.py`)**
    *   **Input**: `input_urls.xlsx` (or the output from Step 1).
    *   **Logic**:
        *   Fetches the full HTML of the article (trying Requests -> Cloudscraper -> Playwright).
        *   Parses the text and checks if it looks like an article (length check).
        *   Classifies the full text using the Zero-Shot model.
    *   **Output**: Excel file with "Is Relevant", "Topic", and "Notes".

## Setup

1.  **Dependencies**:
    ```bash
    pip install -r requirements.txt
    ```
    *Note: You may need to install Playwright browsers: `playwright install`*

2.  **Configuration (`config.json`)**:
    *   **`model_path`**: Path to your local HuggingFace model (e.g., `cross-encoder-nli-deberta-v3-base`).
    *   **`candidate_labels`**: The list of all possible categories.
    *   **`positive_labels`**: The subset of categories that count as "Relevant".
    *   **`step1_prefilter`**: Settings for the metadata keywords and boost logic.
    *   **`step2_scraping`**: Settings for the scraper (max workers, timeouts).

## Usage

**Run Step 1 (Fast):**
```bash
python step1_prefilter.py
```

**Run Step 2 (Deep):**
```bash
python step2_validate.py
```

## Configuration Generator (Experimental)

We have added a prototype script to help generate `config.json` settings using natural language.

**Usage:**

1.  Set your API key in `.env` (created effectively inside `Engineering_Handover/`).
2.  Run the script:
    ```bash
    python config_generator.py "I want to find golf gift guides"
    ```

3.  **GUI Mode (Easier):**
    Run the graphical interface to generate and save configs with a click:
    ```bash
    python config_gui.py
    ```

## File Structure

*   `config.json`: Central configuration.
*   `step1_prefilter.py`: Script for metadata filtering.
*   `step2_validate.py`: Script for scraping and validation.
*   `core_validator.py`: The core logic class containing the scraping methods and classification wrapper.
*   `classifier_wrapper.py`: A wrapper around the HuggingFace pipeline.
