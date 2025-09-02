#!/usr/bin/env python3
"""
Cache busting script to force Replit preview refresh
"""
import os
import time
from flask import Flask, redirect, url_for

# Import our main app
from main import app

@app.route('/force-refresh')
def force_refresh():
    """Force a complete cache refresh"""
    return f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="UTF-8">
        <meta http-equiv="Cache-Control" content="no-cache, no-store, must-revalidate">
        <meta http-equiv="Pragma" content="no-cache">
        <meta http-equiv="Expires" content="0">
        <title>Cache Refresh - {time.time()}</title>
        <script>
            setTimeout(function() {{
                window.location.href = '/login?t={time.time()}';
            }}, 2000);
        </script>
    </head>
    <body style="font-family: Arial, sans-serif; text-align: center; padding: 50px;">
        <h1>🔄 Refreshing Preview Cache</h1>
        <p>Timestamp: {time.time()}</p>
        <p>Redirecting to login page...</p>
        <p><a href="/login?t={time.time()}">Click here if not redirected automatically</a></p>
    </body>
    </html>
    """

if __name__ == '__main__':
    print(f"Cache buster ready! Visit /force-refresh at {time.time()}")