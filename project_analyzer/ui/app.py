from flask import Flask, render_template, request, jsonify, send_from_directory
from pathlib import Path
import json
import os
import sys
import threading
from typing import Dict
import logging
from datetime import datetime

# Добавляем родительскую директорию в path для импорта модулей
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config import Config
from main import ProjectAnalyzer

# Настройка логирования
log_file = os.path.join(os.path.dirname(__file__), '..', 'analyzer.log')
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s [%(levelname)s] %(name)s: %(message)s',
    handlers=[
        logging.FileHandler(log_file, encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Flask App Setup
app = Flask(__name__)
app.config['SECRET_KEY'] = 'dev-secret-key-change-in-production'
app.config['MAX_CONTENT_LENGTH'] = 100 * 1024 * 1024  # 100MB max upload

# Хранилище для результатов анализа (в памяти)
# В продакшене использовать Redis или БД
analysis_results = {}
analysis_progress = {}


@app.route('/')
def index():
    """Главная страница"""
    return render_template('index.html', config={
        'models': Config.AVAILABLE_MODELS,
        'current_model': Config.LLM_MODEL
    })


@app.route('/analyze', methods=['POST'])
def analyze():
    """
    Принимает путь к проекту, запускает анализ в фоне

    Body: {
        "project_path": "/path/to/project"
    }

    Returns: {
        "project_id": "abc123",
        "status": "started"
    }
    """
    try:
        data = request.json
        project_path = data.get('project_path')

        logger.info(f"=== NEW ANALYSIS REQUEST ===")
        logger.info(f"Received project path: {project_path}")
        logger.info(f"Request data: {data}")

        if not project_path:
            logger.error("Project path is empty!")
            return jsonify({'error': 'Project path is required'}), 400

        # Проверяем существование пути
        path_obj = Path(project_path)
        logger.info(f"Path object created: {path_obj}")
        logger.info(f"Path is absolute: {path_obj.is_absolute()}")
        logger.info(f"Path exists: {path_obj.exists()}")

        if not path_obj.exists():
            logger.error(f"Path does not exist: {project_path}")
            return jsonify({'error': f'Path does not exist: {project_path}'}), 400

    except Exception as e:
        logger.exception(f"Error in analyze endpoint (validation): {e}")
        return jsonify({'error': f'Validation error: {str(e)}'}), 400

    # Генерируем ID для проекта
    import uuid
    project_id = str(uuid.uuid4())

    logger.info(f"Generated project_id: {project_id}")

    # Инициализируем прогресс
    analysis_progress[project_id] = {
        'status': 'running',
        'message': 'Starting analysis...',
        'progress': 0
    }

    # Запускаем анализ в отдельном потоке
    def run_analysis():
        try:
            logger.info(f"[{project_id}] Starting analysis thread")
            logger.info(f"[{project_id}] Project path: {project_path}")

            analyzer = ProjectAnalyzer(Config)
            logger.info(f"[{project_id}] ProjectAnalyzer created")

            def progress_callback(message, progress):
                logger.info(f"[{project_id}] Progress: {progress}% - {message}")
                analysis_progress[project_id] = {
                    'status': 'running',
                    'message': message,
                    'progress': progress
                }

            logger.info(f"[{project_id}] Calling analyze_project...")
            results = analyzer.analyze_project(project_path, progress_callback)

            logger.info(f"[{project_id}] Analysis completed successfully")
            logger.info(f"[{project_id}] Results keys: {results.keys() if results else 'None'}")

            # Сохраняем результаты
            analysis_results[project_id] = results
            analysis_progress[project_id] = {
                'status': 'completed',
                'message': 'Analysis complete!',
                'progress': 100
            }

            logger.info(f"[{project_id}] === ANALYSIS FINISHED ===")

        except Exception as e:
            logger.exception(f"[{project_id}] ANALYSIS FAILED: {e}")
            analysis_progress[project_id] = {
                'status': 'error',
                'message': str(e),
                'progress': -1
            }

    thread = threading.Thread(target=run_analysis)
    thread.daemon = True
    thread.start()
    logger.info(f"[{project_id}] Analysis thread started")

    return jsonify({
        'project_id': project_id,
        'status': 'started'
    })


@app.route('/progress/<project_id>')
def get_progress(project_id):
    """
    Возвращает текущий прогресс анализа

    Returns: {
        "status": "running|completed|error",
        "message": "Parsing project...",
        "progress": 45
    }
    """
    if project_id not in analysis_progress:
        return jsonify({'error': 'Unknown project'}), 404

    return jsonify(analysis_progress[project_id])


@app.route('/results/<project_id>')
def get_results(project_id):
    """
    Возвращает результаты анализа

    Returns: {
        "graph": {...},
        "file_tree": [...],
        "issues": {...},
        "stats": {...}
    }
    """
    if project_id not in analysis_results:
        return jsonify({'error': 'Results not found'}), 404

    return jsonify(analysis_results[project_id])


@app.route('/config')
def get_config():
    """
    Возвращает текущую конфигурацию

    Returns: {
        "model": "anthropic/claude-3-5-haiku",
        "available_models": [...],
        "api_key_set": true
    }
    """
    return jsonify({
        'model': Config.LLM_MODEL,
        'available_models': Config.AVAILABLE_MODELS,
        'api_key_set': bool(Config.OPENROUTER_API_KEY)
    })


@app.route('/config/model', methods=['POST'])
def update_model():
    """
    Обновляет модель LLM

    Body: {
        "model": "openai/gpt-4o-mini"
    }
    """
    data = request.json
    new_model = data.get('model')

    if new_model not in Config.AVAILABLE_MODELS:
        return jsonify({'error': 'Invalid model'}), 400

    Config.LLM_MODEL = new_model
    return jsonify({'success': True, 'model': new_model})


if __name__ == '__main__':
    app.run(
        host=Config.UI_HOST,
        port=Config.UI_PORT,
        debug=Config.DEBUG
    )
