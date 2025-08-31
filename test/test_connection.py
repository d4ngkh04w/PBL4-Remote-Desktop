import sys
import time

from common.logger import logger


if len(sys.argv) > 1 and sys.argv[1] == "--client":
    from client.network import network_client

    client_instance = None
    try:
        logger.info("Starting client...")
        client_instance = network_client.NetworkClient()
        client_instance.connect()
        logger.info("Client started successfully")
        while client_instance.running:
            time.sleep(1)
    except KeyboardInterrupt:
        logger.info("Client stopped by user")
        if client_instance:
            client_instance.disconnect()

elif len(sys.argv) > 1 and sys.argv[1] == "--server":
    from common.database import db
    from server.listener import Listener

    listener = None
    try:
        logger.info("Starting server...")
        listener = Listener()
        listener.start()
        logger.info("Server started successfully")
    except KeyboardInterrupt:
        logger.info("Server stopped by user")
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
