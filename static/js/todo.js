let AUTH_TOKEN = '';
let first_load = true
let task_list = [];
let last_task_id = 'default_id';
let categories = [
    'Today',
    'Overdue',
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
let detail_display = 'yaml' // or 'form' or 'json' should be stored in local storage, and some input to select it
let show_completed = false;
let editor;
let editor_theme = 'ace/theme/tomorrow_night';
editor_theme = 'ace/theme/github_dark';

checkStoredAuthToken()



function toggleShowCompleted() {
  show_completed = !show_completed;
}

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
        first_load = true
        load_templates(load_templates_callback);
    }
}

function load_tasks_callback(task_list){
    console.log("load_tasks_callback: " + category)
    save_category = category
    update_counters()
    category = save_category
    console.log("First load: "+first_load)
    if(first_load){
        // create any template tasks
        updateTasksFromTemplates(function(){
            load_tasks(load_tasks_callback);
        })
    }
    // Load the tasks for "Tasks" by default
    filterTasks(category);
}

function load_templates_callback(template_list){
    console.log("load_templates_callback: ")
    update_counter('templates', template_list.length)
    // Load the tasks for "Tasks" by default
    if(category == 'Templates'){
        listTemplates();
    }
    console.log("First load: "+first_load)
    if(first_load){
        load_tasks(load_tasks_callback);
    }
}

function getCategoryCounterId(category) {
    return category.toLowerCase().replace(/\s+/g, '_') + '_count';
}

function update_counter(category, count){
    counter_id = getCategoryCounterId(category)
    console.log(category, counter_id, count)
    p_elem = document.getElementById(counter_id)
    if(p_elem){
        let countStr = String(Number(count));
        // Pad with leading zero if necessary
        countStr = countStr.padStart(2, '0');
        p_elem.innerHTML = countStr;
    }
}

function update_counters(){
    categories.forEach(category => filterTasks(category))
}

function listTemplates() {
    console.log('listTemplates()')
    // Load BreadCrumbs
    setBreadCrumbs(category)
    // Clear detail form
    const container = document.getElementById('taskDetailsContainer');
    container.innerHTML = ''; // Clear previous content
    // Update Task List
    const taskListContainer = document.getElementById('taskListContainer');
    taskListContainer.innerHTML = ''; // Clear existing tasks
    update_counter('templates', template_list.length)
    template_list.sort((a, b) => {
        // Priority first
        if(priorities.indexOf(a.priority) < priorities.indexOf(b.priority)){
            return -1
        }
        if(priorities.indexOf(a.priority) > priorities.indexOf(b.priority)){
            return 1
        }
        return 0
    })
    template_list.forEach(template => {
        // Set default priority if it doesn't exist
        template.priority = template.priority || 'low';
        template.notes = template.notes || '';
        const taskElement = document.createElement('div');
        taskElement.className = `task-item task-priority-${template.priority}`;
        // taskContainer
        const taskContainer = document.createElement('div');
        taskContainer.className = 'd-flex justify-content-between align-items-center';

        // taskLabel
        const taskLabelContainer = document.createElement('div');
        const taskLabelH5 = document.createElement('h5');
        const taskLabelA = document.createElement('a');
        taskLabelA.onclick = function() {
            selectTask(template.template_id);
        };
        taskLabelA.textContent = template.name;
        taskLabelH5.appendChild(taskLabelA);
        taskLabelContainer.appendChild(taskLabelH5);
        taskContainer.appendChild(taskLabelContainer);
        taskElement.appendChild(taskContainer)
        taskListContainer.appendChild(taskElement);
    });
}

function task_history(current_task){
    const history_tree = []
    while (current_task) {
        history_tree.unshift(current_task);
        current_task = task_list.find(t => t.task_id === current_task.parent);
    }
    return history_tree
}

// Function to render tasks
function renderTasks(tasks) {
    const taskListContainer = document.getElementById('taskListContainer');
    tasks.forEach(task => {
        // Set default priority if it doesn't exist
        task.priority = task.priority || 'low';
        task.notes = task.notes || '';
        const taskElement = document.createElement('div');
        taskElement.id = task.task_id
        taskElement.className = `task-item task-priority-${task.priority}`;
        taskElement.dataset.task = JSON.stringify(task)
        taskElement.dataset.history = ''
        const history_tree = task_history(task)
        history_tree.forEach(current_task => { taskElement.dataset.history += `${current_task.name} |`})
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
        if(!show_completed){
            children = children.filter(child_task => child_task.status !== 'completed');
        }
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

function filterTasks(category) {
    console.log('filterTasks(' + category + ')');
    const taskListContainer = document.getElementById('taskListContainer');
    taskListContainer.innerHTML = ''; // Clear existing tasks

    // Load BreadCrumbs
    setBreadCrumbs(category);
    // Clear detail form
    const container = document.getElementById('taskDetailsContainer');
    container.innerHTML = ''; // Clear previous content
    
    // Add text filter input
    const filterInputContainer = document.createElement('div');
    filterInputContainer.className = 'mb-3';
    const filterInput = document.createElement('input');
    filterInput.type = 'text';
    filterInput.id = 'taskFilterInput';
    filterInput.className = 'form-control';
    filterInput. placeholder = 'Filter tasks...';
    filterInputContainer.appendChild(filterInput);
    taskListContainer.appendChild(filterInputContainer);

    console.log(category);
    let filteredTasks = task_list; // Declare filteredTasks in the outer scope

    // Apply category filter
    if (category === 'Tasks') {
        filteredTasks = task_list.filter(task => task.type.trim().toLowerCase() === 'task');
    } else if (category === 'Projects') {
        filteredTasks = task_list.filter(task => task.type.trim().toLowerCase() === 'project');
    } else if (category === 'Today') {
        filteredTasks = task_list.filter(task => {
            const dueDate = new Date(task.timestamps.due);
            return task.type.trim().toLowerCase() === 'task' && isToday(dueDate);
        });
    } else if (category === 'Overdue') {
        filteredTasks = task_list.filter(task => {
            const dueDate = new Date(task.timestamps.due);
            return task.type.trim().toLowerCase() === 'task' && isOverdue(dueDate);
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
    } else if (category === 'Templates') {
        filteredTasks = template_list;
    } else{
        filteredTasks = task_list.filter(task => {
            return task.parent === category;
        });
    }
    if (!show_completed) {
        filteredTasks = filteredTasks.filter(task => task.status !== 'completed');
    }
    
    update_counter(category, filteredTasks.length);
    filteredTasks.sort((a, b) => {
        // Priority first
        if(priorities.indexOf(a.priority) < priorities.indexOf(b.priority)){
            return -1;
        }
        if(priorities.indexOf(a.priority) > priorities.indexOf(b.priority)){
            return 1;
        }
        
        // then status
        if(statii.indexOf(a.status) < statii.indexOf(b.status)){
            return -1;
        }
        if(statii.indexOf(a.status) > statii.indexOf(b.status)){
            return 1;
        }

        // then due date
        if(a.timestamps.due < b.timestamps.due){
            return -1;
        }
        if(a.timestamps.due > b.timestamps.due){
            return 1;
        }
        console.log('Tie');
        return 0;
    });
    console.log('post_sort', filteredTasks);
    renderTasks(filteredTasks);
    // Add event listener for text filter
    filterInput.addEventListener('input', function() {
        const filterText = this.value.toLowerCase();
        const task_items = document.getElementsByClassName('task-item');
        Array.from(task_items).forEach(task_item => {
            const taskContent = task_item.textContent.toLowerCase() + task_item.dataset.task + task_item.dataset.history;

            task_item.style.display = taskContent.includes(filterText) ? 'block' : 'none';
        });
    });
    
}

function selectTask(task_id) {
    console.log("selectTask("+task_id+")");
    console.log(task_id);
    console.log(task_list);
    let task = task_list.find(t => t.task_id === task_id);
    console.log(task);
    if(!task){
        task = template_list.find(t => t.template_id === task_id);
    }
    if (task) {
        document.getElementById('taskDetailsContainer').style.display = 'block'; // Show the container
        renderTaskDetail(task);
    }
}

function setBreadCrumbs(hint) {
    console.log("setBreadCrumbs("+hint+")")
    if (!hint){return}
    const breadcrumbContainer = document.getElementById('breadcrumbContainer');
    
    // Store the first child for later
    const firstBreadcrumb = breadcrumbContainer.firstChild;
    breadcrumbContainer.innerHTML = ''; // Clear existing breadcrumb

    if (categories.includes(hint) || hint === 'Templates') {
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
        const breadcrumbItemAdd = document.createElement('li');
        breadcrumbItemAdd.className = 'breadcrumb-item';
        breadcrumbItemAdd.textContent = '+';
        breadcrumbItemAdd.addEventListener('click', () => newTask());
        breadcrumbContainer.appendChild(breadcrumbItemAdd);      
    }else {
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
        console.log('setting last_task_id: '+task.task_id)
        last_task_id = task.task_id
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
            breadcrumbItem.addEventListener('click', function(){
                console.log(task.name)
                filterTasks(task.task_id),
                renderTaskDetail(task)
                
            });
            breadcrumbContainer.appendChild(breadcrumbItem);
        });

        const breadcrumbItemAdd = document.createElement('li');
        breadcrumbItemAdd.className = 'breadcrumb-item';
        breadcrumbItemAdd.textContent = '+';
        console.log('last_task_id: '+last_task_id);
        breadcrumbItemAdd.addEventListener('click', () => newTask(last_task_id));
        breadcrumbContainer.appendChild(breadcrumbItemAdd);

        // Set the last item as active
        if (breadcrumbContainer.lastChild) {
            breadcrumbContainer.lastChild.className = 'breadcrumb-item active';
            breadcrumbContainer.lastChild.setAttribute('aria-current', 'page');
        }
    }
}

function newTask(parent){
    console.log('newTask('+parent+')')
    const date = new Date();
    date.setHours(17, 0, 0, 0);
    let task = {
        "name": "New Task",
        "type": "task",
        "timestamps": {
            "due": date.toISOString()
        }
    }
    if(category === 'Templates'){
        task = {
            "name": "New Template",
            "type": "template",
            "period": "daily",
            "time": "17:00",
            "days": [1,2,3,4,5],
            "priority": "high"
        }
    }
    if(parent){
        task.parent = parent
    }
    renderTaskDetail(task)
}

function renderTaskDetail(task){
    console.log("renderTaskDetail("+JSON.stringify(task)+")")
    if(task.task_id){
        task_id = task.task_id
        console.log("renderTaskDetail("+task_id+")")
        if(detail_display === 'form'){
            get_task(task_id, renderTaskForm)
        }
        else {
            get_task(task_id, renderTaskEditor)
        }
    } else{
        console.log("renderTaskDetail(new="+JSON.stringify(task)+")")
        console.log(task)
        if(detail_display === 'form'){
            renderTaskForm(task)
        }
        else {
            renderTaskEditor(task)
        }
    }
    document.getElementById('taskDetailsContainer').style.display = 'block';
}

function renderTaskEditor(task) {
    console.log("renderTaskEditor("+JSON.stringify(task)+")")
    if(task.id){
        setBreadCrumbs(task.task_id);
    }
    const container = document.getElementById('taskDetailsContainer');
    container.innerHTML = '<h5>Edit '+detail_display+'</h5>'; // Clear previous content

    const editorDiv = document.createElement('div');
    editorDiv.id = 'aceEditor';
    editorDiv.style.height = '500px';
    editorDiv.style.width = '100%';
    container.appendChild(editorDiv);

    // alert div
    const alertDiv = document.createElement('div');
    alertDiv.id = 'aceEditorAlert';
    alertDiv.classList = 'alert alert-dark'
    alertDiv.innerHTML = "No changes"
    container.appendChild(alertDiv);

    editor = ace.edit(editorDiv.id);
    editor.setTheme(editor_theme); // Optional: set a theme
    if(detail_display === 'json'){
        console.log("Editor: JSON")
        editor.session.setMode('ace/mode/json');
        editor.setValue(JSON.stringify(task, null, 2)); // Format JSON nicely

    } else if (detail_display === 'yaml') {
        console.log("Editor: YAML")
        editor.session.setMode('ace/mode/yaml'); // Format YAML nicely
        // Convert task object to YAML
        const yamlString = jsyaml.dump(task);
        editor.setValue(yamlString);
    }
    
    editor.commands.addCommand({
        name: 'save',
        bindKey: { win: 'Ctrl-S', mac: 'Command-S' },
        exec: function(editor) {
            const content = editor.getValue();
            console.log('Saving content:', content);
            editor_save()
        }
    });

    editor.on('change', function() {
        // alert div
        alertDiv.classList = 'alert alert-warning'
        alertDiv.innerHTML = "Unsaved changes"
    });
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

    editor = ace.edit('jsonEditor');
    editor.session.setMode('ace/mode/json');
    editor.setTheme(editor_theme); // Optional: set a theme
    editor.setValue(JSON.stringify(task, null, 2)); // Format JSON nicely
    editor.commands.addCommand({
        name: 'save',
        bindKey: { win: 'Ctrl-S', mac: 'Command-S' },
        exec: function(editor) {
            const content = editor.getValue();
            console.log('Saving content:', content);
            save_json()
        }
    });
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

    editor = ace.edit('yamlEditor');
    editor.session.setMode('ace/mode/yaml');
    editor.setTheme(editor_theme); // Optional: set a theme

    // Convert task object to YAML
    const yamlString = jsyaml.dump(task);
    editor.setValue(yamlString);
    editor.commands.addCommand({
        name: 'save',
        bindKey: { win: 'Ctrl-S', mac: 'Command-S' },
        exec: function(editor) {
            const content = editor.getValue();
            console.log('Saving content:', content);
            save_yaml()
        }
    });
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

function save_yaml(){
    var editorContent = editor.getValue();
    var yamlObject = jsyaml.load(editorContent);
    update_task(yamlObject)
}

function save_json(){
    var editorContent = editor.getValue();
    var yamlObject = jsyaml.load(editorContent);
    update_task(yamlObject)
}

function editor_save(){
    console.log("editor_save")
    let editorContent = editor.getValue();
    let task = {}
    if (detail_display === 'json'){
        task = JSON.parse(editorContent)
    }
    else if (detail_display === 'yaml'){
        task = jsyaml.load(editorContent);
    }
    let { subtasks, ...remaining_task } = task;
    if(subtasks){
        console.log("subtasks detected")
        // Check the type of subtasks
        if (Array.isArray(subtasks)) {
            subtasks.forEach( new_task => {
                    // FIXME: we need to check to be sure these aren't already added
                    console.log("new_task: " + new_task)
                    if (typeof new_task === 'object') {
                        if(new_task.name){
                            new_task.parent = task.task_id
                            if(!new_task.timestamps){
                                new_task.timestamps = {}
                            }
                            if(!new_task.timestamps.due){
                                new_task.timestamps.due = task.timestamps.due
                            }
                            update_task(new_task)
                        }
                        else{
                            console.log("name missing: "+new_task)
                        }
                    }
                    else{
                        update_task({"name": new_task, "parent": task.task_id, "timestamps":{ "due": task.timestamps.due}})
                    }
                }
            )
            // subtasks is an array
            if (subtasks.length > 0 && typeof subtasks[0] === 'object') {
            // subtasks is an array of objects (dictionaries)
            // Handle the array of dictionaries case
            console.log('subtasks is an array of objects');
            // Your code to handle the array of dictionaries goes here
            } else {
            // subtasks is an array of strings
            // Handle the array of strings case
            console.log('subtasks is an array of strings');
            // Your code to handle the array of strings goes here
            }
        } else if (typeof subtasks === 'object') {
            // subtasks is an object (dictionary)
            // Handle the dictionary case
            console.log('subtasks is an object');
            // Your code to handle the dictionary case goes here
        } else {
            // subtasks is not an array or object
            // Handle the unexpected case
            console.log('subtasks is not an array or object');
            // Your code to handle the unexpected case goes here
        }
    }
    update_task(remaining_task, editor_save_callback)
}

function editor_save_callback(response){
    const alertDiv = document.getElementById('aceEditorAlert')
    alertDiv.classList = 'alert alert-success';
    alertDiv.innerHTML = response.message
}

function updateTasksFromTemplates(callback) {
    const today = new Date();
    today.setHours(0, 0, 0, 0)
    // temp short cuircuite until I fix the current templates:
    first_load = false
    //callback()
    template_list.forEach(template => {
        console.log("Considering Template: "+template.name)
        // daily and today's DoW is in days
        if (template.criteria.period === 'daily' && template.criteria.days.includes(today.getDay())) {
            console.log(template.template_id)
            const existing_task_list = task_list.filter(task => task.template_id === template.template_id);
            console.log(existing_task_list)
            let existingTask = false
            existing_task_list.forEach(existing_task => {
                    console.log(existing_task)
                    let due = new Date(existing_task.timestamps.due)
                    due.setHours(0, 0, 0, 0)
                    console.log("Due: "+due.getTime())
                    console.log("Today: "+today.getTime())
                    console.log("Equael? " + (due.getTime() === today.getTime()))
                    if(due.getTime() === today.getTime()){
                        existingTask = true
                    }
                }
            )

            
            if (!existingTask) {
                console.log("Creating Task from Template: "+template.name)
                const [hours, minutes] = template.criteria.time.split(':').map(Number);
                const dueDate = new Date(today.getFullYear(), today.getMonth(), today.getDate(), hours, minutes);
                const new_task = {
                    ...template,
                    timestamps: {
                    due: dueDate.toISOString()
                    }
                };
                new_task.type = 'task'
                // Remove 'time' and 'period' fields
                delete new_task.criteria;
                delete new_task.timestamps.created;
                delete new_task.timestamps.updated;
                delete new_task.period
                delete new_task.time              
                task_list.push(new_task);
                update_task(new_task)
            }
        }
        });
    
    console.log(task_list)
    callback()
}