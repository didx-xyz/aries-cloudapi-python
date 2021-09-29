from fastapi import FastAPI

from registry import actors, schemas
from dependencies import read_registry

from fastapi import Depends


app = FastAPI()

app.include_router(actors.router)
app.include_router(schemas.router)


@app.get("/")
async def root(registry_file=Depends(read_registry)):
    return registry_file


@app.get("/registry")
async def registry(registry_file=Depends(read_registry)):
    return registry_file
