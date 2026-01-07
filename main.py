from fastapi import FastAPI, Body

app = FastAPI()
# Memoria temporal
estado = {"orden": None, "foto": None}

@app.get("/check")
def check():
    return {"orden": estado["orden"]}

@app.post("/orden")
def poner_orden(data: dict = Body(...)):
    estado["orden"] = data.get("accion") # Ejemplo: "foto"
    estado["foto"] = None
    return {"status": "ok"}

@app.post("/upload")
def upload(data: dict = Body(...)):
    estado["foto"] = data.get("image_data")
    estado["orden"] = None
    return {"status": "ok"}

@app.get("/download")
def download():
    return {"foto": estado["foto"]}
