from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import uvicorn
import os
from .main_service import *

# Crear instancia de FastAPI
app = FastAPI()

# Definir el modelo de datos para la solicitud
class RequestModel(BaseModel):
    prompt: str  # Define el campo 'prompt' como un string

@app.post("/consultar")
async def consultar(request: RequestModel):
    """
    Endpoint para consultar el modelo de IA.

    Args:
        request (Request): Objeto de solicitud de FastAPI que contiene el ID del usuario y el prompt.

    Returns:
        dict: Respuesta del modelo de IA.
    """
    try:
        # Obtener IP real del usuario
        ip_usuario = obtener_ip_real(request)
        # Obtener datos del cuerpo de la solicitud
        prompt = request.prompt
        if not prompt:
            raise HTTPException(status_code=400, detail="El prompt es obligatorio.")
        # Consultar IA y devolver respuesta
        respuesta = consultar_ia(ip_usuario, prompt)
        return {"respuesta": respuesta}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    
if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=int(os.environ.get("PORT", 8000)))