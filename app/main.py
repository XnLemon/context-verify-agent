from fastapi import FastAPI


app = FastAPI(title="Contract Agent (Python)", version="2.0.0")


@app.get("/", include_in_schema=False)
def root() -> dict[str, str]:
    return {
        "service": "agent-python",
        "message": "SaaS API has been split to SpringBoot. Python app only keeps agent capabilities.",
    }

