import sys

from common.logger import setup_logger
from options import parse_args

args = parse_args()

server = None
client_instance = None

logger = setup_logger(is_client=args.client, debug=args.debug)


if args.client:
    from client import client

    try:
        logger.info("Starting client...")
        client_instance = client.RemoteDesktopClient(
            server_host=args.ip,
            server_port=args.port,
            use_ssl=args.ssl,
            cert_file=args.cert,
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

    try:
        logger.info("Starting server...")
        server = Server(
            host=args.ip,
            port=args.port,
            cert_file=args.cert,
            key_file=args.key,
            use_ssl=args.ssl,
        )
        server.start()
        logger.info("Server started successfully")
    except KeyboardInterrupt:
        logger.info("Server stopped by user")
        if server:
            server.stop()
    except Exception as e:
        logger.error(f"Failed to start server: {e}")
        sys.exit(1)
