import sys

from loguru import logger


def configure_logging(service_name: str):
    # 1. Remove the default standard logger
    logger.remove()

    # 2. Add a beautiful console logger for Docker/Local development
    logger.add(
        sys.stdout,
        format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{extra[service]}</cyan> | <cyan>{name}</cyan>:<cyan>{function}</cyan> - <level>{message}</level>",
        colorize=True,
        level="INFO",
    )

    # 3. (Optional for later) Add a JSON logger for production log aggregators
    # logger.add(f"logs/{service_name}.json", serialize=True, rotation="10 MB")

    # Bind the service name so every log automatically knows where it came from
    return logger.bind(service=service_name)


# Export a pre-configured instance for this specific service
log = configure_logging("api-gateway")
