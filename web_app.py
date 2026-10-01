#!/usr/bin/env python3
"""Entry point for the Grid Simulator web GUI.

Usage::

    python web_app.py              # http://127.0.0.1:5000
    python web_app.py --port 8080 --host 0.0.0.0
"""

from web.app import main


if __name__ == "__main__":
    main()
