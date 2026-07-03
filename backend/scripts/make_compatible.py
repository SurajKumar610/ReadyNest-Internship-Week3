import os
import sys
import pandas as pd

# Add backend directory to sys.path so we can import src
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from src.cleaner import clean_dataset
from src.analyzer import calculate_scores

def main():
    script_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.abspath(os.path.join(script_dir, "..", ".."))
    
    input_file = os.path.join(project_root, "data", "processed", "businesses_master_clean.csv")
    output_file = os.path.join(project_root, "data", "processed", "businesses_master_compatible.csv")
    
    if not os.path.exists(input_file):
        print(f"Error: clean dataset not found at {input_file}")
        return
        
    print(f"Loading {input_file}...")
    df = pd.read_csv(input_file)
    
    print("Running compatibility clean_dataset pipeline...")
    cleaned_df, stats = clean_dataset(df)
    
    print("Running scoring engine...")
    scored_df = calculate_scores(cleaned_df)
    
    print(f"Saving compatible dataset to {output_file}...")
    scored_df.to_csv(output_file, index=False)
    print("Successfully created compatible dataset!")

if __name__ == "__main__":
    main()
