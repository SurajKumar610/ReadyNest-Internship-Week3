import os
import json
import pandas as pd
import numpy as np

DEFAULT_SCORING = {
    "weights": {
        "website_missing": 40,
        "rating_under_2_5": 20,
        "rating_2_5_to_3_49": 15,
        "rating_3_5_to_3_99": 10,
        "rating_above_4_0": 0,
        "reviews_under_10": 15,
        "reviews_10_to_49": 10,
        "reviews_50_to_99": 5,
        "reviews_above_100": 0,
        "phone_missing": 5,
        "category_weights": {
            "Restaurant": 8, "Cafe": 8, "Sweet Shop": 8, "Bakery": 8,
            "Retail Shop": 8, "Kirana Store": 8, "Garment Store": 8,
            "Electronics Shop": 8, "Mobile Repair Shop": 8, "Salon": 8,
            "Beauty Parlour": 8, "Gym": 8, "Fitness Centre": 8,
            "Medical Clinic": 10, "Hospital": 10, "Dental Clinic": 10,
            "Diagnostic Lab": 10, "Educational Institute": 10, "Coaching Centre": 10,
            "Construction Company": 10, "Interior Designer": 10, "Real Estate Agency": 10,
            "Travel Agency": 6, "Automobile Service Centre": 8, "Hotel": 8,
            "Pharmacy": 10, "Hardware Store": 8, "Service Provider": 5
        },
        "default_category_weight": 5,
        "verified_bonus_deduction": 10
    }
}

OPTIONAL_FIELDS = [
    "Sub Category", "State", "Pincode", "Latitude", "Longitude", "Email", 
    "Google Maps Link", "Verified Business", "Open Now", "Opening Hours", 
    "Price Level", "Photos Count", "Business Description", "Established Year", 
    "GST Available", "WhatsApp Business", "UPI Accepted", "Google Business Verified"
]

def load_scoring_config() -> dict:
    """Loads opportunity scoring config from config/scoring.json, fallback to defaults."""
    backend_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
    config_path = os.path.join(backend_dir, "config", "scoring.json")
    if os.path.exists(config_path):
        try:
            with open(config_path, "r") as f:
                return json.load(f)
        except Exception:
            pass
    return DEFAULT_SCORING

def calculate_scores(df: pd.DataFrame) -> pd.DataFrame:
    """
    Computes Digital Growth Opportunity Score (0-100) and Data Quality Score (0-100)
    for every listing in the dataframe. Also appends Opportunity Level, Website Status, 
    Recommendation Reason, Has Website, and Missing Phone.
    """
    config = load_scoring_config()
    weights = config.get("weights", DEFAULT_SCORING["weights"])
    
    # Pre-populate some derived columns
    df["Has Website"] = df["Website"].astype(str).str.strip().str.lower() != "no website"
    df["Missing Phone"] = df["Phone Number"].astype(str).str.strip() == ""
    df["Website Status"] = df["Has Website"].map({True: "Has Website", False: "No Website"})
    
    opp_scores = []
    opp_levels = []
    dq_scores = []
    rec_reasons = []
    
    for idx, row in df.iterrows():
        # --- 1. Digital Growth Opportunity Score ---
        opp_score = 0
        
        # Website Missing Weight
        if not row["Has Website"]:
            opp_score += weights.get("website_missing", 40)
            
        # Rating Weight
        rating = row["Rating"]
        if pd.isna(rating):
            opp_score += weights.get("rating_under_2_5", 20)
        else:
            rating = float(rating)
            if rating < 2.5:
                opp_score += weights.get("rating_under_2_5", 20)
            elif rating < 3.5:
                opp_score += weights.get("rating_2_5_to_3_49", 15)
            elif rating < 4.0:
                opp_score += weights.get("rating_3_5_to_3_99", 10)
                
        # Reviews Weight
        reviews = row["Reviews"]
        try:
            reviews_val = int(reviews)
            if reviews_val < 10:
                opp_score += weights.get("reviews_under_10", 15)
            elif reviews_val < 50:
                opp_score += weights.get("reviews_10_to_49", 10)
            elif reviews_val < 100:
                opp_score += weights.get("reviews_50_to_99", 5)
        except (ValueError, TypeError):
            opp_score += weights.get("reviews_under_10", 15)
            
        # Phone Missing Weight
        if row["Missing Phone"]:
            opp_score += weights.get("phone_missing", 5)
            
        # Category Weight
        cat = row["Category"]
        cat_weights = weights.get("category_weights", DEFAULT_SCORING["weights"]["category_weights"])
        cat_weight = cat_weights.get(cat, weights.get("default_category_weight", 5))
        opp_score += cat_weight
        
        # Verified Business Bonus (prevent excellent businesses from appearing as opportunities)
        verified = str(row.get("Verified Business", "No")).strip().lower() in ["yes", "true"]
        is_excellent = row["Has Website"] and not pd.isna(rating) and float(rating) >= 4.2 and int(row["Reviews"]) >= 100
        if verified and is_excellent:
            opp_score -= weights.get("verified_bonus_deduction", 10)
            
        opp_score = max(0, min(100, opp_score))
        opp_scores.append(opp_score)
        
        # Determine Level
        if opp_score >= 90:
            level = "Excellent Opportunity"
        elif opp_score >= 75:
            level = "High Opportunity"
        elif opp_score >= 60:
            level = "Medium Opportunity"
        elif opp_score >= 40:
            level = "Low Opportunity"
        else:
            level = "Digitally Established"
        opp_levels.append(level)
        
        # Generate Recommendation Reason
        if not row["Has Website"]:
            if not pd.isna(rating) and float(rating) >= 4.2:
                reason = "No Website with excellent customer reputation."
            elif not pd.isna(rating) and float(rating) >= 3.5:
                reason = "High ratings but missing digital presence."
            else:
                reason = "Few reviews and no website."
        else:
            if not pd.isna(rating) and float(rating) < 3.5:
                reason = "Website exists but reputation needs improvement."
            else:
                reason = "Website exists with healthy digital engagement."
        rec_reasons.append(reason)
        
        # --- 2. Data Quality Score ---
        dq_score = 100
        
        # Missing Required Fields Deductions
        if not row["Has Website"]:
            dq_score -= 20
        if row["Missing Phone"]:
            dq_score -= 15
        if pd.isna(row.get("Address")) or str(row.get("Address")).strip() == "":
            dq_score -= 10
        if pd.isna(row.get("City")) or str(row.get("City")).strip() == "":
            dq_score -= 10
        if pd.isna(row.get("Rating")):
            dq_score -= 10
            
        # Deduct for cleaning operations applied (obtained from row metadata)
        flags = str(row.get("cleaning_flags", ""))
        if "Invalid Rating Corrected" in flags:
            dq_score -= 10
        if "Negative Reviews Corrected" in flags:
            dq_score -= 10
        if "Category Standardized" in flags:
            dq_score -= 5
        if "Duplicate Removed" in flags:
            dq_score -= 10
            
        # Deduct for Missing Optional Fields
        for opt in OPTIONAL_FIELDS:
            if opt in df.columns:
                opt_val = row[opt]
                if pd.isna(opt_val) or str(opt_val).strip() == "" or str(opt_val).strip().lower() in ["nan", "none"]:
                    dq_score -= 2
            else:
                # Deduct if column is entirely absent in the dataset schema
                dq_score -= 2
                
        dq_score = max(0, min(100, dq_score))
        dq_scores.append(dq_score)
        
    df["Opportunity Score"] = opp_scores
    df["Opportunity Level"] = opp_levels
    df["Data Quality Score"] = dq_scores
    df["Recommendation Reason"] = rec_reasons
    
    # Set Rating and Review Categories for dynamic BI charts
    def rate_cat(r):
        if pd.isna(r): return "Unknown"
        if r < 2.5: return "Low (< 2.5)"
        if r < 3.5: return "Average (2.5-3.5)"
        if r < 4.0: return "Good (3.5-4.0)"
        return "Excellent (>= 4.0)"
        
    def rev_cat(v):
        if v < 10: return "Very Few (< 10)"
        if v < 50: return "Few (10-49)"
        if v < 100: return "Moderate (50-99)"
        return "Many (>= 100)"
        
    df["Rating Category"] = df["Rating"].apply(rate_cat)
    df["Review Category"] = df["Reviews"].apply(rev_cat)
    
    return df

def generate_ai_insights(df: pd.DataFrame) -> list[str]:
    """Generates 5-10 rule-based business insights from the dataset."""
    if len(df) == 0:
        return ["No business listings available for insights."]
        
    insights = []
    
    # 1. Website gap
    noweb_count = (df["Website"] == "No Website").sum()
    noweb_pct = int(round((noweb_count / len(df)) * 100))
    insights.append(f"{noweb_pct}% of analyzed businesses do not have a website, representing a significant digital market gap.")
    
    # 2. Highest Opportunity City
    high_opp_mask = df["Opportunity Level"].isin(["High Opportunity", "Excellent Opportunity"])
    if high_opp_mask.sum() > 0:
        city_counts = df[high_opp_mask]["City"].value_counts()
        if not city_counts.empty:
            top_city = city_counts.index[0]
            top_city_pct = int(round((city_counts.iloc[0] / high_opp_mask.sum()) * 100))
            insights.append(f"{top_city} contains the highest concentration of high-priority digital opportunities ({top_city_pct}% of all priority businesses).")
            
    # 3. Category Opportunities
    cat_opp_counts = df[high_opp_mask]["Category"].value_counts()
    if not cat_opp_counts.empty:
        top_cat = cat_opp_counts.index[0]
        insights.append(f"{top_cat}s represent the single largest business segment in need of digital transformation in this region.")
        
    # 4. Highest rated categories
    avg_ratings = df.groupby("Category")["Rating"].mean()
    if not avg_ratings.empty:
        top_rating_cat = avg_ratings.idxmax()
        insights.append(f"{top_rating_cat}s maintain the highest average customer reputation score ({avg_ratings.max():.2f}/5.0).")
        
    # 5. Reviews distribution
    avg_reviews = df.groupby("Category")["Reviews"].mean()
    if not avg_reviews.empty:
        top_rev_cat = avg_reviews.idxmax()
        insights.append(f"{top_rev_cat}s receive the highest average customer review counts, indicating high local engagement.")
        
    # 6. Website correlation with reviews
    avg_web_rev = df[df["Has Website"]]["Reviews"].mean()
    avg_noweb_rev = df[~df["Has Website"]]["Reviews"].mean()
    if not pd.isna(avg_web_rev) and not pd.isna(avg_noweb_rev):
        insights.append(f"Businesses with websites receive more reviews on average ({avg_web_rev:.1f} reviews) compared to those without ({avg_noweb_rev:.1f} reviews).")
        
    # 7. Customer Rating vs Reviews correlation
    high_rating_rev = df[df["Rating"] >= 4.5]["Reviews"].mean()
    low_rating_rev = df[df["Rating"] < 3.5]["Reviews"].mean()
    if not pd.isna(high_rating_rev) and not pd.isna(low_rating_rev):
        insights.append(f"Top-rated businesses (Rating >= 4.5) average significantly higher customer engagement than lower-rated ones ({high_rating_rev:.1f} vs {low_rating_rev:.1f} reviews).")
        
    # 8. Digital transaction enablement (UPI / GST)
    if "UPI Accepted" in df.columns:
        upi_pct = int(round((df["UPI Accepted"] == "Yes").sum() / len(df) * 100))
        insights.append(f"UPI payment acceptance is high at {upi_pct}% of listings, while website ownership stands at only {100 - noweb_pct}%.")
        
    return insights[:8]

def generate_executive_summary(df: pd.DataFrame) -> dict:
    """Generates a dynamic filtered executive summary in JSON format."""
    if len(df) == 0:
        return {
            "total_businesses": 0,
            "total_cities": 0,
            "total_categories": 0,
            "total_reviews": 0,
            "avg_rating": 0.0,
            "website_gap_percent": 0,
            "phone_gap_percent": 0,
            "highest_represented_category": "N/A",
            "highest_represented_city": "N/A",
            "highest_rated_category": "N/A",
            "highest_rated_category_val": 0.0,
            "most_competitive_category": "N/A",
            "most_competitive_category_reviews": 0,
            "city_with_most_businesses": "N/A",
            "city_with_most_businesses_count": 0,
            "key_opportunity": "N/A",
            "avg_opportunity_score": 0,
            "avg_data_quality_score": 0,
            "top_categories": [],
            "top_city": "N/A",
            "summary_text": "No business records match the current filter selection."
        }
        
    total_biz = len(df)
    total_cities = df["City"].nunique() if "City" in df.columns else 0
    total_categories = df["Category"].nunique() if "Category" in df.columns else 0
    total_reviews = int(df["Reviews"].sum()) if "Reviews" in df.columns else 0
    
    avg_rating = round(df["Rating"].mean(), 2) if "Rating" in df.columns and not df["Rating"].dropna().empty else 0.0
    
    noweb_count = int((df["Website"] == "No Website").sum()) if "Website" in df.columns else 0
    website_gap_percent = int(round((noweb_count / total_biz) * 100)) if total_biz > 0 else 0
    
    nophone_count = int((df["Phone Number"].isna() | (df["Phone Number"].astype(str).str.strip() == "")).sum()) if "Phone Number" in df.columns else 0
    phone_gap_percent = int(round((nophone_count / total_biz) * 100)) if total_biz > 0 else 0
    
    # Highest represented category
    highest_represented_category = df["Category"].mode()[0] if "Category" in df.columns and not df["Category"].empty else "N/A"
    
    # Highest represented city
    highest_represented_city = df["City"].mode()[0] if "City" in df.columns and not df["City"].empty else "N/A"
    
    # Highest Rated Category
    avg_rating_by_cat = df.groupby("Category")["Rating"].mean() if "Category" in df.columns and "Rating" in df.columns else pd.Series()
    highest_rated_category = avg_rating_by_cat.idxmax() if not avg_rating_by_cat.empty else "N/A"
    highest_rated_category_val = round(avg_rating_by_cat.max(), 2) if not avg_rating_by_cat.empty else 0.0
    
    # Most Competitive Category (based on total reviews volume as key engagement indicator)
    reviews_by_cat = df.groupby("Category")["Reviews"].sum() if "Category" in df.columns and "Reviews" in df.columns else pd.Series()
    most_competitive_category = reviews_by_cat.idxmax() if not reviews_by_cat.empty else "N/A"
    most_competitive_category_reviews = int(reviews_by_cat.max()) if not reviews_by_cat.empty else 0
    
    # City with Most Businesses
    city_counts = df["City"].value_counts() if "City" in df.columns else pd.Series()
    city_with_most_businesses = city_counts.index[0] if not city_counts.empty else "N/A"
    city_with_most_businesses_count = int(city_counts.iloc[0]) if not city_counts.empty else 0
    
    avg_opp = int(round(df["Opportunity Score"].mean())) if "Opportunity Score" in df.columns else 0
    avg_dq = int(round(df["Data Quality Score"].mean())) if "Data Quality Score" in df.columns else 0
    
    # Top opportunity categories (most High/Excellent opportunities)
    high_opp_mask = df["Opportunity Level"].isin(["High Opportunity", "Excellent Opportunity"]) if "Opportunity Level" in df.columns else pd.Series()
    top_categories = []
    if not high_opp_mask.empty and high_opp_mask.sum() > 0:
        top_cats = df[high_opp_mask]["Category"].value_counts().index[:3].tolist()
        top_categories = top_cats
    else:
        top_categories = df["Category"].value_counts().index[:3].tolist() if "Category" in df.columns else []
        
    # City with most opportunities
    top_city = "N/A"
    if not high_opp_mask.empty and high_opp_mask.sum() > 0:
        city_counts_opp = df[high_opp_mask]["City"].value_counts()
        if not city_counts_opp.empty:
            top_city = city_counts_opp.index[0]
    else:
        if not city_counts.empty:
            top_city = city_counts.index[0]
            
    # Format categories for text
    cat_str = ""
    if len(top_categories) > 0:
        if len(top_categories) == 1:
            cat_str = top_categories[0]
        elif len(top_categories) == 2:
            cat_str = f"{top_categories[0]} and {top_categories[1]}"
        else:
            cat_str = f"{top_categories[0]}, {top_categories[1]}, and {top_categories[2]}"
            
    # Key business opportunity description
    key_opp = ""
    if website_gap_percent > 30:
        key_opp = f"Equip the {website_gap_percent}% of local listings (primarily {highest_represented_category}s) that are missing websites with functional landing pages."
    elif avg_rating < 4.0:
        key_opp = "Review and reputation management campaign to boost customer feedback metrics."
    else:
        key_opp = "Enhancing rich business profile metadata (UPI payment setup, hours, and photos) to rank higher in local search results."

    summary_text = (
        f"This market overview analyzes {total_biz} business listings across {total_cities} cities, representing {total_categories} distinct commercial categories. "
        f"The most prominent industry segment is {highest_represented_category}, and {highest_represented_city} contains the highest density of business profiles. "
        f"The overall customer reputation stands at an average of {avg_rating}/5.0 stars with {total_reviews:,} total reviews. "
        f"Crucially, {website_gap_percent}% of these local businesses do not have an active website, and {phone_gap_percent}% are missing standard mobile contact details. "
        f"Key Opportunity: {key_opp}"
    )
    
    return {
        "total_businesses": total_biz,
        "total_cities": total_cities,
        "total_categories": total_categories,
        "total_reviews": total_reviews,
        "avg_rating": avg_rating,
        "website_gap_percent": website_gap_percent,
        "phone_gap_percent": phone_gap_percent,
        "highest_represented_category": highest_represented_category,
        "highest_represented_city": highest_represented_city,
        "highest_rated_category": highest_rated_category,
        "highest_rated_category_val": highest_rated_category_val,
        "most_competitive_category": most_competitive_category,
        "most_competitive_category_reviews": most_competitive_category_reviews,
        "city_with_most_businesses": city_with_most_businesses,
        "city_with_most_businesses_count": city_with_most_businesses_count,
        "key_opportunity": key_opp,
        "avg_opportunity_score": avg_opp,
        "avg_data_quality_score": avg_dq,
        "top_categories": top_categories,
        "top_city": top_city,
        "summary_text": summary_text
    }

