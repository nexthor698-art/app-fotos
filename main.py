from fastapi import FastAPI, WebSocket, WebSocketDisconnect
import json
import os
import uvicorn

app = FastAPI()

# Diccionarios para gestionar las conexiones activas
dispositivos_activos = {}
paneles_control = []

@app.get("/")
async def root():
    return {"status": "Servidor activo para Control Android"}

@app.websocket("/ws/{client_id}")
async def websocket_endpoint(websocket: WebSocket, client_id: str):
    await websocket.accept()
    
    if client_id == "PANEL_CONTROL":
        paneles_control.append(websocket)
        print("Panel de control conectado.")
        # Al conectar el panel, enviarle la lista de IDs actuales
        await websocket.send_text(json.dumps({
            "tipo": "lista_dispositivos", 
            "ids": list(dispositivos_activos.keys())
        }))
    else:
        dispositivos_activos[client_id] = websocket
        print(f"Dispositivo registrado: {client_id}")
        await notificar_paneles({"tipo": "nuevo_dispositivo", "id": client_id})

    try:
        while True:
            data = await websocket.receive_text()
            mensaje = json.loads(data)

            if client_id == "PANEL_CONTROL":
                target_id = mensaje.get("target_id")
                if target_id in dispositivos_activos:
                    await dispositivos_activos[target_id].send_text(json.dumps(mensaje))
            else:
                for panel in paneles_control:
                    try:
                        await panel.send_text(json.dumps({
                            "tipo": "imagen_recibida",
                            "device_id": client_id,
                            "image_data": mensaje.get("image_data")
                        }))
                    except:
                        pass

    except WebSocketDisconnect:
        if client_id == "PANEL_CONTROL":
            if websocket in paneles_control:
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

# ESTO ES LO QUE FALTA PARA QUE RENDER NO SE CIERRE
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    uvicorn.run(app, host="0.0.0.0", port=port)
