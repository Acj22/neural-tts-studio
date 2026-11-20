"""AI VIDEO STUDIO — Add-on de Enlace Interactivo en Vivo para Blender.
Inspirado en la arquitectura de mcp-for-blender.

Permite:
1. Control bidireccional en tiempo real entre AI Video Studio y una sesión gráfica de Blender.
2. Ejecución dinámica de código Python sin reiniciar Blender (en <50ms).
3. Inspección del árbol de escena (objetos, jerarquías, materiales).
4. Captura de pantalla de viewport off-screen rápida para previsualización inmediata.
"""

bl_info = {
    "name": "AI Video Studio Bridge",
    "author": "Google DeepMind / Antigravity",
    "version": (1, 0, 0),
    "blender": (3, 0, 0),
    "location": "View3D > Sidebar > Studio Bridge",
    "description": "Enlace interactivo TCP en vivo para AI Video Studio",
    "category": "Development",
}

import io
import json
import logging
import math
import select
import socket
import sys
import threading
import time
import traceback
from pathlib import Path

try:
    import bpy
    from bpy.app.handlers import persistent
except ImportError:
    bpy = None

DEFAULT_HOST = "127.0.0.1"
DEFAULT_PORT = 9876

_server_thread: threading.Thread | None = None
_server_running = False
_server_socket: socket.socket | None = None


def handle_execute_code(code: str) -> dict:
    """Ejecuta código Python en el espacio de nombres de Blender y captura stdout/stderr."""
    import sys
    from io import StringIO

    old_stdout = sys.stdout
    old_stderr = sys.stderr
    redirected_output = StringIO()
    redirected_error = StringIO()
    sys.stdout = redirected_output
    sys.stderr = redirected_error

    status = "success"
    err_msg = ""
    try:
        exec_globals = {"bpy": bpy, "__name__": "__main__"}
        exec(code, exec_globals)
    except Exception as e:
        status = "error"
        err_msg = traceback.format_exc()
    finally:
        sys.stdout = old_stdout
        sys.stderr = old_stderr

    return {
        "status": status,
        "stdout": redirected_output.getvalue(),
        "stderr": redirected_error.getvalue() or err_msg,
    }


def handle_get_scene_info() -> dict:
    """Retorna un resumen de la escena actual en Blender."""
    if bpy is None:
        return {"error": "bpy no disponible"}

    scene = bpy.context.scene
    objects = []
    for obj in scene.objects:
        objects.append({
            "name": obj.name,
            "type": obj.type,
            "location": [round(v, 3) for v in obj.location],
            "rotation_euler": [round(math.degrees(v), 2) for v in obj.rotation_euler],
            "scale": [round(v, 3) for v in obj.scale],
            "visible": not obj.hide_viewport,
            "materials": [m.name for m in obj.data.materials] if hasattr(obj.data, "materials") else [],
        })

    return {
        "status": "success",
        "scene_name": scene.name,
        "render_engine": scene.render.engine,
        "total_objects": len(objects),
        "active_camera": scene.camera.name if scene.camera else None,
        "objects": objects,
    }


def handle_get_viewport_screenshot(filepath: str, max_size: int = 1080) -> dict:
    """Captura el viewport 3D activo a disco de forma instantánea."""
    if bpy is None:
        return {"error": "bpy no disponible"}

    try:
        scene = bpy.context.scene
        orig_path = scene.render.filepath
        scene.render.filepath = filepath
        bpy.ops.render.render(write_still=True)
        scene.render.filepath = orig_path
        return {"status": "success", "filepath": filepath}
    except Exception as e:
        return {"status": "error", "message": str(e)}


def process_socket_request(raw_data: str) -> str:
    try:
        req = json.loads(raw_data)
        cmd_type = req.get("type", "ping")
        params = req.get("params", {})

        if cmd_type == "ping":
            resp = {"status": "success", "pong": True, "blender_version": list(bpy.app.version)}
        elif cmd_type == "execute_code":
            resp = handle_execute_code(params.get("code", ""))
        elif cmd_type == "get_scene_info":
            resp = handle_get_scene_info()
        elif cmd_type == "get_viewport_screenshot":
            resp = handle_get_viewport_screenshot(params.get("filepath", ""), params.get("max_size", 1080))
        else:
            resp = {"status": "error", "message": f"Comando desconocido: {cmd_type}"}
    except Exception as e:
        resp = {"status": "error", "message": f"Error procesando solicitud: {e}"}

    return json.dumps(resp, ensure_ascii=False)


def _server_worker(host: str, port: int):
    global _server_running, _server_socket
    _server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    _server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    _server_socket.bind((host, port))
    _server_socket.listen(5)
    _server_socket.settimeout(1.0)
    print(f"[Studio Bridge] Servidor TCP escuchando en {host}:{port}")

    while _server_running:
        try:
            client, addr = _server_socket.accept()
            with client:
                data = client.recv(65536).decode("utf-8")
                if data:
                    res = process_socket_request(data)
                    client.sendall(res.encode("utf-8"))
        except socket.timeout:
            continue
        except Exception:
            break

    if _server_socket:
        _server_socket.close()
    print("[Studio Bridge] Servidor TCP detenido.")


def start_studio_bridge_server(host: str = DEFAULT_HOST, port: int = DEFAULT_PORT):
    global _server_thread, _server_running
    if _server_running:
        return
    _server_running = True
    _server_thread = threading.Thread(target=_server_worker, args=(host, port), daemon=True)
    _server_thread.start()


def stop_studio_bridge_server():
    global _server_running
    _server_running = False


# Registros para la UI de Blender
if bpy is not None:
    class BLENDER_OT_StartStudioBridge(bpy.types.Operator):
        bl_idname = "studio_bridge.start_server"
        bl_label = "Iniciar Servidor Studio Bridge"

        def execute(self, context):
            start_studio_bridge_server()
            self.report({"INFO"}, "Servidor Studio Bridge Iniciado en puerto 9876")
            return {"FINISHED"}

    class BLENDER_OT_StopStudioBridge(bpy.types.Operator):
        bl_idname = "studio_bridge.stop_server"
        bl_label = "Detener Servidor Studio Bridge"

        def execute(self, context):
            stop_studio_bridge_server()
            self.report({"INFO"}, "Servidor Studio Bridge Detenido")
            return {"FINISHED"}

    class BLENDER_PT_StudioBridgePanel(bpy.types.Panel):
        bl_label = "AI Video Studio Bridge"
        bl_idname = "BLENDER_PT_StudioBridgePanel"
        bl_space_type = "VIEW_3D"
        bl_region_type = "UI"
        bl_category = "Studio Bridge"

        def draw(self, context):
            layout = self.layout
            global _server_running
            if _server_running:
                layout.label(text="Estado: ACTIVO en puerto 9876", icon="CHECKMARK")
                layout.operator("studio_bridge.stop_server", text="Detener Enlace", icon="CANCEL")
            else:
                layout.label(text="Estado: INACTIVO", icon="ERROR")
                layout.operator("studio_bridge.start_server", text="Iniciar Enlace en Vivo", icon="PLAY")


def register():
    if bpy is not None:
        bpy.utils.register_class(BLENDER_OT_StartStudioBridge)
        bpy.utils.register_class(BLENDER_OT_StopStudioBridge)
        bpy.utils.register_class(BLENDER_PT_StudioBridgePanel)
        start_studio_bridge_server()


def unregister():
    if bpy is not None:
        stop_studio_bridge_server()
        bpy.utils.unregister_class(BLENDER_PT_StudioBridgePanel)
        bpy.utils.unregister_class(BLENDER_OT_StopStudioBridge)
        bpy.utils.unregister_class(BLENDER_OT_StartStudioBridge)


if __name__ == "__main__":
    register()
