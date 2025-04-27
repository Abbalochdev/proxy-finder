import logging
from rich.logging import RichHandler

def setup_logging(log_level: int = logging.INFO) -> logging.Logger:
    """
    Set up a rich-formatted logger.
    
    Args:
        log_level (int): Logging level. Defaults to logging.INFO.
    
    Returns:
        logging.Logger: Configured logger instance.
    """
    logging.basicConfig(
        level=log_level,
        format='%(message)s',
        datefmt='[%X]',
        handlers=[RichHandler(rich_tracebacks=True)]
    )
    
    return logging.getLogger('proxy_finder')
