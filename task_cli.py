"""
simple task management cli
"""

import re
import yaml
import json
from tasks import TaskList

client = TaskList()

def display_help():
    """
    Show help
    """
    print ("""
Commands:
show 0-99 - show a task at current level
tree - show tasks at current level and below
cd 0-99 - go to level
up - go up a level
add - add task at this level
modify 0-99 - modify a task
delete 0-99 - delete a task 
quit - quit
""")

def get_new_task(parent_id=None):
    task = {}
    if parent_id:
        task["parent"] = parent_id
        parent = task_by_id(all_tasks, parent_id)
        name = parent.get('name', None)
    else:
        name = 'Root'
    print(f"Add Task to {name}:")
    pattern_field = re.compile(r'(\w+)\s*:\s*(.*)')
    while True:
        print(yaml.dump(task))
        input_text = input("Enter (field:value, save, or abort)")
        if input_text.lower() in ["abort", "quit"]:
            break
        if input_text.lower() in ["save", "done"]:
            return task
        match = pattern_field.match(input_text)
        if match:
            key, value = match.groups()
            try:
                value = int(value)
            except ValueError:
                pass
            task[key] = value  
        else:
            print(f"Invalid input: {input_text}")

    return None

def tree(tasks, parent_id=None):
    tree_dict = {}
    current_tasks_list = [task for task in tasks if task.get('parent', None) == parent_id]
    for task in current_tasks_list:
        tree_dict[task['task_id']] = {}
        for key, value in task.items():
            tree_dict[task['task_id']][key] = value
        # recurse subtasks
        tree_dict[task['task_id']]['subtasks'] = tree(tasks, task['task_id'])
    return tree_dict

def task_by_id(tasks, task_id):
    """
    Grab a task from a list by id
    """
    for task in tasks:
        if task['task_id'] == task_id:
            return task
    return None

def display_menu(tasks, parent=None):
    """
    show menu
    """
    print()
    parent_task = task_by_id(tasks, parent)
    if not parent:
        current_tasks_list = [task for task in tasks if 'parent' not in task]
        print("Categories:")
    else:
        current_tasks_list = [task for task in tasks if task.get('parent', None) == parent]
        print(f"SubTasks of {parent_task.get('name', None)}")
    for idx, task in enumerate(current_tasks_list):
        print(f"{idx:3}: {task.get('name', None)}")
    print()
    return current_tasks_list

pattern_two_part = re.compile(r'(\w+)\s+(\d+)')

all_tasks = client.fetch_all()
cli_level = None
while True:
    cli_tasks = display_menu(all_tasks, cli_level)
    cli_task = task_by_id(all_tasks, cli_level)
    command = input("Enter command: ")
    if 'quit'.startswith(command):
        break
    if command.isdigit():
        cli_level = cli_tasks[int(command)].get('task_id')
    if command == 'up':
        if cli_level:
            cli_level = cli_task.get('parent', None)
        continue
    if command == 'help':
        display_help()
        continue
    if command == 'add':
        new_task = get_new_task(cli_level)
        if new_task:
            response = client.add_task(task=new_task)
            print(response)
            all_tasks = client.fetch_all()
        continue
    if command == 'tree':
        print(yaml.dump(tree(all_tasks, cli_level)))
        continue
    match = pattern_two_part.match(command)
    if match:
        command, index = match.groups()
        index = int(index)
        if command == 'cd':
            cli_level = cli_tasks[index].get('task_id')
        if command == 'delete':
            # FIXME: delete should check for children first
            delete_task_id = cli_tasks[index].get('task_id')
            response = client.delete_task(task_id=delete_task_id)
            print(response)
            all_tasks = client.fetch_all()

print("Good Bye!")
