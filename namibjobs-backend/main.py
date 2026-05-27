from fastapi import FastAPI
from dotenv import load_dotenv

load_dotenv()

app = FastAPI(title="NamibJobs API", version="0.1.0")


@app.get("/")
def root():
    return {"message": "NamibJobs API is running"}
