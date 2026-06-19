import logging
from presidio_analyzer import AnalyzerEngine
from presidio_anonymizer import AnonymizerEngine

# Configure basic logging for the console
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("PIIFirewall")

class PIIFirewall:
    def __init__(self):
        # Initialize the engines. This loads the underlying NLP models (like spaCy)
        self.analyzer = AnalyzerEngine()
        self.anonymizer = AnonymizerEngine()
        
        # The specific entities we want to detect based on requirements
        self.entities_to_detect = ["PERSON", "EMAIL_ADDRESS", "PHONE_NUMBER", "CREDIT_CARD"]

    def scrub_text(self, text: str) -> tuple[str, bool]:
        """
        Scans text for PII and replaces it with placeholders.
        Returns a tuple: (anonymized_text, was_pii_detected)
        """
        if not text:
            return text, False
            
        # 1. Analyze the text to find PII
        results = self.analyzer.analyze(
            text=text,
            entities=self.entities_to_detect,
            language='en'
        )
        
        # 2. If no PII is found, return the original text
        if not results:
            return text, False
            
        # 3. Log that PII was found
        detected_types = set([result.entity_type for result in results])
        logger.info(f"🚨 PII Detected and Sanitized! Entities found: {', '.join(detected_types)}")
        
        # 4. Anonymize the text (replaces with <ENTITY_TYPE> by default)
        anonymized_result = self.anonymizer.anonymize(
            text=text,
            analyzer_results=results
        )
        
        return anonymized_result.text, True
