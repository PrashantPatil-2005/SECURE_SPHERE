"""
SecuriSphere — shared Flask extension instances
===============================================
Extensions are constructed here without an app and bound later via
``init_app(app)`` in ``app.py``. This lets blueprints import the live
``socketio`` instance (e.g. to emit realtime events) without importing
``app.py`` and creating a circular dependency.
"""

from flask_socketio import SocketIO

# Bound to the Flask app in app.py via socketio.init_app(app, ...).
socketio = SocketIO()
