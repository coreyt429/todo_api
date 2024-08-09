"""
simple task management cli

Todo List:
    add template to CLI
        should add a new template with parent at cli context
        similar behavior to new task, get name and type at a minimum
        but let user define other fields
        type: daily, weekly (also collect day), monthly (also collect DoM), yearly (date)
        parent: derived from CLI context or none
        should templates only be for categories? or just for Today?
        pointer templates
        rule based
    on startup:
        pull templates
        if a task should be created today:
            check to see if it already has
            if not, create it
    Notes on Categories:
        Today    - virtual category with tasks built from templates due today and pointers to project tasks
        Week     - same for this week
        Month    - same for this month
        Quarter  - same for this quarter
        Tasks    - one off tasks not associated with a project   
        Projects - structured projects

"""

import re
import yaml
import json
import argparse
import sys
from tasks import TaskList
from templates import TemplateList  # debate point, should the client code handle templates directly or via tasks?
from cfg import Cfg

client = TaskList()
template_client = TemplateList()
cfg = Cfg()

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
config - configure app
quit - quit
""")

pattern_field = re.compile(r'(\w+)\s*:\s*(.*)')

def edit_task(task_id):
    print(f"edit_task({task_id})")
    while True:
        task = task_by_id(all_tasks, task_id)
        print(f"Edit task {task}")
        for key, value in task.data.items():
            print(f"{key}: {value}")
        print()
        input_text = input("Enter (field:value, save, or abort): ")
        if input_text.lower() in ["abort", "quit", "q"]:
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
            task.data[key] = value  
        else:
            print(f"Invalid input: {input_text}")
    return None

def edit_config():
    while True:
        print(f"Edit Config:")
        for key, value in cfg.items():
            print(f"    {key}: {value}")
        print()
        input_text = input("Enter (field:value or quit): ")
        input_text = input_text.rstrip().lstrip()
        print(f"you entered [{input_text}]")
        if input_text.lower() in ["abort", "quit", "q"]:
                break
        match = pattern_field.match(input_text)
        if match:
            key, value = match.groups()
            cfg.set(key, value)
        else:
            print(f"Invalid input: {input_text}")
    return None

def get_new_task(parent_id=None):
    task = {}
    if parent_id:
        task["parent"] = parent_id
        parent = task_by_id(all_tasks, parent_id)
        name = parent.data.get('name', None)
    else:
        name = 'Root'
    print(f"Add Task to {name}: ")
    input_text = input("Enter task name: ")
    task['name'] = input_text

    while True:
        print(yaml.dump(task))
        input_text = input("Enter (field:value, save, or abort): ")
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
    current_tasks_list = [task for task in tasks if task.data.get('parent', None) == parent_id]
    for task in current_tasks_list:
        tree_dict[task.data['task_id']] = {}
        for key, value in task.data.items():
            tree_dict[task.data['task_id']][key] = value
        # recurse subtasks
        tree_dict[task.data['task_id']]['subtasks'] = tree(tasks, task.data['task_id'])
    return tree_dict


##### These should probably move to client
def task_by_id(tasks, task_id):
    """
    Grab a task from a list by id
    """
    for task in tasks:
        if task.data['task_id'] == task_id:
            return task
    return None

def tasks_by_parent(tasks, parent=None):
    if not parent:
        current_tasks_list = [task for task in tasks if not task.data.get('parent', None)]
    else:
        current_tasks_list = [task for task in sorted(tasks) if task.data.get('parent', None) == parent]
    print(f"show_completed? {cfg.get('show_completed')}")
    if not cfg.get('show_completed', True):
        print("trimming completed")
        completed = []
        for task in current_tasks_list:
            print(f"{task.data['status']}")
            # FIXME: we should probably have a status method on task instead
            if task.data['status'] == 'completed':
                print(f"trimming: {task}")
                completed.append(task)
        for task in completed:
            current_tasks_list.pop(current_tasks_list.index(task))
    return current_tasks_list

def task_by_name(tasks, task_name, parent=None):
    """
    Grab a task from a list by id
    """
    current_task_list = tasks_by_parent(tasks, parent)
    for task in current_task_list:
        if task.data['name'] == task_name:
            return task
    # not found, check children:
    for task in current_task_list:
        return task_by_name(tasks, task_name, task.data['task_id'])
    return None
##### These should probably move to client

def display_menu(tasks, parent=None):
    """
    show menu
    """
    print()
    parent_task = task_by_id(tasks, parent)
    current_tasks_list = tasks_by_parent(tasks, parent)
    if not parent:
        print("Categories:")
    else:
        print(f"SubTasks of {parent_task}")
    for idx, task in enumerate(current_tasks_list):
        print(f"{idx:3}: {task}")
    print()
    return current_tasks_list


parser = argparse.ArgumentParser(description="A CLI for managing tasks.")

# Add arguments
parser.add_argument('-p', '--parent', type=str, help='Set the target parent.')
parser.add_argument('-j', '--json', type=str, help='Set json.')
parser.add_argument('-a', '--add', action='store_true', help='Set add to True.')
parser.add_argument('-d', '--display', action='store_true', help='Just print the parent')

# Parse arguments
args = parser.parse_args()

pattern_two_part = re.compile(r'(\w+)\s+(\d+)')

all_tasks = client.fetch_all()
cli_level = None
if args.parent:
    cli_level = task_by_name(all_tasks, args.parent)
    if cli_level:
        cli_level = cli_level.data['task_id']

if args.add:
    if args.json:
        new_task = json.loads(args.json)
    else:
        new_task = get_new_task(cli_level)
    if new_task:
        response = client.add_task(task=new_task)
        print(response)
    sys.exit()

if args.display:
    display_menu(all_tasks, cli_level)
    sys.exit()

while True:
    cli_tasks = display_menu(all_tasks, cli_level)
    cli_task = task_by_id(all_tasks, cli_level)
    command = input("Enter command: ")
    # match any part of quit, but not ''
    if command and 'quit'.startswith(command):
        break
    if command.isdigit():
        try:
            cli_level = cli_tasks[int(command)].data.get('task_id')
        except IndexError:
            print(f"Invalid task {command}")
    if command in ['up', 'cd']:
        if cli_level:
            cli_level = cli_task.data.get('parent', None)
        continue
    if command in ['help', 'h', '?']:
        display_help()
        continue
    if command in ['cfg', 'config', 'conf']:
        edit_config()
    if command in ['add', 'new', 'a', 'n']:
        new_task = get_new_task(cli_level)
        if new_task:
            response = client.add_task(task=new_task)
            print(response)
            all_tasks = client.fetch_all()
        continue
    if command and 'tree'.startswith(command):
        print(yaml.dump(tree(all_tasks, cli_level)))
        continue
    match = pattern_two_part.match(command)
    if match:
        command, index = match.groups()
        index = int(index)
        try:
            task_id = cli_tasks[index].data.get('task_id')
        except IndexError:
            print(f"Invalid task {index}")
            continue
        if command in ['cd', 'go']:
            cli_level = task_id
        if command in ['delete', 'del', 'rm']:
            children = [task for task in all_tasks if task.data.get('parent', None) == task_id]
            if len(children) > 0:
                print(f"Deletion would orphan {len(children)} tasks")
                continue
            response = client.delete_task(task_id=task_id)
            print(response)
            all_tasks = client.fetch_all()
        if command in ["mod", "modify", "edit", 'ed', 'change', 'update', 'upd']:
            new_task = edit_task(task_id)
            if new_task:
                response = client.update_task(task=new_task)
                print(response)
                all_tasks = client.fetch_all()

print("Good Bye!")
