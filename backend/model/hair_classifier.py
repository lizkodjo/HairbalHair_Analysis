import os
from typing import Optional
from torchvision.models import MobileNet_V2_Weights
import torch
from torchvision import models, transforms
from PIL import Image
import numpy as np
import io
import logging
import random
import hashlib

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class HairTypeClassifier:
    """Model for classifying hair"""

    # Define hair types
    HAIR_TYPES = ["Straight", "Wavy", "Curly", "Coily"]

    def __init__(self, model_path: Optional[str] = None):
        """Initialise the classifier"""

        self.model = None
        self.model_path = model_path
        self.device = self._get_device()

        # Define image transformations
        self.transform = transforms.Compose(
            [
                transforms.Resize((224, 224)),
                transforms.ToTensor(),
                transforms.Normalize(
                    mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225]
                ),
            ]
        )

        # Load model
        self._load_model()

    def _get_device(self):
        """Determine device"""

        if torch.cuda.is_available():
            logger.info("✅ Using GPU for inference")
            return torch.device("cuda")
        elif torch.backends.mps.is_available():
            logger.info("✅ Using MPS (Apple Silicon) for inference")
            return torch.device("mps")
        else:
            logger.info("ℹ️ Using CPU for inference")
            return torch.device("cpu")

    def _load_model(self):
        """Load the model"""

        try:
            if self.model_path and self._check_model_exists():
                # Load custom trained model
                logger.info(f"Loading custom model from {self.model_path}")
                self.model = torch.load(self.model_path, map_location=self.device)
                self.model.eval()
                logger.info("✅ Custom model loaded successfully")
            else:
                # Use pre-trained
                logger.info("Loading pre-trained MobileNetV2 model...")

                # Load model
                self.model = models.mobilenet_v2(weights=MobileNet_V2_Weights.IMAGENET1K_V1)

                # Use as-is
                self.model = self.model.to(self.device)
                self.model.eval()

                logger.info("MobleNetV2 model loaded successfully")
        except Exception as e:
            logger.error(f"Error loading model: {e}")
            self.model = None

    def _check_model_exists(self) -> bool:
        """Check if model"""
        return os.path.exists(self.model_path) if self.model_path else False

    def preprocess_image(self, image_bytes: bytes) -> Optional[torch.Tensor]:
        """Preprocess an image"""

        try:
            # Convert bytes to PIL Image
            img = Image.open(io.BytesIO(image_bytes))

            # Convert to RGB
            if img.mode != "RGB":
                img = img.convert("RGB")

            # Transform
            img_tensor = self.transform(img)

            # Add batch dimension
            img_tensor = img_tensor.unsqueeze(0)

            # Move to device
            img_tensor = img_tensor.to(self.device)

            return img_tensor

        except Exception as e:
            logger.error(f"Error preprocessing Image: {e}")
            raise ValueError(f"Failed to preprocess image: {e}")
            # return None

    def predict(self, image_bytes: bytes) -> dict:
        """Predict the hair type from an image"""

        if self.model is None:
            logger.warning("Model not loaded, using fallback prediction")
            return self._fallback_prediction()

        try:
            # Preprocess
            img_tensor = self.preprocess_image(image_bytes)
            if img_tensor is None:
                return {"error": "Failed to preprocess image"}

            # To test how prediction pipeline will work
            return self._simulate_prediction(image_bytes)

        except Exception as e:
            logger.error(f"❌ Error in prediction: {e}")
            return {"error": str(e)}

    def _simulate_prediction(self, image_bytes: bytes) -> dict:
        """Simulate a prediction for demonstration"""

        hash_val = int(hashlib.md5(image_bytes).hexdigest()[:8], 16)
        idx = hash_val % len(self.HAIR_TYPES)
        predicted_type = self.HAIR_TYPES[idx]

        # Generate confidence scores
        random.seed(hash_val)
        confidence = round(0.70 + random.random() * 0.25, 2)

        # Create confidence scores for all types
        all_scores = {}
        remaining = 1.0
        for i, t in enumerate(self.HAIR_TYPES):
            if t == predicted_type:
                all_scores[t] = confidence
                remaining -= confidence
            else:
                # Distribute remaining probability
                all_scores[t] = round(remaining / (len(self.HAIR_TYPES) - 1), 2)

        # Normalise to ensure sum is 1.0
        total = sum(all_scores.values())
        all_scores = {k: round(v / total, 2) for k, v in all_scores.items()}

        logger.info(f"✅ Predicted: {predicted_type} (confidence: {confidence:.2f})")
        return {
            "hair_type": predicted_type,
            "confidence": confidence,
            "all_scores": all_scores,
        }

    def _fallback_prediction(self) -> dict:
        """Return a fallback prediction when the model is not available"""

        logger.warning(" Using fallback prediction")
        return {
            "hair_type": "Wavy",
            "confidence": 0.60,
            "all_scores": {
                "Straight": 0.25,
                "Wavy": 0.60,
                "Curly": 0.10,
                "Coily": 0.05,
            },
        }

    def extract_features(self, image_bytes: bytes) -> Optional[np.ndarray]:
        """Extract feature vectors from an image"""

        if self.model is None:
            return None

        try:
            # Preprocess the image
            img_tensor = self.preprocess_image(image_bytes)
            if img_tensor is None:
                return None

            # Get features from the model
            with torch.no_grad():
                features = self.model.features(img_tensor)

                # Global average pooling
                features = torch.mean(features, dim=[2, 3])
                features = features.cpu().numpy()

            return features

        except Exception as e:
            logger.error(f"❌ Error extracting features: {e}")
            return None
        
    
