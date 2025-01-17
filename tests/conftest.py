import os
import sys

# Since the source code is encapsulated in a separate subfolder (src), we need to tell this to python otherwise the imports won't work
# We import modules with src.module in tests but in the module it imports other modules without the src prefix and that would fail in the test file
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../src')))