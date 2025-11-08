"""
Генератор простого HTML отчета с визуализацией workflow
"""

import json
import sys
from pathlib import Path


def generate_html_report(results_json_path: str, output_html: str):
    """
    Создает простой HTML отчет с визуализацией workflow

    Args:
        results_json_path: Путь к JSON с результатами анализа
        output_html: Путь куда сохранить HTML отчет
    """

    with open(results_json_path, 'r', encoding='utf-8') as f:
        data = json.load(f)

    graph = data['graph']
    stats = data['stats']
    issues = data['issues']

    # Создаем HTML
    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Project Analysis Report</title>
    <style>
        body {{
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            background: #1a1a1a;
            color: #e0e0e0;
            padding: 2rem;
            line-height: 1.6;
        }}
        h1, h2, h3 {{
            color: #4CAF50;
        }}
        .stats {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 1rem;
            margin: 2rem 0;
        }}
        .stat-card {{
            background: #252525;
            padding: 1.5rem;
            border-radius: 8px;
            border-left: 4px solid #4CAF50;
        }}
        .stat-value {{
            font-size: 2rem;
            font-weight: bold;
            color: #4CAF50;
        }}
        .workflow-section {{
            background: #252525;
            padding: 2rem;
            border-radius: 8px;
            margin: 2rem 0;
        }}
        .function-node {{
            background: #2a2a2a;
            padding: 1rem;
            margin: 1rem 0;
            border-left: 4px solid #666;
            border-radius: 4px;
        }}
        .function-node.error {{
            border-left-color: #F44336;
        }}
        .function-node.warning {{
            border-left-color: #FF9800;
        }}
        .function-node.info {{
            border-left-color: #2196F3;
        }}
        .function-name {{
            font-size: 1.2rem;
            font-weight: bold;
            color: #4CAF50;
            margin-bottom: 0.5rem;
        }}
        .function-file {{
            color: #888;
            font-size: 0.9rem;
            margin-bottom: 0.5rem;
        }}
        .function-calls {{
            margin-top: 0.5rem;
            padding-left: 1rem;
        }}
        .call-arrow {{
            color: #4CAF50;
            margin-right: 0.5rem;
        }}
        .issues-section {{
            background: #252525;
            padding: 2rem;
            border-radius: 8px;
            margin: 2rem 0;
        }}
        .issue {{
            background: #2a2a2a;
            padding: 0.8rem;
            margin: 0.5rem 0;
            border-left: 3px solid #666;
            border-radius: 3px;
        }}
        .issue.error {{
            border-left-color: #F44336;
        }}
        .issue.warning {{
            border-left-color: #FF9800;
        }}
        .issue.info {{
            border-left-color: #2196F3;
        }}
    </style>
</head>
<body>
    <h1>📊 Project Analysis Report</h1>

    <div class="stats">
        <div class="stat-card">
            <div class="stat-value">{stats['total_files']}</div>
            <div>Files</div>
        </div>
        <div class="stat-card">
            <div class="stat-value">{stats['total_functions']}</div>
            <div>Functions</div>
        </div>
        <div class="stat-card">
            <div class="stat-value">{stats['total_classes']}</div>
            <div>Classes</div>
        </div>
        <div class="stat-card">
            <div class="stat-value" style="color: #F44336;">{stats['errors']}</div>
            <div>Errors</div>
        </div>
        <div class="stat-card">
            <div class="stat-value" style="color: #FF9800;">{stats['warnings']}</div>
            <div>Warnings</div>
        </div>
    </div>

    <div class="workflow-section">
        <h2>🔄 Workflow & Dependencies</h2>
        <p>Total connections: {len(graph['edges'])}</p>
"""

    # Создаем словарь узлов для быстрого доступа
    nodes_dict = {node['id']: node for node in graph['nodes']}

    # Группируем edges по from (кто вызывает)
    calls_by_function = {}
    for edge in graph['edges']:
        from_id = edge['from']
        to_id = edge['to']

        if from_id not in calls_by_function:
            calls_by_function[from_id] = []
        calls_by_function[from_id].append(to_id)

    # Показываем все функции и их вызовы
    for node_id, node in nodes_dict.items():
        color_class = ""
        if node['color'] == '#F44336':
            color_class = "error"
        elif node['color'] == '#FF9800':
            color_class = "warning"
        elif node['color'] == '#2196F3':
            color_class = "info"

        html += f"""
        <div class="function-node {color_class}">
            <div class="function-name">{node['label']}</div>
            <div class="function-file">📄 {node['data']['file']}:{node['data']['line']}</div>
            <div>{node['title'][:200]}...</div>
"""

        # Показываем что эта функция вызывает
        if node_id in calls_by_function:
            calls = calls_by_function[node_id]
            html += '<div class="function-calls"><strong>Calls:</strong><br>'
            for call_id in calls[:10]:  # Показываем первые 10
                called_node = nodes_dict.get(call_id)
                if called_node:
                    html += f'<div><span class="call-arrow">→</span>{called_node["label"]} ({called_node["data"]["file"]})</div>'
            if len(calls) > 10:
                html += f'<div>... and {len(calls) - 10} more</div>'
            html += '</div>'

        html += '</div>'

    html += """
    </div>

    <div class="issues-section">
        <h2>⚠️ Issues Found</h2>
"""

    # Показываем issues
    for category, category_issues in issues.items():
        if category_issues:
            html += f"<h3>{category.upper()} ({len(category_issues)})</h3>"
            for issue in category_issues[:20]:  # Первые 20
                html += f"""
                <div class="issue {issue['severity']}">
                    <strong>{issue['type'].replace('_', ' ').upper()}</strong><br>
                    {issue['message']}<br>
                    <small>📄 {issue['file']}:{issue.get('line', 'N/A')}</small>
                </div>
"""

    html += """
    </div>

</body>
</html>
"""

    with open(output_html, 'w', encoding='utf-8') as f:
        f.write(html)

    print(f"✓ HTML report generated: {output_html}")
    print(f"✓ Open in browser: file:///{Path(output_html).absolute()}")


if __name__ == '__main__':
    if len(sys.argv) < 3:
        print("Usage: python generate_report.py <results.json> <output.html>")
        sys.exit(1)

    generate_html_report(sys.argv[1], sys.argv[2])
