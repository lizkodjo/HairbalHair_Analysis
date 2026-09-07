from typing import Dict, List, Optional
import pandas as pd
from config import Config


class HerbRepository:
    def __init__(self) -> None:
        self.df = self._load_data()
        self._validate_columns()
        self._clean_data()

    def _load_data(self) -> pd.DataFrame:
        """Load herb data from csv with fallback"""
        try:
            csv_path = Config.HERB_CSV_PATH
            if not csv_path.exists():
                print(f"⚠️ CSV not found: {csv_path}")
                return self._create_fallback_data()

            df = pd.read_csv(csv_path)
            print(f"✅ Loaded {len(df)} herbs from comprehensive CSV")

            # Test
            print(f"   Columns: {', '.join(df.columns.tolist())}")
            print(
                f"   Unique conditions: {len(set(','.join(df['conditions'].astype(str)).split(',')))}"
            )
            print(
                f"   Unique hair types: {len(set(','.join(df['hair_types'].astype(str)).split(',')))}"
            )

            return df
        except Exception as e:
            print(f"❌ Error loading CSV: {e}")
            import traceback

            traceback.print_exc()
            return self._create_fallback_data()

    def _create_fallback_data(self) -> pd.DataFrame:
        """Create comprehensive fallback if CSV is missing"""
        print("⚠️ Creating comprehensive fallback data...")
        data = [
            {
                "herb_name": "Bhringraj",
                "english_name": "False Daisy",
                "botanical_name": "Eclipta alba",
                "sanskrit_name": "Keshraja",
                "parts_used": "Panchanga",
                "benefits": "Promotes hair growth, prevents greying, strengthens roots, reduces hair fall, improves hair thickness",
                "how_to_use": "Apply Bhringraj oil to scalp and massage gently. Leave for 30-60 minutes before washing with mild shampoo. Use 2-3 times weekly.",
                "hair_types": "All,Curly,Coily,Wavy,Straight",
                "conditions": "Hair Growth,Hair Fall,Premature Greying,Dry Hair,Thinning Hair",
                "main_indications": "Khalitya, Palitya, Kamala, Pandu, Yakrit Vikara",
                "dosha_effects": "Vata, Pitta",
                "active_compounds": "Wedelolactone, Flavonoids, Triterpenoids",
                "match_score": 12,
            },
            {
                "herb_name": "Amla",
                "english_name": "Indian Gooseberry",
                "botanical_name": "Emblica officinalis",
                "sanskrit_name": "Amalaki",
                "parts_used": "Phala",
                "benefits": "Rich in Vitamin C, strengthens follicles, reduces hair fall, prevents greying, adds shine, promotes growth",
                "how_to_use": "Mix Amla powder with water or coconut oil, apply to scalp and hair, leave for 20-30 minutes, rinse. Use weekly.",
                "hair_types": "All,Dry,Oily,Straight,Wavy",
                "conditions": "Hair Growth,Hair Fall,Premature Greying,Dull Hair,Dry Hair",
                "main_indications": "Amalaki Rasayana, Jwara, Netraroga, Keshya",
                "dosha_effects": "Tridosha",
                "active_compounds": "Vitamin C, Tannins, Gallic acid, Ellagic acid",
                "match_score": 11,
            },
            {
                "herb_name": "Neem",
                "english_name": "Indian Lilac",
                "botanical_name": "Azadirachta indica",
                "sanskrit_name": "Nimba",
                "parts_used": "Patra",
                "benefits": "Antibacterial, treats scalp infections, controls oil, reduces dandruff, soothes itchy scalp, promotes healthy scalp",
                "how_to_use": "Boil Neem leaves in water, cool, use as final hair rinse. Or mix powder with water for scalp treatment.",
                "hair_types": "Oily,Normal,Straight,Wavy",
                "conditions": "Dandruff,Scalp Health,Itchy Scalp,Oily Scalp,Scalp Infections",
                "main_indications": "Kushta, Krimi, Jwara, Kandu, Visarpa",
                "dosha_effects": "Kapha, Pitta",
                "active_compounds": "Azadirachtin, Nimbin, Nimbolide, Quercetin",
                "match_score": 10,
            },
        ]
        return pd.DataFrame(data)

    def _validate_columns(self):
        """Ensure cols exist"""
        required_cols = [
            "herb_name",
            "benefits",
            "how_to_use",
            "hair_types",
            "conditions",
        ]
        missing = [col for col in required_cols if col not in self.df.columns]

        if missing:
            print(f"⚠️ Missing columns: {missing}")
            for col in missing:
                self.df[col] = "Information not available"

    def _clean_data(self):
        """Clean and prepare data"""
        self.df = self.df.fillna("")
        self.df = self.df.reset_index(drop=True)

        # Convert match_score to int
        if "match_score" in self.df.columns:
            self.df["match_score"] = (
                pd.to_numeric(self.df["match_score"], errors="coerce")
                .fillna(0)
                .astype(int)
            )

    def get_all(self) -> List[Dict]:
        """Get all herbs as dict"""
        return self.df.to_dict("records")

    def get_by_index(self, index: int) -> Optional[Dict]:
        """Get herb by index"""
        if 0 <= index < len(self.df):
            return self.df.iloc[index].to_dict()
        return None

    def search(self, query: str) -> List[Dict]:
        """Search herbs by name, benefits, etc"""
        if not query:
            return []

        query_lower = query.lower()
        results = []

        for _, row in self.df.iterrows():
            # Search multiple fields
            search_text = " ".join(
                [
                    str(row.get("herb_name", "")),
                    str(row.get("english_name", "")),
                    str(row.get("botanical_name", "")),
                    str(row.get("sanskrit_name", "")),
                    str(row.get("benefits", "")),
                    str(row.get("conditions", "")),
                ]
            ).lower()

            if query_lower in search_text:
                results.append(row.to_dict())
        return results

    def get_all_conditions(self) -> List[str]:
        """Get all unique conditions"""
        conditions = set()

        for cond_str in self.df["conditions"]:
            if isinstance(cond_str, str):
                for c in cond_str.split(","):
                    c = c.strip()
                    if c:
                        conditions.add(c)
        return sorted(conditions)

    def get_all_hair_types(self) -> List[str]:
        """Get all unique hair types"""
        hair_types = set()
        for types_str in self.df["hair_types"]:
            if isinstance(types_str, str):
                for t in types_str.split(","):
                    t = t.strip()
                    if t:
                        hair_types.add(t)
        return sorted(hair_types)

    def get_by_condition(self, condition: str) -> List[Dict]:
        """Get herbs that address a specific condtions"""
        condition_lower = condition.lower()
        results = []

        for _, row in self.df.iterrows():
            conditions = str(row.get("conditions", "")).lower()
            if condition_lower in conditions:
                results.append(row.to_dict())

        return results

    def get_by_hair_types(self, hair_type: str) -> List[Dict]:
        """Get herbs suitable for a specific hair type"""
        hair_type_lower = hair_type.lower()
        results = []

        for _, row in self.df.iterrows():
            hair_types = str(row.get("hair_types", "")).lower()
            if hair_type_lower in hair_types or "all" in hair_types:
                results.append(row.to_dict())
        return results

    def count(self) -> int:
        return len(self.df)

    def get_stats(self) -> Dict:
        """Get repo stats"""
        return {
            "total_herbs": self.count(),
            "conditions": len(self.get_all_conditions()),
            "hair_types": len(self.get_all_hair_types()),
            "columns": self.df.columns.tolist(),
        }

    def get_herb_names(self) -> List[Dict]:
        """Get list of all herbs"""
        return self.df["herb_name"].tolist()
