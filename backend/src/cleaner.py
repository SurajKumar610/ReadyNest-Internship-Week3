import os
import json
import re
import pandas as pd
import numpy as np

# Column mapping configuration (lowercased key -> standard column name)
COLUMN_MAP_RULES = {
    # Required
    "businessname": "Business Name", "name": "Business Name", "b_name": "Business Name", "business_name": "Business Name", "companyname": "Business Name", "company_name": "Business Name", "title": "Business Name",
    "category": "Category", "industry": "Category", "type": "Category", "businesstype": "Category", "business_type": "Category", "categoryname": "Category",
    "rating": "Rating", "score": "Rating", "stars": "Rating", "googlerating": "Rating", "google_rating": "Rating", "totalscore": "Rating",
    "reviews": "Reviews", "reviewcount": "Reviews", "review_count": "Reviews", "numberofreviews": "Reviews", "number_of_reviews": "Reviews", "noofreviews": "Reviews", "no_of_reviews": "Reviews", "reviewscount": "Reviews",
    "website": "Website", "web": "Website", "link": "Website", "site": "Website",
    "phonenumber": "Phone Number", "phone": "Phone Number", "mobile": "Phone Number", "contact": "Phone Number", "phoneno": "Phone Number", "phone_no": "Phone Number", "mobileno": "Phone Number", "mobile_no": "Phone Number", "contact_no": "Phone Number",
    "address": "Address", "street": "Address",
    "city": "City", "town": "City", "district": "City",
    
    # Optional
    "subcategory": "Sub Category", "sub_category": "Sub Category",
    "state": "State", "province": "State", "region": "State",
    "pincode": "Pincode", "pin_code": "Pincode", "pin": "Pincode", "zip": "Pincode", "zipcode": "Pincode", "postalcode": "Pincode", "postal_code": "Pincode",
    "latitude": "Latitude", "lat": "Latitude",
    "longitude": "Longitude", "lng": "Longitude", "lon": "Longitude",
    "email": "Email", "e-mail": "Email", "emailaddress": "Email", "email_address": "Email",
    "googlemapslink": "Google Maps Link", "mapslink": "Google Maps Link", "maplink": "Google Maps Link", "gmapslink": "Google Maps Link", "google_maps_link": "Google Maps Link", "url": "Google Maps Link",
    "verifiedbusiness": "Verified Business", "verified": "Verified Business", "isverified": "Verified Business", "is_verified": "Verified Business",
    "opennow": "Open Now", "open_now": "Open Now", "isopen": "Open Now",
    "openinghours": "Opening Hours", "opening_hours": "Opening Hours", "hours": "Opening Hours", "timings": "Opening Hours",
    "pricelevel": "Price Level", "price_level": "Price Level", "price": "Price Level", "cost": "Price Level",
    "photoscount": "Photos Count", "photos_count": "Photos Count", "photos": "Photos Count", "images": "Photos Count",
    "businessdescription": "Business Description", "description": "Business Description", "about": "Business Description",
    "establishedyear": "Established Year", "established_year": "Established Year", "estyear": "Established Year", "founded": "Established Year",
    "gstavailable": "GST Available", "gst_available": "GST Available", "gst": "GST Available",
    "whatsappbusiness": "WhatsApp Business", "whatsapp": "WhatsApp Business", "whatsapp_business": "WhatsApp Business",
    "upiaccepted": "UPI Accepted", "upi_accepted": "UPI Accepted", "upi": "UPI Accepted",
    "googlebusinessverified": "Google Business Verified", "google_business_verified": "Google Business Verified"
}

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

REQUIRED_COLUMNS = ["Business Name", "Category", "Rating", "Reviews", "Website", "Phone Number", "Address", "City"]
STRICT_REQUIRED = ["Business Name", "Category", "Address", "City"]


def get_mapped_columns(columns: list[str]) -> dict[str, str]:
    """
    Computes a mapping from original column names to standard column names.
    Ensures that each standard target column is mapped to at most one original column,
    based on a predefined priority order, thereby avoiding duplicate column names.
    Loads mapping configuration from config/column_mapping.json if available.
    """
    # Load configuration
    backend_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
    config_path = os.path.join(backend_dir, "config", "column_mapping.json")
    
    column_priorities = {}
    if os.path.exists(config_path):
        try:
            with open(config_path, "r") as f:
                column_priorities = json.load(f)
        except Exception:
            pass
            
    if not column_priorities:
        # Fallback to hardcoded list if file can't be loaded
        column_priorities = {
            "Business Name": ["businessname", "name", "business_name", "companyname", "company_name", "title", "b_name"],
            "Category": ["category", "categoryname", "category_name", "businesstype", "business_type", "industry", "type"],
            "Rating": ["rating", "score", "stars", "googlerating", "google_rating", "totalscore"],
            "Reviews": ["review_count", "reviewcount", "numberofreviews", "number_of_reviews", "noofreviews", "no_of_reviews", "reviewscount", "reviews"],
            "Website": ["website", "web", "link", "site"],
            "Phone Number": ["phone_number", "phonenumber", "phone", "mobile", "contact", "phoneno", "phone_no", "mobileno", "mobile_no", "contact_no"],
            "Address": ["address", "street"],
            "City": ["city", "town", "district"],
            "Sub Category": ["subcategory", "sub_category", "subtitle"],
            "State": ["state", "province", "region"],
            "Pincode": ["pincode", "pin_code", "pin", "zip", "zipcode", "postalcode", "postal_code"],
            "Latitude": ["latitude", "lat"],
            "Longitude": ["longitude", "lng", "lon"],
            "Email": ["email", "e-mail", "emailaddress", "email_address"],
            "Google Maps Link": ["googlemapslink", "mapslink", "maplink", "gmapslink", "google_maps_link", "url"],
            "Verified Business": ["verifiedbusiness", "verified", "isverified", "is_verified"],
            "Open Now": ["opennow", "open_now", "isopen"],
            "Opening Hours": ["openinghours", "opening_hours", "hours", "timings"],
            "Price Level": ["pricelevel", "price_level", "price", "cost"],
            "Photos Count": ["photoscount", "photos_count", "photos", "images", "imagescount", "images_count"],
            "Business Description": ["businessdescription", "description", "about", "hoteldescription", "hotel_description"],
            "Established Year": ["establishedyear", "established_year", "estyear", "founded"],
            "GST Available": ["gstavailable", "gst_available", "gst"],
            "WhatsApp Business": ["whatsappbusiness", "whatsapp", "whatsapp_business"],
            "UPI Accepted": ["upiaccepted", "upi_accepted", "upi"],
            "Google Business Verified": ["googlebusinessverified", "google_business_verified"]
        }

    # Normalize dataframe columns
    norm_to_orig = {}
    for col in columns:
        norm = str(col).lower().replace(" ", "").replace("_", "").replace("-", "")
        # Keep the first occurrence of a normalized column name
        if norm not in norm_to_orig:
            norm_to_orig[norm] = col

    mapped_cols = {}
    # Find the best match for each standard target column
    for target, sources in column_priorities.items():
        for src in sources:
            if src in norm_to_orig:
                orig_col = norm_to_orig[src]
                mapped_cols[orig_col] = target
                break

    # For any columns not mapped to standard names, map to themselves
    # Make sure we don't map them to a name that's already used as a target
    used_targets = set(mapped_cols.values())
    for col in columns:
        if col not in mapped_cols:
            if col not in used_targets:
                mapped_cols[col] = str(col)
            else:
                # If there's a conflict, append a suffix to avoid duplicates
                suffix = 1
                new_col = f"{col}_{suffix}"
                while new_col in used_targets or new_col in columns:
                    suffix += 1
                    new_col = f"{col}_{suffix}"
                mapped_cols[col] = new_col

    return mapped_cols


def clean_dataset(df: pd.DataFrame) -> tuple[pd.DataFrame, dict]:
    """
    Validates, cleans, and standardizes a Google Maps business dataset.
    Returns the cleaned DataFrame and a dictionary of cleaning statistics.
    """
    stats = {
        "original_records": int(len(df)),
        "duplicates_removed": 0,
        "empty_names_removed": 0,
        "invalid_ratings_corrected": 0,
        "negative_reviews_corrected": 0,
        "missing_websites_marked": 0,
        "missing_phones_logged": 0,
        "categories_standardized": 0,
        "final_clean_records": 0
    }
    
    # Copy DataFrame to avoid modifying original in-place before operations
    df = df.copy()
    
    # 0. Extract Latitude and Longitude from 'location' if they are missing
    if "Latitude" not in df.columns or "Longitude" not in df.columns:
        loc_col = None
        for col in df.columns:
            if str(col).lower().strip() == "location":
                loc_col = col
                break
        if loc_col:
            latitudes = []
            longitudes = []
            for val in df[loc_col]:
                lat, lng = np.nan, np.nan
                if pd.notna(val) and str(val).strip():
                    val_str = str(val).strip()
                    try:
                        # Extract lat and lng using regex to handle single/double quotes and float values
                        lat_match = re.search(r"['\"]lat['\"]\s*:\s*([\d.-]+)", val_str)
                        lng_match = re.search(r"['\"]lng['\"]\s*:\s*([\d.-]+)", val_str)
                        if not lat_match or not lng_match:
                            # Try without quotes
                            lat_match = re.search(r"lat\s*:\s*([\d.-]+)", val_str)
                            lng_match = re.search(r"lng\s*:\s*([\d.-]+)", val_str)
                        if lat_match:
                            lat = float(lat_match.group(1))
                        if lng_match:
                            lng = float(lng_match.group(1))
                    except Exception:
                        pass
                latitudes.append(lat)
                longitudes.append(lng)
            df["Latitude"] = latitudes
            df["Longitude"] = longitudes

    # 1. Map columns case-insensitively and by common aliases
    mapped_cols = get_mapped_columns(df.columns)
    df = df.rename(columns=mapped_cols)
    
    # Ensure Address and City are clean string types and handle NaNs safely
    if "Address" in df.columns:
        df["Address"] = df["Address"].fillna("").astype(str).str.strip()
    if "City" in df.columns:
        df["City"] = df["City"].fillna("").astype(str).str.strip()
        
    # Clean Pincode if present (remove trailing .0 if stored as float)
    if "Pincode" in df.columns:
        df["Pincode"] = df["Pincode"].apply(
            lambda x: str(int(float(x))) if pd.notna(x) and str(x).strip() != "" and str(x).strip().lower() != "nan" and re.match(r"^\d+(\.0+)?$", str(x).strip()) else (str(x).strip() if pd.notna(x) else "")
        )
    
    # Auto-fill missing required/optional fields with safe defaults to prevent KeyErrors
    from src.analyzer import OPTIONAL_FIELDS
    
    # Default initializations
    auto_fill_defaults = {
        "Rating": np.nan,
        "Reviews": 0,
        "Website": "No Website",
        "Phone Number": "",
        "Address": "",
        "City": ""
    }
    
    for col in REQUIRED_COLUMNS:
        if col not in df.columns:
            df[col] = auto_fill_defaults.get(col, "")
            
    for col in OPTIONAL_FIELDS:
        if col not in df.columns:
            # For verification fields, default to "Unknown" when not present in dataset
            if col in ["Verified Business", "Google Business Verified"]:
                df[col] = "Unknown"
            else:
                df[col] = ""
        else:
            # If the column does exist, replace NaN or empty values with "Unknown" for verification fields
            if col in ["Verified Business", "Google Business Verified"]:
                df[col] = df[col].apply(
                    lambda x: "Unknown" if pd.isna(x) or str(x).strip() == "" or str(x).strip().lower() in ["nan", "none", "unknown"] else str(x).strip()
                )
    
    # 2. Check for missing strictly REQUIRED columns
    strict_missing = [req for req in STRICT_REQUIRED if req not in df.columns or df[req].isna().all()]
    if strict_missing:
        raise ValueError(f"Missing required columns in uploaded dataset: {', '.join(strict_missing)}")
        
    # We copy the dataframe to prevent modifying the original
    cleaned_df = df.copy()
    
    # Add generated logging columns
    cleaned_df["is_cleaned"] = False
    cleaned_df["cleaning_flags"] = ""
    
    # Helper to add cleaning flag to a row
    def add_flag(idx, flag):
        cleaned_df.at[idx, "is_cleaned"] = True
        current = cleaned_df.at[idx, "cleaning_flags"]
        if current:
            cleaned_df.at[idx, "cleaning_flags"] = current + ", " + flag
        else:
            cleaned_df.at[idx, "cleaning_flags"] = flag

    # 3. Drop rows with empty Business Name
    # Save indices before dropping for stats
    initial_len = len(cleaned_df)
    # Filter out nulls, NaNs, and whitespace-only strings
    valid_names_mask = cleaned_df["Business Name"].astype(str).str.strip().replace("nan", "") != ""
    cleaned_df = cleaned_df[valid_names_mask].copy()
    stats["empty_names_removed"] = int(initial_len - len(cleaned_df))
    
    # 4. Remove duplicate entries
    # Keep track of duplicates (name + address + city)
    dup_mask = cleaned_df.duplicated(subset=["Business Name", "Address", "City"], keep="first")
    stats["duplicates_removed"] = int(dup_mask.sum())
    cleaned_df = cleaned_df[~dup_mask].copy().reset_index(drop=True)
    
    # 5. Clean Ratings: must be float, clamp to [1.0, 5.0]
    for idx, row in cleaned_df.iterrows():
        val = row["Rating"]
        try:
            # Check if null/NaN
            if pd.isna(val) or str(val).strip().lower() in ["", "nan", "none"]:
                cleaned_df.at[idx, "Rating"] = np.nan
                continue
            rating_val = float(val)
            if rating_val < 1.0 or rating_val > 5.0:
                clamped = max(1.0, min(5.0, rating_val))
                cleaned_df.at[idx, "Rating"] = clamped
                stats["invalid_ratings_corrected"] += 1
                add_flag(idx, "Invalid Rating Corrected")
            else:
                cleaned_df.at[idx, "Rating"] = rating_val
        except (ValueError, TypeError):
            cleaned_df.at[idx, "Rating"] = np.nan
            stats["invalid_ratings_corrected"] += 1
            add_flag(idx, "Invalid Rating Corrected")
            
    # 6. Clean Reviews: must be int, reviews < 0 force to positive absolute value
    for idx, row in cleaned_df.iterrows():
        val = row["Reviews"]
        try:
            if pd.isna(val) or str(val).strip().lower() in ["", "nan", "none"]:
                cleaned_df.at[idx, "Reviews"] = 0
                continue
            rev_val = int(float(val))
            if rev_val < 0:
                cleaned_df.at[idx, "Reviews"] = abs(rev_val)
                stats["negative_reviews_corrected"] += 1
                add_flag(idx, "Negative Reviews Corrected")
            else:
                cleaned_df.at[idx, "Reviews"] = rev_val
        except (ValueError, TypeError):
            cleaned_df.at[idx, "Reviews"] = 0
            stats["negative_reviews_corrected"] += 1
            add_flag(idx, "Negative Reviews Corrected")
            
    # 7. Clean Website: mark empty values as "No Website"
    for idx, row in cleaned_df.iterrows():
        val = row["Website"]
        if pd.isna(val) or str(val).strip().lower() in ["", "nan", "none"]:
            cleaned_df.at[idx, "Website"] = "No Website"
            stats["missing_websites_marked"] += 1
            add_flag(idx, "Missing Website")
        else:
            cleaned_df.at[idx, "Website"] = str(val).strip()
            
    # 8. Clean Phone: check if empty, add cleaning flag
    for idx, row in cleaned_df.iterrows():
        val = row["Phone Number"]
        if pd.isna(val) or str(val).strip().lower() in ["", "nan", "none"]:
            cleaned_df.at[idx, "Phone Number"] = ""
            stats["missing_phones_logged"] += 1
            add_flag(idx, "Missing Phone")
        else:
            cleaned_df.at[idx, "Phone Number"] = str(val).strip()
            
    # 9. Standardize categories
    for idx, row in cleaned_df.iterrows():
        val = row["Category"]
        if pd.isna(val) or str(val).strip().lower() in ["", "nan", "none"]:
            cleaned_df.at[idx, "Category"] = "Other"
            continue
        cat_lower = str(val).strip().lower()
        if cat_lower in STANDARD_CATEGORIES:
            std_cat = STANDARD_CATEGORIES[cat_lower]
            if str(val).strip() != std_cat:
                cleaned_df.at[idx, "Category"] = std_cat
                stats["categories_standardized"] += 1
                add_flag(idx, "Category Standardized")
        else:
            # Set to title case as default
            cleaned_df.at[idx, "Category"] = str(val).strip().title()
            
    stats["final_clean_records"] = int(len(cleaned_df))
    
    # Save stats and clean dataset (resolving dynamically relative to this file)
    backend_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
    data_dir = os.path.join(backend_dir, "data")
    os.makedirs(data_dir, exist_ok=True)
    
    cleaned_df.to_csv(os.path.join(data_dir, "clean_listings.csv"), index=False)
    with open(os.path.join(data_dir, "cleaning_stats.json"), "w") as f:
        json.dump(stats, f, indent=2)
        
    return cleaned_df, stats

