from pymongo import MongoClient
import os
from dotenv import load_dotenv

load_dotenv()

client = MongoClient(os.getenv("MONGO_URI", "mongodb://localhost:27017/"))
db = client["intucate"]
prompts_col = db["prompts"]

prompt_doc = {
    "_id": "Education_Prompt",
    "template": "You are an expert in education domain. Answer the following: {{userInput}}"
}

existing = prompts_col.find_one({"_id": "Education_Prompt"})
if existing:
    print("Prompt already exists, skipping insert.")
else:
    prompts_col.insert_one(prompt_doc)
    print("Education_Prompt inserted successfully.")
