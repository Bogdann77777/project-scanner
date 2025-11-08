import json
import logging
from typing import Dict, List, Any
from pathlib import Path

logger = logging.getLogger(__name__)


class DataVisualizer:
    """Подготавливает данные для UI - граф, дерево файлов, список проблем"""

    def __init__(self, parsed_data: Dict, issues: List[Dict], descriptions: List[Dict]):
        """Инициализация visualizer

        Args:
            parsed_data: Данные от парсера
            issues: Список проблем от анализатора
            descriptions: Функции с описаниями от LLM
        """
        self.parsed_data = parsed_data
        self.issues = issues
        self.functions = descriptions  # функции с описаниями
        self.classes = parsed_data['classes']

        logger.info(f"DataVisualizer initialized:")
        logger.info(f"  - Functions to visualize: {len(self.functions)}")
        logger.info(f"  - Classes: {len(self.classes)}")
        logger.info(f"  - Issues: {len(self.issues)}")

    def prepare_all_data(self) -> Dict[str, Any]:
        """Вызывает все prepare методы и возвращает полный набор данных для UI

        Returns:
            Dict с graph, file_tree, issues, stats
        """
        return {
            'graph': self.prepare_graph_data(),
            'file_tree': self.prepare_file_tree(),
            'issues': self.prepare_issues_list(),
            'stats': self.prepare_stats()
        }

    def _get_node_color(self, func: Dict) -> str:
        """Определяет цвет ноды по типу проблемы

        Args:
            func: Данные функции

        Returns:
            Hex цвет для ноды
        """
        func_issues = [
            issue for issue in self.issues
            if issue.get('function') == func['name']
        ]

        if not func_issues:
            return '#4CAF50'  # Зеленый - все ок

        # Приоритет: error > warning > info
        severities = [issue['severity'] for issue in func_issues]

        if 'error' in severities:
            return '#F44336'  # Красный
        elif 'warning' in severities:
            return '#FF9800'  # Оранжевый
        else:
            return '#2196F3'  # Синий

    def prepare_graph_data(self) -> Dict[str, Any]:
        """Создает nodes и edges для визуализации графа (формат для vis.js)

        Returns:
            Dict с nodes и edges
        """
        logger.info("Preparing graph data...")
        nodes = []
        edges = []

        logger.info(f"  - Processing {len(self.functions)} functions for nodes...")

        # Создаем ноды для функций
        for i, func in enumerate(self.functions):
            # Определяем цвет по проблемам
            color = self._get_node_color(func)

            # Уникальный ID: file:function_name
            unique_id = f"{func['file']}:{func['name']}"

            node = {
                'id': unique_id,
                'label': func['name'],
                'title': func.get('description', ''),  # Hover tooltip
                'group': func['file'],  # Группировка по файлам
                'color': color,
                'font': {'color': '#ffffff'},
                'data': {  # Дополнительные данные
                    'file': func['file'],
                    'line': func['line_start'],
                    'params': func.get('params', []),
                    'code': func['code'],
                    'description': func.get('description', '')
                }
            }
            nodes.append(node)

            if i < 3:
                logger.info(f"    Node {i+1}: {unique_id} (color: {color})")

        logger.info(f"  - Created {len(nodes)} nodes")

        # Создаем ребра (вызовы)
        # Сначала создаем мапинг имя функции -> все уникальные ID
        logger.info("  - Building function name mapping for edges...")
        func_name_to_ids = {}
        for func in self.functions:
            name = func['name']
            unique_id = f"{func['file']}:{name}"
            if name not in func_name_to_ids:
                func_name_to_ids[name] = []
            func_name_to_ids[name].append(unique_id)

        logger.info(f"  - Function mapping has {len(func_name_to_ids)} unique function names")

        # Теперь создаем ребра
        logger.info("  - Creating edges from function calls...")
        edge_count = 0
        for func in self.functions:
            from_id = f"{func['file']}:{func['name']}"
            calls = func.get('calls', [])

            for called in calls:
                # Находим все возможные узлы с таким именем
                if called in func_name_to_ids:
                    for to_id in func_name_to_ids[called]:
                        edges.append({
                            'from': from_id,
                            'to': to_id,
                            'arrows': 'to',
                            'color': {'color': '#666666'}
                        })
                        edge_count += 1

                        if edge_count <= 3:
                            logger.info(f"    Edge {edge_count}: {from_id} -> {to_id}")

        logger.info(f"  - Created {len(edges)} edges")

        result = {
            'nodes': nodes,
            'edges': edges
        }

        logger.info(f"✓ Graph data prepared: {len(nodes)} nodes, {len(edges)} edges")

        return result

    def prepare_file_tree(self) -> List[Dict]:
        """Строит дерево папок и файлов проекта

        Returns:
            List деревьев файлов
        """
        tree = {}

        for func in self.functions:
            file_path = func['file']
            parts = Path(file_path).parts

            # Строим вложенную структуру
            current = tree
            for part in parts:
                if part not in current:
                    current[part] = {}
                current = current[part]

        # Конвертируем в список для UI
        def dict_to_tree(d, parent=''):
            result = []
            for key, value in d.items():
                node = {
                    'name': key,
                    'path': f"{parent}/{key}" if parent else key,
                    'type': 'folder' if value else 'file',
                    'children': dict_to_tree(value, f"{parent}/{key}") if value else []
                }
                result.append(node)
            return result

        return dict_to_tree(tree)

    def prepare_issues_list(self) -> Dict[str, List[Dict]]:
        """Группирует проблемы по типам

        Returns:
            Dict с errors, warnings, info
        """
        grouped = {
            'errors': [],
            'warnings': [],
            'info': []
        }

        for issue in self.issues:
            severity = issue['severity']
            if severity == 'error':
                grouped['errors'].append(issue)
            elif severity == 'warning':
                grouped['warnings'].append(issue)
            else:
                grouped['info'].append(issue)

        # Сортируем по файлу и строке
        for category in grouped.values():
            category.sort(key=lambda x: (x['file'], x.get('line', 0)))

        return grouped

    def prepare_stats(self) -> Dict[str, int]:
        """Считает статистику проекта

        Returns:
            Dict со статистикой
        """
        return {
            'total_files': len(set(f['file'] for f in self.functions)),
            'total_functions': len(self.functions),
            'total_classes': len(self.classes),
            'total_issues': len(self.issues),
            'errors': len([i for i in self.issues if i['severity'] == 'error']),
            'warnings': len([i for i in self.issues if i['severity'] == 'warning']),
            'dead_code': len([i for i in self.issues if i['type'] == 'dead_code']),
            'placeholders': len([i for i in self.issues if i['type'] == 'placeholder'])
        }
