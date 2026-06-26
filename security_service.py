import logging
from presidio_analyzer import AnalyzerEngine
from faker import Faker

# Configure basic logging for the console
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("PIIFirewall")

class StatefulPIIFirewall:
    def __init__(self):
        # Initialize the engine. This loads the underlying NLP models (like spaCy)
        self.analyzer = AnalyzerEngine()
        self.faker = Faker()
        
        # The specific entities we want to detect based on requirements
        self.entities_to_detect = ["PERSON", "EMAIL_ADDRESS", "PHONE_NUMBER", "CREDIT_CARD"]

    def scrub_text(self, text: str, session_map: dict = None) -> tuple[str, bool, dict]:
        """
        Scans text for PII and replaces it with stateful placeholders.
        Returns a tuple: (anonymized_text, was_pii_detected, session_map)
        """
        if session_map is None:
            session_map = {}
            
        if not text:
            return text, False, session_map
            
        # 1. Analyze the text to find PII
        results = self.analyzer.analyze(
            text=text,
            entities=self.entities_to_detect,
            language='en'
        )
        
        # 2. If no PII is found, return the original text
        if not results:
            return text, False, session_map
            
        # 3. Log that PII was found
        detected_types = set([result.entity_type for result in results])
        logger.info(f"🚨 PII Detected and Sanitized! Entities found: {', '.join(detected_types)}")
        
        # 4. Anonymize the text manually to maintain state
        # We process from the end of the string to the start to avoid messing up indices
        results.sort(key=lambda x: x.start, reverse=True)
        
        # reverse map to check if original text was already masked
        reverse_map = {v: k for k, v in session_map.items()}
        
        anonymized_text = text
        for result in results:
            original_value = text[result.start:result.end]
            ent_type = result.entity_type
            
            if original_value in reverse_map:
                token = reverse_map[original_value]
            else:
                # Generate a realistic fake identity based on entity type
                if ent_type == "PERSON":
                    token = self.faker.name()
                elif ent_type == "EMAIL_ADDRESS":
                    token = self.faker.email()
                elif ent_type == "PHONE_NUMBER":
                    token = self.faker.phone_number()
                elif ent_type == "CREDIT_CARD":
                    token = self.faker.credit_card_number()
                else:
                    # Fallback for unexpected types
                    token = f"[{ent_type}]"
                
                # Make sure our random fake token doesn't already exist in session_map (collision check)
                while token in session_map:
                    if ent_type == "PERSON": token = self.faker.name()
                    elif ent_type == "EMAIL_ADDRESS": token = self.faker.email()
                    elif ent_type == "PHONE_NUMBER": token = self.faker.phone_number()
                    elif ent_type == "CREDIT_CARD": token = self.faker.credit_card_number()
                    else: token = f"[{ent_type}_{len(session_map)}]"
                    
                session_map[token] = original_value
                reverse_map[original_value] = token
                
            anonymized_text = anonymized_text[:result.start] + token + anonymized_text[result.end:]
            
        return anonymized_text, True, session_map

    def unmask_response(self, llm_response: str, mapping: dict) -> str:
        """
        Replaces tokens back with original names using the mapping dictionary.
        """
        if not llm_response or not mapping:
            return llm_response
            
        unmasked = llm_response
        # Sort tokens by length descending to prevent partial replacements
        for token in sorted(mapping.keys(), key=len, reverse=True):
            original_value = mapping[token]
            unmasked = unmasked.replace(token, original_value)
            
        return unmasked
