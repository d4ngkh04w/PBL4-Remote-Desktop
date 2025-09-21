import argparse


class CustomHelpFormatter(argparse.HelpFormatter):
    def _format_action_invocation(self, action):
        if not action.option_strings:
            return super()._format_action_invocation(action)

        parts = []
        parts.extend(action.option_strings)

        if action.nargs != 0:
            parts[-1] += " " + self._format_args(action, action.dest)

        return ", ".join(parts)


def get_parser():
    parser = argparse.ArgumentParser(
        description="Remote Desktop Application",
        formatter_class=CustomHelpFormatter,
    )

    mode_group = parser.add_mutually_exclusive_group(required=True)
    mode_group.add_argument(
        "-c", "--client", action="store_true", help="Start the client"
    )
    mode_group.add_argument(
        "-s", "--server", action="store_true", help="Start the server"
    )

    general = parser.add_argument_group("General Settings")
    general.add_argument("-d", "--debug", action="store_true", help="Debug mode")
    general.add_argument(
        "-i",
        "--ip",
        default="127.0.0.1",
        metavar="IP",
        help="Server IP address (default: 127.0.0.1)",
    )
    general.add_argument(
        "-p",
        "--port",
        type=int,
        default=5000,
        metavar="PORT",
        help="Port number (default: 5000)",
    )
    general.add_argument(
        "--fps",
        type=int,
        default=20,
        metavar="FPS",
        help="Screen sharing frame rate (client only, default: 20 FPS)",
    )
    general.add_argument(
        "-mc",
        "--max-clients",
        type=int,
        default=10,
        metavar="MAX_CLIENTS",
        help="Maximum number of concurrent clients (server only, default: 10)",
    )
    general.add_argument(
        "-st",
        "--session-timeout",
        type=int,
        default=3600,
        metavar="SECONDS",
        help="Session timeout duration in seconds (server only, default: 3600 seconds)",
    )

    security = parser.add_argument_group("Security Options")
    security.add_argument(
        "--ssl",
        action="store_true",
        help="Enable SSL/TLS encryption for communication (default: False)",
    )
    security.add_argument(
        "-crt",
        "--cert",
        type=str,
        default=None,
        metavar="CERT",
        help="Path to SSL certificate file (required if --ssl is set)",
    )
    security.add_argument(
        "-k",
        "--key",
        type=str,
        default=None,
        metavar="KEY",
        help="Path to SSL private key file (required if --ssl is set)",
    )

    return parser


def parse_args():
    return get_parser().parse_args()
