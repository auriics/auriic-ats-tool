import os
from typing import Dict, List, Any, Optional
from backend.engine.normalizer import normalize_for_matching, tokenize_and_lemmatize
from backend.config.loader import load_scoring_config

def detect_industry(text: str, user_override: Optional[str] = None) -> Dict[str, Any]:
    """Detect the most likely industry group among the 8 Auriic domains or apply user override."""
    config = load_scoring_config()
    industries = config.get("industries", {})
    
    valid_ids = list(industries.keys())
    
    # Handle user override if provided
    if user_override and user_override.lower() in valid_ids:
        chosen_id = user_override.lower()
        return {
            "industry_id": chosen_id,
            "industry_name": industries[chosen_id]["name"],
            "is_override": True,
            "confidence": 1.0,
            "scores_by_industry": {k: 0 for k in valid_ids},
            "matched_keywords": [],
        }

    norm_text = normalize_for_matching(text)
    tokens = set(tokenize_and_lemmatize(text))
    
    scores = {}
    matched_by_ind = {}

    for ind_id, ind_data in industries.items():
        score = 0
        matches = []
        
        # Match keywords (weight: 1)
        for kw in ind_data.get("keywords", []):
            norm_kw = normalize_for_matching(kw)
            if " " in norm_kw:
                if norm_kw in norm_text:
                    score += 2
                    matches.append(kw)
            else:
                if norm_kw in tokens:
                    score += 1
                    matches.append(kw)
                    
        # Match domain skills (weight: 2)
        for skill in ind_data.get("skills", []):
            norm_sk = normalize_for_matching(skill)
            if " " in norm_sk:
                if norm_sk in norm_text:
                    score += 3
                    matches.append(skill)
            else:
                if norm_sk in tokens:
                    score += 2
                    matches.append(skill)
                    
        scores[ind_id] = score
        matched_by_ind[ind_id] = matches

    # Determine highest scoring industry
    best_id = "it"  # default baseline
    best_score = -1

    for ind_id, score in scores.items():
        if score > best_score:
            best_score = score
            best_id = ind_id

    total_matches = sum(scores.values())
    confidence = round(best_score / max(1, total_matches), 2) if total_matches > 0 else 0.50

    return {
        "industry_id": best_id,
        "industry_name": industries[best_id]["name"],
        "is_override": False,
        "confidence": confidence,
        "scores_by_industry": scores,
        "matched_keywords": matched_by_ind.get(best_id, [])[:10],
    }
