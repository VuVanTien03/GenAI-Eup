from fastapi import FastAPI
from dotenv import dotenv_values
from fastapi.middleware.cors import CORSMiddleware
from src.features.ai_schedule.schedule_controller import GenSchedule
from src.constant.ScheduleType import Schedule

config = dotenv_values(".env")

app = FastAPI()

# Cho phép tất cả origin (dev)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 🛡 Có thể thay bằng ["http://localhost:3000"] cho frontend cụ thể
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
def root():
    return {"Hello": "World"}

@app.post("/query")
async def query_schedule(req: Schedule):
    return GenSchedule(req)
