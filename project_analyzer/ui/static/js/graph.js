// ===== ГЛОБАЛЬНЫЕ ПЕРЕМЕННЫЕ =====
let currentProjectId = null;
let graphNetwork = null;
let allResults = null;

// ===== DEBUG HELPER =====
function showDebug(message) {
    const debugInfo = document.getElementById('debugInfo');
    const debugText = document.getElementById('debugText');
    if (debugInfo && debugText) {
        debugInfo.style.display = 'block';
        debugText.innerHTML += message + '<br>';
        console.log('DEBUG:', message);
    }
}

// ===== ИНИЦИАЛИЗАЦИЯ =====
document.addEventListener('DOMContentLoaded', function() {
    console.log('=== PAGE LOADED ===');
    showDebug('[1/10] PAGE LOADED - DOMContentLoaded fired');

    // Проверяем загрузку vis.js
    showDebug('[2/10] Checking vis.js library...');
    if (typeof vis === 'undefined') {
        console.error('❌ vis.js library not loaded!');
        console.error('This usually means:');
        console.error('  1. No internet connection');
        console.error('  2. CDN is blocked by firewall/antivirus');
        console.error('  3. Script failed to load from https://unpkg.com/vis-network/');
        showDebug('❌ vis.js NOT loaded on startup!');
        showDebug('   Причины: 1) Нет интернета 2) CDN заблокирован 3) Файл повреждён');

        // Проверяем наличие script tag
        const scripts = document.querySelectorAll('script');
        let visScriptFound = false;
        scripts.forEach(script => {
            if (script.src && script.src.includes('vis-network')) {
                visScriptFound = true;
                console.log('vis.js script tag found:', script.src);
                console.log('Script error state:', script.error);
                showDebug('   Script tag найден: ' + script.src);
            }
        });
        if (!visScriptFound) {
            console.error('❌ vis.js script tag not found in HTML!');
            showDebug('   ❌ Script tag НЕ НАЙДЕН в HTML!');
        }
    } else {
        console.log('✓ vis.js loaded successfully');
        console.log('vis version:', vis.version || 'unknown');
        showDebug('✓ [2/10] vis.js LOADED! Version: ' + (vis.version || '?'));
    }

    showDebug('[3/10] Initializing handlers...');
    initUploadHandlers();
    showDebug('[4/10] Upload handlers OK');
    initModalHandlers();
    showDebug('[5/10] Modal handlers OK');
    initSettingsHandlers();
    showDebug('[6/10] Settings handlers OK');
    initExportHandler();
    showDebug('[7/10] Export handler OK');
    showDebug('[8/10] ✓ ALL INITIALIZED - Ready for analysis!');
});

// ===== UPLOAD HANDLERS =====
function initUploadHandlers() {
    const uploadZone = document.getElementById('uploadZone');
    const pathInput = document.getElementById('pathInput');
    const analyzeBtn = document.getElementById('analyzeBtn');

    // Analyze button
    analyzeBtn.addEventListener('click', () => {
        const path = pathInput.value.trim();
        if (!path) {
            alert('Please enter a project path!');
            return;
        }
        startAnalysis(path);
    });

    // Enter key on path input
    pathInput.addEventListener('keypress', (e) => {
        if (e.key === 'Enter') {
            analyzeBtn.click();
        }
    });

    // Drag & Drop (показываем путь в input)
    uploadZone.addEventListener('dragover', (e) => {
        e.preventDefault();
        uploadZone.classList.add('dragover');
    });

    uploadZone.addEventListener('dragleave', () => {
        uploadZone.classList.remove('dragover');
    });

    uploadZone.addEventListener('drop', (e) => {
        e.preventDefault();
        uploadZone.classList.remove('dragover');

        const items = e.dataTransfer.items;
        if (items && items.length > 0) {
            const item = items[0].webkitGetAsEntry();
            if (item && item.isDirectory) {
                // Пытаемся получить путь (может не сработать в браузере)
                pathInput.value = item.fullPath || item.name;
            }
        }
    });
}

// ===== ANALYSIS =====
function startAnalysis(projectPath) {
    showDebug('');
    showDebug('=== STARTING ANALYSIS ===');
    showDebug('[9/10] Project path: ' + projectPath);
    
    // Показываем progress section
    document.getElementById('uploadSection').style.display = 'none';
    document.getElementById('progressSection').style.display = 'flex';
    showDebug('[9/10] UI switched to progress mode');

    // Отправляем запрос на анализ
    showDebug('[9/10] Sending POST /analyze...');
    fetch('/analyze', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify({ project_path: projectPath })
    })
    .then(response => {
        showDebug('[9/10] Got response from /analyze');
        return response.json();
    })
    .then(data => {
        showDebug('[9/10] Response data: ' + JSON.stringify(data));
        if (data.project_id) {
            showDebug('[9/10] ✓ Analysis started! ID: ' + data.project_id);
            currentProjectId = data.project_id;
            pollProgress(data.project_id);
        } else {
            showDebug('❌ No project_id in response!');
            showError('Failed to start analysis');
        }
    })
    .catch(error => {
        showDebug('❌ FETCH ERROR: ' + error.message);
        showError('Error: ' + error.message);
    });
}

function pollProgress(projectId) {
    const interval = setInterval(() => {
        fetch(`/progress/${projectId}`)
        .then(response => response.json())
        .then(data => {
            updateProgress(data);

            if (data.status === 'completed') {
                clearInterval(interval);
                loadResults(projectId);
            } else if (data.status === 'error') {
                clearInterval(interval);
                showError(data.message);
            }
        })
        .catch(error => {
            clearInterval(interval);
            showError('Error polling progress: ' + error.message);
        });
    }, 500); // Каждые 500ms
}

function updateProgress(data) {
    document.getElementById('progressFill').style.width = data.progress + '%';
    document.getElementById('progressMessage').textContent = data.message;
    document.getElementById('progressPercent').textContent = Math.round(data.progress) + '%';
}

function loadResults(projectId) {
    showDebug('');
    showDebug('[10/10] === LOADING RESULTS ===');
    showDebug('[10/10] Fetching /results/' + projectId);
    
    fetch(`/results/${projectId}`)
    .then(response => {
        showDebug('[10/10] Got response from /results');
        return response.json();
    })
    .then(data => {
        showDebug('[10/10] Results received! Keys: ' + Object.keys(data).join(', '));
        showDebug('[10/10] Nodes: ' + (data.graph?.nodes?.length || 0));
        showDebug('[10/10] Edges: ' + (data.graph?.edges?.length || 0));
        allResults = data;
        showResults(data);
    })
    .catch(error => {
        showDebug('❌ ERROR loading results: ' + error.message);
        showError('Error loading results: ' + error.message);
    });
}

// ===== RESULTS DISPLAY =====
function showResults(data) {
    showDebug('');
    showDebug('=== SHOW RESULTS CALLED ===');
    
    // DEBUG: Выводим все данные
    console.log('=== FULL RESULTS ===');
    console.log('Stats:', data.stats);
    console.log('File tree items:', data.file_tree.length);
    console.log('Graph nodes:', data.graph.nodes.length);
    console.log('Graph edges:', data.graph.edges.length);
    console.log('Issues:', data.issues);

    showDebug('Stats: Files=' + data.stats.total_files + ' Funcs=' + data.stats.total_functions);
    showDebug('Graph: Nodes=' + data.graph.nodes.length + ' Edges=' + data.graph.edges.length);
    showDebug('File tree items: ' + data.file_tree.length);

    // Показываем кнопку Export
    document.getElementById('exportBtn').style.display = 'inline-block';
    showDebug('✓ Export button shown');

    // Скрываем progress, показываем results
    document.getElementById('progressSection').style.display = 'none';
    document.getElementById('resultsSection').style.display = 'block';
    showDebug('✓ UI switched to results section');

    // Обновляем stats
    updateStats(data.stats);
    showDebug('✓ Stats updated');

    // Рендерим компоненты
    renderFileTree(data.file_tree);
    showDebug('✓ File tree rendered');

    showDebug('');
    showDebug('>>> CALLING renderGraph() <<<');
    renderGraph(data.graph);

    renderIssues(data.issues);
    showDebug('✓ Issues rendered');
}

function updateStats(stats) {
    document.getElementById('statFiles').textContent = stats.total_files;
    document.getElementById('statFunctions').textContent = stats.total_functions;
    document.getElementById('statClasses').textContent = stats.total_classes;
    document.getElementById('statErrors').textContent = stats.errors;
    document.getElementById('statWarnings').textContent = stats.warnings;

    // Обновляем badges
    document.getElementById('errorCount').textContent = stats.errors;
    document.getElementById('warningCount').textContent = stats.warnings;
    document.getElementById('infoCount').textContent = stats.total_issues - stats.errors - stats.warnings;
}

// ===== FILE TREE =====
function renderFileTree(tree) {
    const container = document.getElementById('fileTree');
    container.innerHTML = '';

    function createTreeNode(item, level = 0) {
        const div = document.createElement('div');
        div.className = item.type === 'folder' ? 'tree-folder tree-item' : 'tree-file tree-item';
        div.style.paddingLeft = (level * 15) + 'px';
        div.textContent = item.type === 'folder' ? '📁 ' + item.name : '📄 ' + item.name;

        if (item.type === 'file') {
            div.addEventListener('click', () => {
                filterGraphByFile(item.path);
            });
        }

        container.appendChild(div);

        if (item.children && item.children.length > 0) {
            item.children.forEach(child => createTreeNode(child, level + 1));
        }
    }

    tree.forEach(item => createTreeNode(item));
}

// ===== GRAPH =====
function renderGraph(graphData) {
    showDebug('');
    showDebug('>>> renderGraph() STARTED <<<');
    showDebug('Input: nodes=' + graphData.nodes.length + ' edges=' + graphData.edges.length);
    
    const container = document.getElementById('graphContainer');

    if (!container) {
        showDebug('❌ FATAL: graphContainer element NOT FOUND!');
        return;
    }

    showDebug('✓ Container element found');

    // DEBUG: Выводим что пришло
    console.log('=== GRAPH DATA ===');
    console.log('Nodes:', graphData.nodes.length);
    console.log('Edges:', graphData.edges.length);
    console.log('First node:', graphData.nodes[0]);
    console.log('First edge:', graphData.edges[0]);

    if (graphData.nodes.length === 0) {
        console.error('❌ ERROR: No nodes to render!');
        showDebug('❌ No nodes in graphData!');
        container.innerHTML = '<div style="color: white; padding: 2rem; text-align: center;">No functions found to visualize</div>';
        return;
    }

    showDebug('Scheduling requestAnimationFrame (1/2)...');

    // Ждем, пока контейнер получит размеры (следующий frame)
    requestAnimationFrame(() => {
        showDebug('RAF (1/2) executed');
        const w = container.offsetWidth;
        const h = container.offsetHeight;
        console.log('Container dimensions:', w, 'x', h);
        showDebug('Container dimensions: ' + w + ' x ' + h + ' px');

        // Проверяем контейнер
        if (container.offsetHeight === 0) {
            console.error('❌ ERROR: Graph container has 0 height!');
            console.log('Force setting height...');
            showDebug('⚠️  Container height=0! Forcing 600px...');
            container.style.height = '600px';
            container.style.minHeight = '600px';
        }

        // Рендерим граф в следующем frame после установки высоты
        showDebug('Scheduling requestAnimationFrame (2/2)...');
        requestAnimationFrame(() => {
            showDebug('RAF (2/2) executed');
            console.log('Starting vis.js rendering...');
            showDebug('>>> Calling renderGraphInternal() <<<');
            renderGraphInternal(container, graphData);
        });
    });
}

function renderGraphInternal(container, graphData) {
    showDebug('');
    showDebug('>>> renderGraphInternal() STARTED <<<');

    // БОЛЬШОЕ сообщение "Загрузка графа..." с реальными числами
    container.innerHTML = '<div style="display: flex; align-items: center; justify-content: center; height: 100%; color: #4CAF50; font-size: 24px;"><div>⏳ Рендерим граф...<br><small style="font-size: 16px;">' + graphData.nodes.length + ' функций, ' + graphData.edges.length + ' связей</small></div></div>';
    showDebug('Loading message displayed');

    // Проверяем что vis.js загружен
    showDebug('Checking vis.js availability...');
    if (typeof vis === 'undefined') {
        console.error('❌ CRITICAL: vis.js library not found!');
        console.error('CDN URL: https://unpkg.com/vis-network/standalone/umd/vis-network.min.js');
        console.error('Check: 1) Internet connection 2) CDN not blocked 3) Browser console for load errors');
        showDebug('❌ CRITICAL: vis is undefined!');
        showDebug('   typeof vis = ' + typeof vis);
        container.innerHTML = '<div style="color: red; padding: 2rem; text-align: center; font-size: 20px;"><strong>❌ ОШИБКА</strong><br><br>Библиотека vis.js не загружена!<br>Проверьте интернет-соединение.<br><br>Или используйте <button onclick="location.reload()">Перезагрузить</button></div>';
        return;
    }

    showDebug('✓ vis is defined: ' + typeof vis);
    console.log('vis object type:', typeof vis);
    console.log('vis.Network available:', typeof vis.Network);
    console.log('vis.DataSet available:', typeof vis.DataSet);
    showDebug('✓ vis.Network: ' + typeof vis.Network);
    showDebug('✓ vis.DataSet: ' + typeof vis.DataSet);

    // vis.js options
    const options = {
        nodes: {
            shape: 'box',
            font: {
                color: '#ffffff',
                size: 14
            },
            borderWidth: 2,
            shadow: true
        },
        edges: {
            arrows: 'to',
            color: {
                color: '#666666',
                highlight: '#4CAF50'
            },
            smooth: {
                type: 'cubicBezier'
            }
        },
        physics: {
            enabled: true,
            barnesHut: {
                gravitationalConstant: -2000,
                springLength: 150,
                springConstant: 0.04
            }
        },
        interaction: {
            hover: true,
            tooltipDelay: 100
        }
    };

    // Создаем граф
    console.log('Creating vis.js DataSets...');
    showDebug('');
    showDebug('Creating vis.DataSet objects...');

    try {
        showDebug('  new vis.DataSet(nodes)...');
        const nodes = new vis.DataSet(graphData.nodes);
        showDebug('  ✓ Nodes DataSet: ' + nodes.length + ' items');
        
        showDebug('  new vis.DataSet(edges)...');
        const edges = new vis.DataSet(graphData.edges);
        showDebug('  ✓ Edges DataSet: ' + edges.length + ' items');
        
        console.log('DataSets created. Nodes:', nodes.length, 'Edges:', edges.length);

        const data = { nodes, edges };
        console.log('Creating vis.Network...');
        showDebug('');
        showDebug('Creating vis.Network object...');
        showDebug('  Container: ' + container.id);
        showDebug('  Nodes: ' + nodes.length);
        showDebug('  Edges: ' + edges.length);

        graphNetwork = new vis.Network(container, data, options);
        console.log('✓ vis.Network created successfully');
        showDebug('✓ vis.Network CREATED!');
        showDebug('  Network object: ' + typeof graphNetwork);
    } catch (error) {
        showDebug('');
        showDebug('❌❌❌ EXCEPTION CAUGHT ❌❌❌');
        showDebug('Error: ' + error.message);
        showDebug('Stack: ' + error.stack);
        console.error('vis.js error:', error);
        container.innerHTML = '<div style="color: red; padding: 2rem;">ERROR creating graph: ' + error.message + '</div>';
        return;
    }

    // Устанавливаем таймаут - если через 5 секунд граф не появился, показываем ошибку
    let graphRendered = false;
    showDebug('');
    showDebug('Setting 5s timeout for stabilization...');
    setTimeout(() => {
        if (!graphRendered) {
            console.error('❌ Graph rendering timeout!');
            showDebug('❌❌❌ TIMEOUT! Graph did not stabilize in 5s');
            container.innerHTML = '<div style="color: #FF9800; padding: 2rem; text-align: center; font-size: 18px;">' +
                '<strong>⚠️ ГРАФ НЕ ОТОБРАЗИЛСЯ</strong><br><br>' +
                'vis.js создан, но рендеринг завис.<br>' +
                'Узлов: ' + graphData.nodes.length + ', Связей: ' + graphData.edges.length + '<br><br>' +
                '<button onclick="location.reload()" style="padding: 10px 20px; font-size: 16px; cursor: pointer;">🔄 Перезагрузить страницу</button><br><br>' +
                '<small>Проверьте Console (F12) для деталей</small>' +
                '</div>';
        }
    }, 5000);

    // Логируем начало стабилизации
    console.log('Waiting for graph stabilization...');
    showDebug('Subscribing to vis.Network events...');

    // Ждем стабилизации (когда граф закончит рисоваться)
    graphNetwork.once('stabilized', function(params) {
        graphRendered = true;
        console.log('✓ Graph stabilized and rendered!');
        console.log('Stabilization took:', params.iterations, 'iterations');
        showDebug('');
        showDebug('✓✓✓ GRAPH STABILIZED! ✓✓✓');
        showDebug('Iterations: ' + params.iterations);
        console.log('Fitting graph to view...');
        graphNetwork.fit();
        showDebug('✓ Graph fitted to view');

        // Очищаем ВСЕ div'ы с сообщениями
        const divs = container.querySelectorAll('div');
        showDebug('Found ' + divs.length + ' div elements in container');
        divs.forEach((div, idx) => {
            showDebug('  Div ' + idx + ': "' + div.textContent.substring(0, 50) + '"');
            if (div.textContent && (div.textContent.includes('Рендерим граф') || div.textContent.includes('⏳'))) {
                div.remove();
                showDebug('  -> Removed!');
            }
        });
        
        // Проверяем, есть ли canvas
        const canvas = container.querySelector('canvas');
        if (canvas) {
            showDebug('');
            showDebug('✓✓✓ CANVAS FOUND! ✓✓✓');
            showDebug('Canvas size: ' + canvas.width + 'x' + canvas.height + ' px');
            showDebug('Canvas display: ' + canvas.style.display);
            showDebug('Canvas visibility: ' + canvas.style.visibility);
            showDebug('Canvas position: ' + canvas.style.position);
            // Делаем canvas видимым принудительно
            canvas.style.display = 'block';
            canvas.style.visibility = 'visible';
            canvas.style.position = 'relative';
            canvas.style.border = '3px solid red'; // Красная рамка для отладки
            showDebug('✓ Canvas forced visible with RED BORDER');
        } else {
            showDebug('');
            showDebug('❌❌❌ CANVAS NOT FOUND! ❌❌❌');
        }
        
        showDebug('');
        showDebug('Container info:');
        showDebug('  Total children: ' + container.children.length);
        for (let i = 0; i < container.children.length; i++) {
            const child = container.children[i];
            showDebug('  [' + i + '] ' + child.tagName + ' (display: ' + child.style.display + ')');
        }
        
        showDebug('');
        showDebug('=== GRAPH RENDERING COMPLETE ===');
    });

    // Отслеживаем процесс стабилизации
    graphNetwork.on('stabilizationProgress', function(params) {
        const progress = Math.round((params.iterations / params.total) * 100);
        if (progress % 25 === 0) {  // Логируем каждые 25%
            console.log('Stabilization progress:', progress + '%');
            showDebug('Stabilization: ' + progress + '%');
        }
    });

    // Логируем начало стабилизации
    graphNetwork.on('startStabilizing', function() {
        console.log('Graph stabilization started');
        showDebug('EVENT: startStabilizing fired');
    });

    // Отслеживаем любые ошибки
    graphNetwork.on('error', function(error) {
        console.error('❌ vis.js ERROR:', error);
        showDebug('');
        showDebug('❌❌❌ vis.Network ERROR EVENT ❌❌❌');
        showDebug('Error: ' + error);
        container.innerHTML = '<div style="color: red; padding: 2rem; text-align: center;"><strong>❌ ОШИБКА vis.js</strong><br><br>' + error + '</div>';
    });

    // Event handlers
    graphNetwork.on('click', function(params) {
        console.log('Graph clicked:', params);
        if (params.nodes.length > 0) {
            const nodeId = params.nodes[0];
            console.log('Node clicked:', nodeId);
            showFunctionDetails(nodeId);
        }
    });

    graphNetwork.on('hoverNode', function(params) {
        const nodeId = params.node;
        highlightConnections(nodeId);
    });

    // Graph controls
    document.getElementById('zoomInBtn').addEventListener('click', () => {
        graphNetwork.moveTo({ scale: graphNetwork.getScale() * 1.2 });
    });

    document.getElementById('zoomOutBtn').addEventListener('click', () => {
        graphNetwork.moveTo({ scale: graphNetwork.getScale() * 0.8 });
    });

    document.getElementById('resetZoomBtn').addEventListener('click', () => {
        graphNetwork.moveTo({ scale: 1 });
    });

    document.getElementById('fitBtn').addEventListener('click', () => {
        graphNetwork.fit();
    });
}

function highlightConnections(nodeId) {
    const connectedNodes = graphNetwork.getConnectedNodes(nodeId);
    const connectedEdges = graphNetwork.getConnectedEdges(nodeId);

    // Подсвечиваем связанные ноды
    graphNetwork.selectNodes(connectedNodes);
}

function filterGraphByFile(filePath) {
    // Фильтруем граф по файлу
    const nodes = allResults.graph.nodes.filter(n => n.data.file === filePath);
    const nodeIds = nodes.map(n => n.id);

    graphNetwork.selectNodes(nodeIds);
    graphNetwork.fit({
        nodes: nodeIds,
        animation: true
    });
}

// ===== ISSUES =====
function renderIssues(issues) {
    const tabs = document.querySelectorAll('.tab-btn');
    const issuesList = document.getElementById('issuesList');

    // Tab switching
    tabs.forEach(tab => {
        tab.addEventListener('click', () => {
            tabs.forEach(t => t.classList.remove('active'));
            tab.classList.add('active');

            const category = tab.dataset.tab;
            renderIssueCategory(issues[category], issuesList);
        });
    });

    // Изначально показываем errors
    renderIssueCategory(issues.errors, issuesList);
}

function renderIssueCategory(issueList, container) {
    container.innerHTML = '';

    if (issueList.length === 0) {
        container.innerHTML = '<p style="text-align: center; color: #888;">No issues found</p>';
        return;
    }

    issueList.forEach(issue => {
        const div = document.createElement('div');
        div.className = `issue-item ${issue.severity}`;

        div.innerHTML = `
            <div class="issue-title">${issue.type.replace('_', ' ').toUpperCase()}</div>
            <div>${issue.message}</div>
            <div class="issue-location">${issue.file}:${issue.line}</div>
        `;

        div.addEventListener('click', () => {
            if (issue.function && issue.file) {
                // Создаем полный ID: file:function
                const nodeId = `${issue.file}:${issue.function}`;
                showFunctionDetails(nodeId);
            }
        });

        container.appendChild(div);
    });
}

// ===== FUNCTION DETAILS MODAL =====
function initModalHandlers() {
    const modal = document.getElementById('functionModal');
    const closeBtn = modal.querySelector('.close');

    closeBtn.addEventListener('click', () => {
        modal.style.display = 'none';
    });

    window.addEventListener('click', (e) => {
        if (e.target === modal) {
            modal.style.display = 'none';
        }
    });
}

function showFunctionDetails(nodeId) {
    const func = allResults.graph.nodes.find(n => n.id === nodeId);

    if (!func) return;

    const modal = document.getElementById('functionModal');

    document.getElementById('modalFunctionName').textContent = func.label;
    document.getElementById('modalFile').textContent = func.data.file + ':' + func.data.line;
    document.getElementById('modalParams').textContent = func.data.params.join(', ') || 'None';
    document.getElementById('modalDescription').textContent = func.data.description;
    document.getElementById('modalCode').textContent = func.data.code;

    const calls = allResults.graph.edges
        .filter(e => e.from === nodeId)
        .map(e => {
            // Извлекаем только имя функции из ID (file:function -> function)
            const parts = e.to.split(':');
            return parts[parts.length - 1];
        });
    document.getElementById('modalCalls').textContent = calls.join(', ') || 'None';

    modal.style.display = 'block';
}

// ===== SETTINGS MODAL =====
function initSettingsHandlers() {
    const modal = document.getElementById('settingsModal');
    const settingsBtn = document.getElementById('settingsBtn');
    const closeBtn = modal.querySelector('.close');
    const saveBtn = document.getElementById('saveSettingsBtn');

    settingsBtn.addEventListener('click', () => {
        modal.style.display = 'block';
    });

    closeBtn.addEventListener('click', () => {
        modal.style.display = 'none';
    });

    saveBtn.addEventListener('click', () => {
        const newModel = document.getElementById('modelSelect').value;

        fetch('/config/model', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ model: newModel })
        })
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                alert('Model updated successfully!');
                modal.style.display = 'none';
            }
        })
        .catch(error => {
            alert('Error updating model: ' + error.message);
        });
    });
}

// ===== ERROR HANDLING =====
function showError(message) {
    alert('Error: ' + message);
    location.reload();
}

// ===== EXPORT HANDLER =====
function initExportHandler() {
    const exportBtn = document.getElementById('exportBtn');

    exportBtn.addEventListener('click', () => {
        if (!allResults) {
            alert('No results to export');
            return;
        }

        // Создаем JSON blob
        const dataStr = JSON.stringify(allResults, null, 2);
        const dataBlob = new Blob([dataStr], { type: 'application/json' });

        // Создаем ссылку для скачивания
        const url = URL.createObjectURL(dataBlob);
        const link = document.createElement('a');
        link.href = url;
        link.download = `analysis_results_${Date.now()}.json`;

        // Триггерим скачивание
        document.body.appendChild(link);
        link.click();
        document.body.removeChild(link);

        // Очищаем URL
        URL.revokeObjectURL(url);

        console.log('Results exported successfully');
    });
}
