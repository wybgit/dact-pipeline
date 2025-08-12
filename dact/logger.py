import sys
import os
from rich.console import Console
from rich.logging import RichHandler
from rich.text import Text
import logging

# Ensure proper UTF-8 encoding for console output
if sys.platform.startswith('win'):
    # Windows specific encoding setup
    os.environ['PYTHONIOENCODING'] = 'utf-8'
    sys.stdout.reconfigure(encoding='utf-8')
    sys.stderr.reconfigure(encoding='utf-8')

# Create console with explicit UTF-8 support
console = Console(
    force_terminal=True,
    width=None,
    legacy_windows=False,
    file=sys.stdout
)

# Create a custom RichHandler with better Chinese character support
class ChineseRichHandler(RichHandler):
    """Enhanced RichHandler with better Chinese character support."""
    
    def __init__(self, *args, **kwargs):
        # Ensure console uses UTF-8 encoding
        if 'console' not in kwargs:
            kwargs['console'] = console
        super().__init__(*args, **kwargs)
    
    def emit(self, record):
        """Override emit to handle Chinese characters properly."""
        try:
            # Ensure the message is properly encoded
            if hasattr(record, 'msg') and isinstance(record.msg, str):
                # Create Rich Text object to handle Chinese characters properly
                record.msg = Text.from_markup(record.msg, emoji=False)
            super().emit(record)
        except Exception:
            # Fallback to standard handling if Rich formatting fails
            self.handleError(record)

# Configure the root logger with enhanced Chinese support
logging.basicConfig(
    level="INFO",
    format="%(message)s",
    datefmt="[%X]",
    handlers=[ChineseRichHandler(
        rich_tracebacks=True, 
        markup=True,
        show_path=False,
        enable_link_path=False
    )],
    force=True
)

# Get the logger instance
log = logging.getLogger("dact")

# Set encoding for file handlers if needed
def setup_file_logging(log_file_path: str, level: str = "DEBUG"):
    """Setup file logging with proper UTF-8 encoding."""
    file_handler = logging.FileHandler(log_file_path, encoding='utf-8')
    file_formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    file_handler.setFormatter(file_formatter)
    file_handler.setLevel(getattr(logging, level.upper()))
    log.addHandler(file_handler)
    return file_handler

# Enhanced logging functions with Chinese support
def log_chinese_safe(level: str, message: str, **kwargs):
    """Log message with Chinese character safety."""
    try:
        # Use Rich Text to ensure proper rendering
        rich_message = Text(message, style=kwargs.get('style'))
        getattr(log, level.lower())(rich_message)
    except Exception:
        # Fallback to standard logging
        getattr(log, level.lower())(message)

# Convenience functions
def info_chinese(message: str, style: str = None):
    """Log info message with Chinese support."""
    log_chinese_safe("INFO", message, style=style)

def error_chinese(message: str, style: str = "red"):
    """Log error message with Chinese support."""
    log_chinese_safe("ERROR", message, style=style)

def warning_chinese(message: str, style: str = "yellow"):
    """Log warning message with Chinese support."""
    log_chinese_safe("WARNING", message, style=style)

def debug_chinese(message: str, style: str = "dim"):
    """Log debug message with Chinese support."""
    log_chinese_safe("DEBUG", message, style=style)
