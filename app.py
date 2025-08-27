from utils.logger import logger
from utils.config import NetworkConfig

logger.info("Starting Remote Desktop Application")
logger.info(
    f"Server will run on {NetworkConfig.SERVER_HOST}:{NetworkConfig.SERVER_PORT}"
)
