from typing import Dict


class ClassifierService:
    def __init__(self) -> None:
        self.available = False
        self.HAIR_TYPES = ["Dry", "Oily", "Normal", "Curly", "Straight", "Wavy"]
        self._load_classifier()

    def _load_classifier(self):
        """Load the hair classifier model"""

        try:
            from model.hair_classifier import HairTypeClassifier

            self.model = HairTypeClassifier()

            if self.model.model is not None:
                self.available = True
                print(f"✅ Hair classifier loaded with types: {self.HAIR_TYPES}")
            else:
                print("⚠️ Hair classifier model not available")
                self.model = None
        except Exception as e:
            print(f"⚠️ Error loading classifier: {e}")
            self.model = None

    def predict(self, image_data: bytes) -> Dict:
        """Predict hair type from image data"""
        if not self.available or self.model is None:
            return {"error": "Classifier not available"}

        try:
            return self.model.predict(image_data)
        except Exception as e:
            return {"error": str(e)}
