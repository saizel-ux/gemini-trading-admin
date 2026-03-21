<!DOCTYPE html>
<html lang="ru">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Gemini Trade Bot - Админ панель</title>
    <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
    <script src="https://cdn.jsdelivr.net/npm/papaparse@5.3.2/papaparse.min.js"></script>
    <style>
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }

        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif;
            background: linear-gradient(135deg, #1a1a2e 0%, #16213e 100%);
            color: #fff;
            min-height: 100vh;
        }

        .container {
            max-width: 1400px;
            margin: 0 auto;
            padding: 20px;
        }

        /* Header */
        .header {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            padding: 30px;
            border-radius: 20px;
            margin-bottom: 30px;
            text-align: center;
            box-shadow: 0 10px 30px rgba(0,0,0,0.3);
        }

        .header h1 {
            font-size: 2.5rem;
            margin-bottom: 10px;
        }

        .header p {
            opacity: 0.9;
            font-size: 1.1rem;
        }

        /* Stats Cards */
        .stats-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
            gap: 20px;
            margin-bottom: 30px;
        }

        .stat-card {
            background: rgba(255,255,255,0.1);
            backdrop-filter: blur(10px);
            border-radius: 15px;
            padding: 20px;
            text-align: center;
            transition: transform 0.3s;
            border: 1px solid rgba(255,255,255,0.2);
        }

        .stat-card:hover {
            transform: translateY(-5px);
            background: rgba(255,255,255,0.15);
        }

        .stat-card h3 {
            font-size: 0.9rem;
            text-transform: uppercase;
            letter-spacing: 1px;
            color: #aaa;
            margin-bottom: 10px;
        }

        .stat-value {
            font-size: 2.5rem;
            font-weight: bold;
            margin-bottom: 5px;
        }

        .stat-delta {
            font-size: 0.9rem;
            color: #00ff00;
        }

        /* Charts */
        .charts-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(500px, 1fr));
            gap: 20px;
            margin-bottom: 30px;
        }

        .chart-card {
            background: rgba(255,255,255,0.1);
            backdrop-filter: blur(10px);
            border-radius: 15px;
            padding: 20px;
            border: 1px solid rgba(255,255,255,0.2);
        }

        .chart-card h3 {
            margin-bottom: 15px;
            font-size: 1.2rem;
        }

        canvas {
            max-height: 300px;
        }

        /* Filters */
        .filters {
            background: rgba(255,255,255,0.1);
            backdrop-filter: blur(10px);
            border-radius: 15px;
            padding: 20px;
            margin-bottom: 30px;
            display: flex;
            flex-wrap: wrap;
            gap: 15px;
            align-items: center;
        }

        .filter-group {
            display: flex;
            flex-direction: column;
            gap: 5px;
        }

        .filter-group label {
            font-size: 0.8rem;
            color: #aaa;
        }

        select, input {
            padding: 8px 12px;
            border-radius: 8px;
            border: 1px solid rgba(255,255,255,0.2);
            background: rgba(0,0,0,0.5);
            color: white;
            cursor: pointer;
        }

        select:hover, input:hover {
            background: rgba(0,0,0,0.7);
        }

        button {
            padding: 8px 20px;
            border-radius: 8px;
            border: none;
            background: #667eea;
            color: white;
            cursor: pointer;
            transition: all 0.3s;
        }

        button:hover {
            background: #5a67d8;
            transform: scale(1.05);
        }

        /* Table */
        .table-container {
            background: rgba(255,255,255,0.1);
            backdrop-filter: blur(10px);
            border-radius: 15px;
            padding: 20px;
            overflow-x: auto;
        }

        table {
            width: 100%;
            border-collapse: collapse;
        }

        th, td {
            padding: 12px;
            text-align: left;
            border-bottom: 1px solid rgba(255,255,255,0.1);
        }

        th {
            background: rgba(0,0,0,0.3);
            color: #667eea;
            font-weight: bold;
        }

        .long {
            color: #00ff00;
            font-weight: bold;
        }

        .short {
            color: #ff4444;
            font-weight: bold;
        }

        .refresh-info {
            text-align: center;
            margin-top: 20px;
            color: #aaa;
            font-size: 0.8rem;
        }

        /* Loading */
        .loading {
            text-align: center;
            padding: 50px;
            font-size: 1.2rem;
        }

        .spinner {
            border: 3px solid rgba(255,255,255,0.3);
            border-top: 3px solid #667eea;
            border-radius: 50%;
            width: 40px;
            height: 40px;
            animation: spin 1s linear infinite;
            margin: 0 auto 20px;
        }

        @keyframes spin {
            0% { transform: rotate(0deg); }
            100% { transform: rotate(360deg); }
        }

        @media (max-width: 768px) {
            .charts-grid {
                grid-template-columns: 1fr;
            }
            .stats-grid {
                grid-template-columns: repeat(2, 1fr);
            }
            .filters {
                flex-direction: column;
                align-items: stretch;
            }
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>📈 Gemini Trade Bot</h1>
            <p>Аналитическая панель торговых сигналов в реальном времени</p>
        </div>

        <div class="stats-grid" id="stats">
            <div class="stat-card">
                <h3>Всего сигналов</h3>
                <div class="stat-value" id="totalSignals">0</div>
            </div>
            <div class="stat-card">
                <h3>Средняя уверенность</h3>
                <div class="stat-value" id="avgConfidence">0%</div>
                <div class="stat-delta" id="confidenceDelta">—</div>
            </div>
            <div class="stat-card">
                <h3>LONG сигналы</h3>
                <div class="stat-value" id="longCount">0</div>
                <div class="stat-delta" id="longPercent">0%</div>
            </div>
            <div class="stat-card">
                <h3>SHORT сигналы</h3>
                <div class="stat-value" id="shortCount">0</div>
                <div class="stat-delta" id="shortPercent">0%</div>
            </div>
        </div>

        <div class="filters">
            <div class="filter-group">
                <label>📊 Инструмент</label>
                <select id="symbolFilter">
                    <option value="all">Все</option>
                </select>
            </div>
            <div class="filter-group">
                <label>🎯 Направление</label>
                <select id="directionFilter">
                    <option value="all">Все</option>
                    <option value="LONG">LONG</option>
                    <option value="SHORT">SHORT</option>
                </select>
            </div>
            <div class="filter-group">
                <label>📈 Мин. уверенность</label>
                <input type="range" id="confidenceFilter" min="0" max="100" value="0">
                <span id="confidenceValue">0%</span>
            </div>
            <div class="filter-group">
                <label>⚖️ Мин. Risk/Reward</label>
                <input type="range" id="rrFilter" min="0" max="5" step="0.1" value="0">
                <span id="rrValue">0</span>
            </div>
            <button onclick="loadData()">🔄 Обновить</button>
        </div>

        <div class="charts-grid">
            <div class="chart-card">
                <h3>📈 Динамика уверенности</h3>
                <canvas id="confidenceChart"></canvas>
            </div>
            <div class="chart-card">
                <h3>🎯 Распределение по инструментам</h3>
                <canvas id="symbolsChart"></canvas>
            </div>
        </div>

        <div class="table-container">
            <h3>📋 История сделок</h3>
            <div style="overflow-x: auto;">
                <table id="dataTable">
                    <thead>
                        <tr>
                            <th>Дата</th>
                            <th>Символ</th>
                            <th>Направление</th>
                            <th>Вход</th>
                            <th>SL</th>
                            <th>TP</th>
                            <th>Уверенность</th>
                            <th>Risk/Reward</th>
                        </tr>
                    </thead>
                    <tbody id="tableBody">
                        <tr><td colspan="8" class="loading">
                            <div class="spinner"></div>
                            Загрузка данных...
                        </td></tr>
                    </tbody>
                </table>
            </div>
        </div>

        <div class="refresh-info">
            🔄 Данные обновляются автоматически каждые 30 секунд<br>
            📊 Последнее обновление: <span id="lastUpdate">—</span>
        </div>
    </div>

    <script>
        // Google Sheets ID из вашего .env
        const SHEET_ID = '1dxBmcTGmH9kHMOlwM2o1b_3LZ18ofXHA9Lqo4913R6I';
        const CSV_URL = `https://docs.google.com/spreadsheets/d/${SHEET_ID}/export?format=csv&gid=0`;
        
        let allData = [];
        let confidenceChart = null;
        let symbolsChart = null;

        // Загрузка данных
        async function loadData() {
            try {
                document.getElementById('tableBody').innerHTML = '<tr><td colspan="8" class="loading"><div class="spinner"></div>Загрузка...</td></tr>';
                
                const response = await fetch(CSV_URL);
                const csvText = await response.text();
                
                Papa.parse(csvText, {
                    header: true,
                    skipEmptyLines: true,
                    complete: function(results) {
                        allData = results.data.filter(row => row.Date && row.Symbol);
                        processData();
                    }
                });
            } catch (error) {
                console.error('Ошибка загрузки:', error);
                document.getElementById('tableBody').innerHTML = '<tr><td colspan="8" style="color: #ff4444;">❌ Ошибка загрузки данных. Проверьте доступность таблицы.</td></tr>';
            }
        }

        // Обработка данных
        function processData() {
            // Получаем фильтры
            const symbolFilter = document.getElementById('symbolFilter').value;
            const directionFilter = document.getElementById('directionFilter').value;
            const minConfidence = parseInt(document.getElementById('confidenceFilter').value);
            const minRR = parseFloat(document.getElementById('rrFilter').value);
            
            // Фильтруем данные
            let filteredData = allData.filter(row => {
                const confidence = parseFloat(row.Confidence) || 0;
                const entry = parseFloat(row.Entry);
                const sl = parseFloat(row.SL);
                const tp = parseFloat(row.TP);
                
                let rr = 0;
                if (entry && sl && tp) {
                    const profit = Math.abs(tp - entry);
                    const risk = Math.abs(entry - sl);
                    rr = risk > 0 ? profit / risk : 0;
                }
                row.RiskReward = rr;
                
                const symbolMatch = symbolFilter === 'all' || row.Symbol === symbolFilter;
                const directionMatch = directionFilter === 'all' || row.Direction === directionFilter;
                const confidenceMatch = confidence >= minConfidence;
                const rrMatch = rr >= minRR;
                
                return symbolMatch && directionMatch && confidenceMatch && rrMatch;
            });
            
            updateStats(filteredData);
            updateFilters();
            updateTable(filteredData);
            updateCharts(filteredData);
            
            document.getElementById('lastUpdate').textContent = new Date().toLocaleString();
        }

        // Обновление статистики
        function updateStats(data) {
            const total = data.length;
            const avgConfidence = total > 0 ? data.reduce((sum, row) => sum + (parseFloat(row.Confidence) || 0), 0) / total : 0;
            const longCount = data.filter(row => row.Direction === 'LONG').length;
            const shortCount = data.filter(row => row.Direction === 'SHORT').length;
            
            document.getElementById('totalSignals').textContent = total;
            document.getElementById('avgConfidence').textContent = avgConfidence.toFixed(1) + '%';
            document.getElementById('longCount').textContent = longCount;
            document.getElementById('shortCount').textContent = shortCount;
            
            const longPercent = total > 0 ? (longCount / total * 100).toFixed(1) : 0;
            const shortPercent = total > 0 ? (shortCount / total * 100).toFixed(1) : 0;
            document.getElementById('longPercent').textContent = longPercent + '%';
            document.getElementById('shortPercent').textContent = shortPercent + '%';
        }

        // Обновление фильтров
        function updateFilters() {
            const symbols = [...new Set(allData.map(row => row.Symbol))].sort();
            const symbolSelect = document.getElementById('symbolFilter');
            const currentValue = symbolSelect.value;
            
            symbolSelect.innerHTML = '<option value="all">Все</option>';
            symbols.forEach(symbol => {
                const option = document.createElement('option');
                option.value = symbol;
                option.textContent = symbol;
                if (currentValue === symbol) option.selected = true;
                symbolSelect.appendChild(option);
            });
        }

        // Обновление таблицы
        function updateTable(data) {
            const tbody = document.getElementById('tableBody');
            tbody.innerHTML = '';
            
            if (data.length === 0) {
                tbody.innerHTML = '<tr><td colspan="8">Нет данных для отображения</td></tr>';
                return;
            }
            
            const sortedData = [...data].sort((a, b) => new Date(b.Date) - new Date(a.Date)).slice(0, 100);
            
            sortedData.forEach(row => {
                const tr = document.createElement('tr');
                const directionClass = row.Direction === 'LONG' ? 'long' : 'short';
                const rr = row.RiskReward ? row.RiskReward.toFixed(2) : '—';
                
                tr.innerHTML = `
                    <td>${new Date(row.Date).toLocaleString()}</td>
                    <td>${row.Symbol}</td>
                    <td class="${directionClass}">${row.Direction}</td>
                    <td>${parseFloat(row.Entry).toFixed(5)}</td>
                    <td>${parseFloat(row.SL).toFixed(5)}</td>
                    <td>${parseFloat(row.TP).toFixed(5)}</td>
                    <td>${parseFloat(row.Confidence).toFixed(0)}%</td>
                    <td>${rr}</td>
                `;
                tbody.appendChild(tr);
            });
        }

        // Обновление графиков
        function updateCharts(data) {
            // График динамики уверенности
            const dailyData = {};
            data.forEach(row => {
                const date = new Date(row.Date).toLocaleDateString();
                if (!dailyData[date]) {
                    dailyData[date] = { total: 0, count: 0 };
                }
                dailyData[date].total += parseFloat(row.Confidence) || 0;
                dailyData[date].count++;
            });
            
            const dates = Object.keys(dailyData).sort();
            const avgConfidences = dates.map(date => dailyData[date].total / dailyData[date].count);
            
            if (confidenceChart) confidenceChart.destroy();
            
            const ctx1 = document.getElementById('confidenceChart').getContext('2d');
            confidenceChart = new Chart(ctx1, {
                type: 'line',
                data: {
                    labels: dates,
                    datasets: [{
                        label: 'Средняя уверенность (%)',
                        data: avgConfidences,
                        borderColor: '#00ff00',
                        backgroundColor: 'rgba(0, 255, 0, 0.1)',
                        tension: 0.4,
                        fill: true
                    }]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: true,
                    plugins: {
                        legend: {
                            labels: { color: '#fff' }
                        }
                    },
                    scales: {
                        y: {
                            beginAtZero: true,
                            max: 100,
                            grid: { color: 'rgba(255,255,255,0.1)' },
                            ticks: { color: '#fff' }
                        },
                        x: {
                            grid: { color: 'rgba(255,255,255,0.1)' },
                            ticks: { color: '#fff' }
                        }
                    }
                }
            });
            
            // График распределения по символам
            const symbolCounts = {};
            data.forEach(row => {
                symbolCounts[row.Symbol] = (symbolCounts[row.Symbol] || 0) + 1;
            });
            
            const symbols = Object.keys(symbolCounts).slice(0, 10);
            const counts = symbols.map(s => symbolCounts[s]);
            
            if (symbolsChart) symbolsChart.destroy();
            
            const ctx2 = document.getElementById('symbolsChart').getContext('2d');
            symbolsChart = new Chart(ctx2, {
                type: 'bar',
                data: {
                    labels: symbols,
                    datasets: [{
                        label: 'Количество сигналов',
                        data: counts,
                        backgroundColor: 'rgba(102, 126, 234, 0.8)',
                        borderColor: '#667eea',
                        borderWidth: 1
                    }]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: true,
                    plugins: {
                        legend: {
                            labels: { color: '#fff' }
                        }
                    },
                    scales: {
                        y: {
                            beginAtZero: true,
                            grid: { color: 'rgba(255,255,255,0.1)' },
                            ticks: { color: '#fff' }
                        },
                        x: {
                            grid: { color: 'rgba(255,255,255,0.1)' },
                            ticks: { color: '#fff' }
                        }
                    }
                }
            });
        }

        // Слушатели фильтров
        document.getElementById('confidenceFilter').addEventListener('input', (e) => {
            document.getElementById('confidenceValue').textContent = e.target.value + '%';
            processData();
        });
        
        document.getElementById('rrFilter').addEventListener('input', (e) => {
            document.getElementById('rrValue').textContent = e.target.value;
            processData();
        });
        
        document.getElementById('symbolFilter').addEventListener('change', () => processData());
        document.getElementById('directionFilter').addEventListener('change', () => processData());
        
        // Загрузка данных при открытии
        loadData();
        
        // Автообновление каждые 30 секунд
        setInterval(loadData, 30000);
    </script>
</body>
</html>
