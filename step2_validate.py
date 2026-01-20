import pandas as pd
import logging
from concurrent.futures import ThreadPoolExecutor, as_completed
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
    # Check if we should use the output from Step 1 as input, or the raw input
    # For a pipeline, usually Step 2 runs on Step 1's output, filtering only "Valid" or "Not Sure"
    # But to keep it simple and flexible, let's default to reading the MAIN input file, 
    # OR we could add logic to read step1 output. 
    # For this handover, let's stick to the explicit input file defined for step 2 in case they run independently
    # or just reuse the main input file.
    INPUT_FILE = config.get("input_file", "input_urls.xlsx")
    OUTPUT_FILE = config.get("output_file_step2", "results_step2.xlsx")
    
    MODEL_PATH = config.get("model_path")
    DEVICE = config.get("device_id", -1)
    
    CANDIDATE_LABELS = config.get("candidate_labels", [])
    POSITIVE_LABELS = config.get("positive_labels", [])
    
    scraping_config = config.get("step2_scraping", {})
    CONFIDENCE_THRESHOLD = scraping_config.get("confidence_threshold", 0.60)
    MAX_WORKERS = scraping_config.get("max_workers", 4)
    # Timeout is handled in core_validator, passed via property or init? 
    # core_validator currently accepts timeout in init? No, it hardcodes self.timeout=25.
    # We might want to update core_validator to accept timeout, but for now we'll leave it 
    # or assume the engineer will modify core logic if they need deep timeout changes.
    
    logger.info("Initializing Validator...")
    validator = ArticleValidator(MODEL_PATH, device=DEVICE)
    
    logger.info(f"Reading {INPUT_FILE}...")
    try:
        df = pd.read_excel(INPUT_FILE)
        if "URL" not in df.columns:
             df.columns = ["URL"] if len(df.columns) == 1 else ["URL"] + list(df.columns[1:])
    except Exception as e:
        logger.error(f"Error reading file: {e}")
        return

    urls = df["URL"].astype(str).tolist()
    results_map = {}
    
    logger.info(f"Processing {len(urls)} URLs...")
    
    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        future_to_idx = {
            executor.submit(
                validator.validate_url, 
                url, 
                CANDIDATE_LABELS, 
                POSITIVE_LABELS, 
                CONFIDENCE_THRESHOLD
            ): idx 
            for idx, url in enumerate(urls)
        }
        
        for future in as_completed(future_to_idx):
            idx = future_to_idx[future]
            try:
                status, label, score, _, note = future.result()
                results_map[idx] = (status, label, note)
                if idx % 5 == 0: logger.info(f"Processed {idx}")
            except Exception as e:
                logger.error(f"Error on index {idx}: {e}")
                results_map[idx] = ("No", "Error", str(e))
    
    # Assemble results
    is_rel, topics, notes = [], [], []
    for i in range(len(df)):
        res = results_map.get(i, ("No", "Not Processed", ""))
        is_rel.append(res[0])
        topics.append(res[1])
        notes.append(res[2])
        
    df["Is Relevant"] = is_rel
    df["Topic"] = topics
    df["Notes"] = notes
    
    df.to_excel(OUTPUT_FILE, index=False)
    logger.info(f"Saved to {OUTPUT_FILE}")

if __name__ == "__main__":
    main()
