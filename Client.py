import asyncio
import sys
from protocol import send, receive


class Client:
    def __init__(self):
        self.reader = None
        self.writer = None
        self.username = None
        self.running = False

    async def connect(self, host = "127.0.0.1", port = 8888):
        try:
            self.reader, self.writer = await asyncio.open_connection(host, port)
            return True
        except ConnectionRefusedError:
            print("Ошибка: Сервер не запущен или недоступен")
            return False
        except Exception as e:
            print(f"Ошибка подключения: {e}")
            return False

    async def disconnect(self):
        self.running = False

        if self.writer:
            try:
                await send(self.writer, {"type" : "exit"})
            except Exception as e:
                print(f"Ошибка: {e}")
            self.writer.close()
            try:
                await self.writer.wait_closed()
            except Exception as e:
                print(f"Ошибка: {e}")    

    async def login(self, username, password):
        await send(self.writer,{
            "type": "login",
            "username": username,
            "password": password
        })
        result = await receive(self.reader)
        if result and result.get("ok"):
            self.username = username
        return result
        

    async def register(self, username, password):
        await send(self.writer, {
            "type": "register",
            "username": username,
            "password": password
        })

        result = await receive(self.reader)
        return result

    async def listen_messages(self):

        while self.running:
            
            msg = await receive(self.reader)

            if msg is None:
                print("\nСоединение с сервером потеряно")
                self.running = False
                break

            msg_type = msg.get("type")

            if msg_type == "chat":
                sender = msg.get("from", "Unknown")
                text = msg.get("text", "")
                timestamp = msg.get("timestamp", "")

                if sender == "Система":
                        print(f"\n[{timestamp}] {text}")
                else:
                    print(f"\n[{timestamp}] {sender}: {text}")
                print(f"> ", end="", flush=True)

            elif msg_type == "online_users":
                    users = msg.get("users", [])
                    print(f"\nОнлайн пользователи ({len(users)}): {', '.join(users)}")
                    print(f"> ", end="", flush=True)
                
            elif msg_type == "error":
                error_msg = msg.get("message", "Неизвестная ошибка")
                print(f"\nОшибка: {error_msg}")
                print(f"> ", end="", flush=True)

    async def show_help(self):

        print("\n" + "="*50)
        print("Команды:")
        print("  /help     - Показать справку")
        print("  /online   - Показать онлайн пользователей")
        print("  /exit     - Выйти из чата")
        print("="*50 + "\n")

    async def get_online_users(self):
        try:
            await send(self.writer,{
                "type": "get_online"
            })
        except Exception as e:
            print(f"  Ошибка запроса: {e}")

    async def send_message(self, text):

        try:
            await send(self.writer,{
                "type" : "chat",
                "text": text
            })
            return True
        except Exception as e:
            print(f"  Ошибка отправки: {e}")
            return False

    async def run(self):

        if not await self.connect():
            return False

        while True:

            print("\n1. Войти")
            print("2. Зарегистрироваться")
            print("3. Выход")
            choice = input("\nВыберите действие (1-3): ").strip()

            if choice == "3":
                await self.disconnect()
                return
            
            if choice not in ("1", "2"):
                print("Неверный выбор")
                continue

            username = input("Имя пользователя: ").strip()
            password = input("Пароль: ").strip()

            if not username or not password:
                print("Имя пользователя и пароль обязательны")
                continue

            if choice == "2":
                result = await self.register(username, password)
                if result:
                    if result.get("ok"):
                        print(f"{result.get('message', 'Регистрация успешна!')}")
                        print("Теперь войдите в систему")
                    else:
                        print(f"{result.get('error', 'Ошибка регистрации')}")
                continue

            elif choice == "1":
                result = await self.login(username, password)
                if result:
                    if result.get("ok"):
                        print(f"{result.get('message', 'Вход выполнен!')}")
                        break
                    else:
                        print(f"{result.get('error', 'Ошибка входа')}")
                else:
                    print("Ошибка соединения")
            
        self.running = True
        listen_task = asyncio.create_task(self.listen_messages())
            
        loop = asyncio.get_running_loop()

        await self.show_help()

        while self.running:
            try:
                print("> ", end="", flush=True)
                text = await loop.run_in_executor(None, sys.stdin.readline)
                text = text.strip()

                if not text:
                    continue

                if text == "/help":
                    await self.show_help()

                elif text == "/exit":
                    print("\nДо свидания!")
                    await self.disconnect()
                    break
                elif text == "/online":
                    await self.get_online_users()
                else:
                    await self.send_message(text)

            except Exception as e:
                pass

        listen_task.cancel()
        try:
            await listen_task
        except asyncio.CancelledError:
            print(f"  Ошибка: {e}")
            

async def main():
    client = Client()
    await client.run()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n\nВыход...")
    except Exception as e:
        print(f"\n Критическая ошибка: {e}")