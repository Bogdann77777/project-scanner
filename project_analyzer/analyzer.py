import ast
from typing import Dict, List, Any, Set
import networkx as nx


class CodeAnalyzer:
    """Анализатор кода - находит проблемы: мертвый код, обрывы, заглушки"""
    
    # Белый список встроенных функций и популярных методов Python
    BUILTINS = {
        # Встроенные функции Python
        'print', 'len', 'range', 'str', 'int', 'float', 'list', 'dict', 'set', 'tuple',
        'open', 'input', 'type', 'isinstance', 'issubclass', 'hasattr', 'getattr', 'setattr',
        'delattr', 'dir', 'vars', 'help', 'min', 'max', 'sum', 'abs', 'round', 'sorted',
        'reversed', 'enumerate', 'zip', 'map', 'filter', 'all', 'any', 'next', 'iter',
        'callable', 'format', 'repr', 'eval', 'exec', 'compile', 'chr', 'ord', 'bin', 'hex',
        'oct', 'id', 'hash', 'object', 'property', 'staticmethod', 'classmethod',
        
        # Методы строк
        'upper', 'lower', 'title', 'capitalize', 'strip', 'lstrip', 'rstrip', 'split',
        'join', 'replace', 'find', 'rfind', 'index', 'count', 'startswith', 'endswith',
        'isalpha', 'isdigit', 'isalnum', 'isspace', 'islower', 'isupper',
        
        # Методы списков/множеств
        'append', 'extend', 'insert', 'remove', 'pop', 'clear', 'index', 'count', 'sort',
        'reverse', 'copy', 'add', 'update', 'discard',
        
        # Методы словарей
        'keys', 'values', 'items', 'get', 'setdefault', 'update', 'pop', 'popitem',
        
        # Методы файлов
        'read', 'write', 'readline', 'readlines', 'writelines', 'close', 'flush', 'seek', 'tell',
        
        # Методы Path
        'exists', 'is_file', 'is_dir', 'mkdir', 'rmdir', 'unlink', 'rename', 'absolute',
        'resolve', 'parent', 'name', 'stem', 'suffix',
        
        # JSON/pickle
        'load', 'loads', 'dump', 'dumps',
        
        # Исключения
        'ValueError', 'TypeError', 'KeyError', 'IndexError', 'AttributeError', 'RuntimeError',
        'NotImplementedError', 'Exception', 'BaseException',
    }

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

            # Пропускаем entry points и специальные методы
            if func_name in ['main', '__init__', '__main__', '__call__', '__str__', '__repr__']:
                continue
            
            # Пропускаем magic methods
            if func_name.startswith('__') and func_name.endswith('__'):
                continue
            
            # Пропускаем функции из if __name__ == '__main__' блока
            # (эти функции часто вызываются вручную, не через код)
            if func.get('in_main_block', False):
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
                # Пропускаем встроенные функции и методы
                if called in self.BUILTINS:
                    continue
                    
                # Пропускаем приватные методы (начинаются с _)
                if called.startswith('_'):
                    continue
                
                # Если вызов не в списке функций и не импортирован
                if called not in all_functions and called not in all_imports:
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
