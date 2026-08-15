# -*- coding: utf-8 -*-
"""
AI Assistant — ёрдамчии AI барои омӯзиши забони русӣ.

Ин модул тамоми мантиқи муоширатро бо провайдери AI дар бар мегирад ва
frontend ҳаргиз бевосита бо API-и AI кор намекунад — ҳама чиз тавассути
backend (эндпоинти /api/ai/chat) мегузарад, то калиди махфӣ ошкор нашавад.

Барои пайваст кардани AI воқеӣ:
  1. Файли ".env.example"-ро нусхабардорӣ карда, номи онро ".env" гузоред.
  2. AI_PROVIDER-ро "groq", "openai" ё "anthropic" гузоред ва AI_API_KEY-ро пур кунед.
  3. Серверро аз нав оғоз кунед — frontend ҳеҷ тағйирот лозим надорад.

То даме ки AI_API_KEY холӣ аст, ассистент дар "реҷаи демо" кор мекунад: барои
дархостҳои оддии тарҷума аз луғати маҳаллии курс (data/words.json) ҷавоб
медиҳад, дар дигар ҳолатҳо паёми равшан медиҳад, ки AI ҳанӯз пайваст нашудааст.
"""
import json
import urllib.error
import urllib.request

from config import AI_API_KEY, AI_MODEL, AI_PROVIDER, WORDS_JSON_PATH

MAX_HISTORY_TURNS = 8
MAX_MESSAGE_CHARS = 4000
REQUEST_TIMEOUT = 25

SYSTEM_PROMPT = (
    "Ту як AI-ёрдамчии дӯстона барои омӯзиши забони русӣ дар платформаи "
    "таълимии \"1300 Луғат\" ҳастӣ. Корбаронат тоҷикзабонҳое ҳастанд, ки "
    "забони русиро ҳамчун забони хориҷӣ меомӯзанд.\n\n"
    "Қоидаҳо:\n"
    "- Ҳамеша бо забони тоҷикӣ ҷавоб деҳ (ба ғайр аз худи калима/ҷумлаҳои "
    "русӣ, ки шарҳ медиҳӣ ё тарҷума мекунӣ).\n"
    "- Ҷавобҳоят равшан, мухтасар ва барои омӯзандаи оддӣ фаҳмо бошанд.\n"
    "- Ҳангоми фаҳмонидани калима: маънои он ва як мисоли истифодаро деҳ.\n"
    "- Ҳангоми сохтани ҷумла: ҷумлаи русӣ бо тарҷумаи тоҷикиаш деҳ.\n"
    "- Ҳангоми сохтани тест ё саволҳо: саволҳои чандинтанхобӣ (а, б, в, г) "
    "бо ҷавоби дуруст дар охир деҳ.\n"
    "- Агар дар паём контексти калимаи мушаххас омада бошад, ҷавобатро ба "
    "ҳамон калима алоқаманд кун.\n"
    "- Аз ҷавобҳои хеле дарозу пур аз матн худдорӣ кун."
)


def _load_words():
    try:
        with open(WORDS_JSON_PATH, encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return []


def _local_translate(term: str):
    term = (term or "").strip().lower()
    if not term:
        return None
    for w in _load_words():
        if w.get("ru", "").lower() == term or w.get("tj", "").lower() == term:
            return w
    return None


def _demo_reply(user_message: str, context_word) -> str:
    """Used while no real AI provider is configured yet, so the feature is
    still useful (and the whole flow can be tested end-to-end)."""
    lower = (user_message or "").lower()

    if context_word and context_word.get("ru"):
        ru = context_word["ru"]
        tj = (context_word.get("tj") or "").strip()

        if "тарҷум" in lower:
            return f"📘 «{ru}» бо тоҷикӣ маънояш «{tj}» аст." if tj else \
                f"Мутаассифона, тарҷумаи маҳаллии «{ru}» ёфт нашуд."

        if "ҷумла" in lower:
            return (
                f"📝 Намунаи ҷумла: «Я хорошо помню слово «{ru}».»\n"
                f"(Тарҷума: Ман калимаи «{tj}»-ро хуб дар ёд дорам.)\n\n"
                f"ℹ️ Ин намунаи демо аст. Барои ҷумлаҳои гуногун ва зинда, "
                f"AI-и воқеиро тавассути файли .env пайваст кунед."
            )

        if "тест" in lower or "савол" in lower:
            return (
                f"🧠 Саволи демо:\n«{ru}» бо тоҷикӣ чӣ маъно дорад?\n"
                f"а) {tj}\nб) ?\nв) ?\nг) ?\n\n"
                f"✅ Ҷавоби дуруст: а) {tj}\n\n"
                f"ℹ️ Барои тестҳои воқеӣ ва гуногуни AI, дар .env "
                f"AI_API_KEY-ро гузоред."
            )

        if "фарқ" in lower:
            return (
                "🔍 Барои муқоисаи ду калима лутфан ҳарду калимаро дар паём "
                "нависед. Дар реҷаи демо ман танҳо шарҳи оддии як калимаро "
                "медиҳам — барои таҳлили пурраи фарқият, AI-и воқеиро "
                "пайваст кунед."
            )

        return (
            f"🤖 Калимаи «{ru}»" + (f" маънояш «{tj}» аст." if tj else " ") +
            "\n\nАссистенти AI ҳоло дар реҷаи демо кор мекунад (провайдери "
            "воқеӣ пайваст нашудааст). Барои ҷавобҳои пурра ва зинда, дар "
            "файли .env қиматҳои AI_PROVIDER ва AI_API_KEY-ро танзим кунед."
        )

    found = _local_translate(user_message)
    if found:
        return (
            f"📘 «{found['ru']}» → «{found['tj']}» "
            f"(Дарси {found['lesson']}: {found['lesson_title']})"
        )

    return (
        "🤖 Салом! Ман ассистенти AI-и «1300 Луғат» ҳастам.\n\n"
        "Ҳоло ман дар реҷаи демо кор мекунам, зеро провайдери AI ҳанӯз "
        "пайваст нашудааст. Барои фаъол кардани ҷавобҳои пурраи AI, дар "
        "файли .env (нигаред ба .env.example) қиматҳои AI_PROVIDER ва "
        "AI_API_KEY-ро танзим кунед ва серверро аз нав оғоз кунед.\n\n"
        "Дар ин ҳол ҳам метавонам калимаҳои дарсҳоро аз луғати маҳаллӣ "
        "тарҷума кунам — танҳо калимаи русӣ ё тоҷикиро нависед."
    )


def _build_messages(user_message: str, context_word, history):
    messages = [{"role": "system", "content": SYSTEM_PROMPT}]

    for turn in (history or [])[-MAX_HISTORY_TURNS:]:
        role = "assistant" if turn.get("role") == "assistant" else "user"
        content = (turn.get("content") or "").strip()
        if content:
            messages.append({"role": role, "content": content[:MAX_MESSAGE_CHARS]})

    user_content = user_message.strip()
    if context_word and context_word.get("ru"):
        ctx = f"[Контексти дарс — калимаи русӣ: «{context_word['ru']}»"
        if context_word.get("tj"):
            ctx += f", тарҷумаи тоҷикӣ: «{context_word['tj']}»"
        ctx += "]\n"
        user_content = ctx + user_content

    messages.append({"role": "user", "content": user_content[:MAX_MESSAGE_CHARS]})
    return messages


def _call_openai_compatible(url, model_default, messages):
    """Shared by any provider that speaks the OpenAI chat-completions format
    (OpenAI itself, Groq, and other compatible APIs)."""
    payload = json.dumps({
        "model": AI_MODEL or model_default,
        "messages": messages,
        "temperature": 0.6,
        "max_tokens": 700,
    }).encode("utf-8")
    req = urllib.request.Request(url, data=payload, method="POST", headers={
        "Content-Type": "application/json",
        "Authorization": f"Bearer {AI_API_KEY}",
    })
    with urllib.request.urlopen(req, timeout=REQUEST_TIMEOUT) as resp:
        data = json.loads(resp.read().decode("utf-8"))
    return data["choices"][0]["message"]["content"].strip()


def _call_openai(messages):
    return _call_openai_compatible(
        "https://api.openai.com/v1/chat/completions", "gpt-4o-mini", messages,
    )


def _call_groq(messages):
    return _call_openai_compatible(
        "https://api.groq.com/openai/v1/chat/completions",
        "llama-3.3-70b-versatile",
        messages,
    )


def _call_anthropic(messages):
    url = "https://api.anthropic.com/v1/messages"
    system = ""
    conv = []
    for m in messages:
        if m["role"] == "system":
            system = m["content"]
        else:
            conv.append(m)
    payload = json.dumps({
        "model": AI_MODEL or "claude-3-5-haiku-20241022",
        "system": system,
        "messages": conv,
        "max_tokens": 700,
    }).encode("utf-8")
    req = urllib.request.Request(url, data=payload, method="POST", headers={
        "Content-Type": "application/json",
        "x-api-key": AI_API_KEY,
        "anthropic-version": "2023-06-01",
    })
    with urllib.request.urlopen(req, timeout=REQUEST_TIMEOUT) as resp:
        data = json.loads(resp.read().decode("utf-8"))
    parts = data.get("content", [])
    return "".join(p.get("text", "") for p in parts if p.get("type") == "text").strip()


SUPPORTED_PROVIDERS = ("openai", "anthropic", "groq")


def get_ai_reply(user_message: str, context_word=None, history=None):
    """Returns (reply_text, error_code). Exactly one of them is truthy."""
    user_message = (user_message or "").strip()
    if not user_message:
        return None, "empty"

    if AI_PROVIDER not in SUPPORTED_PROVIDERS or not AI_API_KEY:
        return _demo_reply(user_message, context_word), None

    messages = _build_messages(user_message, context_word, history)
    try:
        if AI_PROVIDER == "openai":
            reply = _call_openai(messages)
        elif AI_PROVIDER == "groq":
            reply = _call_groq(messages)
        else:
            reply = _call_anthropic(messages)
        if not reply:
            return None, "empty_response"
        return reply, None
    except urllib.error.HTTPError as e:
        return None, f"provider_http_{e.code}"
    except urllib.error.URLError:
        return None, "network"
    except (KeyError, IndexError, ValueError):
        return None, "bad_response"
    except Exception:
        return None, "unknown"
