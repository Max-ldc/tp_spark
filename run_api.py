#!/usr/bin/env python3
"""
Script de démarrage de l'API avec logging.
"""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

try:
    from api.main import app
    import uvicorn
    
    print("Starting API on http://127.0.0.1:8000...")
    uvicorn.run(app, host='127.0.0.1', port=8000, log_level='info')
    
except Exception as e:
    print(f"Error: {type(e).__name__}: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)
