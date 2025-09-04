import sys
import threading
import time


from common.logger import logger

stop_event = threading.Event()


def show_all_clients():
    previous_clients = {}
    while not stop_event.is_set():
        clients = ClientManager.get_all_clients() or {}

        if clients != previous_clients:
            if not clients:
                continue
            else:
                print("\nConnected Clients:")
                for client_id, info in clients.items():
                    ip = info.get("ip")
                    status = info.get("status")
                    print(f"- ID: {client_id}, IP: {ip}, Status: {status}")

            previous_clients = clients.copy()

        time.sleep(1)


if len(sys.argv) > 1 and sys.argv[1] == "--client":
    from client import client

    client_instance = None
    try:
        logger.info("Starting client...")
        client_instance = client.RemoteDesktopClient()
        client_instance.run()
    except KeyboardInterrupt:
        logger.info("Client stopped by user")
        if client_instance:
            client_instance.shutdown()
    except Exception as e:
        logger.error(f"Failed to start client: {e}")
        sys.exit(1)
elif len(sys.argv) > 1 and sys.argv[1] == "--server":
    from server.server import Server
    from server.client_manager import ClientManager

    listener = None
    try:
        t = threading.Thread(target=show_all_clients, daemon=True)
        t.start()
        logger.info("Starting server...")
        listener = Server()
        listener.start()
        logger.info("Server started successfully")

    except KeyboardInterrupt:
        logger.info("Server stopped by user")
        stop_event.set()
        if listener:
            listener.stop()
    except Exception as e:
        logger.error(f"Failed to start server: {e}")
        sys.exit(1)
elif len(sys.argv) > 1 and sys.argv[1] == "--help":
    print("Usage:")
    print("  --client   Start the client")
    print("  --server   Start the server")
else:
    print("Invalid argument. Use --help for usage information.")
