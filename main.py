import os

from app import app  # noqa: F401
from dotenv import load_dotenv
load_dotenv()

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=os.environ.get("PORT", 3000), debug=True)
