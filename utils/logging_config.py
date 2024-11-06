import logging

def setup_logging():
  console_handler = logging.StreamHandler()
  console_handler.setLevel(logging.INFO)
  logging.getLogger().addHandler(console_handler)