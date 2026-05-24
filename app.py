from flask import Flask, render_template, request, jsonify, session
from rag_pipeline import handle_query as rag_handle
from rag_pipeline import (
    extract_category,
    extract_course,
    extract_district,
    extract_year,
    is_cutoff_query,
    is_college_query,
    is_definition_question,
    normalize_query,
    extract_keywords_from_output,
    format_extracted_keywords,
)
from llm_api import call_llm
import os
import uuid

app = Flask(__name__)
app.secret_key = os.environ.get("FLASK_SECRET_KEY", "eva-dev-secret-change-me")

# In-memory per-session state (lost on server restart by design)
CONVERSATIONS = {}
MAX_HISTORY = 20

GREETINGS = {"hi", "hello", "hey", "hai"}
SYSTEM_QS = {
    "who are you",
    "what is eva",
    "what can you do",
    "about you"
}


def get_session_id() -> str:
    sid = session.get("sid")
    if not sid:
        sid = str(uuid.uuid4())
        session["sid"] = sid
    return sid


def get_state() -> dict:
    sid = get_session_id()
    if sid not in CONVERSATIONS:
        CONVERSATIONS[sid] = {
            "history": [],
            "last_rag": {
                "intent": None,
                "district": None,
                "course": None,
                "category": None,
                "year": None,
            },
            "pending_rag": {
                "intent": None,
                "district": None,
                "course": None,
                "category": None,
                "year": None,
            },
        }
    return CONVERSATIONS[sid]


def append_history(state: dict, role: str, content: str):
    if not content:
        return
    state["history"].append({"role": role, "content": content})
    if len(state["history"]) > MAX_HISTORY:
        state["history"] = state["history"][-MAX_HISTORY:]


def update_rag_context(state: dict, query: str):
    q = normalize_query(query.lower())
    intent = None
    if is_cutoff_query(q):
        intent = "cutoff"
    elif is_college_query(q):
        intent = "college"

    if not intent:
        return

    district = extract_district(q)
    course = extract_course(q)
    category = extract_category(q)
    year = extract_year(q)

    # If query clearly defines a new topic anchor, reset stale fields.
    has_new_anchor = bool(district or course or "cutoff" in q)
    if has_new_anchor:
        state["last_rag"] = {
            "intent": intent,
            "district": district,
            "course": course,
            "category": category,
            "year": year,
        }
        return

    ctx = state["last_rag"]
    ctx["intent"] = intent
    ctx["district"] = district or ctx.get("district")
    ctx["course"] = course or ctx.get("course")
    ctx["category"] = category or ctx.get("category")
    ctx["year"] = year or ctx.get("year")


def update_pending_rag_from_query(state: dict, query: str):
    q = normalize_query(query.lower())

    intent = None
    if is_cutoff_query(q):
        intent = "cutoff"
    elif is_college_query(q):
        intent = "college"

    if not intent:
        return

    state["pending_rag"] = {
        "intent": intent,
        "district": extract_district(q),
        "course": extract_course(q),
        "category": extract_category(q),
        "year": extract_year(q),
    }


def clear_pending_rag(state: dict):
    state["pending_rag"] = {
        "intent": None,
        "district": None,
        "course": None,
        "category": None,
        "year": None,
    }


def build_effective_query(user_query: str, state: dict) -> str:
    q = normalize_query(user_query.lower().strip())

    # FIRST: Check if this is a DEFINITION question - NEVER merge context for these!
    if is_definition_question(q):
        print(f"[BUILD_EFFECTIVE_QUERY] Definition question detected, returning as-is: '{q}'")
        return q  # Pass through without merging context

    # SECOND: Check for comparison/analysis keywords - PASS THROUGH AS-IS
    comparison_keywords = {"compare", "difference", "similar", "vs", "versus", "show history", "past queries"}
    if any(kw in q for kw in comparison_keywords):
        print(f"[BUILD_EFFECTIVE_QUERY] Comparison detected, passing through: '{q}'")
        return q  # Return as-is, don't merge with context

    # Keep as-is only when user already provided meaningful query structure.
    if is_cutoff_query(q) and (
        "cutoff" in q or extract_district(q) or extract_course(q)
    ):
        return q

    if is_college_query(q):
        return q

    pending = state.get("pending_rag", {})
    use_pending = pending.get("intent") in {"cutoff", "college"}

    ctx = pending if use_pending else state.get("last_rag", {})
    intent = ctx.get("intent")
    if intent not in {"cutoff", "college"}:
        return q

    current_category = extract_category(q)
    current_course = extract_course(q)
    current_district = extract_district(q)

    # Follow-up completion for short context replies like "mbc".
    if intent == "cutoff" and (current_category or len(q.split()) <= 3):
        merged_course = current_course or ctx.get("course")
        merged_district = current_district or ctx.get("district")
        merged_category = current_category or ctx.get("category")
        merged_year = ctx.get("year") or 2024

        parts = [
            "cutoff",
            f"for {merged_course}" if merged_course else "",
            f"in {merged_district}" if merged_district else "",
            merged_category or "",
            str(merged_year),
        ]
        return " ".join(p for p in parts if p).strip()

    if intent == "college" and len(q.split()) <= 3:
        merged_course = current_course or ctx.get("course")
        merged_district = current_district or ctx.get("district")
        parts = [
            "colleges",
            f"offering {merged_course}" if merged_course else "",
            f"in {merged_district}" if merged_district else "",
        ]
        return " ".join(p for p in parts if p).strip()

    return q

def quick_response(q):
    ql = q.lower().strip()

    if ql in GREETINGS:
        return ["Hello 👋 I am EVA. How can I help you?"]

    if ql in SYSTEM_QS:
        return [
            "I am EVA, a TNEA student assistant.",
            "I use official cutoff and college data.",
            "Always verify with counselling authorities."
        ]

    return None


def is_rag_question(q: str) -> bool:
    q = q.lower()

    # Explicit data-seeking signals (COMPARISON & COLLEGE/CUTOFF)
    data_signals = {
        "cutoff", "rank", "marks", "list", "colleges",
        "college", "available", "eligibility",
        "compare", "difference", "similar", "vs", "versus"
    }

    # Category-only should NOT trigger RAG alone
    categories = {"bc","oc","mbc","bcm","sc","sca","st"}

    # If user is asking conceptual explanation (NOT comparison or data lookup)
    explain_signals = {
        "what is", "explain", "meaning",
        "scope", "career", "about"
    }

    # Explanation questions get NO as RAG
    if any(e in q for e in explain_signals):
        return False

    # Check for comparison + data signals
    if any(d in q for d in data_signals):
        return True

    # Category + course alone is incomplete → still RAG
    if any(c in q for c in categories) and "cutoff" in q:
        return True

    return False



@app.route("/")
def home():
    return render_template("index.html")


@app.route("/clear", methods=["POST"])
def clear_chat():
    sid = session.get("sid")
    if sid and sid in CONVERSATIONS:
        CONVERSATIONS[sid] = {
            "history": [],
            "last_rag": {
                "intent": None,
                "district": None,
                "course": None,
                "category": None,
                "year": None,
            },
            "pending_rag": {
                "intent": None,
                "district": None,
                "course": None,
                "category": None,
                "year": None,
            },
        }
    return jsonify({"ok": True})


@app.route("/ask", methods=["POST"])
def ask():
    try:
        payload = request.get_json(silent=True) or {}
        user_query = payload.get("query", "").strip()
        if not user_query:
            return jsonify({"lines": ["Please type a question."]})

        state = get_state()
        sid = get_session_id()
        append_history(state, "user", user_query)

        effective_query = build_effective_query(user_query, state)

        # 1️⃣ Fast system replies
        fast = quick_response(user_query)
        if fast:
            append_history(state, "assistant", "\n".join(fast))
            return jsonify({"lines": fast})

        # 1️⃣b REJECT definition questions from RAG - send to LLM instead
        if is_definition_question(effective_query):
            answer = call_llm(user_query, history=state["history"][:-1])
            append_history(state, "assistant", answer)
            return jsonify({"lines": [answer]})

        # 2️⃣ RAG path (authoritative)
        if (
            is_rag_question(effective_query)
            or is_cutoff_query(effective_query)
            or is_college_query(effective_query)
        ):
            update_pending_rag_from_query(state, effective_query)
            lines = rag_handle(effective_query, session_id=sid)
            update_rag_context(state, effective_query)
            if lines and lines[0].lower().startswith("for cutoff info, please specify:"):
                # Keep pending context so next short reply (e.g. "mbc") fills missing fields.
                pass
            else:
                clear_pending_rag(state)
            append_history(state, "assistant", "\n".join(lines))
            return jsonify({"lines": lines})

        # 3️⃣ General LLM path
        answer = call_llm(user_query, history=state["history"][:-1])
        
        # Extract keywords from LLM response
        keyword_data = extract_keywords_from_output(answer)
        extracted = keyword_data['extracted']
        remaining_text = keyword_data['remaining_text']
        
        # Format extracted keywords if any were found
        formatted_keywords = format_extracted_keywords(keyword_data)
        
        # Build final response
        response_lines = []
        if formatted_keywords:
            response_lines.append(formatted_keywords)
            response_lines.append("")  # Blank line for readability
        
        if remaining_text.strip():
            response_lines.append(remaining_text.strip())
        elif not formatted_keywords:
            # Fallback: if no keywords or remaining text, use original answer
            response_lines.append(answer)
        
        final_answer = "\n".join(response_lines)
        append_history(state, "assistant", final_answer)
        return jsonify({"lines": [final_answer]})
    
    except Exception as e:
        print(f"[ERROR] Exception in ask(): {str(e)}")
        import traceback
        traceback.print_exc()
        return jsonify({"lines": [f"Error processing query: {str(e)}"]}), 500


if __name__ == "__main__":
    app.run(
        host="0.0.0.0",
        port=int(os.environ.get("PORT", 5000)),
        debug=True
    )
