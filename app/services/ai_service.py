import os
import anthropic

_PROMPT_PATH = os.path.join(os.path.dirname(__file__), '..', 'prompts', 'server-audit-agent-prompt-v2.md')


def _load_system_prompt():
    with open(_PROMPT_PATH, 'r', encoding='utf-8') as f:
        return f.read()


def _get_anthropic_key():
    from app.models import Settings
    from app.services.crypto import decrypt_data
    encrypted = Settings.get('anthropic_api_key')
    if encrypted:
        try:
            return decrypt_data(encrypted)
        except Exception:
            pass
    return os.environ.get('ANTHROPIC_API_KEY')


def _get_gemini_key():
    from app.models import Settings
    from app.services.crypto import decrypt_data
    encrypted = Settings.get('gemini_api_key')
    if encrypted:
        try:
            return decrypt_data(encrypted)
        except Exception:
            pass
    return None


def analyze_report(report_content):
    """Send report content to AI for security audit analysis.
    Uses preferred provider from settings, falls back to available one.
    Returns (analysis_text, success_bool).
    """
    from app.models import Settings
    provider = Settings.get('ai_provider') or 'anthropic'

    if provider == 'gemini':
        return _analyze_with_gemini(report_content)
    return _analyze_with_anthropic(report_content)


def _analyze_with_anthropic(report_content):
    api_key = _get_anthropic_key()
    if not api_key:
        return 'Brak klucza Anthropic API. Skonfiguruj go w Ustawieniach.', False

    try:
        system_prompt = _load_system_prompt()
        from app.models import Settings
        model_name = Settings.get('anthropic_model') or 'claude-opus-4-6'
        client = anthropic.Anthropic(api_key=api_key)
        message = client.messages.create(
            model=model_name,
            max_tokens=8096,
            system=system_prompt,
            messages=[{'role': 'user', 'content': report_content}]
        )
        return message.content[0].text, True
    except Exception as e:
        return f'Błąd podczas analizy (Anthropic): {str(e)}', False


def _analyze_with_gemini(report_content):
    api_key = _get_gemini_key()
    if not api_key:
        return 'Brak klucza Gemini API. Skonfiguruj go w Ustawieniach.', False

    try:
        import google.generativeai as genai
        system_prompt = _load_system_prompt()
        from app.models import Settings
        model_name = Settings.get('gemini_model') or 'gemini-2.0-flash'
        genai.configure(api_key=api_key)
        model = genai.GenerativeModel(
            model_name=model_name,
            system_instruction=system_prompt
        )
        response = model.generate_content(report_content)
        return response.text, True
    except Exception as e:
        return f'Błąd podczas analizy (Gemini): {str(e)}', False
