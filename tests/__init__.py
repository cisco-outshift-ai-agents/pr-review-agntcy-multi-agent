import os
import sys
from dotenv import load_dotenv

load_dotenv()

os.environ["TESTENV"] = "true"

# Since the source code is encapsulated in a separate subfolder (src), we need to tell this to python otherwise the imports won't work
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../src")))
