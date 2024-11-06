import logging

def setup_logging():
  # Clear existing handlers to avoid side effects 
  if logging.root.handlers:
    for handler in logging.root.handlers[:]:
      logging.root.removeHandler(handler)

  # Set the necessary root logger handler, later we can add more handlers here if needed
  logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')