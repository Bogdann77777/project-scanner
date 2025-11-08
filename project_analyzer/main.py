from pathlib import Path
from typing import Dict, Any, Callable, Optional
import json
import logging
from config import Config
from parser import CodeParser
from analyzer import CodeAnalyzer
from llm_describer import FunctionDescriber
from visualizer import DataVisualizer

logger = logging.getLogger(__name__)


class ProjectAnalyzer:
    """Оркестратор - связывает все модули, управляет процессом анализа"""

    def __init__(self, config: Config = None):
        """Инициализация анализатора

        Args:
            config: Конфигурация (опционально, используется Config по умолчанию)
        """
        self.config = config or Config()
        self.results = None

    def analyze_project(self, project_path: str, progress_callback: Optional[Callable] = None) -> Dict[str, Any]:
        """Полный цикл анализа проекта

        Args:
            project_path: Путь к проекту для анализа
            progress_callback: Callback для отчета о прогрессе (message, progress)

        Returns:
            Dict с полными результатами анализа
        """
        try:
            logger.info("="*80)
            logger.info(f"STARTING PROJECT ANALYSIS: {project_path}")
            logger.info("="*80)

            # Этап 1: Парсинг структуры (10-40%)
            if progress_callback:
                progress_callback("Parsing project structure...", 10)

            logger.info(">>> STEP 1: PARSING PROJECT FILES")
            parser = CodeParser(project_path)
            parsed_data = parser.parse_project()

            logger.info(f"✓ Parsing complete!")
            logger.info(f"  - Total files: {len(parsed_data.get('files', []))}")
            logger.info(f"  - Total functions: {len(parsed_data.get('functions', []))}")
            logger.info(f"  - Total classes: {len(parsed_data.get('classes', []))}")
            logger.info(f"  - Total imports: {len(parsed_data.get('imports', []))}")

            # Логируем первые 5 функций
            logger.info("  - First 5 functions:")
            for i, func in enumerate(parsed_data.get('functions', [])[:5]):
                logger.info(f"    {i+1}. {func.get('name')} in {func.get('file')} (line {func.get('line_start')})")

            if progress_callback:
                progress_callback("Building call graph...", 30)

            call_graph = parser.build_call_graph()
            parsed_data['call_graph'] = call_graph
            logger.info(f"  - Call graph edges: {len(call_graph)}")

            # Этап 2: Анализ проблем (40-60%)
            if progress_callback:
                progress_callback("Analyzing code issues...", 40)

            logger.info(">>> STEP 2: ANALYZING CODE ISSUES")
            analyzer = CodeAnalyzer(parsed_data)
            issues = analyzer.analyze()

            logger.info(f"✓ Analysis complete!")
            logger.info(f"  - Total issues: {len(issues)}")
            logger.info(f"  - Errors: {len([i for i in issues if i['severity'] == 'error'])}")
            logger.info(f"  - Warnings: {len([i for i in issues if i['severity'] == 'warning'])}")
            logger.info(f"  - Info: {len([i for i in issues if i['severity'] == 'info'])}")

            # Этап 3: Генерация описаний через LLM (60-90%)
            if progress_callback:
                progress_callback("Generating function descriptions...", 60)

            logger.info(">>> STEP 3: GENERATING LLM DESCRIPTIONS")
            logger.info(f"  - Sending {len(parsed_data['functions'])} functions to LLM...")
            logger.info(f"  - Using model: {self.config.LLM_MODEL}")

            describer = FunctionDescriber(
                api_key=self.config.OPENROUTER_API_KEY,
                model=self.config.LLM_MODEL
            )

            functions_with_descriptions = describer.describe_all_functions(
                parsed_data['functions'],
                progress_callback=progress_callback
            )

            logger.info(f"✓ LLM descriptions complete!")
            logger.info(f"  - Functions sent: {len(parsed_data['functions'])}")
            logger.info(f"  - Functions described: {len(functions_with_descriptions)}")
            logger.info(f"  - Success rate: {len(functions_with_descriptions) / max(len(parsed_data['functions']), 1) * 100:.1f}%")

            # Логируем первую описанную функцию
            if functions_with_descriptions:
                logger.info("  - First described function:")
                first = functions_with_descriptions[0]
                logger.info(f"    Name: {first.get('name')}")
                logger.info(f"    File: {first.get('file')}")
                logger.info(f"    Description: {first.get('description', 'N/A')[:100]}...")
                logger.info(f"    Has calls: {len(first.get('calls', []))} calls")

            # Этап 4: Подготовка визуализации (90-100%)
            if progress_callback:
                progress_callback("Preparing visualization...", 90)

            logger.info(">>> STEP 4: PREPARING VISUALIZATION DATA")

            visualizer = DataVisualizer(
                parsed_data={'functions': functions_with_descriptions, 'classes': parsed_data['classes']},
                issues=issues,
                descriptions=functions_with_descriptions
            )

            self.results = visualizer.prepare_all_data()

            logger.info(f"✓ Visualization data prepared!")
            logger.info(f"  - Graph nodes created: {len(self.results['graph']['nodes'])}")
            logger.info(f"  - Graph edges created: {len(self.results['graph']['edges'])}")
            logger.info(f"  - File tree items: {len(self.results['file_tree'])}")
            logger.info(f"  - Issues grouped: {sum(len(v) for v in self.results['issues'].values())}")

            # Логируем первую ноду графа
            if self.results['graph']['nodes']:
                logger.info("  - First graph node:")
                first_node = self.results['graph']['nodes'][0]
                logger.info(f"    ID: {first_node.get('id')}")
                logger.info(f"    Label: {first_node.get('label')}")
                logger.info(f"    Color: {first_node.get('color')}")

            # Логируем первый edge
            if self.results['graph']['edges']:
                logger.info("  - First graph edge:")
                first_edge = self.results['graph']['edges'][0]
                logger.info(f"    From: {first_edge.get('from')}")
                logger.info(f"    To: {first_edge.get('to')}")

            if progress_callback:
                progress_callback("Analysis complete!", 100)

            logger.info("="*80)
            logger.info("ANALYSIS COMPLETE!")
            logger.info("="*80)

            return self.results

        except Exception as e:
            logger.error(f"!!! ANALYSIS FAILED !!!")
            logger.error(f"Error: {str(e)}", exc_info=True)
            if progress_callback:
                progress_callback(f"Error: {str(e)}", -1)
            raise

    def save_results(self, output_path: str) -> None:
        """Сохраняет результаты в JSON файл

        Args:
            output_path: Путь для сохранения результатов
        """
        if not self.results:
            raise ValueError("No results to save. Run analyze_project() first.")

        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(self.results, f, indent=2, ensure_ascii=False)

    def load_results(self, input_path: str) -> Dict[str, Any]:
        """Загружает результаты из JSON файла

        Args:
            input_path: Путь к файлу с результатами

        Returns:
            Dict с результатами
        """
        with open(input_path, 'r', encoding='utf-8') as f:
            self.results = json.load(f)
        return self.results
