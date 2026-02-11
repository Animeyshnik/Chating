import asyncio
import sys
from datetime import datetime
from protocol import send, receive
from database import register_user, authenticate_user


clients = {}
online_users = {}

async def send_online_users(writer):


    users_list = list(online_users.keys())
    await send(writer,
        {
            "type": "online_users",
            "users": users_list
        }
    )


async def cleanup_client(writer):
    if writer in clients:
        username = clients[writer]
        del clients[writer]
        if username in online_users:
            del online_users[username]
        print(f"Клиент {username} отключен")


async def broadcast_message(sender_username: str, message: str, exclude_writer = None):
    dead_writers = []

    for writer, username in list(clients.items()):
        if writer == exclude_writer:
            continue

        try:
            success = await send(writer, {
                "type": "chat",
                "from": sender_username,
                "text": message,
                "timestamp": datetime.now().strftime("%H:%M:%S")
            })
            if not success:
                dead_writers.append(writer)
        except Exception as e:
            print(f"Ошибка отправки сообщения {username}: {e}")
            dead_writers.append(writer)
    
    for writer in dead_writers:
        await cleanup_client(writer)

async def broadcast_user_status(username: str, status: str):

    await broadcast_message("Система", f"{username} {status}")

async def handle_client(reader, writer):

    addr = writer.get_extra_info("peername")
    print(f"Новое подклэюение {addr}")

    username = None

    try:
        while True:
            msg = await receive(reader)

            if msg is None:
                break

            msg_type = msg.get("type")

            if msg_type == "register":
                username_input = msg.get("username", "").strip()
                password_input = msg.get("password", "")

                if not username_input or not password_input:
                    await send(writer, {
                        "type": "register_result",
                        "ok": False,
                        "error": "Имя пользователя и пароль обязательны"
                    })
                    continue

                if len(username_input) < 3:
                    await send(writer, {
                        "type": "register_result",
                        "ok": False,
                        "error": "Имя пользователя должно быть не менее 3 символов"
                    })
                    continue

                if len(username_input) > 20:
                    await send(writer, {
                        "type": "register_result",
                        "ok": False,
                        "error": "Имя пользователя должно быть не более 20 символов"
                    })
                    continue
                
                if len(password_input) < 4:
                    await send(writer, {
                        "type": "register_result",
                        "ok": False,
                        "error": "Пароль должен быть не менее 4 символов"
                    })
                    continue

                ok = register_user(username_input, password_input)

                if ok:
                    await send(writer, {
                        "type": "register_result",
                        "ok": True,
                        "message": "Регистрация успешна!"
                    })
                else:
                    await send(writer, {
                        "type": "register_result",
                        "ok": False,
                        "error": "Пользователь с таким именем уже существует"
                    })

            elif msg_type == "login":

                username_input = msg.get("username", "").strip()
                password_input = msg.get("password", "")

                if not username_input or not password_input:
                    await send(writer,{
                        "type": "login_result",
                        "ok": False,
                        "error": "Имя пользователя и пароль обязательны"
                    })
                    continue

                if authenticate_user(username_input, password_input):

                    if username_input in online_users:
                        await send(writer, {
                            "type": "login_result",
                            "ok": False,
                            "error": "Пользователь уже в сети"
                        })
                        continue
                
                    username = username_input
                    clients[writer] = username
                    online_users[username] = writer

                    await send(writer, {
                        "type": "login_result",
                        "ok": True,
                        "message": f"Добро пожаловать, {username}!"
                    })  

                    await send_online_users(writer)
                    
                    await broadcast_user_status(username, "подключился")
                    print(f"Пользователь {username} вошел в систему")
                else:
                    await send(writer, {
                        "type": "login_result",
                        "ok": False,
                        "error": "Неверное имя пользователя или пароль"
                    })
            elif msg_type == "get_online":

                if username:
                    await send_online_users(writer)
    
            elif msg_type == "chat":
                if not username:
                    await send(writer,{
                        "type": "error",
                        "message": "Сначала необходимо войти в систему"
                    })
                    continue

                text = msg.get("text", "").strip()
                if not text:
                    continue

                print(f"[{username}]: {text}")
                await broadcast_message(username, text)

            elif msg_type == "exit":
                print(f"Пользователь {username} вышел")
                break
            
            else:
                await send(writer, {
                    "type": "error",
                    "message": f"Неизвестная команда: {msg_type}"
                })

    except asyncio.CancelledError:
        print(f"Соединение с {addr} прервано")
        raise
    
    except Exception as e:
        
        print(f"Ошибка обработки клиента {addr}: {e}")
    
    finally:

        if username:
            await broadcast_user_status(username, "отключился")
        
        await cleanup_client(writer)
        
        try:
    
            writer.close()
            await writer.wait_closed()
    
        except Exception:
            pass


async def main():
    try:
        server = await asyncio.start_server(
            handle_client,
            "127.0.0.1",
            8888
        )

        addr = server.sockets[0].getsockname()
        print(f"Сервер запущен на {addr}")

        async with server:
            await server.serve_forever()

    except OSError as e:
        print(f"Ошибка запуска сервера: {e}")
        print("Возможно, порт 8888 уже занят")
        sys.exit(1)
    except KeyboardInterrupt:
        print("\n\nСервер остановлен")
    except Exception as e:
        print(f"Критическая ошибка: {e}")
        sys.exit(1)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nВыход...")