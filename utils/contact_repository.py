from typing import Dict, List, Optional


def find_contact_id(
    supabase,
    owner_id: str,
    full_name: str,
    company: Optional[str] = None,
    email: Optional[str] = None,
    phone: Optional[str] = None,
) -> Optional[str]:
    """
    Matching order:
    1) owner_id + email (best)
    2) owner_id + full_name + company
    3) owner_id + full_name
    4) owner_id + phone (fallback)
    """
    if email:
        res = (
            supabase.table("contacts")
            .select("id")
            .eq("owner_id", owner_id)
            .eq("email", email)
            .limit(1)
            .execute()
        )
        if res.data:
            return res.data[0]["id"]

    if full_name and company:
        res = (
            supabase.table("contacts")
            .select("id")
            .eq("owner_id", owner_id)
            .eq("full_name", full_name)
            .eq("company", company)
            .limit(1)
            .execute()
        )
        if res.data:
            return res.data[0]["id"]

    if full_name:
        res = (
            supabase.table("contacts")
            .select("id")
            .eq("owner_id", owner_id)
            .eq("full_name", full_name)
            .limit(1)
            .execute()
        )
        if res.data:
            return res.data[0]["id"]

    if phone:
        res = (
            supabase.table("contacts")
            .select("id")
            .eq("owner_id", owner_id)
            .eq("phone", phone)
            .limit(1)
            .execute()
        )
        if res.data:
            return res.data[0]["id"]

    return None


def upsert_contact(supabase, owner_id: str, contact: Dict) -> str:
    """
    - If match found: update ONLY fields that are currently NULL in DB.
    - If no match: insert new contact.
    Returns contact_id.
    """
    full_name = contact.get("full_name", "").strip()
    company = contact.get("company")
    email = contact.get("email")
    phone = contact.get("phone")

    contact_id = find_contact_id(
        supabase=supabase,
        owner_id=owner_id,
        full_name=full_name,
        company=company,
        email=email,
        phone=phone,
    )

    if contact_id:
        existing = (
            supabase.table("contacts")
            .select("*")
            .eq("id", contact_id)
            .limit(1)
            .execute()
        )
        existing_row = existing.data[0] if existing.data else {}

        # Update only missing fields (NULL in DB) and present in extracted data
        update_fields = {}
        for k, v in contact.items():
            if v is None:
                continue
            if k in existing_row and existing_row.get(k) is None:
                update_fields[k] = v

        if update_fields:
            supabase.table("contacts").update(update_fields).eq("id", contact_id).execute()

        return contact_id

    # Insert new
    payload = dict(contact)
    payload["owner_id"] = owner_id

    res = supabase.table("contacts").insert(payload).execute()
    return res.data[0]["id"]


def insert_contact_notes(supabase, owner_id: str, contact_id: str, notes: List[Dict]) -> int:
    """
    Append-only notes. Returns number of notes inserted.
    """
    if not notes:
        return 0

    rows = []
    for n in notes:
        note_text = (n.get("note") or "").strip()
        if not note_text:
            continue
        rows.append(
            {
                "owner_id": owner_id,
                "contact_id": contact_id,
                "note": note_text,
                "note_type": n.get("note_type"),
                "event_name": n.get("event_name"),
                "event_location": n.get("event_location"),
                "event_date": n.get("event_date"),
                "tags": n.get("tags"),
            }
        )

    if not rows:
        return 0

    supabase.table("contact_notes").insert(rows).execute()
    return len(rows)
