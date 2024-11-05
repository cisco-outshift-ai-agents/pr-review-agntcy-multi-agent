import logging

import google.cloud.logging


def setup_logging():
  client = google.cloud.logging.Client()
  client.setup_logging()
  console_handler = logging.StreamHandler()
  console_handler.setLevel(logging.INFO)
  logging.getLogger().addHandler(console_handler)