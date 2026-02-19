"""
Pipeline Logging Configuration
==============================

Sets up structured logging for B2B outreach pipeline runs.
Logs go to both console and a file in the pipeline output directory.
"""

import logging
from pathlib import Path


def setup_pipeline_logging(output_dir: Path, level: int = logging.INFO) -> logging.Logger:
    """Configure logging for a pipeline run.

    Creates a logger named "b2b_outreach" with two handlers:
    - Console: shows log messages in the terminal
    - File: writes to {output_dir}/pipeline.log for audit

    Args:
        output_dir: Directory where pipeline.log will be created.
        level: Logging level (default: INFO).

    Returns:
        Configured logger instance.
    """
    logger = logging.getLogger("b2b_outreach")
    logger.setLevel(level)
    logger.handlers.clear()

    formatter = logging.Formatter(
        "%(asctime)s | %(name)s | %(levelname)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    )

    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)

    log_file = output_dir / "pipeline.log"
    file_handler = logging.FileHandler(log_file)
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)

    return logger
