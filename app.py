from flask import Flask, render_template, request, jsonify
from rag_pipeline import handle_query as rag_handle
from llm_api import call_llm
import os

app = Flask(__name__)

GREETINGS = {"hi", "hello", "hey", "hai"}
SYSTEM_QS = {
    "who are you",
    "what is eva",
    "what can you do",
    "about you"
}

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

    # Explicit data-seeking signals
    data_signals = {
        "cutoff", "rank", "marks", "list", "colleges",
        "college", "available", "eligibility"
    }

    # Category-only should NOT trigger RAG alone
    categories = {"bc","oc","mbc","bcm","sc","sca","st"}

    # If user is asking explanation
    explain_signals = {
        "what is", "explain", "meaning", "difference",
        "scope", "career", "about"
    }

    if any(e in q for e in explain_signals):
        return False

    if any(d in q for d in data_signals):
        return True

    # Category + course alone is incomplete → still RAG
    if any(c in q for c in categories) and "cutoff" in q:
        return True

    return False



@app.route("/")
def home():
    return render_template("index.html")


@app.route("/ask", methods=["POST"])
def ask():
    user_query = request.json.get("query", "").strip()

    # 1️⃣ Fast system replies
    fast = quick_response(user_query)
    if fast:
        return jsonify({"lines": fast})

    # 2️⃣ RAG path (authoritative)
    if is_rag_question(user_query):
        lines = rag_handle(user_query)
        return jsonify({"lines": lines})

    # 3️⃣ General LLM path
    answer = call_llm(user_query)
    return jsonify({"lines": [answer]})


if __name__ == "__main__":
    app.run(
        host="0.0.0.0",
        port=int(os.environ.get("PORT", 5000))
    )
