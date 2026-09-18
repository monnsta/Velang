import sys
import os

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
SERVER = os.path.join(ROOT, "server")
if str(SERVER) not in sys.path:
	sys.path.insert(0, str(SERVER))
