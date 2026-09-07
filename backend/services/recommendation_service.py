from typing import List, Dict, Optional
from database.herb_repository import HerbRepository
from services.classifier_service import ClassifierService
from services.ai_service import AIService
from config import Config

class RecommendationService:
    def __init__(self, herb_repo: HerbRepository, classifier: ClassifierService, ai: AIService):
        self.repo = herb_repo
        self.classifier = classifier
        self.ai = ai
        self.weights = Config.CONDITION_SCORE_WEIGHTS
    
    def recommend_by_conditions(self, conditions: List[str], limit: int = Config.DEFAULT_LIMIT, 
                               include_ai: bool = True) -> Dict:
        """Get recommendations based on conditions only"""
        condition_names = [c.replace("_", " ").title() for c in conditions]
        scored_herbs = self._score_herbs(condition_names, hair_type=None)
        
        if not scored_herbs:
            return {
                "success": False,
                "message": "No herbs found for these conditions. Try different conditions."
            }
        
        recommendations = self._prepare_recommendations(scored_herbs[:limit], condition_names)
        
        # Add AI explanations
        ai_result = self._add_ai_explanations(recommendations, "Hair Growth", condition_names, include_ai)
        summary = self._generate_summary("Hair Growth", recommendations[:3], condition_names, include_ai)
        
        return {
            "success": True,
            "mode": "condition-only",
            "conditions": condition_names,
            "total_found": len(recommendations),
            "recommendations": ai_result,
            "summary": summary,
            "message": f"🌿 Found {len(recommendations)} herbs for your conditions"
        }
    
    def recommend_with_image(self, conditions: List[str], image_data: Optional[bytes] = None, 
                            limit: int = Config.DEFAULT_LIMIT) -> Dict:
        """Get recommendations with optional image-based hair type detection"""
        condition_names = [c.replace("_", " ").title() for c in conditions]
        
        # Detect hair type from image if provided
        hair_type = None
        confidence = None
        has_image = image_data is not None
        
        if has_image and self.classifier.available:
            prediction = self.classifier.predict(image_data)
            if "error" not in prediction:
                hair_type = prediction.get("hair_type")
                confidence = prediction.get("confidence")
        
        # Score herbs with hair type bonus
        scored_herbs = self._score_herbs(condition_names, hair_type)
        
        if not scored_herbs:
            return {
                "success": False,
                "message": "No herbs found for your conditions."
            }
        
        recommendations = self._prepare_recommendations(scored_herbs[:limit], condition_names, hair_type)
        
        # Add AI explanations
        ai_enabled = self.ai.available
        herb_type = hair_type if hair_type else "Hair Growth"
        ai_result = self._add_ai_explanations(recommendations, herb_type, condition_names, ai_enabled)
        summary = self._generate_summary(herb_type, recommendations[:3], condition_names, ai_enabled)
        
        return {
            "success": True,
            "mode": "image-analysis" if has_image else "condition-only",
            "hair_type": hair_type,
            "confidence": confidence,
            "conditions": condition_names,
            "total_found": len(recommendations),
            "recommendations": ai_result,
            "summary": summary,
            "message": f"🌿 Found {len(recommendations)} herbs for your {'hair type and ' if hair_type else ''}conditions"
        }
    
    def _score_herbs(self, condition_names: List[str], hair_type: Optional[str]) -> List[tuple]:
        """Score each herb based on conditions and optional hair type"""
        herb_scores = []
        conditions_lower = [c.lower() for c in condition_names]
        
        for idx, row in self.repo.df.iterrows():
            score = 0
            benefits = str(row.get("benefits", "")).lower()
            conditions_text = str(row.get("conditions", "")).lower()
            herb_name = str(row.get("herb_name", "")).lower()
            hair_types = str(row.get("hair_types", "")).lower()
            
            # Score based on conditions
            for cond in conditions_lower:
                if cond in benefits:
                    score += self.weights["benefit_match"]
                if cond in conditions_text:
                    score += self.weights["condition_match"]
                if cond in herb_name:
                    score += self.weights["name_match"]
                
                # Partial matches
                for word in cond.split():
                    if len(word) > 3 and (word in benefits or word in conditions_text):
                        score += self.weights["partial_match"]
            
            # Hair type bonus
            if hair_type and hair_type.lower() in hair_types:
                score += self.weights["hair_type_bonus"]
            
            if score > 0:
                herb_scores.append((idx, score, row))
        
        herb_scores.sort(key=lambda x: x[1], reverse=True)
        return herb_scores
    
    def _prepare_recommendations(self, scored_herbs: List[tuple], condition_names: List[str], 
                                hair_type: Optional[str] = None) -> List[Dict]:
        """Prepare recommendation dicts with scores"""
        recommendations = []
        
        for idx, score, row in scored_herbs:
            herb_dict = row.to_dict()
            herb_dict["match_score"] = score
            
            # Calculate match percentage
            total_possible = len(condition_names) * self.weights["benefit_match"]
            match_percentage = min(100, int((score / total_possible) * 100)) if total_possible > 0 else 0
            herb_dict["match_percentage"] = match_percentage
            
            # Find matching conditions
            matching = []
            for condition in condition_names:
                if condition.lower() in str(row.get("benefits", "")).lower():
                    matching.append(condition)
            herb_dict["matching_conditions"] = matching
            
            # Hair type match info
            if hair_type:
                herb_dict["hair_type_match"] = hair_type.lower() in str(row.get("hair_types", "")).lower()
            
            recommendations.append(herb_dict)
        
        return recommendations
    
    def _add_ai_explanations(self, recommendations: List[Dict], hair_type: str, 
                            conditions: List[str], enabled: bool) -> List[Dict]:
        """Add AI explanations to recommendations"""
        if enabled and self.ai.available:
            try:
                result = self.ai.generate_full_response(recommendations, hair_type, conditions)
                return result["explanations"]
            except Exception as e:
                print(f"⚠️ AI explanation error: {e}")
                # Fall through to fallback
        
        # Fallback explanations
        for herb in recommendations:
            herb_name = herb.get('herb_name', 'This herb')
            herb["ai_explanation"] = f"{herb_name} is a traditional Ayurvedic herb for hair health. It supports natural growth and scalp wellness."
        return recommendations
    
    def _generate_summary(self, hair_type: str, recommendations: List[Dict], 
                          conditions: List[str], enabled: bool) -> str:
        """Generate a summary of recommendations"""
        if enabled and self.ai.available:
            try:
                return self.ai.generate_summary(hair_type, recommendations, conditions)
            except Exception as e:
                print(f"⚠️ AI summary error: {e}")
                # Fall through to fallback
        
        return self._create_fallback_summary(hair_type, recommendations)
    
    def _create_fallback_summary(self, hair_type: str, recommendations: List[Dict]) -> str:
        """Create a simple fallback summary"""
        if not recommendations:
            return "No recommendations available."
        
        # FIXED: Use .get() with default value
        herb_names = [h.get('herb_name', 'Unknown') for h in recommendations[:3]]
        herb_list = ", ".join(herb_names)
        
        return f"Based on your {hair_type} condition, we recommend {herb_list}. These Ayurvedic herbs are traditionally used for hair health and growth. Start with one herb and observe how your hair responds."