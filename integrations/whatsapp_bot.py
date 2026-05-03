"""
integrations/whatsapp_bot.py — WhatsApp webhook bot for Sara AI.

This is for inbound WhatsApp messages. It requires a provider that can
POST webhook events to this app, such as Twilio WhatsApp Sandbox or a
WhatsApp Cloud API setup that forwards incoming messages here.
"""

import logging
import os
import threading

from dotenv import load_dotenv
from flask import Flask, request

from agent.agent_loop import process_turn

try:
	from twilio.twiml.messaging_response import MessagingResponse
except ImportError:  # pragma: no cover - dependency issue is surfaced at runtime
	MessagingResponse = None


logger = logging.getLogger(__name__)
load_dotenv()


def create_whatsapp_app() -> Flask:
	app = Flask(__name__)

	@app.get("/")
	def health_check():
		return {"status": "ok", "service": "whatsapp-bot"}

	@app.post("/whatsapp")
	def whatsapp_webhook():
		if MessagingResponse is None:
			return "twilio package is not installed", 500

		from_number = request.form.get("From", "")
		body = (request.form.get("Body", "") or "").strip()

		if not body:
			response = MessagingResponse()
			response.message("Send a text message and I’ll reply.")
			return str(response)

		user_id = f"whatsapp_{from_number or 'unknown'}"
		try:
			reply_text = process_turn(user_id, body, channel="whatsapp").render_text()
		except Exception as exc:
			logger.exception("WhatsApp processing failed: %s", exc)
			reply_text = "⚠️ Sorry, I hit an error while processing that."

		response = MessagingResponse()
		response.message(reply_text)
		return str(response)

	return app


def start_whatsapp_bot() -> None:
	"""Start a local webhook server for WhatsApp inbound messages."""
	host = os.getenv("WHATSAPP_WEBHOOK_HOST", "0.0.0.0")
	port = int(os.getenv("WHATSAPP_WEBHOOK_PORT", "5005"))
	app = create_whatsapp_app()
	app.run(host=host, port=port, debug=False, use_reloader=False)


def run_whatsapp_bot_in_thread() -> threading.Thread:
	thread = threading.Thread(target=start_whatsapp_bot, daemon=True, name="whatsapp-bot")
	thread.start()
	return thread
