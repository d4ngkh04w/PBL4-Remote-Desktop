import sys
import threading
import time

from common.logger import setup_logger
from options import parse_args
from common.utils import get_resource_usage

args = parse_args()
logger = setup_logger(is_client=args.client, debug=args.debug)

banner = r"""
    ____                       __          ____            __   __            
   / __ \___  ____ ___  ____  / /____     / __ \___  _____/ /__/ /_____  ____ 
  / /_/ / _ \/ __ `__ \/ __ \/ __/ _ \   / / / / _ \/ ___/ //_/ __/ __ \/ __ \
 / _, _/  __/ / / / / / /_/ / /_/  __/  / /_/ /  __(__  ) ,< / /_/ /_/ / /_/ /
/_/ |_|\___/_/ /_/ /_/\____/\__/\___/  /_____/\___/____/_/|_|\__/\____/ .___/ 
                                                                     /_/      
                                                    Remote Desktop Application
"""

print(banner)

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
    stop_event = threading.Event()
    try:
        logger.info("Starting server...")
        server = Server(
            host=args.ip,
            port=args.port,
            cert_file=args.cert,
            key_file=args.key,
            use_ssl=args.ssl,
            max_clients=args.max_clients,
        )

        server_thread = threading.Thread(target=server.start, daemon=True)
        server_thread.start()

        last_cpu, last_ram = -1, -1

        def resource_monitor():
            global last_cpu, last_ram
            while not stop_event.is_set():
                cpu_usage, ram_usage = get_resource_usage()
                if cpu_usage > 80 or ram_usage > 80:
                    logger.warning(
                        f"High resource usage detected - CPU: {cpu_usage}%, RAM: {ram_usage}%"
                    )
                else:
                    if abs(cpu_usage - last_cpu) > 5 or abs(ram_usage - last_ram) > 5:
                        logger.debug(f"CPU Usage: {cpu_usage}%, RAM: {ram_usage}%")
                last_cpu, last_ram = cpu_usage, ram_usage
                stop_event.wait(timeout=10)

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
            stop_event.set()
            monitor_thread.join()
            logger.info("Resource monitor stopped")
        sys.exit(0)
    except Exception as e:
        logger.error(f"Failed to start server: {e}")
        sys.exit(1)
