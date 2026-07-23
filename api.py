from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import random

app = FastAPI()

# Allow the React frontend to communicate with this local API
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], 
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/api/recommendations")
def get_recommendations(commander: str = "", spice: int = 50):
    # Temporary mock data so we can test the Sidebar object hand-off.
    # Later, we will wire this up to your recommend_deck.py logic!
    return [
        {"name": "Blood Artist", "cmc": 2, "spice_score": 10},
        {"name": "Viscera Seer", "cmc": 1, "spice_score": 20},
        {"name": "Spice Engine", "cmc": 4, "spice_score": 90}
    ]
