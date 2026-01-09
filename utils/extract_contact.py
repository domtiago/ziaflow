import re
from typing import Dict, List

PHONE_REGEX = re.compile(r"(\(?\d{3}\)?[-.\s]\d{3}[-.\s]\d{4}(?:\s*x\d+)?)")

def extract_contact(text: str) -> Dict:
    lines = [l.strip() for l in text.splitlines() if l.strip()]
    contact = {}
    notes: List[Dict] = []

    # Name
    for line in lines:
        if len(line.split()) == 2 and line.istitle():
            contact["full_name"] = line
            contact["first_name"], contact["last_name"] = line.split()
            break

    # Company
    for line in lines:
        if any(k in line for k in ["Corp", "Inc", "LLC", "Ltd", "-"]):
            contact["company"] = line
            break

    # Phone
    phones = PHONE_REGEX.findall(text)
    if phones:
        contact["phone"] = phones[0]

    # Address
    for i, line in enumerate(lines):
        if re.match(r"\d+ .+", line):
            contact["address_line1"] = line
            if i + 1 < len(lines):
                city_line = lines[i + 1]
                m = re.match(r"(.+),\s*([A-Z]{2})\s*(\d{5})", city_line)
                if m:
                    contact["city"] = m.group(1)
                    contact["state"] = m.group(2)
                    contact["postal_code"] = m.group(3)
                    contact["country"] = "USA"
            break

    # Relationship notes (everything else)
    notes.append({
        "note_type": "context",
        "note": text
    })

    return {
        "contact": contact,
        "notes": notes
    }
