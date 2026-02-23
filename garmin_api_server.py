from flask import Flask, Blueprint, request, jsonify

# Create Flask app
app = Flask(__name__)
garmin_bp = Blueprint('garmin', __name__)

@garmin_bp.route("/oauth/initiate", methods=["POST"])
def initiate_oauth():
    return jsonify({"message": "Initiate Garmin OAuth flow"}), 200

@garmin_bp.route("/oauth/callback", methods=["GET"])
def oauth_callback():
    return jsonify({"message": "Handle Garmin OAuth callback"}), 200

@garmin_bp.route("/webhook", methods=["POST"])
def webhook():
    return jsonify({"message": "Webhook received"}), 200

@garmin_bp.route("/user/<user_id>/sync/status", methods=["GET"])
def sync_status(user_id):
    return jsonify({
        "user_id": user_id,
        "last_sync": "2025-09-22T04:10:00Z",
        "missing_ranges": [
            {"start": "2025-09-21T10:00:00Z", "end": "2025-09-21T11:00:00Z"}
        ],
        "should_fallback": True
    }), 200

@garmin_bp.route("/user/<user_id>/sync/data/<datatype>", methods=["GET"])
def get_data(user_id, datatype):
    return jsonify({
        "user_id": user_id,
        "datatype": datatype,
        "data": []
    }), 200

@garmin_bp.route("/user/<user_id>/sync/fallback/upload", methods=["POST"])
def upload_fallback(user_id):
    return jsonify({"message": "Fallback data received", "user_id": user_id}), 200

@garmin_bp.route("/user/<user_id>/device/status", methods=["GET"])
def device_status(user_id):
    return jsonify({
        "user_id": user_id,
        "device": "Garmin Forerunner",
        "last_sync": "2025-09-22T04:10:00Z"
    }), 200

# Register blueprint under /api/garmin
app.register_blueprint(garmin_bp, url_prefix="/api/garmin")

# WSGI application object
application = app
