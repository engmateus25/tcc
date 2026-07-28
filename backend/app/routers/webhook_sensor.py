from app.routers.alerts import sensor_event_webhook
from fastapi import APIRouter

router = APIRouter()


router.add_api_route("/sensor-event", sensor_event_webhook, methods=["POST"])
