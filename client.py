from tasks import TaskList
import json

client = TaskList()

def dump_tasks(task_list):
    if isinstance(task_list, dict):
        if "error" in task_list:
            print(task_list)
            print()
            #print(json.dumps(task_list, indent=2))
            return
        task_list = [task_list]
    for task in task_list:
        print(task)
    print()

print("Fetch All Test")
my_tasks = client.fetch_all()
dump_tasks(my_tasks)

print("Search Test 1")
my_tasks = client.search(query="Record")
dump_tasks(my_tasks)

print("Search Test 2")
my_tasks = client.search(field="Name",query="2")
dump_tasks(my_tasks)

print("fetch by id test")
task_id = "285008ba-ebb1-4765-91f7-55dc93fdf74f"
my_tasks = client.get_task(task_id=task_id)
dump_tasks(my_tasks)

#https://todo.coreyt.com/tasks/task_id/285008ba-ebb1-4765-91f7-55dc93fdf74f
#https://todo.coreyt.com/tasks/task_id/eb3d2e91-59ca-4f17-85fa-06e71c29b145
print("fetch by id test, no task_id")
task_id = "285008ba-ebb1-4765-91f7-55dc93fdf74f"
my_tasks = client.get_task()
dump_tasks(my_tasks)

print("fetch by id test, invalid task_id")
task_id = "285008ba-ebb1-4765-91f7-55dc93fdf74f"
my_tasks = client.get_task(task_id="test")
dump_tasks(my_tasks)

print("add task")
task = {"Name": "Dummy", "Status": "delete"}
my_tasks = client.add_task(task=task)
dump_tasks(my_tasks)
print("after add")
my_tasks = client.fetch_all()
dump_tasks(my_tasks)


print("delete task")
my_tasks = client.fetch_all()
for task in my_tasks:
    if task['Name'] == 'Dummy':
        my_tasks = client.delete_task(task_id=task["task_id"])
        dump_tasks(my_tasks)

print("after deletes")
my_tasks = client.fetch_all()
dump_tasks(my_tasks)