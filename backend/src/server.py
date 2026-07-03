import os
import json
import io
import tempfile
import pandas as pd
import numpy as np
from fastapi import FastAPI, UploadFile, File, Form, Query, HTTPException, Header, Depends
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware

# Import backend modules
from src.generator import generate_dataset
from src.cleaner import clean_dataset
from src.analyzer import calculate_scores, generate_ai_insights, generate_executive_summary, load_scoring_config, OPTIONAL_FIELDS

app = FastAPI(title="Google Maps Business Analysis Platform")

# Allow CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["Content-Disposition"],
)

# File Paths (resolving dynamically relative to the backend root directory)
BACKEND_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
RAW_FILE = os.path.join(BACKEND_DIR, "data", "raw_listings.csv")
CLEAN_FILE = os.path.join(BACKEND_DIR, "data", "clean_listings.csv")
STATS_FILE = os.path.join(BACKEND_DIR, "data", "cleaning_stats.json")


def get_current_df() -> pd.DataFrame:
    """Helper to load the currently cleaned and analyzed dataset."""
    if not os.path.exists(CLEAN_FILE):
        return pd.DataFrame()
    return pd.read_csv(CLEAN_FILE)

def filter_df(df: pd.DataFrame, category: str = None, city: str = None, 
              website_status: str = None, opportunity_level: str = None, 
              search: str = None, min_rating: float = None) -> pd.DataFrame:
    """Applies dynamic filters to the dataframe."""
    if df.empty:
        return df
        
    filtered = df.copy()
    
    if category and category.lower() != "all":
        filtered = filtered[filtered["Category"].astype(str).str.lower() == category.lower()]
        
    if city and city.lower() != "all":
        filtered = filtered[filtered["City"].astype(str).str.lower() == city.lower()]
        
    if website_status and website_status.lower() != "all":
        filtered = filtered[filtered["Website Status"].astype(str).str.lower() == website_status.lower()]
        
    if opportunity_level and opportunity_level.lower() != "all":
        filtered = filtered[filtered["Opportunity Level"].astype(str).str.lower() == opportunity_level.lower()]
        
    if min_rating is not None and min_rating > 0:
        filtered = filtered[filtered["Rating"].notna() & (filtered["Rating"] >= min_rating)]
        
    if search:
        search_lower = search.lower()
        name_match = filtered["Business Name"].astype(str).str.lower().str.contains(search_lower)
        addr_match = filtered["Address"].astype(str).str.lower().str.contains(search_lower)
        cat_match = filtered["Category"].astype(str).str.lower().str.contains(search_lower)
        filtered = filtered[name_match | addr_match | cat_match]
        
    return filtered

# Authentication Dependency
async def get_current_user(authorization: str = Header(None)):
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Not authenticated")
    token = authorization.split(" ")[1]
    from src.database import get_session
    session = get_session(token)
    if not session:
        raise HTTPException(status_code=401, detail="Session invalid or expired")
    return session["username"]

# Authentication Routes
@app.post("/api/auth/signup")
async def api_signup(payload: dict):
    username = payload.get("username")
    password = payload.get("password")
    if not username or not password:
        raise HTTPException(status_code=400, detail="Username and password are required")
    if len(username.strip()) < 3:
        raise HTTPException(status_code=400, detail="Username must be at least 3 characters")
    if len(password) < 6:
        raise HTTPException(status_code=400, detail="Password must be at least 6 characters")
        
    from src.database import create_user
    success = create_user(username, password)
    if not success:
        raise HTTPException(status_code=400, detail="Username already exists")
        
    return {"status": "success", "message": "User registered successfully"}

@app.post("/api/auth/login")
async def api_login(payload: dict):
    username = payload.get("username")
    password = payload.get("password")
    if not username or not password:
        raise HTTPException(status_code=400, detail="Username and password are required")
        
    from src.database import get_user, verify_password, create_session
    user = get_user(username)
    if not user or not verify_password(password, user["password_hash"], user["salt"]):
        raise HTTPException(status_code=401, detail="Invalid username or password")
        
    token = create_session(username)
    return {
        "status": "success",
        "token": token,
        "username": username
    }

@app.post("/api/auth/logout")
async def api_logout(authorization: str = Header(None)):
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=400, detail="Invalid session")
    token = authorization.split(" ")[1]
    from src.database import delete_session
    delete_session(token)
    return {"status": "success", "message": "Logged out successfully"}

@app.get("/api/auth/me")
async def api_auth_me(current_user: str = Depends(get_current_user)):
    return {"username": current_user}

@app.post("/api/generate")
async def api_generate(payload: dict, current_user: str = Depends(get_current_user)):
    """
    Generates a new India-focused demo dataset of requested size.
    """
    record_count = payload.get("record_count", 500)
    if record_count < 100 or record_count > 5000:
        raise HTTPException(status_code=400, detail="Record count must be between 100 and 5000.")
        
    try:
        # 1. Generate
        raw_df = generate_dataset(record_count)
        os.makedirs("data", exist_ok=True)
        raw_df.to_csv(RAW_FILE, index=False)
        
        # 2. Clean & Preprocess
        clean_df, stats = clean_dataset(raw_df)
        
        # 3. Analyze & Score
        scored_df = calculate_scores(clean_df)
        scored_df.to_csv(CLEAN_FILE, index=False)
        
        # Extract metadata counts for success dialog
        num_no_website = int((scored_df["Website"] == "No Website").sum())
        num_duplicates = int(stats.get("duplicates_removed", 0))
        num_invalid_ratings = int(stats.get("invalid_ratings_corrected", 0))
        num_missing_phones = int(stats.get("missing_phones_logged", 0))
        
        return {
            "status": "success",
            "size": len(scored_df),
            "categories": int(scored_df["Category"].nunique()),
            "cities": int(scored_df["City"].nunique()),
            "no_website": num_no_website,
            "duplicates": num_duplicates,
            "invalid_ratings": num_invalid_ratings,
            "missing_phones": num_missing_phones
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Generation failed: {str(e)}")

@app.post("/api/upload")
async def api_upload(file: UploadFile = File(...), current_user: str = Depends(get_current_user)):
    """
    Uploads a custom business dataset, inspects it, and populates validation.
    """
    content = await file.read()
    filename = file.filename
    
    try:
        # Load depending on extension
        if filename.endswith(".csv"):
            df = pd.read_csv(io.BytesIO(content))
        elif filename.endswith((".xls", ".xlsx")):
            df = pd.read_excel(io.BytesIO(content))
        else:
            raise HTTPException(status_code=400, detail="Invalid file format. Upload CSV or Excel.")
            
        # Map columns to inspect schema
        from src.cleaner import get_mapped_columns
        mapped_cols = get_mapped_columns(df.columns)
        df_mapped = df.rename(columns=mapped_cols)
        
        # Run required columns checks
        from src.cleaner import REQUIRED_COLUMNS, STRICT_REQUIRED
        detected_req = {req: (req in df_mapped.columns) for req in REQUIRED_COLUMNS}
        
        # Run optional columns checks
        detected_opt = {opt: (opt in df_mapped.columns) for opt in OPTIONAL_FIELDS}
        
        # If all strictly required columns exist, proceed to auto-save and run pipeline
        missing_req = [k for k, v in detected_req.items() if not v]
        strict_missing = [k for k, v in detected_req.items() if not v and k in STRICT_REQUIRED]
        is_valid = len(strict_missing) == 0
        
        stats = {}
        if is_valid:
            # Save raw file
            os.makedirs("data", exist_ok=True)
            df.to_csv(RAW_FILE, index=False)
            
            # Clean and Score
            clean_df, stats = clean_dataset(df_mapped)
            scored_df = calculate_scores(clean_df)
            scored_df.to_csv(CLEAN_FILE, index=False)
            
        return {
            "filename": filename,
            "total_records": len(df),
            "total_columns": len(df.columns),
            "is_valid": is_valid,
            "detected_required": detected_req,
            "detected_optional": detected_opt,
            "missing_required": missing_req,
            "cleaning_stats": stats
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Upload failed: {str(e)}")

@app.get("/api/clean-summary")
async def api_clean_summary(current_user: str = Depends(get_current_user)):
    """Returns data cleaning statistics."""
    if not os.path.exists(STATS_FILE):
        return {"status": "no_data"}
    with open(STATS_FILE, "r") as f:
        return json.load(f)

@app.get("/api/listings")
async def api_listings(
    category: str = None, city: str = None, 
    website_status: str = None, opportunity_level: str = None,
    search: str = None, min_rating: float = None,
    sort_by: str = "Opportunity Score", sort_order: str = "desc", 
    page: int = 1, page_size: int = 20,
    current_user: str = Depends(get_current_user)
):
    """Returns filtered, sorted, and paginated business listings."""
    df = get_current_df()
    if df.empty:
        return {"listings": [], "total": 0, "pages": 0}
        
    filtered = filter_df(df, category, city, website_status, opportunity_level, search, min_rating)
    
    # Sort
    if sort_by in filtered.columns:
        ascending = (sort_order == "asc")
        filtered = filtered.sort_values(by=sort_by, ascending=ascending)
        
    # Paginate
    total = len(filtered)
    total_pages = (total + page_size - 1) // page_size
    start = (page - 1) * page_size
    end = start + page_size
    
    # Clean NaN values for JSON compatibility
    paginated = filtered.iloc[start:end].copy()
    paginated = paginated.replace({np.nan: None})
    
    listings_list = paginated.to_dict(orient="records")
    
    return {
        "listings": listings_list,
        "total": total,
        "pages": total_pages,
        "current_page": page
    }

@app.get("/api/charts")
async def api_charts(
    category: str = None, city: str = None, 
    website_status: str = None, opportunity_level: str = None,
    search: str = None, min_rating: float = None,
    current_user: str = Depends(get_current_user)
):
    """Returns dynamic chart analytics based on current UI filters."""
    df = get_current_df()
    if df.empty:
        return {}
        
    filtered = filter_df(df, category, city, website_status, opportunity_level, search, min_rating)
    
    # 1. Website Availability Status count
    web_status_counts = filtered["Website Status"].value_counts().to_dict()
    
    # 2. Categories Distribution
    cat_counts = filtered["Category"].value_counts().head(10).to_dict()
    
    # 3. Rating distribution (e.g. Rating Category)
    rating_cat_counts = filtered["Rating Category"].value_counts().to_dict()
    
    # 4. Review distribution (e.g. Review Category)
    review_cat_counts = filtered["Review Category"].value_counts().to_dict()
    
    # 5. Opportunity Level count
    opp_level_counts = filtered["Opportunity Level"].value_counts().to_dict()
    
    # 6. Avg rating by Category
    avg_rating_cat = filtered.groupby("Category")["Rating"].mean().dropna().sort_values(ascending=False).head(10).to_dict()
    
    # 7. Businesses by City
    city_counts = filtered["City"].value_counts().to_dict()
    
    # 8. Stacked bar (Website Status by Category)
    # Get top 8 categories
    top_cats = filtered["Category"].value_counts().head(8).index.tolist()
    website_category = {}
    for c in top_cats:
        cat_df = filtered[filtered["Category"] == c]
        website_category[c] = cat_df["Website Status"].value_counts().to_dict()
        
    # 9. Scatter plot (Rating vs Reviews)
    # Limit scatter details count to 200 for frontend rendering efficiency
    scatter_df = filtered.dropna(subset=["Rating", "Reviews"]).head(200)
    scatter_data = [
        {
            "x": float(row["Rating"]), 
            "y": int(row["Reviews"]), 
            "name": row["Business Name"],
            "level": row["Opportunity Level"]
        } 
        for idx, row in scatter_df.iterrows()
    ]
    
    # 10. Horizontal Bar (Top 10 highest opportunities)
    top_opps_df = filtered.sort_values(by="Opportunity Score", ascending=False).head(10)
    top_opps = {row["Business Name"]: int(row["Opportunity Score"]) for idx, row in top_opps_df.iterrows()}
    
    # 11. Opportunity vs Data Quality (Scatter Plot)
    opp_dq_scatter = [
        {
            "x": float(row["Opportunity Score"]),
            "y": float(row["Data Quality Score"]),
            "name": row["Business Name"],
            "level": row["Opportunity Level"]
        }
        for idx, row in filtered.head(200).iterrows()
    ]
    
    # 12. State counts (optional)
    state_counts = {}
    if "State" in filtered.columns:
        state_counts = filtered["State"].value_counts().to_dict()
        
    # 13. Geospatial coordinates availability check
    has_coordinates = False
    if "Latitude" in filtered.columns and "Longitude" in filtered.columns:
        has_coordinates = bool(filtered["Latitude"].notna().any() and filtered["Longitude"].notna().any())
        
    # 14. Cost Distribution (Price Level)
    price_levels = {}
    if "Price Level" in filtered.columns:
        price_series = filtered["Price Level"].astype(str).str.strip()
        price_series = price_series[price_series != ""]
        if not price_series.empty:
            price_levels = price_series.value_counts().to_dict()
            
    # 15. Verified counts
    verified_counts = {}
    if "Verified Business" in filtered.columns:
        verified_counts = filtered["Verified Business"].value_counts().to_dict()
        
    return {
        "website_status": web_status_counts,
        "categories": cat_counts,
        "ratings": rating_cat_counts,
        "reviews": review_cat_counts,
        "opportunity_levels": opp_level_counts,
        "avg_rating_category": avg_rating_cat,
        "cities": city_counts,
        "website_category": website_category,
        "reviews_rating_scatter": scatter_data,
        "top_opportunities": top_opps,
        "opp_dq_scatter": opp_dq_scatter,
        "states": state_counts,
        "has_coordinates": has_coordinates,
        "price_levels": price_levels,
        "verified_counts": verified_counts
    }

@app.get("/api/insights")
async def api_insights(
    category: str = None, city: str = None, 
    website_status: str = None, opportunity_level: str = None,
    search: str = None, min_rating: float = None,
    current_user: str = Depends(get_current_user)
):
    """Returns AI insights array for the current filtered list."""
    df = get_current_df()
    if df.empty:
        return []
    filtered = filter_df(df, category, city, website_status, opportunity_level, search, min_rating)
    return generate_ai_insights(filtered)

@app.get("/api/executive-summary")
async def api_executive_summary(
    category: str = None, city: str = None, 
    website_status: str = None, opportunity_level: str = None,
    search: str = None, min_rating: float = None,
    current_user: str = Depends(get_current_user)
):
    """Returns filtered executive summary details."""
    df = get_current_df()
    if df.empty:
        empty_res = generate_executive_summary(df)
        empty_res["summary_text"] = "Dataset not initialized. Generate or upload a dataset to begin."
        return empty_res
    filtered = filter_df(df, category, city, website_status, opportunity_level, search, min_rating)
    return generate_executive_summary(filtered)

@app.get("/api/export/{format}")
async def api_export(
    format: str, category: str = None, city: str = None, 
    website_status: str = None, opportunity_level: str = None,
    search: str = None, min_rating: float = None,
    current_user: str = Depends(get_current_user)
):
    """
    Renders and exports CSV, Excel, PDF, or PowerPoint PPTX files for the filtered dataset.
    """
    df = get_current_df()
    if df.empty:
        raise HTTPException(status_code=400, detail="No data available to export.")
        
    filtered = filter_df(df, category, city, website_status, opportunity_level, search, min_rating)
    
    # Load cleaning stats
    stats = {}
    if os.path.exists(STATS_FILE):
        with open(STATS_FILE, "r") as f:
            stats = json.load(f)
            
    # Create output filename
    out_dir = tempfile.gettempdir()
    
    if format == "csv":
        out_path = os.path.join(out_dir, "business_opportunities.csv")
        filtered.to_csv(out_path, index=False)
        return FileResponse(out_path, media_type="text/csv", filename="business_opportunities.csv")
        
    elif format == "excel":
        out_path = os.path.join(out_dir, "business_opportunities.xlsx")
        # Format columns cleanly using openpyxl engine
        with pd.ExcelWriter(out_path, engine="openpyxl") as writer:
            filtered.to_excel(writer, index=False, sheet_name="Opportunities")
        return FileResponse(out_path, media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", filename="business_opportunities.xlsx")
        
    elif format == "pdf":
        from src.exporter import create_pdf_report
        out_path = os.path.join(out_dir, "digital_opportunity_report.pdf")
        create_pdf_report(filtered, stats, out_path)
        return FileResponse(out_path, media_type="application/pdf", filename="digital_opportunity_report.pdf")
        
    elif format == "pptx":
        from src.exporter import create_pptx_report
        out_path = os.path.join(out_dir, "digital_opportunity_presentation.pptx")
        create_pptx_report(filtered, stats, out_path)
        return FileResponse(out_path, media_type="application/vnd.openxmlformats-officedocument.presentationml.presentation", filename="digital_opportunity_presentation.pptx")
        
    else:
        raise HTTPException(status_code=400, detail="Invalid export format. Choose csv, excel, pdf, or pptx.")

# Mount frontend files dynamically resolving relative to this file
frontend_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../frontend"))
if os.path.exists(frontend_dir):
    app.mount("/", StaticFiles(directory=frontend_dir, html=True), name="static")
else:
    # Fallback to local static directory if exists, or print warning
    local_static = os.path.join(os.path.dirname(__file__), "static")
    if os.path.exists(local_static):
        app.mount("/", StaticFiles(directory=local_static, html=True), name="static")
    else:
        print(f"Warning: Frontend directory not found at {frontend_dir} or {local_static}")

