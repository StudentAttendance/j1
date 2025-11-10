from flask import Flask


def create_app() -> Flask:
    app = Flask(__name__)
    app.config.update(
        SECRET_KEY="change-me",
    )

    from .routes import bp as main_bp
    app.register_blueprint(main_bp)
    return app


