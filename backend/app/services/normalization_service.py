import rapidfuzz
from sqlalchemy.orm import Session
from app.database.models import GTFSStop
from typing import Dict, List, Tuple, Optional
from sqlalchemy import func
from pydantic import BaseModel

class NormalizationResult(BaseModel):
    status: str
    canonical_stop: Optional[str] = None
    suggestions: List[str] = []
    confidence: float

class StopNormalizationService:
    # Manual mappings for UI-friendly names to canonical GTFS names
    ALIAS_MAP: Dict[str, str] = {
        "majestic": "Corporation",
        "whitefield": "Big Bazzar ITPL",
        "koramangala": "Koramangala",
        "jayanagar": "Jayanagara 5th Block",
        "rajajinagar": "Rajajinagara 1st Block",
        "electronic city": "Electronic City Wipro Main Gate",
        "hebbal": "Hebbala Canara Bank",
        "banashankari": "Banashankari Bus Station",
        "btm layout": "Kuvempunagara Bus Station(BTM Layout)",
        "hsr layout": "14th Main HSR Layout",
        "yeshwanthpur": "Yeshwanthpur",
        "kr puram": "KR Puram",
        "shivajinagar": "Shivajinagar",
        "indiranagar": "Indiranagar",
        "marathahalli": "Marathahalli"
    }

    _cached_stop_names: List[str] = []

    @classmethod
    def _get_all_stop_names(cls, db: Session) -> List[str]:
        if not cls._cached_stop_names:
            stops = db.query(
                GTFSStop.stop_name, 
                func.count(GTFSStop.stop_id).label("freq")
            ).group_by(GTFSStop.stop_name).all()
            
            # Filter out None values and sort by frequency descending, then alphabetically ascending
            valid_stops = [s for s in stops if s[0]]
            sorted_stops = sorted(valid_stops, key=lambda x: (-x[1], x[0]))
            cls._cached_stop_names = [s[0] for s in sorted_stops]
        return cls._cached_stop_names

    @classmethod
    def normalize_stop(cls, db: Session, user_input: str) -> NormalizationResult:
        """
        Normalizes a user-input stop name to a canonical GTFS stop name.
        """
        normalized_input = user_input.lower().strip()
        
        # 1. Alias Match Override (Exact Override)
        if normalized_input in cls.ALIAS_MAP:
            return NormalizationResult(
                status="auto_corrected",
                canonical_stop=cls.ALIAS_MAP[normalized_input],
                suggestions=[],
                confidence=100.0
            )

        all_stops = cls._get_all_stop_names(db)
        
        # 2. Exact Match Check (Case-insensitive)
        for stop in all_stops:
            if normalized_input == stop.lower().strip():
                return NormalizationResult(
                    status="auto_corrected",
                    canonical_stop=stop,
                    suggestions=[],
                    confidence=100.0
                )

        # 3. Fuzzy Matching using RapidFuzz
        matches = rapidfuzz.process.extract(
            user_input, 
            all_stops, 
            scorer=rapidfuzz.fuzz.token_sort_ratio,
            limit=5
        )
        
        if not matches:
            return NormalizationResult(
                status="rejected",
                canonical_stop=None,
                suggestions=[],
                confidence=0.0
            )

        # RapidFuzz match tuple: (match_string, score, index_in_all_stops)
        # Tie-breaking: sort by (-score, index_in_all_stops). 
        # Lower index = higher frequency (because all_stops is sorted by freq desc)
        sorted_matches = sorted(matches, key=lambda m: (-m[1], m[2]))
        
        best_match, score, _ = sorted_matches[0]
        suggestions = [m[0] for m in sorted_matches]
        
        # 4. Threshold Check
        if score >= 85.0:
            status = "auto_corrected"
        elif score >= 70.0:
            status = "suggested"
        else:
            status = "rejected"
            
        return NormalizationResult(
            status=status,
            canonical_stop=best_match if status != "rejected" else None,
            suggestions=suggestions,
            confidence=score
        )
