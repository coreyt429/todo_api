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
let priorities = [
    "high",
    "medium",
    "low"
]
let statii = [
    "completed",
    "in_progress",
    "not_started",
    "blocked"
]

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
    console.log("load_tasks_callback: " + category)
    // Load the tasks for "Tasks" by default
    filterTasks(category);
}

function filterTasks(category) {
    console.log('filterTasks('+category+')')
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
    } else{
        filteredTasks = task_list.filter(task => {
            const dueDate = new Date(task.timestamps.due);
            return task.parent === category;
        });
    }
    if (!show_completed) {
        filteredTasks = filteredTasks.filter(task => task.status !== 'completed');
    }
    filteredTasks.sort((a, b) => {
        // Priority first
        if(priorities.indexOf(a.priority) < priorities.indexOf(b.priority)){
            return -1
        }
        if(priorities.indexOf(a.priority) > priorities.indexOf(b.priority)){
            return 1
        }
        
        // then status
        if(statii.indexOf(a.status) < statii.indexOf(b.status)){
            return -1
        }
        if(statii.indexOf(a.status) > statii.indexOf(b.status)){
            return 1
        }

        // then due date
        if(a.timestamps.due < b.timestamps.due){
            return -1
        }
        if(a.timestamps.due > b.timestamps.due){
            return 1
        }
        console.log('Tie')
        return 0
    })
    console.log('post_sort', filteredTasks)
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
        // taskContainer
        const taskContainer = document.createElement('div');
        taskContainer.className = 'd-flex justify-content-between align-items-center';
        // taskLabel
        const taskLabelContainer = document.createElement('div');
        const taskLabelH5 = document.createElement('h5');
        const taskLabelA = document.createElement('a');
        taskLabelA.onclick = function() {
            selectTask(task.task_id);
        };
        taskLabelA.textContent = task.name;
        taskLabelH5.appendChild(taskLabelA);
        taskLabelContainer.appendChild(taskLabelH5);

        /*
        // taskNotes
        const taskLabelNotes = document.createElement('p');
        taskLabelNotes.className = 'mb-0';
        taskLabelNotes.textContent = task.notes
        taskLabelContainer.appendChild(taskLabelNotes)
        */

        // childTasks
        let children = task_list.filter(child_task => child_task.parent === task.task_id);
        const taskChildren = document.createElement('p');
        taskChildren.textContent = `${children.length} subtasks`;
        const taskChildrenAnchor = document.createElement('a');
        taskChildrenAnchor.onclick = function(){
            console.log('taskChildrenAnchor.onclick');
            console.log("task_id: " + task.task_id);
            //category = task.task_id;
            console.log("category: " + category);
            filterTasks(task.task_id);
        }
        taskChildrenAnchor.appendChild(taskChildren);
        taskLabelContainer.appendChild(taskChildrenAnchor);
        taskContainer.appendChild(taskLabelContainer);

        // taskDate
        const taskDateContainer = document.createElement('div');
        taskDateContainer.className = 'ms-auto';
        const dateElement = document.createElement('p');
        dateElement.className = 'mb-0';
        dateElement.textContent = formattedDate;
        taskDateContainer.appendChild(dateElement);

        // taskStatus
        const statusElement = document.createElement('p');
        statusElement.className = 'mb-0';
        statusElement.textContent = task.status;
        taskDateContainer.appendChild(statusElement);
        taskContainer.appendChild(taskDateContainer)
        
        
        taskElement.appendChild(taskContainer)
        taskListContainer.appendChild(taskElement);
    });
}

function selectTask(task_id) {
    console.log("selectTask("+task_id+")");
    console.log(task_id);
    console.log(task_list);
    const task = task_list.find(t => t.task_id === task_id);
    console.log(task);
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
            breadcrumbItem.addEventListener('click', () => filterTasks(task.task_id));
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
    console.log("renderTaskDetail("+task+")")
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

function updateIsoTimestamp() {
    base = this.id.replace('.date','').replace('.time','')
    input_date = document.getElementById(base+'.date')
    input_time = document.getElementById(base+'.time')
    input = document.getElementById(base+'.iso')
    const localDateTime = `${input_date.value}T${input_time.value}:00`;
    const date = new Date(localDateTime);
    input.value = date.toISOString();
}

function renderTaskForm(task) {
    setBreadCrumbs(task.task_id);
    const container = document.getElementById('taskDetailsContainer');
    container.innerHTML = ''; // Clear previous content

    const form = document.createElement('form');
    form.id = 'taskForm';

    const disabled = ['timestamps.created', 'timestamps.updated'];
    const hidden = ['task_id'];
    const selects = {
        'status': statii
    }

    // Recursively create form fields based on task properties
    function createFields(obj, parentKey = '') {
        for (const key in obj) {
            if (obj.hasOwnProperty(key)) {
                const fieldContainer = document.createElement('div');
                fieldContainer.classList.add('field-container');
                let dateTimeContainer = ''
                const fullKey = parentKey ? `${parentKey}.${key}` : key;
                let input = ''
                if (typeof obj[key] === 'object' && obj[key] !== null) {
                    // Recursively handle nested objects and arrays
                    createFields(obj[key], fullKey);
                } else {
                    // Check if the field should be a select
                    if (Object.keys(selects).includes(fullKey)) {
                        input = document.createElement('select');
                        input.name = fullKey;
                        
                        selects[fullKey].forEach(option => {
                            const optionElement = document.createElement('option');
                            optionElement.value = option;
                            optionElement.textContent = option;
                            if(optionElement.value === obj[key]){
                                optionElement.selected = true
                            }
                            input.appendChild(optionElement);
                        });  
                    }
                    else if(fullKey.startsWith('timestamp')){
                        console.log(fullKey)
                        input = document.createElement('input');
                        input.type = 'hidden'
                        input.id = fullKey+'.iso'
                        input.name = fullKey
                        input.value = obj[key]; // Set the ISO value
                        input_date = document.createElement('input');
                        input_date.type = 'date'
                        input_date.id = fullKey+'.date'
                        input_time = document.createElement('input');
                        input_time.type = 'time'
                        input_time.id = fullKey+'.time'
                        dateTimeContainer = document.createElement('div');
                        dateTimeContainer.classList.add('date-time-container');
                        dateTimeContainer.appendChild(input_date)
                        dateTimeContainer.appendChild(input_time)
                        // Set initial date and time values
                        if (obj[key]) {
                            const date = new Date(obj[key]);
                            input_date.value = date.toLocaleDateString('en-CA'); // YYYY-MM-DD format
                            input_time.value = date.toLocaleTimeString('en-GB', { hour: '2-digit', minute: '2-digit' }); // HH:MM format
                        }

                        // Add event listeners for updates
                        input_date.addEventListener('change', updateIsoTimestamp);
                        input_time.addEventListener('change', updateIsoTimestamp);
                    }
                    else{
                        input = document.createElement('input');
                        // Check if the field should be hidden
                        if (hidden.includes(fullKey)) {
                            input.type = 'hidden';
                            if(fullKey.startsWith('timestamp')){
                                input_date.hidden = true;
                                input_time.hidden = true;
                            }
                        }
                        else{
                            input.type = 'text';
                        }
                        input.value = obj[key];
                    }
                    input.name = fullKey;
                    
                    // Check if the field should be disabled
                    if (disabled.includes(fullKey)) {
                        input.disabled = true;
                        if(fullKey.startsWith('timestamp')){
                            input_date.disabled = true;
                            input_time.disabled = true;
                        }
                    }

                    // Append label only if the input is not hidden
                    console.log("DEBUG: "+fullKey)
                    console.log("DEBUG: "+(input.type !== 'hidden' || fullKey.startsWith('timestamp')))
                    if (input.type !== 'hidden' || fullKey.startsWith('timestamp')) {
                        const label = document.createElement('label');
                        label.textContent = fullKey;
                        console.log("Label: "+label.textContent)
                        fieldContainer.appendChild(label);
                    }
                    fieldContainer.appendChild(input);
                    if(fullKey.startsWith('timestamp')){
                        fieldContainer.appendChild(dateTimeContainer);
                    }
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

    document.querySelector('#taskForm').addEventListener('keypress', function(e) {
        if (e.key === 'Enter') {
            e.preventDefault(); // Prevent default to avoid submitting twice
            saveTask(task.task_id);
        }
    });
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
