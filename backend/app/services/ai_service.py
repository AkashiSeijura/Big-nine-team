import json
import logging
from groq import AsyncGroq
from app.config import settings

logger = logging.getLogger(__name__)

# Initialize the Groq client
# Ensure that GROQ_API_KEY is present in the environment or config
try:
    groq_client = AsyncGroq(api_key=settings.GROQ_API_KEY)
except Exception as e:
    logger.error(f"Failed to initialize Groq client: {e}")
    groq_client = None

async def analyze_ticket_with_ai(ticket_text: str) -> dict:
    """
    Analyzes a support ticket using Llama 3.3 via Groq API.
    Returns a dictionary with:
      - sentiment (positive, neutral, negative)
      - category (string)
      - draft_response (string)
      - confidence (float)
    """
    if not groq_client:
        logger.error("Groq client not initialized, returning fallback data")
        return {
            "sentiment": "neutral",
            "category": "other",
            "full_name": None,
            "company": None,
            "phone": None,
            "device_serials": [],
            "device_type": None,
            "summary": None,
            "draft_response": "Извините, в данный момент ИИ-помощник недоступен.",
            "confidence": 0.0,
        }

    system_prompt = """
Вы — ИИ-агент технической поддержки компании ЭРИС (производитель газоаналитического оборудования).
Ваша задача — проанализировать входящее обращение клиента и извлечь из него структурированную информацию.

Правила определения типа прибора по заводскому номеру (9 цифр):
- Первые три цифры — код модели. Примеры: 230 → «ДГС ЭРИС-230», 124 → «ДГС ЭРИС-124».
- Если тип прибора явно указан в тексте — используйте его. Если нет — определяйте по первым трём цифрам серийного номера.

Ответьте ТОЛЬКО в формате JSON со следующими ключами (все строки на русском, null если информация отсутствует):
- "sentiment": "positive" | "neutral" | "negative" — эмоциональная тональность обращения
- "category": "malfunction" | "calibration" | "documentation" | "other" — категория запроса
- "full_name": строка или null — ФИО отправителя
- "company": строка или null — название организации / объекта / предприятия
- "phone": строка или null — номер телефона
- "device_serials": массив строк — все найденные заводские номера приборов (9-значные числа), пустой массив если не найдены
- "device_type": строка или null — тип(ы) прибора (определить по серийному номеру или из текста)
- "summary": строка — краткое изложение сути обращения (1-3 предложения)
- "draft_response": строка — подробный, вежливый ответ клиенту на русском языке
- "confidence": число от 0.0 до 1.0 — уверенность в ответе
"""

    try:
        response = await groq_client.chat.completions.create(
            messages=[
                {
                    "role": "system",
                    "content": system_prompt
                },
                {
                    "role": "user",
                    "content": ticket_text
                }
            ],
            model="llama-3.3-70b-versatile",
            temperature=0.3,
            max_tokens=1024,
            response_format={"type": "json_object"}
        )

        content = response.choices[0].message.content
        result = json.loads(content)
        
        # Validation/Normalization
        sentiment = result.get("sentiment", "neutral").lower()
        if sentiment not in ["positive", "neutral", "negative"]:
            sentiment = "neutral"

        category = result.get("category", "other").lower()
        if category not in ["malfunction", "calibration", "documentation", "other"]:
            category = "other"

        device_serials = result.get("device_serials", [])
        if not isinstance(device_serials, list):
            device_serials = []

        return {
            "sentiment": sentiment,
            "category": category,
            "full_name": result.get("full_name") or None,
            "company": result.get("company") or None,
            "phone": result.get("phone") or None,
            "device_serials": [str(s) for s in device_serials],
            "device_type": result.get("device_type") or None,
            "summary": result.get("summary") or None,
            "draft_response": result.get("draft_response", ""),
            "confidence": float(result.get("confidence", 1.0)),
        }
        
    except Exception as e:
        logger.error(f"Error during AI analysis: {e}")
        return {
            "sentiment": "neutral",
            "category": "other",
            "full_name": None,
            "company": None,
            "phone": None,
            "device_serials": [],
            "device_type": None,
            "summary": None,
            "draft_response": "Извините, произошла ошибка при генерации ответа.",
            "confidence": 0.0,
        }


async def generate_chat_reply(ticket_context: str, chat_history: list[dict]) -> str:
    """Generate a contextual AI reply for the chat window."""
    if not groq_client:
        return "ИИ-помощник временно недоступен."

    system_prompt = (
        "Вы — ИИ-агент технической поддержки компании ЭРИС (газоаналитическое оборудование). "
        "Вы ведёте диалог с оператором службы поддержки, помогая разобраться в обращении клиента. "
        "Отвечайте кратко и по существу на русском языке. "
        "Если не знаете точного ответа — скажите об этом и предложите варианты.\n\n"
        f"Контекст заявки:\n{ticket_context}"
    )

    messages = [{"role": "system", "content": system_prompt}]
    for m in chat_history:
        role = "assistant" if m["role"] == "bot" else "user"
        messages.append({"role": role, "content": m["text"]})

    try:
        response = await groq_client.chat.completions.create(
            messages=messages,
            model="llama-3.3-70b-versatile",
            temperature=0.5,
            max_tokens=512,
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        logger.error(f"Chat reply generation error: {e}")
        return "Извините, не удалось сгенерировать ответ."
