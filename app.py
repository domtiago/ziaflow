import json
import uuid
import streamlit as st
from supabase import create_client, Client
from openai import OpenAI

# ---------- CONFIG ----------
st.set_page_config(page_title="ZiaFlow", page_icon="✨", layout="wide")

# Read secrets (you'll set these in Streamlit later)
SUPABASE_URL = st.secrets.get("SUPABASE_URL", "")
SUPABASE_KEY = st.secrets.get("SUPABASE_KEY", "")
OPENAI_API_KEY = st.secrets.get("OPENAI_API_KEY", "")

# Temporary single-user ID for dev (we'll replace with real auth later)
USER_ID = uuid.UUID("00000000-0000-0000-0000-000000000001")

# ---------- INIT CLIENTS ----------
@st.cache_resource
def get_supabase_client() -> Client:
    if not SUPABASE_URL or not SUPABASE_KEY:
        st.error("Supabase URL / KEY not set in Streamlit secrets.")
        st.stop()
    return create_client(SUPABASE_URL, SUPABASE_KEY)

@st.cache_resource
def get_openai_client() -> OpenAI:
    if not OPENAI_API_KEY:
        st.error("OPENAI_API_KEY not set in Streamlit secrets.")
        st.stop()
    return OpenAI(api_key=OPENAI_API_KEY)

supabase = get_supabase_client()
oa_client = get_openai_client()

# ---------- AI HELPER ----------
def analyze_note(text: str) -> dict:
    """
    Ask OpenAI to categorize the note and extract tags.
    Returns a dict like:
      {
        "category": "recipe",
        "tags": ["octopus","seafood","favorite"],
        "linked_list": "food_recipes",
        "has_reminder": false
      }
    """
    system_prompt = """
You are ZiaFlow, a life organization assistant.
Given a short note from the user, classify it into a JSON object with:
- category: one of ["recipe","golf","bike","home","kids","health","work","travel","misc"]
- tags: list of 1-6 short keyword strings
- linked_list: optional list name if it belongs to a recurring list
  e.g. "golf_drills","cocktail_recipes","food_recipes","bike_settings","home_maintenance","kids_notes"
- has_reminder: true if the user is clearly asking to be reminded at a specific time; otherwise false.

Respond with ONLY valid JSON, nothing else.
"""
    user_prompt = f"Note: {text}"

    try:
        resp = oa_client.responses.create(
            model="gpt-5.1-mini",
            input=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
        )
        raw = resp.output[0].content[0].text
        data = json.loads(raw)
    except Exception as e:
        # Fallback: put everything as misc
        st.warning(f"AI parsing issue, saving as 'misc'. Details: {e}")
        data = {
            "category": "misc",
            "tags": [],
            "linked_list": None,
            "has_reminder": False,
        }
    return data

# ---------- DB HELPERS ----------
def insert_note(raw_text: str, analysis: dict):
    data = {
        "user_id": str(USER_ID),
        "raw_text": raw_text,
        "ai_category": analysis.get("category"),
        "ai_tags": analysis.get("tags"),
        "linked_list": analysis.get("linked_list"),
        "has_reminder": analysis.get("has_reminder", False),
    }
    res = supabase.table("notes").insert(data).execute()
    if res.error:
        st.error(f"Error saving note: {res.error}")
    else:
        st.success("Note saved to ZiaFlow inbox ✅")

def fetch_notes(limit: int = 50):
    res = (
        supabase.table("notes")
        .select("*")
        .eq("user_id", str(USER_ID))
        .order("created_at", desc=True)
        .limit(limit)
        .execute()
    )
    if res.error:
        st.error(f"Error loading notes: {res.error}")
        return []
    return res.data

# ---------- UI ----------
st.title("✨ ZiaFlow — Inbox")
st.write(
    "Capture anything: recipes, bike settings, golf drills, kids notes, home tasks. "
    "ZiaFlow will tag and organize them automatically."
)

with st.form("new_note"):
    note_text = st.text_area("New note", height=120, placeholder="E.g. Octopus recipe with smoked paprika I loved last night...")
    submitted = st.form_submit_button("Save to ZiaFlow")

    if submitted:
        if not note_text.strip():
            st.warning("Please type something before saving.")
        else:
            analysis = analyze_note(note_text.strip())
            insert_note(note_text.strip(), analysis)

st.markdown("---")
st.subheader("Recent notes")

notes = fetch_notes(limit=50)
if not notes:
    st.info("No notes yet. Add your first note above!")
else:
    for n in notes:
        n.pop("user_id", None)
    st.dataframe(notes, use_container_width=True)
