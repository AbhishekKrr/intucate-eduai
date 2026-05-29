"""
EduAI - Flask backend for the case study solution for Intucate Full Stack Developer.

These are the technologies used: Python, Flask, MongoDB (Atlas), and Groq LLM API.
"""

from flask import Flask, request, jsonify, render_template
from pymongo import MongoClient
from groq import Groq, AsyncGroq
import asyncio
import os
from dotenv import load_dotenv
from datetime import datetime

# Derive environment variables from .env file
load_dotenv()

app = Flask(__name__)

# ── Database setup ──────────────────────────────────────────────────────────
# Connect to MongoDB Atlas using the URI from the .env file
mongo_client = MongoClient(os.getenv("MONGO_URI", "mongodb://localhost:27017/"), serverSelectionTimeoutMS=5000)
db = mongo_client["intucate"]

# 'prompts' collection: Contains re-usable prompt templates keyed by _id
prompts_col = db["prompts"]

# 'history' collection: is used for keeping all the requests/response pairs for auditing purposes
history_col = db["history"]

# ── LLM client setup ─────────────────────────────────────────────────────────
# Sync client for single requests; Async client for concurrent batch requests
groq_client = Groq(api_key=os.getenv("GROQ_API_KEY"))
async_groq_client = AsyncGroq(api_key=os.getenv("GROQ_API_KEY"))

# Model to use for all completions
MODEL = "llama-3.3-70b-versatile"


# ── Helpers ──────────────────────────────────────────────────────────────────

def get_template(prompt_id="Education_Prompt"):
    """Get a prompt template document from MongoDB, based on its _id."""
    doc = prompts_col.find_one({"_id": prompt_id})
    return doc["template"] if doc else None


def call_groq_sync(prompt_text):
    """Send one line of text to Groq and return Groq's response."""
    res = groq_client.chat.completions.create(
        model=MODEL,
        messages=[{"role": "user", "content": prompt_text}]
    )
    return res.choices[0].message.content


async def call_groq_async(prompt_text):
    """Async version of call_groq_sync — for concurrent batch processing."""
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
    Read a question from one user, go to Step 1-5 and select Accept a single user question.
    Use MongoDB to store the request/response in history,
    return the AI response.

    Request body:  { "userInput": "How much do I have to score to pass CA final?" }
    Response body: { "response": "..." }
    """
    # get_json() will return none when the body of the request is missing, or if the Content-Type is not application/json.
    data = request.get_json()
    if not data:
        return jsonify({"error": "Request body must be valid JSON"}), 400

    user_input = data.get("userInput", "").strip()
    if not user_input:
        return jsonify({"error": "userInput is required and cannot be empty"}), 400

    # Get prompt template from 'prompts' collection in the MongoDB database
    template = get_template()
    if not template:
        return jsonify({"error": "Prompt template not found in DB"}), 404

    # Inject userInput into the template (replaces {{userInput}} placeholder)
    final_prompt = template.replace("{{userInput}}", user_input)

    # If the API call fails, return a clean JSON error from the LLM.
    try:
        ai_response = call_groq_sync(final_prompt)
    except Exception as e:
        return jsonify({"error": f"LLM API error: {str(e)}"}), 502

    # Keep the entire request/response in the "history" collection.
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
    Step 6: Retrieve the prompt template once, given a list of user questions,
    then process all questions at once with asyncio.gather, so that
    LLM calls don't block each other. Responses are fed back in the same
    order as the input list.

    Request body:  { "userInputs": ["question 1", "question 2", ...] }
    Response body: { "responses": ["answer 1", "answer 2", ...] }
    """
    # get_json() returns None when no body is provided or Content-Type is not correct
    data = request.get_json()
    if not data:
        return jsonify({"error": "Request body must be valid JSON"}), 400

    user_inputs = data.get("userInputs", [])

    # Validate: must be a non-empty list of strings
    if not user_inputs or not isinstance(user_inputs, list):
        return jsonify({"error": "userInputs must be a non-empty list"}), 400

    if not all(isinstance(item, str) and item.strip() for item in user_inputs):
        return jsonify({"error": "Every item in userInputs must be a non-empty string"}), 400

    # Strip spaces from each of the input values.
    user_inputs = [inp.strip() for inp in user_inputs]

    # Load the prompt template only once (for each input).
    template = get_template()
    if not template:
        return jsonify({"error": "Prompt template not found in DB"}), 404

    # For each input, build one full prompt.
    prompts = [template.replace("{{userInput}}", inp) for inp in user_inputs]

    # Fire all LLM calls concurrently; asyncio.gather preserves input order
    async def gather_all():
        tasks = [call_groq_async(p) for p in prompts]
        return await asyncio.gather(*tasks)

    try:
        responses = asyncio.run(gather_all())
    except Exception as e:
        return jsonify({"error": f"LLM API error: {str(e)}"}), 502

    # Save each request/response to history with a UTC date/time stamp
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
