"""
EduAI - Flask backend for the Intucate Full Stack Developer case study.

Stack: Python + Flask + MongoDB (Atlas) + Groq LLM API
"""

from flask import Flask, request, jsonify, render_template
from pymongo import MongoClient
from groq import Groq, AsyncGroq
import asyncio
import os
from dotenv import load_dotenv
from datetime import datetime

# Load environment variables from .env file
load_dotenv()

app = Flask(__name__)

# ── Database setup ──────────────────────────────────────────────────────────
# Connect to MongoDB Atlas using the URI stored in .env
mongo_client = MongoClient(os.getenv("MONGO_URI", "mongodb://localhost:27017/"))
db = mongo_client["intucate"]

# 'prompts' collection: stores reusable prompt templates keyed by _id
prompts_col = db["prompts"]

# 'history' collection: stores every request/response pair for auditing
history_col = db["history"]

# ── LLM client setup ─────────────────────────────────────────────────────────
# Sync client for single requests; Async client for concurrent batch requests
groq_client = Groq(api_key=os.getenv("GROQ_API_KEY"))
async_groq_client = AsyncGroq(api_key=os.getenv("GROQ_API_KEY"))

# Model to use for all completions
MODEL = "llama-3.3-70b-versatile"


# ── Helpers ──────────────────────────────────────────────────────────────────

def get_template(prompt_id="Education_Prompt"):
    """Fetch a prompt template document from MongoDB by its _id."""
    doc = prompts_col.find_one({"_id": prompt_id})
    return doc["template"] if doc else None


def call_groq_sync(prompt_text):
    """Send a single prompt to Groq and return the text response."""
    res = groq_client.chat.completions.create(
        model=MODEL,
        messages=[{"role": "user", "content": prompt_text}]
    )
    return res.choices[0].message.content


async def call_groq_async(prompt_text):
    """Async version of call_groq_sync — used for concurrent batch processing."""
    res = await async_groq_client.chat.completions.create(
        model=MODEL,
        messages=[{"role": "user", "content": prompt_text}]
    )
    return res.choices[0].message.content


# ── Routes ───────────────────────────────────────────────────────────────────

@app.route("/", methods=["GET"])
def index():
    """Serve the frontend UI."""
    return render_template("index.html")


@app.route("/ask", methods=["POST"])
def ask():
    """
    Step 1-5: Accept a single user question, fetch the prompt template from
    MongoDB, call the Groq LLM, store the request/response in history, and
    return the AI response.

    Request body:  { "userInput": "How much should I score to pass CA final?" }
    Response body: { "response": "..." }
    """
    # get_json() returns None if body is missing or Content-Type is not application/json
    data = request.get_json()
    if not data:
        return jsonify({"error": "Request body must be valid JSON"}), 400

    user_input = data.get("userInput", "").strip()
    if not user_input:
        return jsonify({"error": "userInput is required and cannot be empty"}), 400

    # Fetch prompt template from the 'prompts' MongoDB collection
    template = get_template()
    if not template:
        return jsonify({"error": "Prompt template not found in DB"}), 404

    # Inject userInput into the template (replaces {{userInput}} placeholder)
    final_prompt = template.replace("{{userInput}}", user_input)

    # Call the LLM and return a clean JSON error if the API call fails
    try:
        ai_response = call_groq_sync(final_prompt)
    except Exception as e:
        return jsonify({"error": f"LLM API error: {str(e)}"}), 502

    # Persist the full request/response pair in the 'history' collection
    history_col.insert_one({
        "userInput": user_input,
        "prompt": final_prompt,
        "response": ai_response,
        "timestamp": datetime.utcnow()  # UTC timestamp for every record
    })

    return jsonify({"response": ai_response})


@app.route("/ask-batch", methods=["POST"])
def ask_batch():
    """
    Step 6: Accept a list of user questions, fetch the prompt template once,
    then process all questions concurrently using asyncio.gather so that
    LLM calls don't block each other. Responses are returned in the same
    order as the input list.

    Request body:  { "userInputs": ["question 1", "question 2", ...] }
    Response body: { "responses": ["answer 1", "answer 2", ...] }
    """
    # get_json() returns None if body is missing or Content-Type is wrong
    data = request.get_json()
    if not data:
        return jsonify({"error": "Request body must be valid JSON"}), 400

    user_inputs = data.get("userInputs", [])

    # Validate: must be a non-empty list of strings
    if not user_inputs or not isinstance(user_inputs, list):
        return jsonify({"error": "userInputs must be a non-empty list"}), 400

    if not all(isinstance(item, str) and item.strip() for item in user_inputs):
        return jsonify({"error": "Every item in userInputs must be a non-empty string"}), 400

    # Strip whitespace from each input
    user_inputs = [inp.strip() for inp in user_inputs]

    # Fetch the prompt template once (reused for every input)
    template = get_template()
    if not template:
        return jsonify({"error": "Prompt template not found in DB"}), 404

    # Build one complete prompt per input
    prompts = [template.replace("{{userInput}}", inp) for inp in user_inputs]

    # Fire all LLM calls concurrently; asyncio.gather preserves input order
    async def gather_all():
        tasks = [call_groq_async(p) for p in prompts]
        return await asyncio.gather(*tasks)

    try:
        responses = asyncio.run(gather_all())
    except Exception as e:
        return jsonify({"error": f"LLM API error: {str(e)}"}), 502

    # Store each request/response pair in history with a UTC timestamp
    docs = [
        {
            "userInput": user_inputs[i],
            "prompt": prompts[i],
            "response": responses[i],
            "timestamp": datetime.utcnow()  # UTC timestamp for every record
        }
        for i in range(len(user_inputs))
    ]
    history_col.insert_many(docs)

    return jsonify({"responses": list(responses)})


if __name__ == "__main__":
    app.run(debug=True)
