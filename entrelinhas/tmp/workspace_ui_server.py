"""Isolated UI QA. Uses generated examples; never touches the user's jobs."""
import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import server
server.DATA=server.ROOT/'.runtime'/'workspace-ui-qa'/'jobs'
server.DATA.mkdir(parents=True,exist_ok=True)
http=server.ThreadingHTTPServer(('127.0.0.1',8766),server.Handler)
print('UI QA: http://127.0.0.1:8766',flush=True)
try:http.serve_forever()
except KeyboardInterrupt:pass
finally:http.server_close()
