import os
import re
import logging
import pandas as pd
import numpy as np

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[
        logging.StreamHandler()
    ]
)

# Standard Category Mapping (lowercase -> standard category name)
STANDARD_CATEGORIES = {
    "restaurant": "Restaurant",
    "restraunt": "Restaurant",
    "cafe": "Cafe",
    "coffee shop": "Cafe",
    "sweet shop": "Sweet Shop",
    "sweets": "Sweet Shop",
    "bakery": "Bakery",
    "bakers": "Bakery",
    "kirana store": "Kirana Store",
    "kirana": "Kirana Store",
    "grocery": "Kirana Store",
    "pharmacy": "Pharmacy",
    "chemist": "Pharmacy",
    "medical clinic": "Medical Clinic",
    "dental clinic": "Dental Clinic",
    "diagnostic lab": "Diagnostic Lab",
    "retail shop": "Retail Shop",
    "garment store": "Garment Store",
    "garments": "Garment Store",
    "electronics shop": "Electronics Shop",
    "electronics": "Electronics Shop",
    "mobile repair shop": "Mobile Repair Shop",
    "mobile repair": "Mobile Repair Shop",
    "salon": "Salon",
    "beauty parlour": "Beauty Parlour",
    "gym": "Gym",
    "fitness centre": "Fitness Centre",
    "educational institute": "Educational Institute",
    "coaching centre": "Coaching Centre",
    "coaching": "Coaching Centre",
    "construction company": "Construction Company",
    "construction": "Construction Company",
    "interior designer": "Interior Designer",
    "real estate agency": "Real Estate Agency",
    "travel agency": "Travel Agency",
    "automobile service centre": "Automobile Service Centre",
    "hotel": "Hotel",
    "hardware store": "Hardware Store",
    "service provider": "Service Provider"
}

# City Standardization Map
CITY_MAP = {
    "bangalore": "Bengaluru",
    "bengaluru": "Bengaluru",
    "delhi": "Delhi",
    "new delhi": "Delhi",
    "mumbai": "Mumbai",
    "bombay": "Mumbai",
    "kolkata": "Kolkata",
    "calcutta": "Kolkata",
    "madras": "Chennai",
    "chennai": "Chennai",
    "pune": "Pune",
    "poona": "Pune",
    "hyderabad": "Hyderabad",
    "ahmedabad": "Ahmedabad",
    "jaipur": "Jaipur",
    "lucknow": "Lucknow",
    "surat": "Surat",
    "chandigarh": "Chandigarh"
}

# State Standardization Map
STATE_MAP = {
    "karnataka": "Karnataka",
    "maharashtra": "Maharashtra",
    "tamil nadu": "Tamil Nadu",
    "tamilnadu": "Tamil Nadu",
    "delhi": "Delhi",
    "nct of delhi": "Delhi",
    "west bengal": "West Bengal",
    "gujarat": "Gujarat",
    "rajasthan": "Rajasthan",
    "uttar pradesh": "Uttar Pradesh",
    "up": "Uttar Pradesh",
    "telangana": "Telangana",
    "andhra pradesh": "Andhra Pradesh",
    "ap": "Andhra Pradesh"
}

def get_project_paths():
    """Resolves project paths dynamically relative to this script's location."""
    script_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.abspath(os.path.join(script_dir, "..", ".."))
    processed_dir = os.path.join(project_root, "data", "processed")
    return processed_dir

def normalize_category(cat_val):
    """Standardizes category names using exact and substring matching."""
    if pd.isna(cat_val):
        return "Other"
    cat_str = str(cat_val).strip()
    if not cat_str:
        return "Other"
    cat_lower = cat_str.lower()
    
    # 1. Exact match in standard dictionary
    if cat_lower in STANDARD_CATEGORIES:
        return STANDARD_CATEGORIES[cat_lower]
        
    # 2. Substring match
    for key, std_val in STANDARD_CATEGORIES.items():
        if key in cat_lower:
            return std_val
            
    # 3. Fallback: Title Case
    return cat_str.title()

def normalize_city(city_val):
    """Cleans and standardizes city names."""
    if pd.isna(city_val):
        return ""
    city_str = str(city_val).strip().lower()
    if city_str in CITY_MAP:
        return CITY_MAP[city_str]
    return str(city_val).strip().title()

def normalize_state(state_val):
    """Cleans and standardizes state names."""
    if pd.isna(state_val):
        return ""
    state_str = str(state_val).strip().lower()
    if state_str in STATE_MAP:
        return STATE_MAP[state_str]
    return str(state_val).strip().title()

def standardize_phone(phone_val):
    """Standardizes Indian phone numbers to '+91 XXXXXXXXXX' format."""
    if pd.isna(phone_val):
        return ""
    phone_str = str(phone_val).strip()
    if not phone_str:
        return ""
        
    # Remove all non-digit characters except '+'
    cleaned = re.sub(r"[^\d+]", "", phone_str)
    
    # Check if it starts with '+91'
    if cleaned.startswith("+91"):
        digits = cleaned[3:]
        if len(digits) == 10:
            return f"+91 {digits}"
        return cleaned
        
    # Check if it starts with '91' and has 12 digits
    if cleaned.startswith("91") and len(cleaned) == 12:
        return f"+91 {cleaned[2:]}"
        
    # Check if starts with local prefix '0' and has 11 digits
    if cleaned.startswith("0") and len(cleaned) == 11:
        return f"+91 {cleaned[1:]}"
        
    # Check if exactly 10 digits
    if len(cleaned) == 10 and cleaned.isdigit():
        return f"+91 {cleaned}"
        
    # Return cleaned version if format is unfamiliar
    return phone_str

def main():
    processed_dir = get_project_paths()
    input_csv = os.path.join(processed_dir, "businesses_master.csv")
    
    if not os.path.exists(input_csv):
        logging.error(f"Merged master dataset not found at: {input_csv}")
        logging.error("Please run merge_json.py first.")
        return
        
    logging.info(f"Loading merged dataset from: {input_csv}")
    df = pd.read_csv(input_csv)
    initial_len = len(df)
    logging.info(f"Loaded {initial_len} records for cleaning.")
    
    # 1. Trim whitespace in string columns
    logging.info("Trimming extra spaces from string columns...")
    for col in df.columns:
        if df[col].dtype == object:
            df[col] = df[col].apply(lambda x: str(x).strip() if pd.notna(x) else x)
            
    # Helper to identify columns case-insensitively
    def get_column_by_aliases(aliases):
        for alias in aliases:
            for col in df.columns:
                if col.lower().replace("_", "").replace(" ", "") == alias.lower():
                    return col
        return None
        
    # Identify key columns
    name_col = get_column_by_aliases(["title", "name", "businessname", "business_name"])
    category_col = get_column_by_aliases(["categoryName", "category", "type"])
    city_col = get_column_by_aliases(["city", "town"])
    state_col = get_column_by_aliases(["state", "province"])
    rating_col = get_column_by_aliases(["rating", "stars", "score", "totalscore", "total_score"])
    reviews_col = get_column_by_aliases(["reviewsCount", "reviews", "review_count", "reviewscount", "reviews_count"])
    phone_col = get_column_by_aliases(["phone", "phoneNumber", "phone_no"])
    
    # 2. Remove empty rows (rows where all columns are empty OR name is empty)
    df = df.dropna(how="all")
    if name_col:
        # Drop rows where name/title is empty
        df = df[df[name_col].notna() & (df[name_col].astype(str).str.strip() != "")]
    else:
        logging.warning("Business Name/Title column not detected. Skipping empty name filtering.")
        
    rows_after_empty_filter = len(df)
    empty_removed = initial_len - rows_after_empty_filter
    logging.info(f"Filtered empty rows. Removed: {empty_removed}")
    
    # 3. Normalize Category
    if category_col:
        logging.info(f"Normalizing category column: '{category_col}'...")
        df[category_col] = df[category_col].apply(normalize_category)
    else:
        logging.warning("Category column not detected. Skipping category normalization.")
        
    # 4. Normalize City & State
    if city_col:
        logging.info(f"Normalizing city column: '{city_col}'...")
        df[city_col] = df[city_col].apply(normalize_city)
    if state_col:
        logging.info(f"Normalizing state column: '{state_col}'...")
        df[state_col] = df[state_col].apply(normalize_state)
        
    # 5. Clean Ratings (Convert to float, remove outside [1.0, 5.0])
    invalid_ratings_count = 0
    if rating_col:
        logging.info(f"Converting and cleaning ratings column: '{rating_col}'...")
        # Force numeric conversion
        df[rating_col] = pd.to_numeric(df[rating_col], errors="coerce")
        # Identify out-of-bound ratings
        invalid_mask = (df[rating_col] < 1.0) | (df[rating_col] > 5.0)
        invalid_ratings_count = int(invalid_mask.sum())
        # Replace invalid ratings with NaN (representing empty/missing value)
        df.loc[invalid_mask, rating_col] = np.nan
        logging.info(f"Set {invalid_ratings_count} invalid ratings to NaN.")
        
        # Standardize and Rename to 'rating'
        df = df.rename(columns={rating_col: "rating"})
        rating_col = "rating"
        logging.info("Renamed ratings column to 'rating'")
    else:
        logging.warning("Ratings column not detected. Skipping ratings cleaning.")
        
    # 6. Clean and convert Reviews Count to integer
    if reviews_col:
        logging.info(f"Converting reviews volume column: '{reviews_col}'...")
        df[reviews_col] = pd.to_numeric(df[reviews_col], errors="coerce").fillna(0).astype(int)
        
        # Standardize and Rename to 'review_count'
        df = df.rename(columns={reviews_col: "review_count"})
        reviews_col = "review_count"
        logging.info("Renamed reviews column to 'review_count'")
    else:
        logging.warning("Reviews column not detected. Skipping reviews conversion.")
        
    # 7. Standardize Phone Numbers
    if phone_col:
        logging.info(f"Standardizing phone numbers in column: '{phone_col}'...")
        df[phone_col] = df[phone_col].apply(standardize_phone)
    else:
        logging.warning("Phone column not detected. Skipping phone number standardization.")
        
    final_len = len(df)
    
    # Save output files
    csv_out = os.path.join(processed_dir, "businesses_master_clean.csv")
    xlsx_out = os.path.join(processed_dir, "businesses_master_clean.xlsx")
    
    try:
        # Save to CSV
        df.to_csv(csv_out, index=False, encoding="utf-8")
        logging.info(f"Successfully saved clean CSV to: {csv_out}")
        
        # Save to Excel
        df.to_excel(xlsx_out, index=False, engine="openpyxl")
        logging.info(f"Successfully saved clean Excel to: {xlsx_out}")
        
        # Log Summary
        print("\n" + "="*50)
        print("CLEANING PIPELINE SUMMARY")
        print("="*50)
        print(f"Original Records:     {initial_len}")
        print(f"Empty Rows Removed:   {empty_removed}")
        print(f"Invalid Ratings:      {invalid_ratings_count} (set to NaN)")
        print(f"Final Clean Records:  {final_len}")
        print("="*50 + "\n")
        
    except Exception as e:
        logging.error(f"Error saving clean datasets: {e}")

if __name__ == "__main__":
    main()
