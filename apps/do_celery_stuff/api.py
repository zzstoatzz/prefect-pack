from fastapi import FastAPI
from tasks import find_primes_up_to

app = FastAPI()


@app.get("/health")
async def health():
    return {"status": "ok"}


@app.post("/find_primes_up_to")
async def submit_find_primes_up_to(n: int):
    future = find_primes_up_to.delay(n)
    return {"task_id": future.task_run_id}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
