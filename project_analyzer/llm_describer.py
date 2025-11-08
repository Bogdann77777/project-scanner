import requests
import json
import logging
from typing import List, Dict, Any, Callable, Optional
from config import Config
import time

logger = logging.getLogger(__name__)


class FunctionDescriber:
    """Генерирует описания функций через LLM (OpenRouter API)"""

    def __init__(self, api_key: str = None, model: str = None):
        """Инициализация describer

        Args:
            api_key: OpenRouter API key (опционально, берется из Config)
            model: Модель LLM (опционально, берется из Config)
        """
        self.api_key = api_key or Config.OPENROUTER_API_KEY
        self.model = model or Config.LLM_MODEL
        self.base_url = Config.OPENROUTER_BASE_URL
        self.timeout = Config.LLM_TIMEOUT

    def _build_prompt(self, functions: List[Dict]) -> str:
        """Создает промпт для LLM с четкими инструкциями

        Args:
            functions: Список функций для описания

        Returns:
            Промпт в виде строки
        """
        prompt = """Ты - эксперт по анализу кода. Твоя задача - дать МАКСИМАЛЬНО ДЕТАЛЬНОЕ описание каждой функции на РУССКОМ языке.

КРИТИЧЕСКИ ВАЖНО: Описание должно быть настолько подробным, чтобы разработчик, который видит код первый раз, полностью понял:
1. ЧТО делает функция (её назначение в проекте)
2. КАК она это делает (пошаговая логика, алгоритм)
3. КАКИЕ конкретные данные принимает (типы, форматы, примеры значений)
4. ЧТО возвращает (тип результата, возможные варианты)
5. КАКИЕ другие функции/модули/библиотеки использует
6. КАКИЕ особые случаи или условия обрабатывает
7. КАКИЕ конкретные настройки/параметры/константы использует (с их значениями!)

ПРИМЕРЫ ХОРОШЕГО ОПИСАНИЯ:
- "Функция convert_text_to_speech преобразует текст в аудио. Она принимает строку text и словарь настроек settings. Внутри функция: 1) Очищает текст от специальных символов через regex r'[^\w\s]', 2) Разбивает на предложения по точкам, 3) Для каждого предложения вызывает TTS API с параметрами: voice='ru-RU-Wavenet-D', speed=1.2, pitch=0, 4) Склеивает аудио через pydub. Возвращает путь к итоговому MP3 файлу."

- "Функция filter_special_chars удаляет все знаки препинания из текста. Конкретно удаляет: . , ! ? ; : - ( ) [ ] { } ' \" / \ @ # $ % ^ & *. Использует метод str.translate() с таблицей маппинга. Возвращает очищенную строку в lowercase."

ФОРМАТ ОТВЕТА - чистый JSON массив (без markdown, без комментариев):
[
  {
    "name": "function_name",
    "description": "Детальное описание на русском языке..."
  }
]

Функции для анализа:
"""

        for i, func in enumerate(functions, 1):
            prompt += f"\n\n--- Функция {i} ---\n"
            prompt += f"Имя: {func['name']}\n"
            prompt += f"Файл: {func['file']}\n"
            prompt += f"Параметры: {func.get('params', [])}\n"
            if func.get('docstring'):
                prompt += f"Docstring: {func['docstring']}\n"
            prompt += f"Код:\n```python\n{func['code']}\n```\n"

        return prompt

    def _parse_response(self, response_text: str, functions: List[Dict]) -> List[Dict]:
        """Парсит JSON ответ от LLM и добавляет описания к функциям

        Args:
            response_text: Текст ответа от LLM
            functions: Список функций

        Returns:
            Функции с добавленным полем 'description'
        """
        try:
            # Убираем возможные markdown блоки
            clean_text = response_text.strip()
            if clean_text.startswith('```json'):
                clean_text = clean_text[7:]  # Убираем ```json
            if clean_text.startswith('```'):
                clean_text = clean_text[3:]  # Убираем ```
            if clean_text.endswith('```'):
                clean_text = clean_text[:-3]  # Убираем ```
            clean_text = clean_text.strip()
            
            # Пытаемся распарсить JSON
            descriptions = json.loads(clean_text)

            # Создаем словарь для быстрого поиска
            desc_map = {d['name']: d['description'] for d in descriptions}

            # Добавляем описания к функциям
            for func in functions:
                func['description'] = desc_map.get(
                    func['name'],
                    f"Функция {func['name']} (описание не предоставлено)"
                )

            return functions

        except json.JSONDecodeError as e:
            logger.error(f"    JSON parsing error: {e}")
            logger.error(f"    Raw response: {response_text[:500]}...")
            # Если LLM вернул не JSON, пытаемся извлечь текст
            for func in functions:
                func['description'] = f"Функция {func['name']} - ошибка парсинга JSON"
            return functions

    def describe_functions_batch(self, functions: List[Dict]) -> List[Dict]:
        """Генерирует описания для батча функций через LLM API

        Args:
            functions: Список функций (до MAX_FUNCTIONS_PER_BATCH)

        Returns:
            Функции с добавленным полем 'description'
        """
        logger.info(f"    Sending batch of {len(functions)} functions to LLM...")
        logger.info(f"    Model: {self.model}")
        logger.info(f"    Functions: {[f['name'] for f in functions]}")

        prompt = self._build_prompt(functions)
        logger.info(f"    Prompt length: {len(prompt)} chars")

        # Логируем частичный ключ для безопасности
        if len(self.api_key) > 24:
            logger.info(f"    API Key: {self.api_key[:20]}...{self.api_key[-4:]}")

        # НО отправляем ПОЛНЫЙ ключ
        headers = {
            'Authorization': f'Bearer {self.api_key}',
            'Content-Type': 'application/json',
            'HTTP-Referer': 'http://localhost:8000',  # Required by OpenRouter
        }

        data = {
            'model': self.model,
            'messages': [
                {'role': 'user', 'content': prompt}
            ],
            'temperature': 0.3,  # Низкая для точности
            'max_tokens': 4000  # Увеличил с 2000 для детальных описаний
        }

        try:
            logger.info(f"    Making API call to {self.base_url}/chat/completions")
            response = requests.post(
                f'{self.base_url}/chat/completions',
                headers=headers,
                json=data,
                timeout=self.timeout
            )

            logger.info(f"    Response status: {response.status_code}")
            response.raise_for_status()

            result = response.json()
            description_text = result['choices'][0]['message']['content']

            logger.info(f"    Response length: {len(description_text)} chars")
            logger.info(f"    Response preview: {description_text[:200]}...")

            parsed = self._parse_response(description_text, functions)
            logger.info(f"    ✓ Batch processed successfully ({len(parsed)} functions)")

            return parsed

        except requests.exceptions.Timeout:
            logger.error(f"    ✗ LLM API timeout after {self.timeout}s")
            for func in functions:
                func['description'] = f"Function {func['name']} (timeout)"
            return functions

        except requests.exceptions.HTTPError as e:
            logger.error(f"    ✗ LLM API HTTP error: {e}")
            logger.error(f"    Response text: {e.response.text}")
            for func in functions:
                func['description'] = f"Function {func['name']} (API error)"
            return functions

        except Exception as e:
            logger.error(f"    ✗ LLM error: {e}", exc_info=True)
            for func in functions:
                func['description'] = f"Function {func['name']} (error)"
            return functions

    def describe_all_functions(self, all_functions: List[Dict], progress_callback: Optional[Callable] = None) -> List[Dict]:
        """Обрабатывает ВСЕ функции проекта батчами

        Args:
            all_functions: Список всех функций проекта
            progress_callback: Callback для отчета о прогрессе (опционально)

        Returns:
            Все функции с описаниями
        """
        described = []
        total = len(all_functions)
        batch_size = Config.MAX_FUNCTIONS_PER_BATCH

        logger.info(f"  Processing {total} functions in batches of {batch_size}")
        num_batches = (total + batch_size - 1) // batch_size
        logger.info(f"  Total batches: {num_batches}")

        for batch_num, i in enumerate(range(0, total, batch_size), 1):
            batch = all_functions[i:i+batch_size]

            logger.info(f"  === Batch {batch_num}/{num_batches} ===")

            if progress_callback:
                progress = 60 + (i / total) * 30  # 60-90% общего прогресса
                progress_callback(f"Describing functions {i+1}-{min(i+batch_size, total)}...", progress)

            described_batch = self.describe_functions_batch(batch)
            described.extend(described_batch)

            logger.info(f"  Batch {batch_num} complete. Total described so far: {len(described)}/{total}")

            # Увеличенная задержка между батчами (rate limiting protection)
            if i + batch_size < total:
                logger.info(f"  Waiting 3s before next batch...")
                time.sleep(3)  # Увеличил с 1s до 3s

        logger.info(f"  All batches complete! Total functions described: {len(described)}")

        return described
