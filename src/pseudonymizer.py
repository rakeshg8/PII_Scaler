from faker import Faker
import random
import datetime
import re

class EntityMapper:
    def __init__(self):
        self._map = {}  # (entity_type, normalized_text) -> fake value
        self._faker = Faker("en_IN")
        self._faker_def = Faker()  # default locale for SSN, Email, etc.

    def get_fake(self, entity_type: str, original_text: str) -> str:
        key = (entity_type, original_text.strip().lower())
        if key not in self._map:
            self._map[key] = self._generate(entity_type, original_text)
        return self._map[key]

    def _generate(self, entity_type: str, original_text: str) -> str:
        original_text = original_text.strip()
        
        if entity_type == "EMAIL":
            first_name = self._faker.first_name().lower()
            last_name = self._faker.last_name().lower()
            domain = self._faker_def.free_email_domain()
            return f"{first_name}.{last_name}@{domain}"
            
        elif entity_type == "PHONE":
            if "+91" in original_text:
                has_space = " " in original_text
                num = "".join(random.choices("789", k=1)) + "".join(random.choices("0123456789", k=9))
                if has_space:
                    return f"+91 {num[:5]} {num[5:]}"
                else:
                    return f"+91{num}"
            else:
                std_code = "020"
                if "-" in original_text:
                    parts = original_text.split("-")
                    if parts[0].isdigit():
                        std_code = parts[0]
                num = "".join(random.choices("0123456789", k=8))
                return f"{std_code}-{num}"
                
        elif entity_type == "SSN":
            return self._faker_def.ssn()
            
        elif entity_type == "CREDIT_CARD":
            return self._faker_def.credit_card_number()
            
        elif entity_type == "IP_ADDRESS":
            if ":" in original_text:
                return self._faker_def.ipv6()
            return self._faker_def.ipv4()
            
        elif entity_type == "DATE_OF_BIRTH":
            year = random.randint(1945, 2005)
            month = random.randint(1, 12)
            day = random.randint(1, 28)
            dt = datetime.date(year, month, day)
            
            orig_lower = original_text.lower()
            months_list = ["jan", "feb", "mar", "apr", "may", "jun", "jul", "aug", "sep", "oct", "nov", "dec"]
            has_month_word = any(m in orig_lower for m in months_list)
            
            if has_month_word:
                if "," in original_text:
                    return dt.strftime("%B %d, %Y")
                else:
                    return dt.strftime("%d %B %Y")
            elif "-" in original_text:
                return dt.strftime("%d-%m-%Y")
            elif "/" in original_text:
                return dt.strftime("%d/%m/%Y")
            else:
                return dt.strftime("%d %b %Y")
                
        elif entity_type == "PERSON":
            fake_name = self._faker.name()
            if "," in original_text:
                parts = fake_name.split()
                if len(parts) > 1:
                    fake_name = f"{parts[-1]}, {' '.join(parts[:-1])}"
            return fake_name
            
        elif entity_type == "COMPANY":
            comp = self._faker.company()
            if "private limited" in original_text.lower() or "pvt" in original_text.lower():
                comp = re.sub(r"\s+(?:Limited|Ltd\.?|LLP|Inc\.?|Corporation|Corp\.?)$", "", comp)
                comp += " Private Limited"
            elif "limited" in original_text.lower() or "ltd" in original_text.lower():
                comp = re.sub(r"\s+(?:Limited|Ltd\.?|LLP|Inc\.?|Corporation|Corp\.?)$", "", comp)
                comp += " Limited"
            elif "llp" in original_text.lower():
                comp = re.sub(r"\s+(?:Limited|Ltd\.?|LLP|Inc\.?|Corporation|Corp\.?)$", "", comp)
                comp += " LLP"
            return comp
            
        elif entity_type == "ADDRESS":
            addr = self._faker.address().replace("\n", ", ")
            if not re.search(r"\b\d{6}\b", addr):
                pin = "".join(random.choices("0123456789", k=6))
                addr += f" - {pin}"
            return addr
            
        else:
            return f"FAKE_{entity_type}_{random.randint(1000, 9999)}"
