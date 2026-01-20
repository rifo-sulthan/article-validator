# generic_zero_shot_classifier.py
from transformers import pipeline
import logging

logger = logging.getLogger(__name__)

class GenericZeroShotClassifier:
    def __init__(self, model_path, device=-1):
        """
        Initialize the zero-shot classifier with a specific model.
        
        Args:
            model_path (str): Path or ID of the model to use.
            device (int): Device to run on (-1 for CPU, 0 for GPU).
        """
        logger.info(f"Loading zero-shot model from: {model_path}")
        try:
            self.classifier = pipeline(
                "zero-shot-classification",
                model=model_path,
                device=device
            )
            logger.info("Model loaded successfully.")
        except Exception as e:
            logger.error(f"Failed to load model: {e}")
            raise

    def classify_article(self, text, candidate_labels, threshold=0.75, multi_label=False):
        """
        Classify text using the loaded zero-shot model.

        Args:
            text (str): The text to classify.
            candidate_labels (list): List of string labels.
            threshold (float): Score threshold for positive identification.
            multi_label (bool): Whether multiple labels can apply.

        Returns:
            dict: {
                "top_label": str,
                "top_score": float,
                "all_scores": dict,
                "raw_result": dict
            }
        """
        # For very long articles, truncate to first ~1500 words to keep inference fast
        # Most "topic" content is in the beginning anyway
        words = text.split()
        if len(words) > 1500:
            text = " ".join(words[:1500])

        result = self.classifier(
            text,
            candidate_labels=candidate_labels,
            hypothesis_template="This text is {}.",
            multi_label=multi_label
        )

        top_label = result["labels"][0]
        top_score = result["scores"][0]
        
        all_scores = {label: score for label, score in zip(result["labels"], result["scores"])}

        return {
            "top_label": top_label,
            "top_score": top_score,
            "all_scores": all_scores,
            "raw_result": result
        }
