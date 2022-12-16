from fastapi import FastAPI

app = FastAPI()


@app.get("/metrics")
async def root():
    return {"message": "Hello World"}
