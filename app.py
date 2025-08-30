from server.listener import Listener
from client.connection import Connection
from common.logger import logger
from client import client
import sys


if len(sys.argv) > 1 and sys.argv[1] == "--client":
    conn = None
    try:
        logger.info("Starting client...")
        client_instance = client.RemoteDesktopClient()
        client_instance.run()
        
        logger.info("Client started successfully")
    except KeyboardInterrupt:
        logger.info("Client stopped by user")
        if client_instance:
            client_instance.shutdown()
    except Exception as e:
        logger.error(f"Failed to start client: {e}")
        sys.exit(1)
elif len(sys.argv) > 1 and sys.argv[1] == "--server":
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
