import ast
from typing import Dict, List, Any, Set
import networkx as nx


class CodeAnalyzer:
    """Анализатор кода - находит проблемы: мертвый код, обрывы, заглушки"""

    def __init__(self, parsed_data: Dict[str, Any]):
        """Инициализация анализатора

        Args:
            parsed_data: Данные от парсера (functions, classes, imports, etc.)
        """
        self.parsed_data = parsed_data
        self.issues = []
        self.call_graph = nx.DiGraph()  # Направленный граф
        self._build_graph()

    def _build_graph(self) -> None:
        """Строит networkx граф из данных парсера"""
        for func in self.parsed_data['functions']:
            self.call_graph.add_node(func['name'])
            for called in func.get('calls', []):
                self.call_graph.add_edge(func['name'], called)

    def analyze(self) -> List[Dict]:
        """Запускает все проверки и возвращает список проблем

        Returns:
            List of Dict с проблемами (type, severity, file, line, message)
        """
        self.find_dead_code()
        self.find_broken_calls()
        self.find_placeholders()
        self.find_missing_returns()
        self.find_unused_imports()
        return self.issues

    def find_dead_code(self) -> None:
        """Находит функции, которые никто не вызывает (мертвый код)"""
        for func in self.parsed_data['functions']:
            func_name = func['name']

            # Пропускаем entry points
            if func_name in ['main', '__init__', '__main__']:
                continue

            # Проверяем есть ли входящие вызовы
            if self.call_graph.in_degree(func_name) == 0:
                self.issues.append({
                    'type': 'dead_code',
                    'severity': 'warning',
                    'file': func['file'],
                    'line': func['line_start'],
                    'function': func_name,
                    'message': f"Function '{func_name}' is never called"
                })

    def find_broken_calls(self) -> None:
        """Находит вызовы функций, которые не существуют в проекте"""
        all_functions = {f['name'] for f in self.parsed_data['functions']}
        all_imports = {imp['module'] for imp in self.parsed_data['imports']}

        # Добавляем также имена из импортов
        for imp in self.parsed_data['imports']:
            all_imports.update(imp.get('names', []))

        for func in self.parsed_data['functions']:
            for called in func.get('calls', []):
                # Если вызов не в списке функций и не импортирован
                if called not in all_functions and called not in all_imports:
                    # Пропускаем встроенные функции
                    if called not in dir(__builtins__):
                        self.issues.append({
                            'type': 'broken_call',
                            'severity': 'error',
                            'file': func['file'],
                            'line': func['line_start'],
                            'function': func['name'],
                            'message': f"Calls undefined function '{called}'"
                        })

    def find_placeholders(self) -> None:
        """Ищет заглушки: pass, TODO, FIXME, NotImplementedError"""
        for func in self.parsed_data['functions']:
            code = func['code']

            # Проверяем на pass (если это единственная строка)
            if code.strip() == 'pass':
                self.issues.append({
                    'type': 'placeholder',
                    'severity': 'warning',
                    'file': func['file'],
                    'line': func['line_start'],
                    'function': func['name'],
                    'message': f"Function '{func['name']}' is empty (only 'pass')"
                })

            # Проверяем TODO/FIXME
            if 'TODO' in code or 'FIXME' in code:
                self.issues.append({
                    'type': 'placeholder',
                    'severity': 'info',
                    'file': func['file'],
                    'line': func['line_start'],
                    'function': func['name'],
                    'message': f"Function '{func['name']}' has TODO/FIXME comment"
                })

            # Проверяем NotImplementedError
            if 'NotImplementedError' in code:
                self.issues.append({
                    'type': 'placeholder',
                    'severity': 'warning',
                    'file': func['file'],
                    'line': func['line_start'],
                    'function': func['name'],
                    'message': f"Function '{func['name']}' raises NotImplementedError"
                })

    def find_missing_returns(self) -> None:
        """Находит функции с return type аннотацией, но без return statement"""
        for func in self.parsed_data['functions']:
            # Если есть аннотация return и это не None/void
            if func.get('return_type') and func['return_type'] != 'None':
                code = func['code']

                # Ищем 'return' в коде (простая проверка)
                if 'return' not in code:
                    self.issues.append({
                        'type': 'missing_return',
                        'severity': 'error',
                        'file': func['file'],
                        'line': func['line_start'],
                        'function': func['name'],
                        'message': f"Function expects return type '{func['return_type']}' but has no return"
                    })

    def find_unused_imports(self) -> None:
        """Находит импорты, которые не используются в коде файла"""
        # Группируем импорты по файлам
        imports_by_file = {}
        for imp in self.parsed_data['imports']:
            file = imp['file']
            if file not in imports_by_file:
                imports_by_file[file] = []
            imports_by_file[file].extend(imp['names'])

        # Собираем все используемые имена в файле
        for file, imports in imports_by_file.items():
            # Находим все функции в этом файле
            file_funcs = [f for f in self.parsed_data['functions'] if f['file'] == file]

            # Собираем все вызовы
            used_names = set()
            for func in file_funcs:
                used_names.update(func.get('calls', []))

            # Проверяем какие импорты не используются
            for imp_name in imports:
                if imp_name not in used_names:
                    self.issues.append({
                        'type': 'unused_import',
                        'severity': 'info',
                        'file': file,
                        'line': 0,  # TODO: можно добавить строку импорта
                        'message': f"Import '{imp_name}' is not used"
                    })
