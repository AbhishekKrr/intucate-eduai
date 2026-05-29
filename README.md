# EduAI — Education Assistant

A Flask + MongoDB + Groq LLM application built for the Intucate Full Stack Developer case study.

---

## Tech Stack

| Layer    | Technology                          |
|----------|-------------------------------------|
| Backend  | Python 3, Flask                     |
| Database | MongoDB Atlas (pymongo)             |
| LLM      | Groq API — Llama 3.3 70B Versatile  |
| Frontend | Vanilla HTML/CSS/JS (served by Flask) |

---

## Project Structure

```
intucate-fsd/
├── app.py              # Flask app — all API routes
├── seed_db.py          # One-time script to insert the prompt template into MongoDB
├── requirements.txt    # Python dependencies
├── .env                # Environment variables (not committed)
├── templates/
│   └── index.html      # Frontend UI
└── README.md
```

---

## Setup & Run Locally

### 1. Clone / open the project

```bash
cd intucate-fsd
```

### 2. Create and activate a virtual environment

```bash
python -m venv venv
venv\Scripts\activate        # Windows
# source venv/bin/activate   # Mac/Linux
```

### 3. Install dependencies

```bash
pip install -r requirements.txt
```

### 4. Configure environment variables

Create a `.env` file in the project root:

```
GROQ_API_KEY=your_groq_api_key_here
MONGO_URI=mongodb+srv://<user>:<password>@cluster.mongodb.net/?appName=Cluster0
```

- Get a free Groq API key at: https://console.groq.com
- MongoDB Atlas free tier works fine.

### 5. Seed the database

Inserts the `Education_Prompt` document into the `prompts` collection (run once):

```bash
python seed_db.py
```

### 6. Start the server

```bash
python app.py
```

Open **http://127.0.0.1:5000** in your browser.

---

## API Endpoints

### POST `/ask` — Single question

Fetches the prompt template from MongoDB, calls the LLM, saves the result to history, and returns the response.

**Request:**
```json
{ "userInput": "How much should I score in each subject to pass CA final?" }
```

**Response:**
```json
{ "response": "..." }
```

---

### POST `/ask-batch` — Multiple questions (async)

Accepts a list of questions, processes each one **concurrently** using `asyncio.gather`, and returns responses in the same order.

**Request:**
```json
{ "userInputs": ["What is CA final syllabus?", "How to prepare for IPCC?"] }
```

**Response:**
```json
{ "responses": ["...", "..."] }
```

---

## Database Schema

### Collection: `prompts`

Stores reusable LLM prompt templates.

```json
{
  "_id": "Education_Prompt",
  "template": "You are an expert in education domain. Answer the following: {{userInput}}"
}
```

### Collection: `history`

Stores every request/response pair for auditing.

```json
{
  "userInput": "How much should I score to pass CA final?",
  "prompt": "You are an expert in education domain. Answer the following: ...",
  "response": "...",
  "timestamp": "2026-05-29T10:00:00Z"
}
```

---

## Design Decisions

- **Groq instead of OpenAI** — Groq provides a fully compatible API with significantly faster inference. The FAQ explicitly states any LLM alternative is acceptable.
- **Async batch processing** — `AsyncGroq` with `asyncio.gather` fires all LLM calls simultaneously, so N questions take roughly the same time as 1 instead of N×1.
- **Prompt stored in MongoDB** — Decouples the prompt from code; templates can be updated without a redeploy.
- **history collection** — Every request/response is persisted with a UTC timestamp for full auditability.
