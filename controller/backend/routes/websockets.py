"""WebSocket routes — live logs streaming and web terminal."""

import asyncio

from fastapi import APIRouter, WebSocket, WebSocketDisconnect, HTTPException

from ..helpers import docker_client, sanitize_container_name

router = APIRouter()


def verify_ws_auth(websocket: WebSocket) -> bool:
    """Verify WebSocket auth via query param token (Basic credentials base64)."""
    import base64
    import os
    import secrets

    auth_user = os.environ.get("CONTROLLER_USER", "admin")
    auth_pass = os.environ.get("CONTROLLER_PASS", "")
    token = websocket.query_params.get("token", "")
    if not token or not auth_pass:
        return False
    try:
        decoded = base64.b64decode(token).decode()
        user, password = decoded.split(":", 1)
        return (
            secrets.compare_digest(user.encode(), auth_user.encode())
            and secrets.compare_digest(password.encode(), auth_pass.encode())
        )
    except Exception:
        return False


@router.websocket("/ws/logs/{name}")
async def ws_logs(websocket: WebSocket, name: str):
    if not verify_ws_auth(websocket):
        await websocket.close(code=4401)
        return
    await websocket.accept()

    try:
        container_name = sanitize_container_name(name)
    except HTTPException:
        await websocket.send_text(f"Unknown container: '{name}'")
        await websocket.close()
        return

    try:
        container = docker_client.containers.get(container_name)
    except Exception:
        await websocket.send_text(f"Container '{name}' not found")
        await websocket.close()
        return

    log_generator = container.logs(stream=True, follow=True, tail=100)
    loop = asyncio.get_event_loop()
    try:
        while True:
            chunk = await loop.run_in_executor(None, next, log_generator, None)
            if chunk is None:
                break
            await websocket.send_text(chunk.decode(errors="replace"))
    except WebSocketDisconnect:
        pass
    except Exception:
        await websocket.close()
    finally:
        log_generator.close()


@router.websocket("/ws/terminal/{name}")
async def ws_terminal(websocket: WebSocket, name: str):
    if not verify_ws_auth(websocket):
        await websocket.close(code=4401)
        return
    await websocket.accept()

    try:
        container_name = sanitize_container_name(name)
    except HTTPException:
        await websocket.send_text(f"\r\nUnknown container: '{name}'\r\n")
        await websocket.close()
        return

    try:
        docker_client.containers.get(container_name)
    except Exception:
        await websocket.send_text(f"\r\nContainer '{container_name}' not found\r\n")
        await websocket.close()
        return

    exec_id = docker_client.api.exec_create(
        container_name, "/bin/bash", stdin=True, tty=True, stdout=True, stderr=True,
    )
    sock = docker_client.api.exec_start(exec_id, socket=True, tty=True)
    raw_sock = sock._sock

    async def read_from_container():
        loop = asyncio.get_event_loop()
        try:
            while True:
                data = await loop.run_in_executor(None, raw_sock.recv, 4096)
                if not data:
                    break
                await websocket.send_bytes(data)
        except Exception:
            pass

    reader_task = asyncio.create_task(read_from_container())
    try:
        while True:
            data = await websocket.receive_bytes()
            raw_sock.sendall(data)
    except WebSocketDisconnect:
        pass
    finally:
        reader_task.cancel()
        raw_sock.close()
