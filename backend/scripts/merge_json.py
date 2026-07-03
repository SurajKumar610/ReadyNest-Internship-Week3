import os
import glob
import json
import logging
import pandas as pd

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[
        logging.StreamHandler()
    ]
)

def get_project_paths():
    """Resolves project paths dynamically relative to this script's location."""
    script_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.abspath(os.path.join(script_dir, "..", ".."))
    
    raw_dir = os.path.join(project_root, "data", "raw")
    processed_dir = os.path.join(project_root, "data", "processed")
    
    return raw_dir, processed_dir

def load_json_file(file_path):
    """
    Parses a JSON or JSONL file flexibly.
    Handles JSON arrays, keyed lists, single objects, and JSON Lines (JSONL).
    """
    records = []
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            content = f.read().strip()
            if not content:
                return []
            
            # Try parsing as standard JSON
            try:
                data = json.loads(content)
                if isinstance(data, list):
                    records = data
                elif isinstance(data, dict):
                    # Look for lists in common dictionary keys
                    for key in ["results", "data", "items", "listings"]:
                        if key in data and isinstance(data[key], list):
                            records = data[key]
                            break
                    else:
                        # Fallback: look for any list value inside the dict
                        for val in data.values():
                            if isinstance(val, list):
                                records = val
                                break
                        else:
                            # It's a single listing dict
                            records = [data]
            except json.JSONDecodeError:
                # If standard JSON parsing fails, try reading as JSON Lines (JSONL)
                f.seek(0)
                for line_num, line in enumerate(f, 1):
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        records.append(json.loads(line))
                    except json.JSONDecodeError as e:
                        logging.warning(f"Skipping malformed line {line_num} in {os.path.basename(file_path)}: {e}")
    except Exception as e:
        logging.error(f"Failed to read file {file_path}: {e}")
    
    return records

def deduplicate_dataframe(df):
    """
    Deduplicates the DataFrame using:
    1. Place ID (placeId, place_id)
    2. Google Maps URL (url, googleMapsLink, link)
    3. Business Name + Address (fallback)
    """
    if df.empty:
        return df, 0
        
    # Helper to find relevant columns case-insensitively
    def find_cols(keywords):
        return [c for c in df.columns if any(kw in c.lower() for kw in keywords)]
        
    place_id_cols = find_cols(["placeid", "place_id"])
    url_cols = find_cols(["url", "mapslink", "link"])
    name_cols = find_cols(["title", "name", "businessname", "business_name"])
    address_cols = find_cols(["address", "street", "location"])
    
    dedup_keys = []
    for idx, row in df.iterrows():
        # 1. Try Place ID
        pid = None
        for col in place_id_cols:
            val = row[col]
            if pd.notna(val) and str(val).strip():
                pid = str(val).strip()
                break
        if pid:
            dedup_keys.append(f"pid:{pid}")
            continue
            
        # 2. Try URL
        url = None
        for col in url_cols:
            val = row[col]
            if pd.notna(val) and str(val).strip():
                url = str(val).strip()
                break
        if url:
            dedup_keys.append(f"url:{url}")
            continue
            
        # 3. Fallback: Name + Address
        name = ""
        for col in name_cols:
            val = row[col]
            if pd.notna(val) and str(val).strip():
                name = str(val).strip().lower()
                break
        addr = ""
        for col in address_cols:
            val = row[col]
            if pd.notna(val) and str(val).strip():
                addr = str(val).strip().lower()
                break
        
        if name or addr:
            dedup_keys.append(f"name_addr:{name}_{addr}")
        else:
            dedup_keys.append(f"index:{idx}")
            
    df["_dedup_key"] = dedup_keys
    initial_len = len(df)
    
    # Drop duplicates keeping the first occurrence
    df_dedup = df.drop_duplicates(subset=["_dedup_key"], keep="first").copy()
    df_dedup = df_dedup.drop(columns=["_dedup_key"])
    duplicates_removed = initial_len - len(df_dedup)
    
    return df_dedup, duplicates_removed

def main():
    raw_dir, processed_dir = get_project_paths()
    os.makedirs(processed_dir, exist_ok=True)
    
    logging.info("Starting JSON dataset merging process...")
    logging.info(f"Scanning for JSON files in: {raw_dir}")
    
    # Scan for all JSON / JSONL files
    json_patterns = [os.path.join(raw_dir, "*.json"), os.path.join(raw_dir, "*.jsonl")]
    json_files = []
    for pattern in json_patterns:
        json_files.extend(glob.glob(pattern))
        
    if not json_files:
        logging.warning("No JSON or JSONL files found in data/raw/ directory.")
        logging.info("Exiting merging process.")
        return
        
    logging.info(f"Found {len(json_files)} files to process.")
    
    all_records = []
    files_processed = 0
    
    for file_path in json_files:
        filename = os.path.basename(file_path)
        logging.info(f"Processing: {filename}")
        records = load_json_file(file_path)
        if records:
            all_records.extend(records)
            files_processed += 1
            logging.info(f"Loaded {len(records)} records from {filename}.")
        else:
            logging.warning(f"No records parsed or file failed: {filename}")
            
    total_loaded = len(all_records)
    logging.info(f"Total raw businesses loaded: {total_loaded} across {files_processed} files.")
    
    if not all_records:
        logging.warning("No data loaded. Master datasets will not be created.")
        return
        
    # Convert to DataFrame
    df = pd.DataFrame(all_records)
    
    # Deduplicate
    df_dedup, duplicates_removed = deduplicate_dataframe(df)
    final_count = len(df_dedup)
    
    logging.info(f"Deduplication complete. Duplicates removed: {duplicates_removed}")
    logging.info(f"Final master business count: {final_count}")
    
    # Save output
    csv_out = os.path.join(processed_dir, "businesses_master.csv")
    xlsx_out = os.path.join(processed_dir, "businesses_master.xlsx")
    
    try:
        # Save to CSV
        df_dedup.to_csv(csv_out, index=False, encoding="utf-8")
        logging.info(f"Successfully saved master CSV to: {csv_out}")
        
        # Save to Excel
        df_dedup.to_excel(xlsx_out, index=False, engine="openpyxl")
        logging.info(f"Successfully saved master Excel to: {xlsx_out}")
        
        # Log Summary
        print("\n" + "="*50)
        print("MERGE STATISTICS SUMMARY")
        print("="*50)
        print(f"Files Processed:      {files_processed}")
        print(f"Businesses Loaded:    {total_loaded}")
        print(f"Duplicates Removed:   {duplicates_removed}")
        print(f"Final Unique Count:   {final_count}")
        print("="*50 + "\n")
        
    except Exception as e:
        logging.error(f"Error saving processed datasets: {e}")

if __name__ == "__main__":
    main()
