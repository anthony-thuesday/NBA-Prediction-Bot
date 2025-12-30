from fastapi import FastAPI
from .predictor import train_bundle, predict_today

app = FastAPI()

bundle = None

@app.on_event("startup")
def startup():
    global bundle
    bundle = train_bundle()

@app.get("/health")
def health():
    return {"ok": True}

@app.get("/predict/today")
def predict_today_route():
    games = predict_today(bundle)
    return {"games": games}
