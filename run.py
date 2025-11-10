from webapp import create_app
from webapp.db import init_db


app = create_app()

# Initialize DB at startup (Flask 3 removed before_first_request)
with app.app_context():
    init_db()


if __name__ == "__main__":
    app.run(debug=True, use_reloader=False)


