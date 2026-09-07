import logging
from typing import Dict, List, Optional
from dotenv import load_dotenv
from huggingface_hub import HfApi, InferenceClient
from huggingface_hub.errors import HfHubHTTPError
import os
import time
import requests

load_dotenv()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class HuggingFaceAPI:
    """Integrate with Hugging Face API"""

    def __init__(
        self,
        api_token: Optional[str] = None,
        model_name: str = "google/flan-t5-base",
    ):
        """Initialise the Hugging Face API client"""

        # Get API token
        if api_token is None:
            api_token = os.getenv("HUGGINGFACE_API_TOKEN")

        self.api_token = api_token
        self.model_name = model_name
        self.available = False
        self.client = None
        self.api = None
        self.is_chat_model = "Instruct" in model_name or "Chat" in model_name

        # Initialise the API
        self._initialise()

    def _initialise(self):
        """Initialise the Hugging Face API client"""

        try:
            if not self.api_token:
                logger.warning("No Hugging Face API token found. Features disabled")
                logger.info(
                    "Get your free token at: https://huggingface.co/settings/tokens"
                )
                return

            # Try primary model
            if self._test_model(self.model_name):
                self._setup_client(self.model_name)
                return

            # Try fallback models
            fallback_models = [
                "google/flan-t5-base",
                "google/flan-t5-small",
            ]

            for fallback in fallback_models:
                if self._test_model(fallback):
                    self.model_name = fallback
                    self._setup_client(fallback)
                    logger.info(f"✅ Using fallback model: {fallback}")
                    return

            logger.warning("⚠️ No Hugging Face models available. Using fallback mode.")
            self.available = False

        except Exception as e:
            logger.error(f"Error initialising Hugging Face API: {e}")
            self.available = False

    def _test_model(self, model_name: str) -> bool:
        """Test if a model is accessible"""
        try:
            api = HfApi(token=self.api_token)
            api.model_info(repo_id=model_name, token=self.api_token)
            return True
        except Exception:
            return False

    def _setup_client(self, model_name: str):
        """Setup the API client for a specific model"""
        try:
            self.client = InferenceClient(
                model=model_name, token=self.api_token, timeout=30
            )
            self.api = HfApi(token=self.api_token)

            user = self.api.whoami()
            logger.info(
                f"✅ Hugging Face API initialised with {model_name} as: {user.get('name', 'Unknown')}"
            )
            self.available = True
        except Exception as e:
            logger.error(f"Error setting up client: {e}")
            self.available = False

    def _call_text_generation(
        self, prompt: str, max_tokens: int = 150
    ) -> Optional[str]:
        """
        Call text generation API using the InferenceClient
        This works with flan-t5-large
        """
        if not self.available or not self.client:
            return None

        try:
            # Use the client's text_generation method
            response = self.client.text_generation(
                prompt,
                max_new_tokens=max_tokens,
                temperature=0.7,
                do_sample=True,
                return_full_text=False,
            )

            if response and isinstance(response, str):
                return response.strip()

            # If we get a different response format, try to extract text
            if response and hasattr(response, "generated_text"):
                return response.generated_text.strip()

            return None

        except HfHubHTTPError as e:
            if e.response.status_code == 429:  # Rate limit
                logger.warning("Rate limit hit, waiting 3 seconds...")
                time.sleep(3)
                # Retry once
                try:
                    response = self.client.text_generation(
                        prompt,
                        max_new_tokens=max_tokens,
                        temperature=0.7,
                        do_sample=True,
                        return_full_text=False,
                    )
                    if response and isinstance(response, str):
                        return response.strip()
                except:
                    pass
            elif e.response.status_code == 503:  # Model loading
                logger.warning("Model loading, waiting 5 seconds...")
                time.sleep(5)
                # Retry once
                try:
                    response = self.client.text_generation(
                        prompt,
                        max_new_tokens=max_tokens,
                        temperature=0.7,
                        do_sample=True,
                        return_full_text=False,
                    )
                    if response and isinstance(response, str):
                        return response.strip()
                except:
                    pass
            else:
                logger.error(f"API error: {e}")
            return None
        except Exception as e:
            logger.error(f"Error calling text generation: {e}")
            return None

    def _call_inference_api(self, prompt: str, max_tokens: int = 150) -> Optional[str]:
        """
        Alternative: Call the Inference API directly using requests
        This sometimes works better with flan-t5-large
        """
        if not self.api_token:
            return None

        try:
            api_url = f"https://api-inference.huggingface.co/models/{self.model_name}"
            headers = {"Authorization": f"Bearer {self.api_token}"}

            payload = {
                "inputs": prompt,
                "parameters": {
                    "max_new_tokens": max_tokens,
                    "temperature": 0.7,
                    "do_sample": True,
                    "return_full_text": False,
                },
            }

            response = requests.post(api_url, headers=headers, json=payload, timeout=30)

            if response.status_code == 200:
                result = response.json()
                # Handle different response formats
                if isinstance(result, list) and len(result) > 0:
                    if "generated_text" in result[0]:
                        return result[0]["generated_text"].strip()
                elif isinstance(result, dict) and "generated_text" in result:
                    return result["generated_text"].strip()
                return None
            elif response.status_code == 503:
                logger.warning("Model is loading, waiting 3 seconds...")
                time.sleep(3)
                # Retry once
                response = requests.post(
                    api_url, headers=headers, json=payload, timeout=30
                )
                if response.status_code == 200:
                    result = response.json()
                    if isinstance(result, list) and len(result) > 0:
                        if "generated_text" in result[0]:
                            return result[0]["generated_text"].strip()
            else:
                logger.warning(f"API returned status {response.status_code}")
                return None

        except Exception as e:
            logger.error(f"Error calling inference API: {e}")
            return None

    def generate_explanation(
        self,
        herb_name: str,
        hair_type: str,
        benefits: str,
        conditions: Optional[List[str]] = None,
    ) -> str:
        """Generates an explanation for a herb recommendation"""

        # Clean up condition names
        clean_conditions = []
        if conditions:
            for c in conditions:
                c_clean = c.replace("_", " ").title()
                clean_conditions.append(c_clean)

        condition_text = ""
        if clean_conditions:
            condition_text = f" The user also has these hair conditions: {', '.join(clean_conditions[:3])}."

        # Simplified prompt for flan-t5-large
        prompt = f"Explain why {herb_name} is good for {hair_type} hair. Benefits: {benefits}.{condition_text} Keep it short (2 sentences)."

        # Try InferenceClient first
        if self.available:
            result = self._call_text_generation(prompt, max_tokens=100)
            if result:
                return result

        # Try direct Inference API as fallback
        result = self._call_inference_api(prompt, max_tokens=100)
        if result:
            return result

        # Final fallback
        condition_list = (
            f"for {', '.join(clean_conditions[:2])}"
            if clean_conditions
            else f"for {hair_type} hair"
        )
        return f"{herb_name} is beneficial {condition_list}. Its {benefits} properties help support healthy, natural hair."

    def generate_summary(
        self,
        hair_type: str,
        recommendations: List[Dict],
        conditions: Optional[List[str]] = None,
    ) -> str:
        """Generate summary of recommendations"""

        if not recommendations:
            return f"For {hair_type} hair, we recommend checking our complete herb database for natural hair care options."

        try:
            # Clean conditions
            clean_conditions = []
            if conditions:
                for c in conditions:
                    c_clean = c.replace("_", " ").title()
                    clean_conditions.append(c_clean)

            condition_text = ""
            if clean_conditions:
                condition_text = f" The user wants to address these conditions: {', '.join(clean_conditions[:3])}."

            # Safely get herb names
            herb_names = []
            herbs_text = ""
            for herb in recommendations[:3]:
                if isinstance(herb, dict):
                    name = herb.get("herb_name", "Unknown herb")
                    herb_names.append(name)
                    herbs_text += f"- {name}\n"
                else:
                    herb_names.append(str(herb))

            # Simplified prompt for flan-t5-large
            prompt = f"Write a short summary (3 sentences) for someone with {hair_type} hair. Recommend these herbs: {', '.join(herb_names)}.{condition_text} Make it encouraging."

            # Try InferenceClient first
            if self.available:
                result = self._call_text_generation(prompt, max_tokens=150)
                if result:
                    return result

            # Try direct Inference API as fallback
            result = self._call_inference_api(prompt, max_tokens=150)
            if result:
                return result

            # Final fallback
            herb_list = ", ".join(herb_names[:3])
            condition_text_fallback = (
                f" for addressing {', '.join(clean_conditions[:3])}"
                if clean_conditions
                else ""
            )
            return f"For your {hair_type} hair{condition_text_fallback}, we recommend {herb_list}. These Ayurvedic herbs are known to support healthy, vibrant hair naturally. Start with one herb and observe the results."

        except Exception as e:
            logger.error(f"Error generating summary: {e}")
            return self._fallback_summary(hair_type, recommendations, conditions)

    def _fallback_explanation(
        self,
        herb_name: str,
        hair_type: str,
        benefits: str,
        conditions: Optional[List[str]] = None,
    ) -> str:
        """Fallback explanation when API fails"""
        clean_conditions = [c.replace("_", " ").title() for c in (conditions or [])[:2]]
        condition_text = (
            f" for addressing {', '.join(clean_conditions)}"
            if clean_conditions
            else f" for {hair_type} hair"
        )
        return f"{herb_name} is traditionally used{condition_text}. Its {benefits} properties help support healthy, natural hair."

    def _fallback_summary(
        self,
        hair_type: str,
        recommendations: List[Dict],
        conditions: Optional[List[str]] = None,
    ) -> str:
        """Fallback summary when API is unavailable"""
        if not recommendations:
            return f"For {hair_type} hair, we recommend checking our complete herb database for natural hair care options."

        herb_names = []
        for r in recommendations[:3]:
            if isinstance(r, dict):
                herb_names.append(r.get("herb_name", "Unknown herb"))
            else:
                herb_names.append(str(r))

        herb_list = ", ".join(herb_names)
        clean_conditions = [c.replace("_", " ").title() for c in (conditions or [])[:3]]
        condition_text = (
            f" for addressing {', '.join(clean_conditions)}" if clean_conditions else ""
        )

        return f"For your {hair_type} hair{condition_text}, we recommend {herb_list}. These Ayurvedic herbs are known to support healthy, vibrant hair naturally."

    def list_available_models(self) -> List[str]:
        """List models that I have access to"""
        if not self.available or not self.api:
            return []

        try:
            models = self.api.list_models(
                author="google", limit=10, token=self.api_token
            )
            return [model.id for model in models]
        except Exception as e:
            logger.error(f"Error listing models: {e}")
            return []

    def get_model_info(self) -> Dict:
        """Get information about the current model"""
        if not self.available or not self.api:
            return {}

        try:
            model_info = self.api.model_info(
                repo_id=self.model_name, token=self.api_token
            )
            return {
                "id": model_info.id,
                "downloads": model_info.downloads,
                "likes": model_info.likes,
                "private": model_info.private,
                "tags": model_info.tags[:5] if model_info.tags else [],
            }
        except Exception as e:
            logger.error(f"Error getting model info: {e}")
            return {}
