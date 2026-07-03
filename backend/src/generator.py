import os
import random
import pandas as pd
import numpy as np

# Configurations
INDIAN_CITIES = {
    "Delhi": {"state": "Delhi", "prefix": "1100", "lat": 28.6139, "lng": 77.2090},
    "Mumbai": {"state": "Maharashtra", "prefix": "4000", "lat": 18.9750, "lng": 72.8258},
    "Bengaluru": {"state": "Karnataka", "prefix": "5600", "lat": 12.9716, "lng": 77.5946},
    "Hyderabad": {"state": "Telangana", "prefix": "5000", "lat": 17.3850, "lng": 78.4867},
    "Chennai": {"state": "Tamil Nadu", "prefix": "6000", "lat": 13.0827, "lng": 80.2707},
    "Pune": {"state": "Maharashtra", "prefix": "4110", "lat": 18.5204, "lng": 73.8567},
    "Ahmedabad": {"state": "Gujarat", "prefix": "3800", "lat": 23.0225, "lng": 72.5714},
    "Jaipur": {"state": "Rajasthan", "prefix": "3020", "lat": 26.9124, "lng": 75.7873},
    "Chandigarh": {"state": "Chandigarh", "prefix": "1600", "lat": 30.7333, "lng": 76.7794},
    "Lucknow": {"state": "Uttar Pradesh", "prefix": "2260", "lat": 26.8467, "lng": 80.9462},
    "Kolkata": {"state": "West Bengal", "prefix": "7000", "lat": 22.5726, "lng": 88.3639},
    "Surat": {"state": "Gujarat", "prefix": "3950", "lat": 21.1702, "lng": 72.8311}
}

SURNAMES = ["Gupta", "Sharma", "Patel", "Singh", "Verma", "Agarwal", "Kumar", "Mehta", "Joshi", "Shah", "Rao", "Reddy", "Nair", "Iyer", "Sen", "Das", "Roy", "Bose", "Dwivedi", "Mishra", "Pillai", "Choudhury", "Bhattacharya", "Kulkarni"]

STREETS = ["MG Road", "Connaught Place", "Banjara Hills", "Koregaon Park", "C G Road", "Vaishali Nagar", "Hazratganj", "Park Street", "Sector 17", "Ghatkopar Road", "Indiranagar Double Road", "Anna Salai"]
MARKETS = ["Main Market", "Local Shopping Complex", "Super Market", "Commercial Center", "Shopping Plaza"]
AREAS = ["Sector 15", "Sector 22", "Sector 35", "Indiranagar", "Koramangala", "Jayanagar", "Andheri West", "Bandra", "Colaba", "Gachibowli", "Madhapur", "Adyar", "T Nagar", "Aliganj", "Gomti Nagar", "Salt Lake", "Rajajinagar"]

CATEGORY_CONFIGS = {
    "Restaurant": {"freq": 0.18, "rating_range": (3.8, 4.7), "reviews_range": (50, 1500), "has_website_prob": 0.8},
    "Cafe": {"freq": 0.08, "rating_range": (3.9, 4.6), "reviews_range": (30, 800), "has_website_prob": 0.75},
    "Sweet Shop": {"freq": 0.07, "rating_range": (4.0, 4.8), "reviews_range": (40, 1200), "has_website_prob": 0.4},
    "Bakery": {"freq": 0.05, "rating_range": (3.8, 4.5), "reviews_range": (20, 600), "has_website_prob": 0.6},
    "Kirana Store": {"freq": 0.15, "rating_range": (3.5, 4.4), "reviews_range": (5, 80), "has_website_prob": 0.1},
    "Pharmacy": {"freq": 0.06, "rating_range": (3.7, 4.6), "reviews_range": (15, 300), "has_website_prob": 0.3},
    "Medical Clinic": {"freq": 0.08, "rating_range": (3.6, 4.5), "reviews_range": (10, 150), "has_website_prob": 0.25},
    "Hospital": {"freq": 0.03, "rating_range": (3.5, 4.4), "reviews_range": (100, 3000), "has_website_prob": 0.95},
    "Coaching Centre": {"freq": 0.07, "rating_range": (3.8, 4.8), "reviews_range": (25, 450), "has_website_prob": 0.7},
    "Retail Shop": {"freq": 0.12, "rating_range": (3.6, 4.5), "reviews_range": (10, 200), "has_website_prob": 0.5},
    "Construction Company": {"freq": 0.04, "rating_range": (3.2, 4.3), "reviews_range": (5, 60), "has_website_prob": 0.4},
    "Hotel": {"freq": 0.02, "rating_range": (3.5, 4.3), "reviews_range": (50, 2000), "has_website_prob": 0.9}
}

INCONSISTENT_CATEGORIES = {
    "Restaurant": ["restraunt", "RESTAURANT", "Restaurant"],
    "Cafe": ["CAFE", "Cafe", "coffee shop"],
    "Medical Clinic": ["medical clinic", "Med Clinic", "Medical Clinic"],
    "Kirana Store": ["kirana store", "Kirana Shop", "Kirana Store"],
    "Coaching Centre": ["coaching centre", "Coaching Classes", "Coaching Centre"],
    "Retail Shop": ["retail shop", "Retail Outlet", "Retail Shop"]
}

def generate_dataset(record_count: int = 500) -> pd.DataFrame:
    """
    Generates a realistic India-focused business listing dataset with anomalies.
    """
    # Adjust count to account for duplicate generation (we will generate raw rows and duplicate them)
    num_duplicates = int(record_count * 0.10)
    num_unique = record_count - num_duplicates
    
    rows = []
    categories = list(CATEGORY_CONFIGS.keys())
    weights = [CATEGORY_CONFIGS[c]["freq"] for c in categories]
    # Normalize weights to sum to 1.0
    sum_w = sum(weights)
    weights = [w / sum_w for w in weights]
    
    cities = list(INDIAN_CITIES.keys())
    
    for i in range(num_unique):
        # Pick category & city
        category = random.choices(categories, weights=weights)[0]
        city = random.choice(cities)
        city_info = INDIAN_CITIES[city]
        
        # Surnames & names
        surname = random.choice(SURNAMES)
        road = random.choice(STREETS)
        area = random.choice(AREAS)
        market = random.choice(MARKETS)
        num = random.randint(1, 400)
        sec = random.randint(1, 50)
        
        # Name generation based on category
        if category == "Restaurant":
            b_name = f"{surname} Spice Kitchen" if random.random() > 0.5 else f"Delhi Spice Restaurant"
            sub_cat = "North Indian, South Indian"
        elif category == "Cafe":
            b_name = f"{surname} Cafe" if random.random() > 0.5 else "Royal Cafe"
            sub_cat = "Beverages, Desserts"
        elif category == "Sweet Shop":
            b_name = f"{surname} Sweets" if random.random() > 0.5 else "Bikaner Sweets"
            sub_cat = "Indian Sweets & Snacks"
        elif category == "Bakery":
            b_name = f"{surname} Bakers" if random.random() > 0.5 else "Punjab Bakers"
            sub_cat = "Cakes & Pastries"
        elif category == "Kirana Store":
            b_name = f"{surname} Kirana Store" if random.random() > 0.5 else "Krishna Garments"
            sub_cat = "Grocery Store"
        elif category == "Pharmacy":
            b_name = f"{surname} Medical Store" if random.random() > 0.5 else "Sai Medical Centre"
            sub_cat = "Chemist"
        elif category == "Medical Clinic":
            b_name = f"{surname} Medical Centre" if random.random() > 0.5 else "Verma Dental Clinic"
            sub_cat = "General Physician"
        elif category == "Hospital":
            b_name = f"{surname} Hospital" if random.random() > 0.5 else "Metro Hospital"
            sub_cat = "Multi Specialty Hospital"
        elif category == "Coaching Centre":
            b_name = f"{surname} Coaching Centre" if random.random() > 0.5 else "Modern Coaching Centre"
            sub_cat = "IIT JEE & NEET Prep"
        elif category == "Retail Shop":
            b_name = f"{surname} Traders" if random.random() > 0.5 else "Krishna Garments"
            sub_cat = "Clothing Store"
        elif category == "Construction Company":
            b_name = f"{surname} Construction" if random.random() > 0.5 else "Modern Construction Co"
            sub_cat = "Builder & Developer"
        elif category == "Hotel":
            b_name = f"Hotel {surname}" if random.random() > 0.5 else "Royal Palace Hotel"
            sub_cat = "Lodging & Guest House"
        else:
            b_name = f"{surname} Enterprises"
            sub_cat = "Service Provider"
            
        # Address format
        addr_fmt = random.choice([
            f"Shop No {num}, {market}, {area}, {city}",
            f"SCO {num}, Sector {sec}, {city}",
            f"{num}, {road}, {area}, {city}"
        ])
        
        # Phone
        phone_no = f"+91 {random.choice([9, 8, 7, 6])}{random.randint(100000000, 999999999)}"
        
        # Rating & reviews
        rating_cfg = CATEGORY_CONFIGS[category]["rating_range"]
        rev_cfg = CATEGORY_CONFIGS[category]["reviews_range"]
        
        rating = round(random.uniform(rating_cfg[0], rating_cfg[1]), 1)
        reviews = random.randint(rev_cfg[0], rev_cfg[1])
        
        # Website status
        has_web = random.random() < CATEGORY_CONFIGS[category]["has_website_prob"]
        web_domain = b_name.lower().replace(" ", "")
        website = f"http://{web_domain}.in" if has_web else ""
        
        # Optional fields
        state = city_info["state"]
        pincode = f"{city_info['prefix']}{random.randint(10, 99)}"
        
        # Jitter coordinates slightly
        lat = city_info["lat"] + random.uniform(-0.08, 0.08)
        lng = city_info["lng"] + random.uniform(-0.08, 0.08)
        
        email = f"info@{web_domain}.in" if has_web else f"{web_domain}@gmail.com"
        maps_link = f"https://maps.google.com/?cid={random.randint(10000000, 99999999)}"
        
        verified = "Yes" if (random.random() < 0.6 or category in ["Hospital", "Hotel"]) else "No"
        open_now = "Yes" if random.random() > 0.3 else "No"
        opening = f"{random.choice([8, 9, 10])}:00 AM"
        closing = f"{random.choice([8, 9, 10])}:00 PM"
        
        price_lvl = random.choice(["₹", "₹₹", "₹₹₹"]) if category in ["Restaurant", "Cafe", "Hotel"] else ""
        photos = random.randint(0, 300) if has_web else random.randint(0, 10)
        
        est_year = random.randint(1990, 2024)
        description = f"Leading {category.lower()} offering professional services in {city}."
        
        gst = "Yes" if (random.random() < 0.5 or category in ["Hospital", "Hotel", "Construction Company"]) else "No"
        whatsapp = "Yes" if random.random() > 0.4 else "No"
        upi = "Yes" if random.random() > 0.2 else "No"
        
        row = {
            "Business Name": b_name,
            "Category": category,
            "Rating": rating,
            "Reviews": reviews,
            "Website": website,
            "Phone Number": phone_no,
            "Address": addr_fmt,
            "City": city,
            "Sub Category": sub_cat,
            "State": state,
            "Pincode": pincode,
            "Latitude": lat,
            "Longitude": lng,
            "Email": email,
            "Google Maps Link": maps_link,
            "Verified Business": verified,
            "Open Now": open_now,
            "Opening Hours": f"{opening} - {closing}",
            "Price Level": price_lvl,
            "Photos Count": photos,
            "Business Description": description,
            "Established Year": est_year,
            "GST Available": gst,
            "WhatsApp Business": whatsapp,
            "UPI Accepted": upi,
            "Google Business Verified": verified
        }
        
        rows.append(row)
        
    df = pd.DataFrame(rows)
    
    # ------------------ INJECT ANOMALIES ------------------
    # 25% missing websites (set to empty or Nan)
    # The generation naturally has some missing websites, let's enforce that exactly 25% of final rows have No Website.
    web_missing_count = int(record_count * 0.25)
    indices_for_no_web = random.sample(range(len(df)), web_missing_count)
    df.loc[indices_for_no_web, "Website"] = ""
    
    # 15% missing phone numbers
    phone_missing_count = int(record_count * 0.15)
    indices_for_no_phone = random.sample(range(len(df)), phone_missing_count)
    df.loc[indices_for_no_phone, "Phone Number"] = ""
    
    # 5% empty business names
    name_missing_count = int(record_count * 0.05)
    indices_for_no_name = random.sample(range(len(df)), name_missing_count)
    df.loc[indices_for_no_name, "Business Name"] = ""
    
    # 5% invalid ratings (outside [1.0, 5.0])
    rating_invalid_count = int(record_count * 0.05)
    indices_for_invalid_rating = random.sample(range(len(df)), rating_invalid_count)
    for idx in indices_for_invalid_rating:
        df.loc[idx, "Rating"] = random.choice([0.0, 6.0, 10.0, -1.0])
        
    # 5% negative review counts
    review_invalid_count = int(record_count * 0.05)
    indices_for_invalid_review = random.sample(range(len(df)), review_invalid_count)
    for idx in indices_for_invalid_review:
        df.loc[idx, "Reviews"] = -abs(int(df.loc[idx, "Reviews"]))
        
    # Inconsistent category spellings
    for cat, spellings in INCONSISTENT_CATEGORIES.items():
        cat_indices = df[df["Category"] == cat].index.tolist()
        # Randomly replace category name with misspelled version for 30% of category rows
        to_replace = int(len(cat_indices) * 0.3)
        if to_replace > 0:
            replace_indices = random.sample(cat_indices, to_replace)
            for idx in replace_indices:
                df.loc[idx, "Category"] = random.choice(spellings[:-1]) # pick misspelled ones
                
    # Randomly omit optional fields from some rows (to test adaptive layout)
    # E.g. set State, Pin, Lat, Lng to empty for some rows
    # But let's keep them mostly present so the dashboard displays them unless the user uploads a file with missing columns.
    
    # Duplicate records (10%)
    # Let's take the first duplicate_count rows and append them again.
    dup_df = df.iloc[:num_duplicates].copy()
    # We should alter their indices or let pandas handle it
    df = pd.concat([df, dup_df], ignore_index=True)
    
    # Trim to exact record count if needed (it should match exactly record_count)
    df = df.iloc[:record_count].reset_index(drop=True)
    
    return df

if __name__ == "__main__":
    # Test generation
    df = generate_dataset(500)
    print(f"Generated {len(df)} records.")
    print(df.head(3))
