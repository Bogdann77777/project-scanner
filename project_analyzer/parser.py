import ast
import os
from pathlib import Path
import json
import logging
from typing import Dict, List, Any, Optional, Union
from config import Config

logger = logging.getLogger(__name__)


class CodeParser:
    """Алгоритмический парсер кода - читает файлы, строит AST, извлекает функции/классы/импорты"""

    def __init__(self, project_path: str):
        """Инициализация парсера

        Args:
            project_path: Путь к проекту для анализа
        """
        self.project_path = Path(project_path)
        self.parsed_data = {
            'files': [],
            'functions': [],
            'classes': [],
            'imports': [],
            'call_graph': {}
        }

    def parse_project(self) -> Dict[str, Any]:
        """Сканирует проект рекурсивно и парсит все поддерживаемые файлы

        Returns:
            Dict со всеми распарсенными данными (files, functions, classes, imports, call_graph)
        """
        logger.info(f"Scanning project: {self.project_path}")
        logger.info(f"Supported extensions: {Config.SUPPORTED_EXTENSIONS}")
        logger.info(f"Ignored directories: {Config.IGNORE_DIRS}")

        file_count = 0
        for root, dirs, files in os.walk(self.project_path):
            # Удаляем игнорируемые папки
            dirs[:] = [d for d in dirs if d not in Config.IGNORE_DIRS]

            for file in files:
                if any(file.endswith(ext) for ext in Config.SUPPORTED_EXTENSIONS):
                    file_path = Path(root) / file
                    logger.debug(f"Parsing file: {file_path}")
                    self.parse_file(file_path)
                    file_count += 1

        logger.info(f"Parsed {file_count} files")
        logger.info(f"Total functions: {len(self.parsed_data['functions'])}")
        logger.info(f"Total classes: {len(self.parsed_data['classes'])}")
        logger.info(f"Total imports: {len(self.parsed_data['imports'])}")

        return self.parsed_data

    def parse_file(self, file_path: Path) -> None:
        """Читает и парсит один файл

        Args:
            file_path: Путь к файлу для парсинга
        """
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()

            # Проверка размера файла
            if len(content.encode('utf-8')) > Config.MAX_FILE_SIZE:
                logger.warning(f"File too large, skipping: {file_path}")
                return  # Пропускаем слишком большие файлы

            # Парсинг Python
            if file_path.suffix == '.py':
                logger.debug(f"Parsing Python file: {file_path}")
                tree = ast.parse(content)
                self._extract_python(tree, file_path, content)

            # TODO: JS/TS парсинг через esprima или babel parser

        except UnicodeDecodeError as e:
            logger.error(f"Encoding error in {file_path}: {e}")
        except SyntaxError as e:
            logger.error(f"Syntax error in {file_path}: {e}")
        except Exception as e:
            logger.exception(f"Unexpected error parsing {file_path}: {e}")

    def _extract_python(self, tree: ast.AST, file_path: Path, content: str) -> None:
        """Извлекает функции, классы и импорты из Python AST

        Args:
            tree: AST дерево
            file_path: Путь к файлу
            content: Содержимое файла
        """
        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef):
                func_data = self._extract_function(node, file_path, content)
                self.parsed_data['functions'].append(func_data)
            elif isinstance(node, ast.ClassDef):
                class_data = self._extract_class(node, file_path, content)
                self.parsed_data['classes'].append(class_data)
            elif isinstance(node, (ast.Import, ast.ImportFrom)):
                self._extract_import(node, file_path)

    def _extract_function(self, node: ast.FunctionDef, file_path: Path, content: str) -> Dict:
        """Извлекает данные о функции из AST

        Args:
            node: AST узел функции
            file_path: Путь к файлу
            content: Содержимое файла

        Returns:
            Dict с данными функции
        """
        # Имя функции
        name = node.name

        # Параметры
        params = [arg.arg for arg in node.args.args]

        # Return type annotation
        return_type = None
        if node.returns:
            return_type = ast.unparse(node.returns) if hasattr(ast, 'unparse') else 'Any'

        # Строки кода
        line_start = node.lineno
        line_end = node.end_lineno if hasattr(node, 'end_lineno') else line_start

        # Извлекаем код функции
        lines = content.split('\n')
        code = '\n'.join(lines[line_start - 1:line_end])

        # Docstring
        docstring = ast.get_docstring(node)

        # Вызовы других функций
        calls = []
        for sub_node in ast.walk(node):
            if isinstance(sub_node, ast.Call):
                if isinstance(sub_node.func, ast.Name):
                    calls.append(sub_node.func.id)
                elif isinstance(sub_node.func, ast.Attribute):
                    calls.append(sub_node.func.attr)

        # Async функция?
        is_async = isinstance(node, ast.AsyncFunctionDef)

        # Декораторы
        decorators = []
        for decorator in node.decorator_list:
            if isinstance(decorator, ast.Name):
                decorators.append(f"@{decorator.id}")
            elif isinstance(decorator, ast.Call) and isinstance(decorator.func, ast.Name):
                decorators.append(f"@{decorator.func.id}")

        return {
            'name': name,
            'file': str(file_path.name),
            'line_start': line_start,
            'line_end': line_end,
            'params': params,
            'return_type': return_type,
            'code': code,
            'docstring': docstring,
            'calls': calls,
            'is_async': is_async,
            'decorators': decorators
        }

    def _extract_class(self, node: ast.ClassDef, file_path: Path, content: str) -> Dict:
        """Извлекает данные о классе из AST

        Args:
            node: AST узел класса
            file_path: Путь к файлу
            content: Содержимое файла

        Returns:
            Dict с данными класса
        """
        # Имя класса
        name = node.name

        # Строки кода
        line_start = node.lineno
        line_end = node.end_lineno if hasattr(node, 'end_lineno') else line_start

        # Методы класса
        methods = []
        for item in node.body:
            if isinstance(item, ast.FunctionDef):
                method_data = self._extract_function(item, file_path, content)
                methods.append(method_data)

        # Родительские классы
        bases = []
        for base in node.bases:
            if isinstance(base, ast.Name):
                bases.append(base.id)
            elif isinstance(base, ast.Attribute):
                bases.append(base.attr)

        # Docstring
        docstring = ast.get_docstring(node)

        return {
            'name': name,
            'file': str(file_path.name),
            'line_start': line_start,
            'line_end': line_end,
            'methods': methods,
            'bases': bases,
            'docstring': docstring
        }

    def _extract_import(self, node: Union[ast.Import, ast.ImportFrom], file_path: Path) -> None:
        """Извлекает данные об импорте из AST и добавляет в parsed_data

        Args:
            node: AST узел импорта
            file_path: Путь к файлу
        """
        line = node.lineno

        if isinstance(node, ast.Import):
            # import module1, module2
            # Для каждого модуля создаем отдельную запись
            for alias in node.names:
                self.parsed_data['imports'].append({
                    'file': str(file_path.name),
                    'line': line,
                    'module': alias.name,
                    'names': [alias.name],
                    'alias': alias.asname
                })
        elif isinstance(node, ast.ImportFrom):
            # from module import name1, name2
            module = node.module or ''
            names = [alias.name for alias in node.names]
            alias = node.names[0].asname if len(node.names) == 1 else None

            self.parsed_data['imports'].append({
                'file': str(file_path.name),
                'line': line,
                'module': module,
                'names': names,
                'alias': alias
            })

    def build_call_graph(self) -> Dict[str, List[str]]:
        """Строит граф вызовов функций

        Returns:
            Dict вида {function_name: [called_func1, called_func2, ...]}
        """
        call_graph = {}

        for func in self.parsed_data['functions']:
            function_name = func['name']
            called_functions = func.get('calls', [])
            call_graph[function_name] = called_functions

        return call_graph
