import os
import sys
import tempfile
import pandas as pd

# Add the workspace root to python path to import src
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from src.generator import generate_dataset
from src.cleaner import clean_dataset, STRICT_REQUIRED
from src.analyzer import calculate_scores, generate_executive_summary, generate_ai_insights
from src.exporter import create_pdf_report, create_pptx_report

def run_tests():
    print("--------------------------------------------------")
    print("Running Google Maps BI Platform Integration Tests...")
    print("--------------------------------------------------")
    
    # 1. Test Demo Dataset Generation
    print("Step 1: Testing Indian Business Demo Generator...")
    df_raw = generate_dataset(200)
    assert len(df_raw) == 200, f"Expected 200 rows, got {len(df_raw)}"
    assert "Business Name" in df_raw.columns, "Missing Business Name column"
    assert "Phone Number" in df_raw.columns, "Missing Phone Number column"
    assert "City" in df_raw.columns, "Missing City column"
    assert (df_raw["Phone Number"].str.startswith("+91") | (df_raw["Phone Number"] == "")).all(), "Phone number should start with +91 or be empty"
    print("Generation passed.")
    
    # 2. Test Data Cleaning Pipeline
    print("Step 2: Testing Data Cleaning & Preprocessing Pipeline...")
    df_clean, stats = clean_dataset(df_raw)
    assert len(df_clean) == stats["final_clean_records"], "Clean df length mismatch with stats"
    assert stats["original_records"] == 200, "Original record count should be 200"
    assert (df_clean["Website"] != "").all(), "Websites should not contain empty strings, they should be mapped to 'No Website'"
    print("Cleaning pipeline passed.")
    
    # 3. Test Opportunity Scoring Engine
    print("Step 3: Testing 0-100 Scoring Engine...")
    df_scored = calculate_scores(df_clean)
    assert "Opportunity Score" in df_scored.columns, "Missing Opportunity Score column"
    assert "Data Quality Score" in df_scored.columns, "Missing Data Quality Score column"
    assert "Opportunity Level" in df_scored.columns, "Missing Opportunity Level column"
    assert "Recommendation Reason" in df_scored.columns, "Missing Recommendation Reason column"
    assert (df_scored["Opportunity Score"] >= 0).all() and (df_scored["Opportunity Score"] <= 100).all(), "Opp score out of bounds"
    assert (df_scored["Data Quality Score"] >= 0).all() and (df_scored["Data Quality Score"] <= 100).all(), "DQ score out of bounds"
    print("Opportunity and Quality Scoring engines passed.")
    
    # 4. Test Executive Summary & AI Insights Compilation
    print("Step 4: Testing Executive Summaries and AI Insights...")
    summary = generate_executive_summary(df_scored)
    assert summary["total_businesses"] == len(df_scored), "Total businesses count mismatch"
    assert "summary_text" in summary, "Missing summary text"
    
    insights = generate_ai_insights(df_scored)
    assert len(insights) >= 5, f"Expected at least 5 insights, got {len(insights)}"
    print("Analytics brief compilation passed.")
    
    # 5. Test PDF and PowerPoint Exports
    print("Step 5: Testing PDF & PPTX Exporters...")
    with tempfile.TemporaryDirectory() as temp_dir:
        pdf_path = os.path.join(temp_dir, "test_report.pdf")
        pptx_path = os.path.join(temp_dir, "test_presentation.pptx")
        
        create_pdf_report(df_scored, stats, pdf_path)
        assert os.path.exists(pdf_path), "PDF file was not created"
        assert os.path.getsize(pdf_path) > 0, "PDF file is empty"
        
        create_pptx_report(df_scored, stats, pptx_path)
        assert os.path.exists(pptx_path), "PPTX file was not created"
        assert os.path.getsize(pptx_path) > 0, "PPTX file is empty"
        
    print("Report exports passed.")
    
    # 6. Test Custom Google Maps Dataset Ingestion
    print("Step 6: Testing Custom Google Maps Dataset Ingestion & Processing...")
    project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
    custom_raw_path = os.path.join(project_root, "data", "processed", "businesses_master_clean.csv")
    
    if os.path.exists(custom_raw_path):
        df_custom_raw = pd.read_csv(custom_raw_path)
        df_custom_clean, custom_stats = clean_dataset(df_custom_raw)
        
        # Verify that priority mapping resolved duplicate columns (Address and Reviews)
        assert not df_custom_clean.columns.duplicated().any(), "Cleaned columns contain duplicates!"
        
        # Verify strictly required fields are present
        for req in STRICT_REQUIRED:
            assert req in df_custom_clean.columns, f"Missing required column: {req}"
            
        # Verify Latitude/Longitude coordinate extraction
        assert "Latitude" in df_custom_clean.columns and "Longitude" in df_custom_clean.columns, "Missing coordinate columns"
        assert df_custom_clean["Latitude"].notna().any(), "All extracted Latitudes are NaN"
        assert df_custom_clean["Longitude"].notna().any(), "All extracted Longitudes are NaN"
        
        # Verify cautious verification status (set to Unknown)
        assert "Verified Business" in df_custom_clean.columns, "Missing Verified Business"
        assert (df_custom_clean["Verified Business"] == "Unknown").all(), "Verified Business should be Unknown"
        
        # Run through scoring and insights
        df_custom_scored = calculate_scores(df_custom_clean)
        custom_summary = generate_executive_summary(df_custom_scored)
        custom_insights = generate_ai_insights(df_custom_scored)
        
        assert "Opportunity Score" in df_custom_scored.columns, "Missing Opportunity Score"
        assert custom_summary["total_businesses"] == len(df_custom_scored), "Scored business count mismatch"
        assert len(custom_insights) > 0, "No custom insights compiled"
        
        print("Custom Google Maps dataset compatibility tests passed.")
    else:
        print(f"Skipping Step 6: Custom raw file not found at {custom_raw_path}")
        
    # 7. Test User Authentication Database Operations
    print("Step 7: Testing User Authentication & Database Operations...")
    from src.database import create_user, get_user, verify_password, create_session, get_session, delete_session
    
    test_username = "test_user_integration"
    test_password = "secure_password_123"
    
    # Clean up user if left from previous runs (for robustness)
    import sqlite3
    from src.database import DB_FILE
    conn = sqlite3.connect(DB_FILE)
    conn.execute("DELETE FROM users WHERE username = ?", (test_username,))
    conn.execute("DELETE FROM sessions WHERE username = ?", (test_username,))
    conn.commit()
    conn.close()
    
    # Create user
    success = create_user(test_username, test_password)
    assert success is True, "Failed to create test user"
    
    # Try duplicate user
    dup_success = create_user(test_username, test_password)
    assert dup_success is False, "Duplicate user creation should fail"
    
    # Retrieve user
    user = get_user(test_username)
    assert user is not None, "Failed to retrieve user details"
    assert user["username"] == test_username
    assert user["password_hash"] != test_password, "Password hash must not be plain text"
    
    # Verify password
    assert verify_password(test_password, user["password_hash"], user["salt"]) is True, "Password verification failed"
    assert verify_password("wrong_password", user["password_hash"], user["salt"]) is False, "Invalid password passed verification"
    
    # Create session
    token = create_session(test_username)
    assert token is not None, "Failed to create session token"
    
    # Retrieve session
    session = get_session(token)
    assert session is not None, "Failed to retrieve active session"
    assert session["username"] == test_username
    
    # Invalidate session
    logout_success = delete_session(token)
    assert logout_success is True, "Logout/delete session failed"
    assert get_session(token) is None, "Session remains valid after logout"
    
    # Clean up test user
    conn = sqlite3.connect(DB_FILE)
    conn.execute("DELETE FROM users WHERE username = ?", (test_username,))
    conn.commit()
    conn.close()
    
    print("User authentication database tests passed.")
        
    print("--------------------------------------------------")
    print("All integration tests completed successfully!")
    print("--------------------------------------------------")

if __name__ == "__main__":
    run_tests()
