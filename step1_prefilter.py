import pandas as pd
import logging
from core_validator import ArticleValidator
import json

# CONFIG
import os
os.chdir(os.path.dirname(os.path.abspath(__file__)))
CONFIG_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "config.json")

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def load_config():
    try:
        with open(CONFIG_FILE, "r") as f:
            return json.load(f)
    except Exception as e:
        logger.error(f"Error loading config: {e}")
        return None

def main():
    config = load_config()
    if not config: return

    # Extract Config
    INPUT_FILE = config.get("input_file", "input_urls.xlsx")
    OUTPUT_FILE = config.get("output_file_step1", "results_step1.xlsx")
    MODEL_PATH = config.get("model_path")
    DEVICE = config.get("device_id", -1)
    
    CANDIDATE_LABELS = config.get("candidate_labels", [])
    POSITIVE_LABELS = config.get("positive_labels", [])
    
    step1_config = config.get("step1_prefilter", {})
    FORCE_VALID_KEYWORDS = step1_config.get("force_valid_keywords", [])
    THRESHOLD_VALID = step1_config.get("threshold_valid", 0.85)
    THRESHOLD_INVALID = step1_config.get("threshold_invalid", 0.30)
    
    logger.info("Initializing Validator...")
    validator = ArticleValidator(MODEL_PATH, device=DEVICE)
    
    logger.info(f"Reading {INPUT_FILE}...")
    try:
        df = pd.read_excel(INPUT_FILE)
        # Ensure columns exist
        if "Title" not in df.columns or "URL" not in df.columns:
            logger.error("Input file must have 'Title' and 'URL' columns.")
            if len(df.columns) >= 2:
                logger.warning(f"Columns 'Title'/'URL' not found. Using first two columns: {df.columns[0]}, {df.columns[1]}")
                df.rename(columns={df.columns[0]: "Title", df.columns[1]: "URL"}, inplace=True)
            else:
                return
    except Exception as e:
        logger.error(f"Error reading file {INPUT_FILE}: {e}")
        return

    results = []
    logger.info(f"Processing {len(df)} items...")
    
    for index, row in df.iterrows():
        title = str(row["Title"])
        url = str(row["URL"])
        
        status, label, score, note = validator.prefilter_metadata(
            title, url, 
            CANDIDATE_LABELS, POSITIVE_LABELS, 
            threshold_valid=THRESHOLD_VALID, 
            threshold_invalid=THRESHOLD_INVALID,
            force_valid_keywords=FORCE_VALID_KEYWORDS
        )
        
        results.append({
            "Status": status,
            "Meta-Label": label,
            "Score": score,
            "Note": note
        })
        
        if index % 10 == 0:
            logger.info(f"Processed {index + 1}/{len(df)}")

    # Add results to DF
    results_df = pd.DataFrame(results)
    final_df = pd.concat([df, results_df], axis=1)
    
    try:
        final_df.to_excel(OUTPUT_FILE, index=False)
        logger.info(f"Saved results to {OUTPUT_FILE}")
    except Exception as e:
        logger.error(f"Failed to save results: {e}")

if __name__ == "__main__":
    main()
