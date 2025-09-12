import sys
import threading
import time

from common.logger import setup_logger
from options import parse_args
from common.utils import monitor_resources

args = parse_args()
logger = setup_logger(is_client=args.client, debug=args.debug)


if args.client:
    from client import client

    client_instance = None

    try:
        logger.info("Starting client...")
        client_instance = client.RemoteDesktopClient(
            server_host=args.ip,
            server_port=args.port,
            use_ssl=args.ssl,
            cert_file=args.cert,
            fps=args.fps,
        )
        client_instance.run()
    except KeyboardInterrupt:
        logger.info("Client stopped by user")
        if client_instance:
            client_instance.shutdown()
    except Exception as e:
        logger.error(f"Failed to start client: {e}")
        sys.exit(1)

elif args.server:
    from server.server import Server

    server = None
    server_thread = None
    monitor_thread = None
    try:
        logger.info("Starting server...")
        server = Server(
            host=args.ip,
            port=args.port,
            cert_file=args.cert,
            key_file=args.key,
            use_ssl=args.ssl,
        )

        server_thread = threading.Thread(target=server.start, daemon=True)
        server_thread.start()

        def resource_monitor():
            while server and server.is_listening:
                cpu_usage, ram_usage = monitor_resources()
                if cpu_usage > 80 or ram_usage > 80:
                    logger.warning(
                        f"High resource usage detected - CPU: {cpu_usage}%, RAM: {ram_usage}%"
                    )
                else:
                    logger.debug(f"CPU Usage: {cpu_usage}%, RAM Usage: {ram_usage}%")

            logger.debug("Resource monitor stopped.")

        while not server.is_listening:
            time.sleep(0.1)

        monitor_thread = threading.Thread(target=resource_monitor, daemon=True)
        monitor_thread.start()

        while server_thread.is_alive():
            server_thread.join(timeout=0.5)

        monitor_thread.join()

    except KeyboardInterrupt:
        logger.info("Server stopped by user")
        if server:
            server.stop()
        if server_thread:
            server_thread.join(timeout=5)
        if monitor_thread:
            monitor_thread.join(timeout=5)

        sys.exit(0)
    except Exception as e:
        logger.error(f"Failed to start server: {e}")
        sys.exit(1)
