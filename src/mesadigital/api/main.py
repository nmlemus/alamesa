import uvicorn
from fastapi import FastAPI

app = FastAPI(title="Mesa Digital API")


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


def main() -> None:
    uvicorn.run("mesadigital.api.main:app", host="0.0.0.0", port=8000, reload=False)
