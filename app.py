import os
from datetime import datetime, time
import streamlit as st
from supabase import create_client

# -----------------------------
# Config
# -----------------------------
st.set_page_config(page_title="ZiaFlow", page_icon="✨", layout="wide")

SUPABASE_URL = st.secrets.get("SUPABASE_URL") or os.getenv("SUPABASE_URL")
SUPABASE_KEY = st.secrets.get("SUPABASE_KEY") or os.getenv("SUPABASE_KEY")
st.write("DEBUG SUPABASE_URL:", repr(SUPABASE_URL))







import socket, httpx

try:
    host = SUPABASE_URL.replace("https://", "").replace("http://", "").split("/")[0]
    st.write("DEBUG host:", host)
    st.write("DEBUG DNS:", socket.gethostbyname(host))
except Exception as e:
    st.error(f"DEBUG DNS failed: {e}")

try:
    r = httpx.get(SUPABASE_URL, timeout=10.0)
    st.write("DEBUG HTTP status:", r.status_code)
except Exception as e:
    st.error(f"DEBUG HTTP failed: {e}")








if not SUPABASE_URL or not SUPABASE_KEY:
    st.error("Missing Supabase secrets. Set SUPABASE_URL and SUPABASE_KEY in Streamlit secrets.")
    st.stop()

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

# DEV MODE: single-user id (matches your RLS policy)
DEV_USER_ID = "00000000-0000-0000-0000-000000000001"

# -----------------------------
# Helpers (safe response handling)
# -----------------------------
def _resp_data(resp):
    # supabase-py responses vary slightly across versions
    return getattr(resp, "data", None)

def _show_err(prefix, err):
    st.warning(f"{prefix}: {err}")

# -----------------------------
# NOTES (keep your existing implementation if you already have it)
# -----------------------------
def create_note(raw_text: str, ai_category: str = "misc", ai_tags: list[str] | None = None):
    ai_tags = ai_tags or []
    payload = {
        "user_id": DEV_USER_ID,
        "raw_text": raw_text,
        "ai_category": ai_category,
        "ai_tags": ai_tags,
    }
    try:
        resp = supabase.table("notes").insert(payload).execute()
        data = _resp_data(resp)
        return data[0] if data else None, None
    except Exception as e:
        return None, str(e)

def fetch_notes(limit: int = 50):
    try:
        resp = (
            supabase.table("notes")
            .select("*")
            .eq("user_id", DEV_USER_ID)
            .order("created_at", desc=True)
            .limit(limit)
            .execute()
        )
        return _resp_data(resp) or [], None
    except Exception as e:
        return [], str(e)

# -----------------------------
# TASKS (NEW)
# -----------------------------
def create_task(title: str, details: str | None = None, due_at: datetime | None = None, source_note_id: str | None = None):
    payload = {
        "user_id": DEV_USER_ID,
        "title": title.strip(),
        "details": details.strip() if details else None,
        "due_at": due_at.isoformat() if due_at else None,
        "status": "open",
        "source_note_id": source_note_id,
    }
    try:
        resp = supabase.table("tasks").insert(payload).execute()
        data = _resp_data(resp)
        return data[0] if data else None, None
    except Exception as e:
        return None, str(e)

def fetch_tasks(status: str = "open", limit: int = 200):
    try:
        q = (
            supabase.table("tasks")
            .select("*")
            .eq("user_id", DEV_USER_ID)
            .order("due_at", desc=False)
            .order("created_at", desc=True)
            .limit(limit)
        )
        if status:
            q = q.eq("status", status)
        resp = q.execute()
        return _resp_data(resp) or [], None
    except Exception as e:
        return [], str(e)

def set_task_status(task_id: str, status: str):
    updates = {"status": status}
    if status == "done":
        updates["completed_at"] = datetime.utcnow().isoformat()
    if status != "done":
        updates["completed_at"] = None

    try:
        supabase.table("tasks").update(updates).eq("id", task_id).eq("user_id", DEV_USER_ID).execute()
        return None
    except Exception as e:
        return str(e)

# -----------------------------
# UI
# -----------------------------
st.title("✨ ZiaFlow — Inbox")
st.caption("Capture anything: recipes, bike settings, golf drills, kids notes, home tasks. ZiaFlow will tag and organize them automatically.")

tab_inbox, tab_tasks = st.tabs(["Inbox", "Tasks"])

with tab_inbox:
    st.subheader("New note")
    raw_text = st.text_area("New note", placeholder="E.g. Octopus recipe with smoked paprika I loved last night...", height=140)

    colA, colB = st.columns([1, 2])
    with colA:
        save = st.button("Save to ZiaFlow", type="primary")
    with colB:
        st.write("")

    # NOTE: for now we keep AI optional. If AI fails, we still save note as misc.
    if save and raw_text.strip():
        # Replace this with your AI parsing later; for now keep safe defaults.
        ai_category = "misc"
        ai_tags = []

        note_row, err = create_note(raw_text.strip(), ai_category, ai_tags)
        if err:
            st.error(f"Error saving note: {err}")
        else:
            st.success("Note saved to ZiaFlow inbox ✅")

    st.divider()
    st.subheader("Recent notes")
    notes, err = fetch_notes(limit=50)
    if err:
        st.error(f"Error fetching notes: {err}")
    else:
        if notes:
            st.dataframe(notes, use_container_width=True)
        else:
            st.info("No notes yet.")

with tab_tasks:
    st.subheader("Create a task")
    tcol1, tcol2 = st.columns([2, 1])

    with tcol1:
        task_title = st.text_input("Task title", placeholder="E.g. Take son to dirt bike class")
        task_details = st.text_area("Details (optional)", placeholder="Anything helpful… link, notes, what to bring", height=90)

    with tcol2:
        use_due = st.checkbox("Add due date/time", value=True)
        due_date = st.date_input("Due date", value=None, disabled=not use_due)
        due_time = st.time_input("Due time", value=time(9, 0), disabled=not use_due)

    create_task_btn = st.button("Add task", type="primary")
    if create_task_btn and task_title.strip():
        due_at = None
        if use_due and due_date:
            due_at = datetime.combine(due_date, due_time)
        row, err = create_task(task_title, task_details, due_at=due_at)
        if err:
            st.error(f"Error creating task: {err}")
        else:
            st.success("Task created ✅")

    st.divider()
    st.subheader("Open tasks")
    tasks, err = fetch_tasks(status="open", limit=200)
    if err:
        st.error(f"Error fetching tasks: {err}")
    else:
        if not tasks:
            st.info("No open tasks. Add one above.")
        else:
            for t in tasks:
                left, right = st.columns([4, 1])
                with left:
                    due_txt = t.get("due_at") or ""
                    st.write(f"**{t.get('title','(no title)')}**")
                    if t.get("details"):
                        st.caption(t["details"])
                    if due_txt:
                        st.caption(f"Due: {due_txt}")
                with right:
                    if st.button("✅ Done", key=f"done_{t['id']}"):
                        e = set_task_status(t["id"], "done")
                        if e:
                            st.error(e)
                        else:
                            st.rerun()

    st.divider()
    st.subheader("Recently completed")
    done_tasks, err = fetch_tasks(status="done", limit=50)
    if err:
        st.error(f"Error fetching completed tasks: {err}")
    else:
        if done_tasks:
            for t in done_tasks[:10]:
                cols = st.columns([4, 1])
                cols[0].write(f"✅ {t.get('title','(no title)')}")
                if cols[1].button("Reopen", key=f"reopen_{t['id']}"):
                    e = set_task_status(t["id"], "open")
                    if e:
                        st.error(e)
                    else:
                        st.rerun()
        else:
            st.caption("No completed tasks yet.")
