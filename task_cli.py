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
        Today    - tasks of any type that have a due date today
        Week     - tasks of any type that have a due date this week
        Month    - tasks of any type that have a due date this month
        Quarter  - tasks of any type that have a due date this quarter
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

def set_task_key(task, key, value):
    # Split the key by periods
    keys = key.split('.')
    d = task.data
    current_dict = d
    # Iterate through the keys except the last one to create or traverse nested dictionaries
    for k in keys[:-1]:
        if k not in current_dict:
            current_dict[k] = {}
        current_dict = current_dict[k]

    # Set the final key to the value
    current_dict[keys[-1]] = value

def edit_task(task_id):
    print(f"edit_task({task_id})")
    while True:
        task = client.task_by_id(task_id)
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
            # user set_task_key to handle nested keys like timestamps.due
            set_task_key(task, key, value)
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
        try:
            print(f"parent: {parent_id}")
            task["parent"] = parent_id
            parent = client.task_by_id(parent_id)
            name = parent.data.get('name', None)
        except AttributeError:
            task.pop('parent')
            name = 'Root'
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

def display_menu(tasks, parent=None):
    """
    show menu
    """
    print()    
    parent_task = client.task_by_id(parent)
    if not parent:
        print("Categories:")
    elif parent in client.categories:
        print(f"Tasks for {parent}")
    else:
        print(f"SubTasks of {parent_task}")
    current_tasks_list = client.tasks_by_parent(parent)
    for idx, task in enumerate(current_tasks_list):
        print(f"{idx:3}: {task}")
    print()
    
    return current_tasks_list

def goto_cli_context(parent, input_val):
    print(f"goto_cli_context({parent}, {input_val})")
    child_list = client.tasks_by_parent(parent)
    print(f"child_list: {child_list}")
    # Is this a string we can turn into a number?
    if input_val.isdigit():
        try:
            input_val = int(input_val) 
        except IndexError:
            pass
    # do we have anumber yet?
    if not isinstance(input_val, int) or input_val >=len(child_list):
        print(f"Invalid task {input_val}")
        return None
    print(f"input_val: {input_val}")
    print(f"returning: {child_list[input_val]}")
    return child_list[input_val]
    
def process_command(parent, input_text):
    cli_task = client.task_by_id(parent)
    cli_tasks = client.tasks_by_parent(cli_task)
    if input_text.isdigit():
        return goto_cli_context(parent, input_text)
    if input_text and 'quit'.startswith(input_text):
        return 'exit'
    if input_text in ['up', 'cd']:
        if cli_task:
            return cli_task.parent
        return None
    if input_text in ['help', 'h', '?']:
        display_help()
        return None
    if input_text in ['cfg', 'config', 'conf']:
            edit_config()
    if input_text in ['add', 'new', 'a', 'n']:
        new_task = get_new_task(parent)
        if new_task:
            response = client.add_task(task=new_task)
            print(response)
            client.fetch_all()
        return parent
    if input_text and 'tree'.startswith(input_text):
        print(yaml.dump(tree(client.tasks, cli_level)))
        return parent
    match = pattern_two_part.match(input_text)
    if match:
        command, index = match.groups()
        index = int(index)
    try:
        print(cli_tasks[index])
        task_id = cli_tasks[index].data.get('task_id')
    except IndexError:
        print(cli_tasks)
        print(f"IndexError: Invalid task {index}")
        return parent
    except AttributeError:
        print(f"AttributeError: Invalid task {index}")
        return parent
    if command in ['cd', 'go']:
        return goto_cli_context(parent, index)
    if command in ['delete', 'del', 'rm']:
        children = client.tasks_by_parent(cli_tasks[index])
        if len(children) > 0:
            print(f"Deletion would orphan {len(children)} tasks")
            return parent
        response = client.delete_task(task_id=task_id)
        print(response)
        client.fetch_all()
        return parent
    if command in ["mod", "modify", "edit", 'ed', 'change', 'update', 'upd']:
        new_task = edit_task(task_id)
        if new_task:
            response = client.update_task(task=new_task)
            print(response)
            client.fetch_all()
            return parent
    return False # return False to quit, triggering a loop break in the caller

if __name__ == "__main__":
    pattern_field = re.compile(r'(\w+)\s*:\s*(.*)')


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
        cli_level = client.task_by_name(args.parent)
        if cli_level and not isinstance(cli_level, str):
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
        try:
            cli_level = cli_task.task_id
        except NameError:
            cli_task = client.task_by_id(cli_level)
        except AttributeError:
            cli_task = client.task_by_id(cli_level)
        cli_tasks = display_menu(all_tasks, cli_level)
        cli_task = client.task_by_id(cli_level)
        command = input("Enter command: ")
        cli_task = process_command(cli_level, command)
        try:
            cli_level = cli_task.task_id
        except AttributeError:
            cli_level = cli_task

        if cli_task == 'exit':
            break
    print("Good Bye!")
