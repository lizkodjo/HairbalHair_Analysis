import os
import logging
import re
from typing import Dict, List, Optional
from dotenv import load_dotenv

load_dotenv()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class GeminiSimple:
    """Simple Gemini API integration with batch processing"""

    def __init__(self, model_name: str = "gemini-3.6-flash"):
        """
        Initialise with API key from environment
        """

        # Try multiple possible environment variable names
        self.api_key = (
            os.getenv("GOOGLE_API_KEY")
            or os.getenv("GOOGLE_AI_STUDIO_KEY")
            or os.getenv("GEMINI_API_KEY")
        )

        self.model_name = model_name
        self.available = False
        self.client = None
        self.rate_limited = False
        self.retry_after = 0
        self.daily_quota_exceeded = False

        if not self.api_key:
            logger.warning("⚠️ No Google API key found. Gemini features disabled.")
            logger.info("📝 Get your key at: https://aistudio.google.com/app/apikey")
            return

        try:
            from google import genai

            self.client = genai.Client(api_key=self.api_key)

            # Try to initialize with the primary model
            try:
                self.chat = self.client.chats.create(model=self.model_name)
                test_response = self.chat.send_message("Say OK")

                if test_response and test_response.text:
                    self.available = True
                    logger.info(f"✅ Gemini API initialized with {self.model_name}!")
                else:
                    logger.warning("⚠️ Gemini API test returned empty response")

            except Exception as e:
                error_str = str(e)

                # Check if this is a quota/rate limit error
                if self._is_rate_limit_error(e):
                    self.daily_quota_exceeded = True
                    self.rate_limited = True
                    self.available = False

                    # Extract retry time if available
                    retry_match = re.search(r"retry in ([\d.]+)s", error_str)
                    if retry_match:
                        self.retry_after = float(retry_match.group(1))
                        logger.warning(
                            f"⚠️ Daily quota exceeded! Retry in {self.retry_after:.0f}s"
                        )
                    else:
                        logger.warning("⚠️ Daily quota exceeded! Using fallback mode.")

                else:
                    logger.error(f"❌ Error initializing Gemini: {e}")
                    self.available = False

        except ImportError:
            logger.warning(
                "⚠️ google-genai not installed. Install with: pip install google-genai"
            )
        except Exception as e:
            logger.error(f"❌ Error initializing Gemini: {e}")
            self.available = False

    def _is_rate_limit_error(self, error: Exception) -> bool:
        """Check if the error is a rate limit or quota error"""
        error_str = str(error).lower()
        rate_limit_keywords = [
            "rate limit",
            "quota",
            "exceeded",
            "too many requests",
            "429",
            "resource exhausted",
            "quota exceeded",
            "generate_content_free_tier_requests",
            "quota for metric",
            "daily quota",
            "per day",
            "free tier",
        ]
        return any(keyword in error_str for keyword in rate_limit_keywords)

    def generate_full_response(
        self, herbs: List[Dict], hair_type: str, conditions: Optional[List[str]] = None
    ) -> Dict:
        """
        Generate BOTH explanations AND summary in ONE API call.
        This is the FASTEST approach - 1 call instead of 2.

        Returns:
            Dict with 'explanations' (list of herbs) and 'summary' (string)
        """

        # If no herbs, return empty
        if not herbs:
            return {"explanations": [], "summary": ""}

        # If API not available, use fallback
        if not self.available or self.daily_quota_exceeded:
            for herb in herbs:
                herb["ai_explanation"] = self._fallback_explanation(
                    herb.get("herb_name", "Unknown"),
                    hair_type,
                    herb.get("benefits", ""),
                    conditions,
                )
            return {
                "explanations": herbs,
                "summary": self._fallback_summary(hair_type, herbs, conditions),
            }

        # Clean conditions
        clean_conditions = []
        if conditions:
            for c in conditions:
                clean_conditions.append(c.replace("_", " ").title())

        try:
            # Build ONE prompt for EVERYTHING
            herb_names = [h.get("herb_name", "Unknown") for h in herbs]
            herb_details = "\n".join(
                [
                    f"- {h.get('herb_name', 'Unknown')}: {h.get('benefits', '')[:100]}"
                    for h in herbs
                ]
            )

            condition_text = (
                ", ".join(clean_conditions) if clean_conditions else "hair health"
            )

            prompt = f"""You are an Ayurvedic hair care expert. 

    USER HAS: {hair_type} hair with conditions: {condition_text}

    RECOMMENDED HERBS:
    {herb_details}

    TASK 1: For EACH herb above, provide a brief 2-sentence explanation of why it's beneficial.
    Format each as:
    HERB: [name]
    EXPLANATION: [2 sentences]

    TASK 2: After all herbs, provide a warm 3-sentence summary for this user.

    Format your response EXACTLY like this:

    HERB: [herb name]
    EXPLANATION: [2-sentence explanation]

    HERB: [next herb name]
    EXPLANATION: [2-sentence explanation]

    ... (repeat for all herbs)

    SUMMARY: [3-sentence warm summary]"""

            # Make ONE API call for everything
            logger.info(
                f"🚀 Making single combined API call for {len(herbs)} herbs + summary..."
            )
            chat = self.client.chats.create(model=self.model_name)
            response = chat.send_message(prompt)

            if response and response.text:
                # Parse the combined response
                result = self._parse_combined_response(response.text, herbs)

                # Log success
                explained_count = sum(
                    1 for h in result["explanations"] if h.get("ai_explanation")
                )
                logger.info(
                    f"✅ Combined response complete: {explained_count}/{len(herbs)} herbs explained"
                )

                return result

        except Exception as e:
            if self._is_rate_limit_error(e):
                self.daily_quota_exceeded = True
                logger.warning("⚠️ Rate limit hit, using fallback")
            else:
                logger.error(f"❌ Combined API error: {e}")

        # Fallback for everything
        for herb in herbs:
            herb["ai_explanation"] = self._fallback_explanation(
                herb.get("herb_name", "Unknown"),
                hair_type,
                herb.get("benefits", ""),
                conditions,
            )

        return {
            "explanations": herbs,
            "summary": self._fallback_summary(hair_type, herbs, conditions),
        }

    def _parse_combined_response(self, response_text: str, herbs: List[Dict]) -> Dict:
        """
        Parse the combined response into explanations AND summary.
        """
        explanations = {}
        summary = ""
        current_herb = None
        current_explanation = []
        in_summary = False

        lines = response_text.split("\n")

        for line in lines:
            line = line.strip()

            if not line:
                continue

            # Check for SUMMARY marker
            if line.upper().startswith("SUMMARY:"):
                in_summary = True
                # Save any pending herb explanation
                if current_herb and current_explanation:
                    explanations[current_herb] = " ".join(current_explanation).strip()
                current_herb = None
                current_explanation = []
                # Add summary text
                summary = line[8:].strip()
                continue

            # If in summary, append to summary
            if in_summary:
                if summary:
                    summary += " " + line
                else:
                    summary = line
                continue

            # Check for HERB marker
            if line.upper().startswith("HERB:"):
                # Save previous herb's explanation
                if current_herb and current_explanation:
                    explanations[current_herb] = " ".join(current_explanation).strip()

                # Start new herb
                current_herb = line[5:].strip()
                current_explanation = []

            elif line.upper().startswith("EXPLANATION:"):
                # Add to current explanation
                text = line[12:].strip()
                if text:
                    current_explanation.append(text)

            elif current_herb and current_explanation:
                # Continue explanation on next lines
                if not line.upper().startswith("HERB:") and not line.upper().startswith(
                    "SUMMARY:"
                ):
                    current_explanation.append(line)

        # Save the last herb
        if current_herb and current_explanation:
            explanations[current_herb] = " ".join(current_explanation).strip()

        # Add explanations to herbs
        for herb in herbs:
            herb_name = herb.get("herb_name", "Unknown")
            explanation = explanations.get(herb_name)

            # Try case-insensitive if not found
            if not explanation:
                for key, value in explanations.items():
                    if key.lower() == herb_name.lower():
                        explanation = value
                        break

            if not explanation:
                explanation = self._fallback_explanation(
                    herb_name, "your hair", herb.get("benefits", ""), []
                )

            herb["ai_explanation"] = explanation

        return {
            "explanations": herbs,
            "summary": (
                summary if summary else self._fallback_summary("your hair", herbs, [])
            ),
        }

    # ===== SINGLE EXPLANATION (Fallback for individual requests) =====

    def generate_explanation(
        self,
        herb_name: str,
        hair_type: str,
        benefits: str,
        conditions: Optional[List[str]] = None,
    ) -> str:
        """Generate a single herb explanation (for backward compatibility)"""

        # If API not available, use fallback
        if not self.available or self.daily_quota_exceeded:
            return self._fallback_explanation(
                herb_name, hair_type, benefits, conditions
            )

        try:
            clean_conditions = []
            if conditions:
                for c in conditions:
                    clean_conditions.append(c.replace("_", " ").title())

            condition_text = ""
            if clean_conditions:
                condition_text = f" The user also has these conditions: {', '.join(clean_conditions[:3])}."

            prompt = f"""You are an Ayurvedic hair care expert. Explain why {herb_name} is beneficial for {hair_type} hair.

Key benefits: {benefits}.{condition_text}

Write a brief, informative explanation (2-3 sentences) that:
1. Explains how the herb works on {hair_type} hair
2. Mentions its key properties
3. Gives a practical tip for use

Keep it warm, educational, and encouraging. Don't mention that you're an AI."""

            chat = self.client.chats.create(model=self.model_name)
            response = chat.send_message(prompt)

            if response and response.text:
                return response.text.strip()

        except Exception as e:
            if self._is_rate_limit_error(e):
                self.daily_quota_exceeded = True
                logger.warning("⚠️ Rate limit hit, using fallback")
            else:
                logger.error(f"❌ Gemini error: {e}")

        return self._fallback_explanation(herb_name, hair_type, benefits, conditions)

    # ===== SUMMARIES =====

    def generate_summary(
        self,
        hair_type: str,
        recommendations: List[Dict],
        conditions: Optional[List[str]] = None,
    ) -> str:
        """Generate a summary"""

        if not self.available or self.daily_quota_exceeded:
            return self._fallback_summary(hair_type, recommendations, conditions)

        if not recommendations:
            return f"For your {hair_type} hair, we recommend checking our herb database for natural hair care options."

        try:
            clean_conditions = []
            if conditions:
                for c in conditions:
                    clean_conditions.append(c.replace("_", " ").title())

            condition_text = ""
            if clean_conditions:
                condition_text = (
                    f" The user wants to address: {', '.join(clean_conditions[:3])}."
                )

            herb_names = []
            for r in recommendations[:3]:
                if isinstance(r, dict):
                    herb_names.append(r.get("herb_name", "Unknown"))
                else:
                    herb_names.append(str(r))

            prompt = f"""You are an Ayurvedic hair care expert. Create a warm, encouraging summary for someone with {hair_type} hair.

Recommended herbs: {', '.join(herb_names)}.{condition_text}

Write 3-4 sentences that:
1. Welcomes the user
2. Explains how these herbs work together for their hair type
3. Offers one simple way to start using them
4. Ends with an encouraging note

Keep it warm, knowledgeable, and actionable. Don't mention that you're an AI."""

            chat = self.client.chats.create(model=self.model_name)
            response = chat.send_message(prompt)

            if response and response.text:
                return response.text.strip()

        except Exception as e:
            if self._is_rate_limit_error(e):
                self.daily_quota_exceeded = True
                logger.warning("⚠️ Rate limit hit, using fallback")
            else:
                logger.error(f"❌ Gemini summary error: {e}")

        return self._fallback_summary(hair_type, recommendations, conditions)

    # ===== FALLBACKS =====

    def _fallback_explanation(
        self,
        herb_name: str,
        hair_type: str,
        benefits: str,
        conditions: Optional[List[str]] = None,
    ) -> str:
        """More informative fallback explanation"""

        clean_conditions = []
        if conditions:
            for c in conditions:
                clean_conditions.append(c.replace("_", " ").title())

        if clean_conditions:
            condition_text = f", helping to address {', '.join(clean_conditions[:2])}"
        else:
            condition_text = ""

        benefit_list = benefits.split(",")[:3]
        benefit_text = ", ".join(benefit_list).lower()

        return f"{herb_name} is a traditional Ayurvedic herb for {hair_type} hair{condition_text}. It contains compounds that {benefit_text}. Apply regularly and consistently for best results."

    def _fallback_summary(
        self,
        hair_type: str,
        recommendations: List[Dict],
        conditions: Optional[List[str]] = None,
    ) -> str:
        """More informative fallback summary"""

        if not recommendations:
            return f"For your {hair_type} hair, we recommend checking our herb database for natural hair care options."

        herb_names = []
        for r in recommendations[:3]:
            if isinstance(r, dict):
                herb_names.append(r.get("herb_name", "Unknown"))
            else:
                herb_names.append(str(r))

        herb_list = ", ".join(herb_names)

        clean_conditions = []
        if conditions:
            for c in conditions:
                clean_conditions.append(c.replace("_", " ").title())

        condition_text = ""
        if clean_conditions:
            condition_text = f" to address {', '.join(clean_conditions[:3])}"

        return f"For your {hair_type} hair{condition_text}, we recommend {herb_list}. These Ayurvedic herbs work together to support healthy, vibrant hair. Start with one herb and observe how your hair responds."

    def reset_quota_status(self):
        """Reset the quota status (call this when quota resets)"""
        self.daily_quota_exceeded = False
        self.rate_limited = False
        self.available = True
        logger.info("🔄 Quota status reset - Gemini re-enabled")


# Quick test
if __name__ == "__main__":
    print("\n" + "=" * 60)
    print("🧪 Testing Gemini with Batch Processing")
    print("=" * 60)

    gemini = GeminiSimple()

    print(f"\n📡 Status: {'✅ Available' if gemini.available else '⚠️ Fallback mode'}")
    print(f"🤖 Model: {gemini.model_name if gemini.available else 'N/A'}")

    # Test batch processing
    test_herbs = [
        {
            "herb_name": "Bhringraj",
            "benefits": "Promotes hair growth, prevents greying",
        },
        {"herb_name": "Amla", "benefits": "Rich in Vitamin C, strengthens follicles"},
        {"herb_name": "Neem", "benefits": "Antibacterial, treats scalp infections"},
    ]

    print("\n🔍 Testing batch explanations...")
    result = gemini.generate_batch_explanations(
        test_herbs, "Coily", ["Hair Growth", "Hair Fall"]
    )

    for herb in result:
        print(f"\n📝 {herb['herb_name']}:")
        print(f"   {herb.get('ai_explanation', 'No explanation')}")
