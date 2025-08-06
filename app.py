#!/usr/bin/env python3
"""
Heroku-compatible webhook server for FastField to Asana
"""

import os
from production_webhook_server import app

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 8000))
    app.run(host='0.0.0.0', port=port)
