import logging
import re
from sqlalchemy.orm import Session
from presidio_analyzer import AnalyzerEngine, Pattern, PatternRecognizer
from faker import Faker
from models import PIIMapping

# Configure basic logging for the console
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("PIIFirewall")

class StatefulPIIFirewall:
    def __init__(self):
        # Initialize the engine. This loads the underlying NLP models (like spaCy)
        self.analyzer = AnalyzerEngine()
        self.faker = Faker()
        
        # Add custom recognizer for short phone numbers (e.g., 555-0100)
        phone_pattern = Pattern(name="short_phone", regex=r"\b\d{3}-\d{4}\b", score=0.85)
        short_phone_recognizer = PatternRecognizer(supported_entity="PHONE_NUMBER", patterns=[phone_pattern])
        self.analyzer.registry.add_recognizer(short_phone_recognizer)
        
        # Add custom recognizer for Indian phone numbers (e.g., 9876543210)
        # Using a low base score of 0.4, but if context words are present, Presidio boosts the score over the 0.5 threshold
        indian_phone_pattern = Pattern(name="indian_phone", regex=r"\b[6-9]\d{9}\b", score=0.4)
        indian_phone_recognizer = PatternRecognizer(
            supported_entity="PHONE_NUMBER", 
            patterns=[indian_phone_pattern],
            context=["phone", "ph", "mobile", "mob", "call", "number", "contact", "+91", "91"]
        )
        self.analyzer.registry.add_recognizer(indian_phone_recognizer)
        
        # The specific entities we want to detect based on requirements
        self.entities_to_detect = ["PERSON", "EMAIL_ADDRESS", "PHONE_NUMBER", "CREDIT_CARD"]

    def mask_pii(self, text: str, chat_id: str, db: Session) -> tuple[str, bool]:
        """
        Scans text for PII and replaces it with stateful placeholders per chat.
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
        
        # 2. Check if any PII was actually detected by the NLP engine
        if not results:
            return text, False
            
        # 3. Log that PII was found (if any)
        detected_types = set([result.entity_type for result in results])
        logger.info(f"🚨 PII Detected and Sanitized! Entities found: {', '.join(detected_types)}")
        
        # 4. Collect unique entities from NLP
        entities = {}
        for result in results:
            val = text[result.start:result.end]
            if val not in entities:
                entities[val] = result.entity_type
                
        # 5. Fetch existing mappings for this chat
        existing_mappings = db.query(PIIMapping).filter(PIIMapping.chat_id == chat_id).all()
        # Build dictionary with lowercase real_value as key for case-insensitive lookup
        db_real_to_fake = {m.real_value.lower(): m.fake_value for m in existing_mappings}
        # Also keep track of all used fake_values to prevent collisions
        used_fake_values = {m.fake_value for m in existing_mappings}
        
        # Extract the faked person name if available for consistent email generation
        faked_person_name = next((m.fake_value for m in existing_mappings if m.entity_type == "PERSON"), None)
        
        # 6. Generate fake values for NEW entities and commit them
        new_mappings_added = False
        # Sort entities so PERSON is processed before EMAIL_ADDRESS
        sorted_entities = sorted(entities.items(), key=lambda x: 0 if x[1] == "PERSON" else 1)
        
        for original_value, ent_type in sorted_entities:
            lower_val = original_value.lower()
            if lower_val not in db_real_to_fake:
                # Generate a realistic fake value using Faker
                token = ""
                if ent_type == "PERSON":
                    token = self.faker.name()
                    if not faked_person_name:
                        faked_person_name = token
                elif ent_type == "EMAIL_ADDRESS":
                    if faked_person_name:
                        clean_name = re.sub(r'[^a-z0-9.]', '', faked_person_name.replace(" ", ".").lower())
                        token = f"{clean_name}@{self.faker.free_email_domain()}"
                    else:
                        token = self.faker.email()
                elif ent_type == "PHONE_NUMBER":
                    token = self.faker.phone_number()
                elif ent_type == "CREDIT_CARD":
                    token = self.faker.credit_card_number()
                else:
                    token = f"[{ent_type}_{self.faker.uuid4()[:8]}]"
                    
                # Ensure no collisions
                while token in used_fake_values:
                    if ent_type == "PERSON":
                        token = self.faker.name()
                    elif ent_type == "EMAIL_ADDRESS":
                        token = self.faker.email()
                    elif ent_type == "PHONE_NUMBER":
                        token = self.faker.phone_number()
                    elif ent_type == "CREDIT_CARD":
                        token = self.faker.credit_card_number()
                    else:
                        token = f"[{ent_type}_{self.faker.uuid4()[:8]}]"
                    
                # Store in db and local tracking
                new_mapping = PIIMapping(chat_id=chat_id, real_value=original_value, fake_value=token, entity_type=ent_type)
                db.add(new_mapping)
                new_mappings_added = True
                
                db_real_to_fake[lower_val] = token
                used_fake_values.add(token)

        if new_mappings_added:
            db.commit()
            
        # 7. Apply ALL mappings (both historical and new) to the text globally
        anonymized_text = text
        
        # Sort by length descending to prevent partial word overlaps (e.g. replacing 'John' before 'John Doe')
        sorted_keys = sorted(db_real_to_fake.keys(), key=len, reverse=True)
        for lower_key in sorted_keys:
            token = db_real_to_fake[lower_key]
            escaped_val = re.escape(lower_key)
            anonymized_text = re.sub(rf"\b{escaped_val}\b", token, anonymized_text, flags=re.IGNORECASE)
            
        # Check if we actually applied any replacements by comparing lengths or just assume True if db mappings exist
        was_pii_detected = True
            
        return anonymized_text, was_pii_detected

    def unmask_response(self, llm_response: str, chat_id: str, db: Session) -> str:
        """
        Replaces fake tokens back with original names using the database mapping.
        """
        if not llm_response:
            return llm_response
            
        # Fetch existing mappings
        existing_mappings = db.query(PIIMapping).filter(PIIMapping.chat_id == chat_id).all()
        if not existing_mappings:
            return llm_response
            
        unmasked = llm_response
        # Sort tokens by length descending to prevent partial replacements
        sorted_mappings = sorted(existing_mappings, key=lambda m: len(m.fake_value), reverse=True)
        for mapping in sorted_mappings:
            unmasked = unmasked.replace(mapping.fake_value, mapping.real_value)
            
        return unmasked
