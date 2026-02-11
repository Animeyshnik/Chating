import json
import asyncio
import sys


async def send(writer, data: dict):
    try:
        message = json.dumps(data, ensure_ascii=False) + "\n"
        writer.write(message.encode('utf-8'))
        await writer.drain()
        return True
    except (ConnectionResetError, BrokenPipeError, ConnectionAbortedError) as e:
        print(f"Ошибка отправки: {e}")
        return False

async def receive(reader):
    try:
        line = await reader.readline()
        if not line:
            return None
        return json.loads(line.decode('utf-8'))
    except (json.JSONDecodeError, UnicodeDecodeError) as e:
        print(f"Ошибка декодирования: {e}")
        return None
    except (ConnectionResetError, asyncio.IncompleteReadError, ConnectionAbortedError, BrokenPipeError):
        return None