import asyncio
import json
import os
import sys

# Add backend dir to sys.path so we can import src
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from src.court_scrapers.tn_land_records import TN_DISTRICT_DATA
from src.llm_engine import llm_engine

async def main():
    names = set()
    for d, d_data in TN_DISTRICT_DATA.items():
        names.add(d)
        for t in d_data["taluks"]:
            names.add(t)
        for v_list in d_data["villages"].values():
            for v in v_list:
                names.add(v)
    
    names = list(names)
    print(f"Total unique names: {len(names)}")
    
    # Split into chunks of 50 to not overwhelm LLM
    chunks = [names[i:i+50] for i in range(0, len(names), 50)]
    
    translations = {"ta": {}, "hi": {}, "ml": {}}
    
    for lang_code, lang_name in [("ta", "Tamil"), ("hi", "Hindi"), ("ml", "Malayalam")]:
        print(f"Translating to {lang_name}...")
        for chunk in chunks:
            prompt = f"Translate the following list of Tamil Nadu place names (districts, taluks, villages) into {lang_name}. Return ONLY a valid JSON object mapping the English name to the {lang_name} name. Do not include markdown formatting or any other text.\n\nNames:\n" + json.dumps(chunk)
            
            res = await llm_engine._call_groq([{"role": "user", "content": prompt}], temperature=0.1, max_tokens=2048)
            if res:
                cleaned = res.strip()
                if "```json" in cleaned:
                    cleaned = cleaned.split("```json")[1].split("```")[0].strip()
                elif "```" in cleaned:
                    cleaned = cleaned.split("```")[1].split("```")[0].strip()
                
                try:
                    parsed = json.loads(cleaned)
                    translations[lang_code].update(parsed)
                except Exception as e:
                    print(f"Failed to parse chunk for {lang_code}: {e}")
                    print(cleaned)

    # Output to a JS file
    with open("../frontend/src/locations.js", "w", encoding="utf-8") as f:
        f.write("export const LOCATION_TRANSLATIONS = {\n")
        for lang, trans in translations.items():
            f.write(f"  {lang}: {json.dumps(trans, ensure_ascii=False)},\n")
        f.write("};\n")
    
    print("Done! Wrote to frontend/src/locations.js")

if __name__ == "__main__":
    asyncio.run(main())
