from flask import Flask, render_template_string, request, redirect, url_for

import sqlite3
import os
import json

app = Flask(__name__)

DB_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'db', 'personal_data.db')

def get_tables():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
    tables = cursor.fetchall()
    conn.close()
    return [table[0] for table in tables]

def get_column_info(table_name):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute(f"PRAGMA table_info({table_name})")
    columns = cursor.fetchall()
    conn.close()
    return [(col[1], col[2]) for col in columns]

def get_table_data(table_name):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # Get column names and types
    columns = get_column_info(table_name)
    column_names = [col[0] for col in columns]
    
    # Handle view type
    view_type = request.args.get('view', 'grid')  # grid, list, or compact
    
    # Handle sorting
    sort_column = request.args.get('sort')
    sort_direction = request.args.get('direction', 'asc')
    
    # Handle search
    search_query = request.args.get('search', '').strip()
    
    # Build the query
    query = f"SELECT * FROM {table_name}"
    
    # Add search condition if search query exists
    if search_query:
        search_conditions = []
        for col in column_names:
            search_conditions.append(f"{col} LIKE ?")
        query += " WHERE " + " OR ".join(search_conditions)
    
    # Add sorting if specified
    if sort_column in column_names:
        query += f" ORDER BY {sort_column} {sort_direction.upper()}"
    
    # Execute query
    if search_query:
        search_params = [f"%{search_query}%" for _ in column_names]
        cursor.execute(query, search_params)
    else:
        cursor.execute(query)
    
    rows = cursor.fetchall()
    conn.close()
    
    # Create HTML table with controls
    html = '''
    <div class="table-controls mb-3">
        <div class="row align-items-center">
            <div class="col-md-4">
                <input type="text" class="form-control" id="searchInput" 
                       placeholder="Search table..." 
                       value="%s"
                       onkeyup="debounceSearch(this.value)">
            </div>
            <div class="col-md-8">
                <div class="view-controls float-end">
                    <div class="btn-group view-toggle">
                        <button type="button" class="btn btn-sm %s" onclick="changeView('grid')">
                            <i class="bi bi-grid-3x3-gap-fill me-1"></i>Grid
                        </button>
                        <button type="button" class="btn btn-sm %s" onclick="changeView('list')">
                            <i class="bi bi-list me-1"></i>List
                        </button>
                        <button type="button" class="btn btn-sm %s" onclick="changeView('compact')">
                            <i class="bi bi-table me-1"></i>Compact
                        </button>
                    </div>
                </div>
            </div>
        </div>
    </div>
    ''' % (
        search_query or '',
        'btn-primary active' if view_type == 'grid' else 'btn-outline-primary',
        'btn-primary active' if view_type == 'list' else 'btn-outline-primary',
        'btn-primary active' if view_type == 'compact' else 'btn-outline-primary'
    )
    
    # Different view layouts
    if view_type == 'list':
        html += get_list_view(rows, column_names, table_name)
    elif view_type == 'compact':
        html += get_compact_view(rows, column_names, table_name)
    else:  # grid view (default)
        html += get_grid_view(rows, column_names, table_name, sort_column, sort_direction)
    
    # Add "Add New Row" button
    html += f'<button onclick="showAddForm(\'{table_name}\')" class="btn btn-success mt-3">Add New Row</button>'
    return html

def get_grid_view(rows, column_names, table_name, sort_column, sort_direction):
    html = '<table class="table table-striped table-bordered">'
    # Add header with sorting
    html += '<thead><tr>'
    for column in column_names:
        sort_indicator = ''
        if sort_column == column:
            sort_indicator = '↑' if sort_direction == 'asc' else '↓'
        html += f'''
            <th>
                <div class="d-flex justify-content-between align-items-center">
                    <span>{column}</span>
                    <button class="btn btn-link btn-sm p-0 ms-2" 
                            onclick="sortTable('{column}')" 
                            title="Sort by {column}">
                        {sort_indicator}
                    </button>
                </div>
            </th>
        '''
    html += '<th>Actions</th></tr></thead>'
    
    # Add rows
    html += '<tbody>'
    for row in rows:
        html += '<tr>'
        for value in row:
            html += f'<td>{value}</td>'
        row_id = row[0]
        html += f'''
            <td>
                <button onclick="editRow('{table_name}', {row_id})" class="btn btn-sm btn-primary">Edit</button>
                <button onclick="deleteRow('{table_name}', {row_id})" class="btn btn-sm btn-danger">Delete</button>
            </td>
        '''
        html += '</tr>'
    html += '</tbody></table>'
    return html

def get_list_view(rows, column_names, table_name):
    html = '<div class="list-view">'
    for row in rows:
        html += f'''
        <div class="card mb-3">
            <div class="card-body">
                <div class="row">
                    <div class="col-md-10">
        '''
        for i, value in enumerate(row):
            html += f'''
                <div class="mb-2">
                    <strong>{column_names[i]}:</strong> {value}
                </div>
            '''
        html += f'''
                    </div>
                    <div class="col-md-2 text-end">
                        <button onclick="editRow('{table_name}', {row[0]})" class="btn btn-sm btn-primary mb-2">Edit</button>
                        <button onclick="deleteRow('{table_name}', {row[0]})" class="btn btn-sm btn-danger">Delete</button>
                    </div>
                </div>
            </div>
        </div>
        '''
    html += '</div>'
    return html

def get_compact_view(rows, column_names, table_name):
    html = '<table class="table table-sm table-bordered table-hover">'
    # Add header
    html += '<thead><tr>'
    for column in column_names[:3]:  # Show only first 3 columns
        html += f'<th>{column}</th>'
    html += '<th>Actions</th></tr></thead>'
    
    # Add rows
    html += '<tbody>'
    for row in rows:
        html += '<tr>'
        for value in row[:3]:  # Show only first 3 columns
            html += f'<td>{value}</td>'
        row_id = row[0]
        html += f'''
            <td>
                <button onclick="editRow('{table_name}', {row_id})" class="btn btn-sm btn-primary btn-xs">Edit</button>
                <button onclick="deleteRow('{table_name}', {row_id})" class="btn btn-sm btn-danger btn-xs">Delete</button>
            </td>
        '''
        html += '</tr>'
    html += '</tbody></table>'
    return html

@app.route('/edit_row/<table_name>/<int:row_id>', methods=['GET'])
def edit_row(table_name, row_id):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    columns = get_column_info(table_name)
    cursor.execute(f"SELECT * FROM {table_name} WHERE id = ?", (row_id,))
    row = cursor.fetchone()
    conn.close()
    
    return render_template_string(EDIT_FORM_TEMPLATE,
        table_name=table_name,
        row_id=row_id,
        columns=columns,
        row=row
    )

@app.route('/update_row/<table_name>/<int:row_id>', methods=['POST'])
def update_row(table_name, row_id):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    columns = get_column_info(table_name)
    update_values = []
    for col in columns:
        value = request.form.get(col[0], '')
        update_values.append(value)
    
    set_clause = ", ".join([f"{col[0]} = ?" for col in columns])
    update_values.append(row_id)  # for WHERE clause
    
    cursor.execute(f"UPDATE {table_name} SET {set_clause} WHERE id = ?", update_values)
    conn.commit()
    conn.close()
    
    return redirect(f'/?table={table_name}')

@app.route('/delete_row/<table_name>/<int:row_id>', methods=['POST'])
def delete_row(table_name, row_id):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute(f"DELETE FROM {table_name} WHERE id = ?", (row_id,))
    conn.commit()
    conn.close()
    return redirect(f'/?table={table_name}')

@app.route('/add_row/<table_name>', methods=['GET', 'POST'])
def add_row(table_name):
    if request.method == 'GET':
        columns = get_column_info(table_name)
        return render_template_string(ADD_FORM_TEMPLATE,
            table_name=table_name,
            columns=columns
        )
    else:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        columns = get_column_info(table_name)
        insert_values = []
        for col in columns:
            value = request.form.get(col[0], '')
            insert_values.append(value)
        
        placeholders = ", ".join(["?" for _ in columns])
        column_names = ", ".join([col[0] for col in columns])
        
        cursor.execute(f"INSERT INTO {table_name} ({column_names}) VALUES ({placeholders})", insert_values)
        conn.commit()
        conn.close()
        
        return redirect(f'/?table={table_name}')

HTML_TEMPLATE = '''
<!DOCTYPE html>
<html>
<head>
    <title>JackTable - Database Viewer</title>
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.1.3/dist/css/bootstrap.min.css" rel="stylesheet">
    <link href="https://cdn.jsdelivr.net/npm/bootstrap-icons@1.7.2/font/bootstrap-icons.css" rel="stylesheet">
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600&family=Mountains+of+Christmas:wght@700&display=swap" rel="stylesheet">
    <style>
        body { 
            padding: 20px;
            font-family: 'Inter', sans-serif;
            background-color: #1a2634;
            min-height: 100vh;
            position: relative;
            overflow-x: hidden;
        }
        .snowflake {
            position: fixed;
            top: -10px;
            animation: fall linear forwards;
        }
        @keyframes fall {
            to {
                transform: translateY(100vh);
            }
        }
        .container {
            max-width: 1200px;
            margin: 0 auto;
            background-color: rgba(255, 255, 255, 0.95);
            padding: 2rem;
            border-radius: 12px;
            box-shadow: 0 4px 24px rgba(0, 0, 0, 0.2);
            position: relative;
            z-index: 1;
            backdrop-filter: blur(8px);
        }
        .table-container { 
            margin-top: 20px; 
            overflow-x: auto;
            border-radius: 8px;
            box-shadow: 0 2px 8px rgba(0, 0, 0, 0.05);
        }
        .nav-pills { 
            margin-bottom: 20px;
            gap: 0.5rem;
        }
        .nav-pills .nav-link {
            border-radius: 6px;
            padding: 0.5rem 1rem;
            color: #495057;
            font-weight: 500;
            transition: all 0.2s;
        }
        .nav-pills .nav-link:hover {
            background-color: #e9ecef;
        }
        .nav-pills .nav-link.active {
            background-color: #dc3545;
            color: white;
        }
        .table {
            margin-bottom: 0;
        }
        .table thead th {
            background-color: #f8f9fa;
            border-bottom: 2px solid #dee2e6;
            padding: 1rem;
            font-weight: 600;
            color: #495057;
        }
        .table td {
            padding: 1rem;
            vertical-align: middle;
        }
        .btn {
            font-weight: 500;
            padding: 0.5rem 1rem;
            border-radius: 6px;
            transition: all 0.2s;
        }
        .btn:hover {
            transform: translateY(-1px);
        }
        .btn-sm {
            padding: 0.25rem 0.75rem;
        }
        .btn-primary {
            background-color: #2F5373;
            border: none;
            margin-right: 0.5rem;
        }
        .btn-danger {
            background-color: #dc3545;
            border: none;
        }
        .btn-success {
            background-color: #198754;
            border: none;
        }
        h1 {
            color: #dc3545;
            font-family: 'Mountains of Christmas', cursive;
            font-weight: 700;
            font-size: 2.5rem;
            margin-bottom: 1.5rem;
            text-align: center;
            text-shadow: 2px 2px 4px rgba(0, 0, 0, 0.1);
        }
        h2 {
            color: #495057;
            font-weight: 500;
            font-size: 1.25rem;
            margin-bottom: 1rem;
        }
        .festive-border {
            border: 2px solid #dc3545;
            border-radius: 12px;
            padding: 1rem;
            margin-bottom: 1rem;
        }
        .btn-link {
            color: #495057;
            text-decoration: none;
            font-weight: 600;
        }
        .btn-link:hover {
            color: #dc3545;
        }
        .table-controls {
            background: rgba(255, 255, 255, 0.8);
            padding: 1rem;
            border-radius: 8px;
            backdrop-filter: blur(8px);
        }
        .table thead th {
            position: relative;
            cursor: pointer;
        }
        .table thead th:hover .btn-link {
            color: #dc3545;
        }
        .view-controls .view-toggle {
            background: rgba(255, 255, 255, 0.9);
            padding: 0.25rem;
            border-radius: 8px;
            backdrop-filter: blur(8px);
            display: inline-flex;
            gap: 0;
        }
        .view-toggle .btn {
            border: 1px solid #dee2e6;
            padding: 0.5rem 1rem;
            display: inline-flex;
            align-items: center;
            justify-content: center;
            min-width: 100px;
        }
        .view-toggle .btn:not(:last-child) {
            border-right: none;
        }
        .view-toggle .btn.active {
            background-color: #dc3545;
            border-color: #dc3545;
            color: white;
            position: relative;
            z-index: 1;
        }
        .view-toggle .btn:hover:not(.active) {
            background-color: #f8f9fa;
            border-color: #dee2e6;
            z-index: 2;
        }
        .view-toggle .btn i {
            font-size: 1.1rem;
        }
        .list-view .card {
            transition: all 0.2s;
            border: none;
            box-shadow: 0 2px 8px rgba(0, 0, 0, 0.05);
        }
        .list-view .card:hover {
            transform: translateY(-2px);
            box-shadow: 0 4px 12px rgba(0, 0, 0, 0.1);
        }
        .btn-xs {
            padding: 0.1rem 0.4rem;
            font-size: 0.75rem;
        }
        .compact-view td {
            padding: 0.5rem;
        }
    </style>
    <script>
        function createSnowflake() {
            const snowflake = document.createElement('div');
            snowflake.classList.add('snowflake');
            snowflake.style.left = Math.random() * 100 + 'vw';
            snowflake.style.opacity = Math.random();
            snowflake.style.animation = `fall ${Math.random() * 3 + 2}s linear forwards`;
            snowflake.innerHTML = '❄';
            snowflake.style.color = 'white';
            snowflake.style.fontSize = (Math.random() * 10 + 10) + 'px';
            document.body.appendChild(snowflake);

            snowflake.addEventListener('animationend', () => {
                snowflake.remove();
            });
        }

        function startSnow() {
            setInterval(createSnowflake, 100);
        }

        function editRow(tableName, rowId) {
            window.location.href = `/edit_row/${tableName}/${rowId}`;
        }
        
        function deleteRow(tableName, rowId) {
            if (confirm('Are you sure you want to delete this row?')) {
                fetch(`/delete_row/${tableName}/${rowId}`, {
                    method: 'POST'
                }).then(() => window.location.reload());
            }
        }
        
        function showAddForm(tableName) {
            window.location.href = `/add_row/${tableName}`;
        }

        window.onload = function() {
            startSnow();
        }

        let searchTimeout;
        function debounceSearch(value) {
            clearTimeout(searchTimeout);
            searchTimeout = setTimeout(() => {
                const urlParams = new URLSearchParams(window.location.search);
                urlParams.set('search', value);
                window.location.search = urlParams.toString();
            }, 500);
        }
        
        function sortTable(column) {
            const urlParams = new URLSearchParams(window.location.search);
            const currentSort = urlParams.get('sort');
            const currentDirection = urlParams.get('direction');
            
            if (currentSort === column) {
                urlParams.set('direction', currentDirection === 'asc' ? 'desc' : 'asc');
            } else {
                urlParams.set('sort', column);
                urlParams.set('direction', 'asc');
            }
            
            window.location.search = urlParams.toString();
        }

        function changeView(viewType) {
            const urlParams = new URLSearchParams(window.location.search);
            urlParams.set('view', viewType);
            window.location.search = urlParams.toString();
        }
    </script>
</head>
<body>
    <div class="container">
        <h1>❄️ JackTable ❄️</h1>
        <div class="festive-border">
            <ul class="nav nav-pills">
                {% for table in tables %}
                <li class="nav-item">
                    <a class="nav-link {% if table == current_table %}active{% endif %}" 
                       href="/?table={{ table }}">{{ table }}</a>
                </li>
                {% endfor %}
            </ul>
        </div>
        {% if current_table %}
        <div class="table-container">
            <h2>{{ current_table }}</h2>
            {{ table_html|safe }}
        </div>
        {% endif %}
    </div>
</body>
</html>
'''

EDIT_FORM_TEMPLATE = '''
<!DOCTYPE html>
<html>
<head>
    <title>JackTable - Edit Row</title>
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.1.3/dist/css/bootstrap.min.css" rel="stylesheet">
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600&family=Mountains+of+Christmas:wght@700&display=swap" rel="stylesheet">
    <style>
        body { 
            padding: 20px;
            font-family: 'Inter', sans-serif;
            background-color: #1a2634;
            min-height: 100vh;
        }
        .snowflake {
            position: fixed;
            top: -10px;
            animation: fall linear forwards;
        }
        @keyframes fall {
            to {
                transform: translateY(100vh);
            }
        }
        .container {
            max-width: 800px;
            margin: 0 auto;
            background-color: rgba(255, 255, 255, 0.95);
            padding: 2rem;
            border-radius: 12px;
            box-shadow: 0 4px 24px rgba(0, 0, 0, 0.2);
            position: relative;
            z-index: 1;
            backdrop-filter: blur(8px);
        }
        h2 {
            color: #dc3545;
            font-family: 'Mountains of Christmas', cursive;
            font-weight: 700;
            font-size: 2rem;
            margin-bottom: 1.5rem;
            text-align: center;
        }
        .form-label {
            font-weight: 500;
            color: #495057;
            margin-bottom: 0.5rem;
        }
        .form-control {
            border-radius: 6px;
            padding: 0.75rem;
            border: 1px solid #dee2e6;
        }
        .form-control:focus {
            border-color: #dc3545;
            box-shadow: 0 0 0 0.25rem rgba(220, 53, 69, 0.25);
        }
        .btn {
            font-weight: 500;
            padding: 0.75rem 1.5rem;
            border-radius: 6px;
            transition: all 0.2s;
        }
        .btn:hover {
            transform: translateY(-1px);
        }
        .btn-primary {
            background-color: #dc3545;
            border: none;
            margin-right: 0.5rem;
        }
        .btn-secondary {
            background-color: #6c757d;
            border: none;
        }
    </style>
    <script>
        function createSnowflake() {
            const snowflake = document.createElement('div');
            snowflake.classList.add('snowflake');
            snowflake.style.left = Math.random() * 100 + 'vw';
            snowflake.style.opacity = Math.random();
            snowflake.style.animation = `fall ${Math.random() * 3 + 2}s linear forwards`;
            snowflake.innerHTML = '❄';
            snowflake.style.color = 'white';
            snowflake.style.fontSize = (Math.random() * 10 + 10) + 'px';
            document.body.appendChild(snowflake);

            snowflake.addEventListener('animationend', () => {
                snowflake.remove();
            });
        }

        function startSnow() {
            setInterval(createSnowflake, 100);
        }

        window.onload = function() {
            startSnow();
        }
    </script>
</head>
<body>
    <div class="container">
        <h2>Edit Row in {{ table_name }} ❄️</h2>
        <form action="/update_row/{{ table_name }}/{{ row_id }}" method="post">
            {% for i in range(columns|length) %}
            <div class="mb-3">
                <label class="form-label">{{ columns[i][0] }}</label>
                <input type="text" class="form-control" name="{{ columns[i][0] }}" value="{{ row[i] }}">
            </div>
            {% endfor %}
            <div class="mt-4">
                <button type="submit" class="btn btn-primary">Save Changes</button>
                <a href="/?table={{ table_name }}" class="btn btn-secondary">Cancel</a>
            </div>
        </form>
    </div>
</body>
</html>
'''

ADD_FORM_TEMPLATE = '''
<!DOCTYPE html>
<html>
<head>
    <title>JackTable - Add Row</title>
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.1.3/dist/css/bootstrap.min.css" rel="stylesheet">
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600&family=Mountains+of+Christmas:wght@700&display=swap" rel="stylesheet">
    <style>
        body { 
            padding: 20px;
            font-family: 'Inter', sans-serif;
            background-color: #1a2634;
            min-height: 100vh;
        }
        .snowflake {
            position: fixed;
            top: -10px;
            animation: fall linear forwards;
        }
        @keyframes fall {
            to {
                transform: translateY(100vh);
            }
        }
        .container {
            max-width: 800px;
            margin: 0 auto;
            background-color: rgba(255, 255, 255, 0.95);
            padding: 2rem;
            border-radius: 12px;
            box-shadow: 0 4px 24px rgba(0, 0, 0, 0.2);
            position: relative;
            z-index: 1;
            backdrop-filter: blur(8px);
        }
        h2 {
            color: #dc3545;
            font-family: 'Mountains of Christmas', cursive;
            font-weight: 700;
            font-size: 2rem;
            margin-bottom: 1.5rem;
            text-align: center;
        }
        .form-label {
            font-weight: 500;
            color: #495057;
            margin-bottom: 0.5rem;
        }
        .form-control {
            border-radius: 6px;
            padding: 0.75rem;
            border: 1px solid #dee2e6;
        }
        .form-control:focus {
            border-color: #dc3545;
            box-shadow: 0 0 0 0.25rem rgba(220, 53, 69, 0.25);
        }
        .btn {
            font-weight: 500;
            padding: 0.75rem 1.5rem;
            border-radius: 6px;
            transition: all 0.2s;
        }
        .btn:hover {
            transform: translateY(-1px);
        }
        .btn-primary {
            background-color: #dc3545;
            border: none;
            margin-right: 0.5rem;
        }
        .btn-secondary {
            background-color: #6c757d;
            border: none;
        }
    </style>
    <script>
        function createSnowflake() {
            const snowflake = document.createElement('div');
            snowflake.classList.add('snowflake');
            snowflake.style.left = Math.random() * 100 + 'vw';
            snowflake.style.opacity = Math.random();
            snowflake.style.animation = `fall ${Math.random() * 3 + 2}s linear forwards`;
            snowflake.innerHTML = '❄';
            snowflake.style.color = 'white';
            snowflake.style.fontSize = (Math.random() * 10 + 10) + 'px';
            document.body.appendChild(snowflake);

            snowflake.addEventListener('animationend', () => {
                snowflake.remove();
            });
        }

        function startSnow() {
            setInterval(createSnowflake, 100);
        }

        window.onload = function() {
            startSnow();
        }
    </script>
</head>
<body>
    <div class="container">
        <h2>Add New Row to {{ table_name }} ❄️</h2>
        <form action="/add_row/{{ table_name }}" method="post">
            {% for column in columns %}
            <div class="mb-3">
                <label class="form-label">{{ column[0] }}</label>
                <input type="text" class="form-control" name="{{ column[0] }}" 
                       {% if column[0] == 'id' %}placeholder="Auto-generated" disabled{% endif %}>
            </div>
            {% endfor %}
            <div class="mt-4">
                <button type="submit" class="btn btn-primary">Add Row</button>
                <a href="/?table={{ table_name }}" class="btn btn-secondary">Cancel</a>
            </div>
        </form>
    </div>
</body>
</html>
'''

@app.route('/')
def index():
    tables = get_tables()
    current_table = request.args.get('table', tables[0] if tables else None)
    table_html = get_table_data(current_table) if current_table else ''
    return render_template_string(
        HTML_TEMPLATE,
        tables=tables,
        current_table=current_table,
        table_html=table_html
    )

if __name__ == '__main__':
    app.run(debug=True, port=5000) 