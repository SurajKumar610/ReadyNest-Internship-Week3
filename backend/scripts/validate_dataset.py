import os
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
    
    processed_dir = os.path.join(project_root, "data", "processed")
    exports_dir = os.path.join(project_root, "data", "exports")
    
    return processed_dir, exports_dir

def analyze_completeness(df, col_name):
    """Calculates missing count and percentage for a column."""
    if col_name not in df.columns:
        return len(df), 100.0
        
    series = df[col_name]
    # Check both NaN and empty string
    missing_mask = series.isna() | (series.astype(str).str.strip() == "") | (series.astype(str).str.strip().str.lower() == "nan")
    missing_count = int(missing_mask.sum())
    missing_pct = (missing_count / len(df)) * 100 if len(df) > 0 else 0.0
    return missing_count, missing_pct

def main():
    processed_dir, exports_dir = get_project_paths()
    input_csv = os.path.join(processed_dir, "businesses_master_clean.csv")
    
    if not os.path.exists(input_csv):
        logging.error(f"Cleaned master dataset not found at: {input_csv}")
        logging.error("Please run clean_dataset.py first.")
        return
        
    logging.info(f"Loading cleaned dataset for validation from: {input_csv}")
    df = pd.read_csv(input_csv)
    total_records = len(df)
    logging.info(f"Loaded {total_records} records for validation audits.")
    
    if total_records == 0:
        logging.warning("The dataset is empty. Validation report will contain zero data.")
        
    # Column identification by aliases
    def get_col(aliases):
        for alias in aliases:
            for col in df.columns:
                if col.lower().replace("_", "").replace(" ", "") == alias.lower():
                    return col
        return None
        
    name_col = get_col(["title", "name", "businessname", "business_name"])
    place_id_col = get_col(["placeid", "place_id"])
    phone_col = get_col(["phone", "phoneNumber", "phone_no"])
    website_col = get_col(["website", "url", "link", "site"])
    rating_col = get_col(["rating", "totalscore", "total_score", "stars", "score"])
    address_col = get_col(["address", "street", "location"])
    category_col = get_col(["categoryName", "category", "type"])
    city_col = get_col(["city", "town"])
    
    # 1. Calculate missing data metrics
    phone_missing, phone_pct = analyze_completeness(df, phone_col) if phone_col else (total_records, 100.0)
    web_missing, web_pct = analyze_completeness(df, website_col) if website_col else (total_records, 100.0)
    rating_missing, rating_pct = analyze_completeness(df, rating_col) if rating_col else (total_records, 100.0)
    addr_missing, addr_pct = analyze_completeness(df, address_col) if address_col else (total_records, 100.0)
    
    # 2. Check duplicates
    dup_place_ids = 0
    if place_id_col and place_id_col in df.columns:
        place_series = df[place_id_col].dropna()
        dup_place_ids = int(place_series.duplicated().sum())
        
    dup_names = 0
    if name_col and name_col in df.columns:
        name_series = df[name_col].dropna()
        dup_names = int(name_series.duplicated().sum())
        
    # 3. Calculate distributions
    cat_dist = pd.Series(dtype=int)
    if category_col and category_col in df.columns:
        cat_dist = df[category_col].value_counts()
        
    city_dist = pd.Series(dtype=int)
    if city_col and city_col in df.columns:
        city_dist = df[city_col].value_counts()
        
    # Write plain text report
    txt_report = []
    txt_report.append("="*60)
    txt_report.append("GOOGLE MAPS BUSINESS DATASET VALIDATION REPORT")
    txt_report.append("="*60)
    txt_report.append(f"Total Businesses: {total_records}\n")
    
    txt_report.append("DATA COMPLETENESS AUDIT:")
    txt_report.append(f"- Missing Phone Numbers: {phone_missing} ({phone_pct:.2f}%)")
    txt_report.append(f"- Missing Websites:      {web_missing} ({web_pct:.2f}%)")
    txt_report.append(f"- Missing Ratings:       {rating_missing} ({rating_pct:.2f}%)")
    txt_report.append(f"- Missing Addresses:     {addr_missing} ({addr_pct:.2f}%)\n")
    
    txt_report.append("DUPLICATIONS AUDIT:")
    txt_report.append(f"- Duplicate Place IDs:   {dup_place_ids}")
    txt_report.append(f"- Duplicate Names:       {dup_names}\n")
    
    txt_report.append("TOP BUSINESS CATEGORIES:")
    for cat, count in cat_dist.head(15).items():
        txt_report.append(f"- {cat}: {count}")
    txt_report.append("")
    
    txt_report.append("TOP CITIES DISTRIBUTION:")
    for city, count in city_dist.head(15).items():
        txt_report.append(f"- {city}: {count}")
    txt_report.append("="*60)
    
    txt_report_str = "\n".join(txt_report)
    
    # Write Markdown report
    md_report = []
    md_report.append("# Google Maps Business Dataset Validation Report\n")
    md_report.append(f"**Total Verified Records:** `{total_records}`\n")
    
    md_report.append("## 📈 Data Completeness Audit\n")
    md_report.append("| Field | Missing Count | Completeness | Status |")
    md_report.append("| :--- | :---: | :---: | :---: |")
    
    def get_status_emoji(pct):
        if pct < 10: return "🟢 Good"
        if pct < 40: return "🟡 Warning"
        return "🔴 Critical"
        
    md_report.append(f"| Phone Numbers | {phone_missing} | {100 - phone_pct:.1f}% | {get_status_emoji(phone_pct)} |")
    md_report.append(f"| Websites | {web_missing} | {100 - web_pct:.1f}% | {get_status_emoji(web_pct)} |")
    md_report.append(f"| Customer Ratings | {rating_missing} | {100 - rating_pct:.1f}% | {get_status_emoji(rating_pct)} |")
    md_report.append(f"| Addresses | {addr_missing} | {100 - addr_pct:.1f}% | {get_status_emoji(addr_pct)} |")
    md_report.append("\n")
    
    md_report.append("## 🔍 Duplications Audit\n")
    md_report.append(f"- **Duplicate Place IDs**: `{dup_place_ids}` (Indicates exact scraper overlap)")
    md_report.append(f"- **Duplicate Business Names**: `{dup_names}` (Could represent multi-branch chains)\n")
    
    md_report.append("## 🏷️ Category Distribution (Top 15)\n")
    md_report.append("| Category | Listings Count | Percentage |")
    md_report.append("| :--- | :---: | :---: |")
    for cat, count in cat_dist.head(15).items():
        pct = (count / total_records) * 100 if total_records > 0 else 0.0
        md_report.append(f"| {cat} | {count} | {pct:.1f}% |")
    md_report.append("\n")
    
    md_report.append("## 📍 City Distribution (Top 15)\n")
    md_report.append("| City | Listings Count | Percentage |")
    md_report.append("| :--- | :---: | :---: |")
    for city, count in city_dist.head(15).items():
        pct = (count / total_records) * 100 if total_records > 0 else 0.0
        md_report.append(f"| {city} | {count} | {pct:.1f}% |")
        
    md_report_str = "\n".join(md_report)
    
    # Save files
    txt_out = os.path.join(exports_dir, "validation_report.txt")
    md_out = os.path.join(exports_dir, "validation_report.md")
    
    try:
        os.makedirs(exports_dir, exist_ok=True)
        
        # Save TXT
        with open(txt_out, "w", encoding="utf-8") as f:
            f.write(txt_report_str)
        logging.info(f"Successfully saved text report to: {txt_out}")
        
        # Save MD
        with open(md_out, "w", encoding="utf-8") as f:
            f.write(md_report_str)
        logging.info(f"Successfully saved markdown report to: {md_out}")
        
        # Print Text Report to Console
        print("\n" + txt_report_str + "\n")
        
    except Exception as e:
        logging.error(f"Error saving validation reports: {e}")

if __name__ == "__main__":
    main()
