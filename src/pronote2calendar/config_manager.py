import json
import logging

logger = logging.getLogger(__name__)

def read_config(config_file_path='config.json'):
    logger.debug("Reading configuration from %s", config_file_path)
    with open(config_file_path, 'r') as file:
        config = json.load(file)
    logger.debug("Loaded configuration keys: %s", list(config.keys()))
    return config
