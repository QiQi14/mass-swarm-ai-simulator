import asyncio
import websockets
import json

async def test_ws():
    try:
        async with websockets.connect("ws://127.0.0.1:8080") as websocket:
            print("Connected to WS! Waiting for sync deltas...")
            for _ in range(3):
                message = await websocket.recv()
                print(f"Received ({len(message)} bytes):", message[:100], "...")
                data = json.loads(message)
                assert data["type"] == "SyncDelta"
                assert "tick" in data
                assert "moved" in data
            print("WS JSON schema verified!")
    except Exception as e:
        print(f"Error: {e}")

asyncio.run(test_ws())
