import pandas as pd
import os
import json

# Keywords that trigger a "Risk Alert" when found in the news
RISK_WEIGHTS = {
    "collapse": 20.0, "closed": 20.0, "failure": 20.0, "earthquake": 20.0,
    "fire": 10.0, "flood": 10.0, "spill": 10.0, "accident": 10.0,
    "strike": 5.0, "protest": 5.0, "delay": 2.0, "traffic": 2.0
}

def scan_news_for_risk(target_city):
    """
    Scans the JSON dataset for any negative news regarding the target_city.
    Returns: A dictionary containing the detected risk and cost multiplier.
    """

    target_city = str(target_city).strip().lower()

    print(f"[RISK MONITOR] Scanning 'News_Category_Dataset_v3.json' for {target_city}...")
    
    file_path = 'News_Category_Dataset_v3.json'
    
    if not os.path.exists(file_path):
        print(f"[ERROR] News Dataset not found at {file_path}")
        return None

    try:
        # Load JSON
        try:
            df = pd.read_json(file_path, lines=True)
        except ValueError:
            df = pd.read_json(file_path)

        # Combine text
        df['combined_text'] = ""
        if 'headline' in df.columns:
            df['combined_text'] += df['headline'].astype(str) + " "
        if 'short_description' in df.columns:
            df['combined_text'] += df['short_description'].astype(str)

        df['combined_text'] = df['combined_text'].str.lower()

        # 🔥 FIX: Disable regex interpretation
        city_news = df[df['combined_text'].str.contains(
            target_city,
            case=False,
            regex=False,
            na=False
        )]

        if city_news.empty:
            print(f"[RISK MONITOR] No news found for {target_city}. Route is clear.")
            return None

        max_multiplier = 1.0
        detected_event = None

        print(f"[RISK MONITOR] Found {len(city_news)} articles for {target_city}. Analyzing risks...")

        for _, row in city_news.iterrows():
            text = row['combined_text']
            for keyword, weight in RISK_WEIGHTS.items():
                if keyword in text:
                    if weight > max_multiplier:
                        max_multiplier = weight
                        detected_event = f"{keyword.upper()} reported in {target_city}"

        if max_multiplier > 1.0:
            print(f"[ALERT] Active Risk Identified: {detected_event} (Impact: {max_multiplier}x)")
            return {
                "city": target_city,
                "multiplier": max_multiplier,
                "reason": detected_event
            }

    except Exception as e:
        print(f"[ERROR] Risk Monitor Failed: {e}")

    return None