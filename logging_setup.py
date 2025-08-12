# logging_setup.py

import logging
import logging.config
import json
import os
from datetime import datetime
import collections

class BufferingHandler(logging.Handler):
    """
    A custom logging handler that keeps a buffer of the last N log records.
    It is used to provide context during a critical failure.
    """
    def __init__(self, maxlen=200):
        super().__init__()
        self.buffer = collections.deque(maxlen=maxlen)

    def emit(self, record):
        """Append the formatted record to the buffer."""
        self.buffer.append(self.format(record))

    def get_buffer_lines(self):
        """Return the buffered lines as a list of strings."""
        return list(self.buffer)

class ContextFilter(logging.Filter):
    """
    A custom filter to inject contextual information like run_id, seed, and tick
    into every log record.
    """
    def __init__(self, run_id, seed):
        super().__init__()
        self.run_id = run_id
        self.seed = seed
        self.tick = -1  # Default tick before the main loop starts

    def filter(self, record):
        record.run_id = self.run_id
        record.seed = self.seed
        record.tick = self.tick
        return True

def setup_logging(config_path='config.json'):
    """
    Sets up the logging configuration for the entire application.
    
    - Creates a unique directory for the current run.
    - Loads logging configuration from a JSON file.
    - Injects a custom filter to add context (run_id, seed, tick) to all logs.
    - Returns the filter instance so the main loop can update the tick.
    """
    with open(config_path, 'r') as f:
        config = json.load(f)

    # 1. Create a unique directory for this run's logs and outputs
    run_id = datetime.now().strftime('%Y-%m-%d_%H-%M-%S')
    run_dir = os.path.join("runs", run_id)
    os.makedirs(run_dir, exist_ok=True)

    # 2. Get logging config and update the filename with the unique path
    log_config = config['logging']
    log_filename = os.path.join(run_dir, 'simulation.log')
    log_config['handlers']['file']['filename'] = log_filename
    
    # 3. Configure the logging system
    logging.config.dictConfig(log_config)

    # 4. Create and add the custom context filter to all handlers
    seed = config.get('seed', 'N/A')
    context_filter = ContextFilter(run_id=run_id, seed=seed)
    
    # 5. Create and configure the buffering handler for crash context
    buffering_handler = BufferingHandler()
    buffering_handler.setLevel(logging.DEBUG)
    # Use the same detailed formatter for the buffer
    buffering_handler.setFormatter(logging.Formatter(log_config['formatters']['detailed']['format']))

    # 6. Add the custom context filter and the new buffer handler to the root logger
    root_logger = logging.getLogger()
    root_logger.addHandler(buffering_handler)
    for handler in root_logger.handlers:
        handler.addFilter(context_filter)

    logging.info("Logging configured. Log files will be saved to: %s", run_dir)
    
    return context_filter, run_dir, buffering_handler