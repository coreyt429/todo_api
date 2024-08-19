let AUTH_TOKEN = '';
let task_list = [];
let categories = [
    'Today',
    'This Week',
    'This Month',
    'This Quarter',
    'Tasks',
    'Projects'
];
let category = 'Today';
let detail_display = 'form'
let show_completed = false;

checkStoredAuthToken()

function setAuthToken() {
    const input = document.getElementById('authTokenInput');
    const errorMessage = document.getElementById('errorMessage');
    
    if (input.value.trim() === '') {
        errorMessage.textContent = 'Please enter a valid AUTH_TOKEN.';
        return;
    }

    AUTH_TOKEN = input.value.trim();
    localStorage.setItem('auth_token', AUTH_TOKEN); // Store the token in localStorage
    errorMessage.textContent = '';
    console.log('AUTH_TOKEN set to:', AUTH_TOKEN);
    load_tasks(load_tasks_callback);
}

// Function to check if the AUTH_TOKEN is already stored and use it
function checkStoredAuthToken() {
    const storedToken = localStorage.getItem('auth_token');
    if (storedToken) {
        AUTH_TOKEN = storedToken;
        console.log('AUTH_TOKEN loaded from storage:', AUTH_TOKEN);
        load_tasks(load_tasks_callback);
    }
}

function load_tasks_callback(task_list){
    // Load the tasks for "Tasks" by default
    filterTasks(category);
}

function filterTasks(category) {
    console.log('filterTasks')
    // Load BreadCrumbs
    setBreadCrumbs(category)
    // Clear detail form
    const container = document.getElementById('taskDetailsContainer');
    container.innerHTML = ''; // Clear previous content
    // Update Task List
    const taskListContainer = document.getElementById('taskListContainer');
    taskListContainer.innerHTML = ''; // Clear existing tasks
    console.log(category)
    let filteredTasks = task_list; // Declare filteredTasks in the outer scope
    if (category === 'Tasks') {
        filteredTasks = task_list.filter(task => task.type.trim().toLowerCase() === 'task');
    }
    else if (category === 'Projects') {
        filteredTasks = task_list.filter(task => task.type.trim().toLowerCase() === 'project');
    }
    else if (category === 'Today') {
        filteredTasks = task_list.filter(task => {
            const dueDate = new Date(task.timestamps.due);
            return task.type.trim().toLowerCase() === 'task' && isToday(dueDate);
        });
    } else if (category === 'This Week') {
        filteredTasks = task_list.filter(task => {
            const dueDate = new Date(task.timestamps.due);
            return task.type.trim().toLowerCase() === 'task' && isThisWeek(dueDate);
        });
    } else if (category === 'This Month') {
        filteredTasks = task_list.filter(task => {
            const dueDate = new Date(task.timestamps.due);
            return task.type.trim().toLowerCase() === 'task' && isThisMonth(dueDate);
        });
    } else if (category === 'This Quarter') {
        filteredTasks = task_list.filter(task => {
            const dueDate = new Date(task.timestamps.due);
            return task.type.trim().toLowerCase() === 'task' && isThisQuarter(dueDate);
        });
    }
    if (!show_completed) {
        filteredTasks = filteredTasks.filter(task => task.status !== 'completed');
    }
    filteredTasks.forEach(task => {
        // Set default priority if it doesn't exist
        task.priority = task.priority || 'low';
        task.notes = task.notes || '';
        const taskElement = document.createElement('div');
        taskElement.className = `task-item task-priority-${task.priority}`;

        // Parse the ISO timestamp
        const dueDate = new Date(task.timestamps.due);

        // Get current date information
        const now = new Date();
        const tomorrow = new Date(now);
        tomorrow.setDate(now.getDate() + 1);

        // Determine relative day and format time
        let formattedDate = '';
        if (dueDate.toDateString() === now.toDateString()) {
            formattedDate = `Today ${dueDate.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}`;
        } else if (dueDate.toDateString() === tomorrow.toDateString()) {
            formattedDate = `Tomorrow ${dueDate.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}`;
        } else {
            formattedDate = `${dueDate.getMonth() + 1}/${dueDate.getDate()} ${dueDate.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}`;
        }

        taskElement.innerHTML = `
            <div class="d-flex justify-content-between align-items-center">
                
                <div>
                    <h5><a onclick="selectTask('${task.task_id}')">${task.name}</a></h5>
                    <p class="mb-0">${task.notes}</p>
                </div>
                <div class="ms-auto">
                    <p class="mb-0">${formattedDate}</p>
                    <p class="mb-0">${task.status}</p>
                </div>
            </div>
        `;
        taskListContainer.appendChild(taskElement);
    });
}

function selectTask(task_id) {
    const task = task_list.find(t => t.task_id === task_id);
    if (task) {
        document.getElementById('taskDetailsContainer').style.display = 'block'; // Show the container
        renderTaskDetail(task);
    }
}

function setBreadCrumbs(hint) {
    const breadcrumbContainer = document.getElementById('breadcrumbContainer');
    
    // Store the first child for later
    const firstBreadcrumb = breadcrumbContainer.firstChild;
    breadcrumbContainer.innerHTML = ''; // Clear existing breadcrumb

    if (categories.includes(hint)) {
        // If hint is a category, just display it
        const breadcrumbItem = document.createElement('li');
        breadcrumbItem.className = 'breadcrumb-item active';
        breadcrumbItem.setAttribute('aria-current', 'page');
        breadcrumbItem.textContent = hint;
        breadcrumbItem.addEventListener('click', () => {
            category = hint;
            load_tasks(load_tasks_callback);
        });
        breadcrumbContainer.appendChild(breadcrumbItem);
    } else {
        // Assume hint is a task_id and create breadcrumb chain
        let category = null;

        if (firstBreadcrumb && categories.includes(firstBreadcrumb.textContent)) {
            category = firstBreadcrumb.textContent; // Keep the existing category
        }

        if (category) {
            const breadcrumbItem = document.createElement('li');
            breadcrumbItem.className = 'breadcrumb-item';
            breadcrumbItem.textContent = category;
            breadcrumbItem.addEventListener('click', () => {
                category = category;
                load_tasks(load_tasks_callback);
            });
            breadcrumbContainer.appendChild(breadcrumbItem);
        }

        // Build the breadcrumb chain from the selected task up to the root
        let task = task_list.find(t => t.task_id === hint);
        const breadcrumbChain = [];

        while (task) {
            breadcrumbChain.unshift(task);
            task = task_list.find(t => t.task_id === task.parent);
        }

        // Add the breadcrumb chain to the container
        breadcrumbChain.forEach(task => {
            const breadcrumbItem = document.createElement('li');
            breadcrumbItem.className = 'breadcrumb-item';
            breadcrumbItem.textContent = task.name;
            breadcrumbItem.addEventListener('click', () => selectTask(task.task_id));
            breadcrumbContainer.appendChild(breadcrumbItem);
        });

        // Set the last item as active
        if (breadcrumbContainer.lastChild) {
            breadcrumbContainer.lastChild.className = 'breadcrumb-item active';
            breadcrumbContainer.lastChild.setAttribute('aria-current', 'page');
        }
    }
}

function renderTaskDetail(task){
    if(detail_display === 'form'){
        renderTaskForm(task)
    }
    else if(detail_display === 'json'){
        renderTaskJSON(task)
    }
    else if(detail_display === 'yaml'){
        renderTaskYAML(task)
    }
}

function renderTaskJSON(task) {
    setBreadCrumbs(task.task_id);
    const container = document.getElementById('taskDetailsContainer');
    container.innerHTML = ''; // Clear previous content

    const editorDiv = document.createElement('div');
    editorDiv.id = 'jsonEditor';
    editorDiv.style.height = '500px';
    editorDiv.style.width = '100%';

    container.appendChild(editorDiv);

    const editor = ace.edit('jsonEditor');
    editor.session.setMode('ace/mode/json');
    editor.setTheme('ace/theme/monokai'); // Optional: set a theme
    editor.setValue(JSON.stringify(task, null, 2)); // Format JSON nicely
}

function renderTaskYAML(task) {
    setBreadCrumbs(task.task_id);
    const container = document.getElementById('taskDetailsContainer');
    container.innerHTML = ''; // Clear previous content

    const editorDiv = document.createElement('div');
    editorDiv.id = 'yamlEditor';
    editorDiv.style.height = '500px';
    editorDiv.style.width = '100%';

    container.appendChild(editorDiv);

    const editor = ace.edit('yamlEditor');
    editor.session.setMode('ace/mode/yaml');
    editor.setTheme('ace/theme/monokai'); // Optional: set a theme

    // Convert task object to YAML
    const yamlString = jsyaml.dump(task);
    editor.setValue(yamlString);
}

function renderTaskForm(task) {
    setBreadCrumbs(task.task_id);
    const container = document.getElementById('taskDetailsContainer');
    container.innerHTML = ''; // Clear previous content

    const form = document.createElement('form');
    form.id = 'taskForm';

    const disabled = ['timestamps.created', 'timestamps.updated'];
    const hidden = ['task_id'];

    // Recursively create form fields based on task properties
    function createFields(obj, parentKey = '') {
        for (const key in obj) {
            if (obj.hasOwnProperty(key)) {
                const fieldContainer = document.createElement('div');
                fieldContainer.classList.add('field-container');
                
                const fullKey = parentKey ? `${parentKey}.${key}` : key;

                if (typeof obj[key] === 'object' && obj[key] !== null) {
                    // Recursively handle nested objects and arrays
                    createFields(obj[key], fullKey);
                } else {
                    const input = document.createElement('input');
                    input.type = 'text';
                    input.name = fullKey;
                    input.value = obj[key];
                    // Check if the field should be disabled
                    if (disabled.includes(fullKey)) {
                        input.disabled = true;
                    }
                    // Check if the field should be hidden
                    if (hidden.includes(fullKey)) {
                        input.type = 'hidden';
                    }
                    // Append label only if the input is not hidden
                    if (input.type !== 'hidden') {
                        const label = document.createElement('label');
                        label.textContent = fullKey;
                        fieldContainer.appendChild(label);
                    }
                    fieldContainer.appendChild(input);
                }
                
                form.appendChild(fieldContainer);
            }
        }
    }

    // Start creating fields from the top-level task object
    createFields(task);

    // Add New Subtask button
    const newSubtaskButton = document.createElement('button');
    newSubtaskButton.type = 'button';
    newSubtaskButton.textContent = 'New Subtask';
    newSubtaskButton.onclick = () => createNewSubtask(task.task_id);
    form.appendChild(newSubtaskButton);

    // Add field button
    const addFieldButton = document.createElement('button');
    addFieldButton.type = 'button';
    addFieldButton.textContent = 'Add Field';
    addFieldButton.onclick = addField;
    form.appendChild(addFieldButton);

    // Save button
    const saveButton = document.createElement('button');
    saveButton.type = 'button';
    saveButton.textContent = 'Save';
    saveButton.onclick = () => saveTask(task.task_id);
    form.appendChild(saveButton);
    container.appendChild(form);
    const alertDiv = document.createElement('div')
    alertDiv.id = 'alertDiv'
    container.appendChild(alertDiv)
}

function addField() {
    const form = document.getElementById('taskForm');
    const fieldContainer = document.createElement('div');
    fieldContainer.classList.add('field-container');

    const label = document.createElement('label');
    label.textContent = 'New Field';
    fieldContainer.appendChild(label);

    const input = document.createElement('input');
    input.type = 'text';
    input.name = 'newField';
    fieldContainer.appendChild(input);

    form.appendChild(fieldContainer);
}

function saveTaskCallback(response) {
    const alertDiv = document.getElementById('alertDiv');
    alertDiv.innerHTML = ''; // Clear any existing alerts

    let alertType = 'alert-danger'; // Default to red (error)
    
    // Check if the response contains a success message
    if (response && response.message && response.message.toLowerCase().includes('success')) {
        alertType = 'alert-success'; // Set to green if "success" is in the message
    }

    // Create the alert element
    const alert = document.createElement('div');
    alert.className = `alert ${alertType} alert-dismissible fade show`;
    alert.setAttribute('role', 'alert');
    alert.textContent = response.message || 'An error occurred';

    // Add a close button to the alert
    const closeButton = document.createElement('button');
    closeButton.type = 'button';
    closeButton.className = 'btn-close';
    closeButton.setAttribute('data-bs-dismiss', 'alert');
    closeButton.setAttribute('aria-label', 'Close');

    alert.appendChild(closeButton);
    alertDiv.appendChild(alert);
}


function saveTask(taskId) {
    const form = document.getElementById('taskForm');
    const formData = new FormData(form);
    const updatedTask = { "task_id": taskId };

    // Helper function to set a value in a nested object structure
    function setNestedValue(obj, path, value) {
        const keys = path.split('.');
        let current = obj;
        while (keys.length > 1) {
            const key = keys.shift();
            if (!current[key]) current[key] = {}; // Create the nested object if it doesn't exist
            current = current[key];
        }
        current[keys[0]] = value;
    }

    // Process form data to build the nested task object
    formData.forEach((value, key) => {
        if (value !== 'DELETE') {
            setNestedValue(updatedTask, key, value);
        }
    });

    console.log(updatedTask, taskId);
    // Call update_task to handle saving the task
    update_task(updatedTask, saveTaskCallback);
}
