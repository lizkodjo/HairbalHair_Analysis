from typing import List, Dict

class AIService:
    def __init__(self):
        self.available = False
        self.model_name = None
        self.llm = None
        self._initialize_llm()
    
    def _initialize_llm(self):
        """Initialize LLM with Gemini first, then Hugging Face"""
        # Try Gemini first
        try:
            from api.gemini_simple import GeminiSimple
            gemini = GeminiSimple()
            # Check if Gemini is available by checking if it has the client
            if hasattr(gemini, 'client') and gemini.client is not None:
                self.llm = gemini
                self.available = True
                self.model_name = gemini.model_name
                print(f"✅ Gemini API available (model: {self.model_name})")
                print("   🚀 Batch processing enabled for fast explanations")
                return
            else:
                print("⚠️ Gemini not available - client not initialized")
        except (ImportError, Exception) as e:
            print(f"⚠️ Gemini not available: {e}")
        
        # Try Hugging Face
        try:
            from api.huggingface_integration import HuggingFaceAPI
            huggingface = HuggingFaceAPI()
            # Check if Hugging Face is available
            if hasattr(huggingface, 'available') and huggingface.available:
                self.llm = huggingface
                self.available = True
                self.model_name = "HuggingFace"
                print("✅ Hugging Face API available")
                return
            else:
                print("⚠️ Hugging Face not available")
        except (ImportError, Exception) as e:
            print(f"⚠️ Hugging Face not available: {e}")
        
        print("ℹ️ No AI APIs available - using fallback mode")
        self.llm = None
    
    def generate_full_response(self, recommendations: List[Dict], hair_type: str, 
                              conditions: List[str]) -> Dict:
        """Generate AI explanations for all recommendations in one batch"""
        if not self.available or self.llm is None:
            return {
                "explanations": recommendations,
                "summary": self._fallback_summary(hair_type, conditions)
            }
        
        # Check if the LLM has the method we need
        if hasattr(self.llm, 'generate_full_response'):
            return self.llm.generate_full_response(recommendations, hair_type, conditions)
        elif hasattr(self.llm, 'generate_batch_explanations'):
            # Some LLMs might use this method name
            return self.llm.generate_batch_explanations(recommendations, hair_type, conditions)
        else:
            # Fallback: generate explanations one by one
            explained_herbs = []
            for herb in recommendations:
                herb_copy = herb.copy()
                if hasattr(self.llm, 'generate_explanation'):
                    herb_copy['ai_explanation'] = self.llm.generate_explanation(
                        herb.get('herb_name', 'Unknown'),
                        hair_type,
                        herb.get('benefits', ''),
                        conditions
                    )
                else:
                    herb_copy['ai_explanation'] = self._fallback_explanation(
                        herb.get('herb_name', 'Unknown'),
                        hair_type,
                        herb.get('benefits', '')
                    )
                explained_herbs.append(herb_copy)
            
            return {
                "explanations": explained_herbs,
                "summary": self._fallback_summary(hair_type, conditions)
            }
    
    def generate_summary(self, hair_type: str, recommendations: List[Dict], 
                        conditions: List[str]) -> str:
        """Generate a summary of recommendations"""
        if not self.available or self.llm is None:
            return self._fallback_summary(hair_type, conditions)
        
        if hasattr(self.llm, 'generate_summary'):
            return self.llm.generate_summary(hair_type, recommendations, conditions)
        else:
            return self._fallback_summary(hair_type, conditions)
    
    def _fallback_explanation(self, herb_name: str, hair_type: str, benefits: str) -> str:
        """Fallback explanation generation"""
        benefit_list = benefits.split(",")[:3] if benefits else ["nourishing", "strengthening"]
        benefit_text = ", ".join(benefit_list).lower()
        return f"{herb_name} is a traditional Ayurvedic herb for {hair_type} hair. It contains compounds that {benefit_text}. Apply regularly and consistently for best results."
    
    def _fallback_summary(self, hair_type: str, conditions: List[str]) -> str:
        """Fallback summary generation"""
        cond_text = ", ".join(conditions) if conditions else "hair health"
        return f"🌿 Ayurvedic recommendations for {cond_text}. These herbs support natural hair growth and scalp health."