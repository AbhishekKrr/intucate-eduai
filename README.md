# EduAI — Education Assistant

Flask + MongoDB + Groq LLM Application for the Intucate Full Stack Developer case study.

**Live:** https://intucate-eduai.onrender.com

---

## Tech Stack

| Layer    | Technology                          |
|----------|-------------------------------------|
| Backend  | Python 3, Flask                     |
| Database | MongoDB Atlas (pymongo)             |
| LLM      | Groq API — Llama 3.3 70B Versatile  |

The front-end is served with Flask, and is a vanilla HTML/CSS/JS application.

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

### 1. Duplicate / open project

```bash
cd intucate-fsd
```

### 2. Create and activate a virtual environment.

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

In root directory create a `.env` file:

```
GROQ_API_KEY=your_groq_api_key_here
MONGO_URI=mongodb+srv://<user>:<password>@cluster.mongodb.net/?appName=Cluster0
```

- Get a free Groq API key at: https://console.groq.com

If you use the free tier of MongoDB Atlas, it's fine.

### 5. Seed the database

Adds the file `Education_Prompt` to the collection `prompts` (one time only):

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

Base URL: `https://intucate-eduai.onrender.com`

POSTs to `/ask` return a single question.

POSTs on `/ask` will return 1 question.

Retrieves prompt template from MongoDB, invokes LLM and adds the response to history then returns response.

**Request:**
```json
{ "userInput": "How much should I score in each subject to pass CA final?" }
```

**Response:**
```json
{ "response": "..." }
```

---

### Multiple questions (async)

Takes a list of questions, runs them concurrently in the order they were given using `asyncio.gather`, and returns them in the same order.

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

Stores ReUsable LLM prompt Templates.

```json
{
  "_id": "Education_Prompt",
  "template": "You are an expert in education domain. Answer the following: {{userInput}}"
}
```

### Collection: `history`

Persists all request / response pairs to be audit logged.

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

- Groq over OpenAI: fully compatible API with much faster inference. The FAQ clearly states that any alternative of LLM is acceptable.
- With Async batch processing, `AsyncGroq` launches all LLM calls at the same time using `asyncio.gather`, meaning that N questions take about 1 time rather than N×1.
- **Prompt stored in MongoDB** — Separates prompt from code, templates can be updated without redeploy.
- All requests/response are stored with a UTC timestamp for complete auditing purposes.