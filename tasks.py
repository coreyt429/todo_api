"""
Module for managing tasks on todo.coreyt.com
"""
import json
import requests
from copy import deepcopy
from datetime import datetime, timezone, timedelta, time
import pytz
from zoneinfo import ZoneInfo
from tzlocal import get_localzone_name
from cfg import Cfg

class Task:
    """
    Class for Task
    data is the main element which replaced the previous task=dict() handling
    The purpose of the class is to provide printing and sorting standards
    type:
        
    """

    def __init__(self, task={}):
        self.status = 'not_started'
        self.task_id = None
        self.parent = None
        self.name = None
        self.data = self.apply_defaults(deepcopy(task))
        self.refresh()

    def refresh(self):
        self.status = self.data.get('status', 'not_started')
        self.task_id = self.data.get('task_id', None)
        self.parent = self.data.get('parent', None)
        self.name = self.data.get('name', None)

    def apply_defaults(self, task):
        defaults = {
            'parent': None,
            'status': 'not_started',
            'timestamps': {},
            'type': 'task'
        }
        for key, value in defaults.items():
            task[key] = task.get(key, value)
        if 'created' not in task['timestamps']:
            task['timestamps']['created'] = self.get_current_iso_timestamp()
        if 'due' not in task['timestamps']:
            task['timestamps']['due'] = self.get_gmt_iso_for_local_5pm()           
        return task
    
    def get_gmt_iso_for_local_5pm(self):
        # Get the local timezone object
        local_tz = ZoneInfo(get_localzone_name())
        local_now = datetime.now(local_tz)
        local_5pm = datetime.combine(local_now.date(), time(17, 0, 0)).replace(tzinfo=local_tz)
        gmt_5pm = local_5pm.astimezone(ZoneInfo("GMT"))
        return gmt_5pm.isoformat()
    
    def normalize_to_local_timezone(self, iso_timestamp):
        # Parse the ISO 8601 timestamp to a datetime object
        utc_dt = datetime.fromisoformat(iso_timestamp)

        # Ensure the datetime object is aware (i.e., it has timezone info)
        if utc_dt.tzinfo is None:
            utc_dt = utc_dt.replace(tzinfo=ZoneInfo("UTC"))
        else:
            utc_dt = utc_dt.astimezone(ZoneInfo("UTC"))

        # Get the local timezone object
        local_tz = ZoneInfo(get_localzone_name())

        # Convert the UTC datetime to local timezone
        local_dt = utc_dt.astimezone(local_tz)

        # Return the datetime object in ISO 8601 format
        return local_dt.isoformat()
    
    def get_current_iso_timestamp(self):
        return datetime.now(timezone.utc).isoformat()
    
    def updated(self, timestamp=None):
        if not timestamp:
            timestamp = self.get_current_iso_timestamp()
        # convert old timestamps
        if 'timestamps' not in self.data:
            self.data['timestamps'] = {}
        print(json.dumps(self.data))
        for ts in ['due', 'created', 'updated']:
            ts_old_name = f'ts_{ts}'
            if ts_old_name in self.data:
                self.data['timestamps'][ts] = self.data.pop(ts_old_name)
        print(json.dumps(self.data))
        self.data['timestamps']['updated'] = timestamp
        self.refresh()

    def  __str__(self):
        t = self.data
        ts = t.get('timestamps',{}).get('due', 'no due date')
        # look for old style due date
        if ts == 'no due date':
            ts = t.get('ts_due', 'no due date')
        if not ts == 'no due date':
            ts = self.normalize_to_local_timezone(ts)
        return f"{self.name} [{self.status}]: {ts}"
    
    def __lt__(self, other):
        return self.data['name'] < other.data['name']
    
    def __gt__(self, other):
        return self.data['name'] > other.data['name']

class TaskList:
    """
    Class for TaskList
    """
    def __init__(self):
        self.cfg = Cfg()
        self.tasks = self.fetch_all()
        self.categories = ['Today', 'This Week', 'This Month', 'This Quarter', 'Tasks', 'Projects']
 
    def as_object_list(self, items):
        items_list = list(items)
        new_items_list = []
        for idx, item in enumerate(items_list):
            new_items_list.append(Task(item))
        return new_items_list

    def fetch_all(self):
        self.tasks = self.as_object_list(self.get(path="task"))
        return self.tasks
    
    def search(self, **kwargs):
        query = kwargs.get('query', '-')
        if "field" in kwargs:
            field = kwargs['field']
            return self.as_object_list(self.get(path=f"task/search/{field}/{query}"))
        return self.as_object_list(self.get(path=f"task/search/{query}"))
    
    def get_task(self, **kwargs):
        task_id = kwargs.get('task_id', None)
        if task_id:
            return self.as_object_list(self.get(path=f"task/{task_id}"))
        return self.fetch_all()
    
    def add_task(self, **kwargs):
        task = kwargs.get('task', None)
        if not task:
            return {"error": "no_task"}
        # make it a task object to set defaults
        task = Task(task)
        print(json.dumps(task.data,indent=4))
        return self.post(path="task", payload=task.data)
    
    def update_task(self, **kwargs):
        print(kwargs.get('task'))
        task = kwargs.get('task', None)
        if not task:
            return {"error": "no_task"}
        # set updated timestamp
        task.updated()
        print(json.dumps(task.data,indent=4))
        return self.put(path=f"task/{task.data['task_id']}", payload=task.data)
    
    def delete_task(self, **kwargs):
        task_id = kwargs.get('task_id', None)
        if not task_id:
            return {"error": "no_task_id"}
        return self.delete(path=f"task/{task_id}")

    def task_by_id(self, task_id):
        """
        Grab a task from a list by id
        """
        if task_id in self.categories:
            return Task({"task_id": task_id, "name": task_id})
        for task in self.tasks:
            if task.data['task_id'] == task_id:
                return task
        return None

    def is_valid_iso_timestamp(self, timestamp_str):
        try:
            datetime.fromisoformat(timestamp_str)
            return True
        except ValueError:
            return False
    
    def is_current_day(self, timestamp):
        now = datetime.now()
        return timestamp.date() == now.date()

    def is_current_week(self, timestamp):
        now = datetime.now()
        start_of_week = now - timedelta(days=now.weekday())
        end_of_week = start_of_week + timedelta(days=6)
        return start_of_week.date() <= timestamp.date() <= end_of_week.date()

    def is_current_month(self, timestamp):
        now = datetime.now()
        return timestamp.year == now.year and timestamp.month == now.month

    def is_current_quarter(self, timestamp):
        now = datetime.now()
        current_quarter = (now.month - 1) // 3 + 1
        timestamp_quarter = (timestamp.month - 1) // 3 + 1
        return timestamp.year == now.year and current_quarter == timestamp_quarter

    def trim_completed(self, task_list):
        # if we are showing completed, do nothing, just retur
        if self.cfg.get("show_completed", True):
            return task_list
        new_list = []
        for task in task_list:
            if task.status != 'completed':
                new_list.append(task)
        return new_list

    def tasks_by_parent(self, parent=None):
        #FIXME: trim_completed here could cause orphans, as the client would
        #    no longer see the children and allow delete
        #    Options:
        #        - update api to refuse to delete server side if it would cause orphans
        #        - update tasks_by_parent to take an optional parameter to override 
        #            show_completed
        #    I think I like the first option best, as it protects the data store
        #
        if not parent:
            return self.categories
        # check for psuedo task for category, and normalize
        try:
            if parent.task_id in self.categories:
                parent = parent.task_id
           
        except Exception:
            pass
        if parent in self.categories:
            #{'name': 'Today', 'parent': None, 'status': 'in_progress', 'task_id': 'be444b84-47ed-42dd-9d87-c6e16b1e7f01', 'timestamps': {'created': '2024-08-05T14:08:28.779291+00:00', 'due': '2024-08-05T22:00:00+00:00', 'updated': '2024-08-09T06:46:22.891011+00:00'}, 'ts_created': '2024-08-05T14:08:28.779291+00:00', 'ts_due': '2024-08-05T22:00:00+00:00', 'ts_updated': '2024-08-05T14:51:37.561561+00:00', 'type': 'task'}
            if parent == 'Today':
                current_tasks_list = []
                for task in self.tasks:
                    timestamp_str = task.data.get('timestamps', {}).get('due', None)
                    if self.is_valid_iso_timestamp(timestamp_str):
                        timestamp = datetime.fromisoformat(timestamp_str)
                        if self.is_current_day(timestamp):
                            current_tasks_list.append(task)
                return self.trim_completed(current_tasks_list)
            if parent == 'This Week':
                current_tasks_list = []
                for task in self.tasks:
                    timestamp_str = task.data.get('timestamps', {}).get('due', None)
                    if self.is_valid_iso_timestamp(timestamp_str):
                        timestamp = datetime.fromisoformat(timestamp_str)
                        if self.is_current_week(timestamp):
                            current_tasks_list.append(task)
                return self.trim_completed(current_tasks_list)
            if parent == 'This Month':
                current_tasks_list = []
                for task in self.tasks:
                    timestamp_str = task.data.get('timestamps', {}).get('due', None)
                    if self.is_valid_iso_timestamp(timestamp_str):
                        timestamp = datetime.fromisoformat(timestamp_str)
                        if self.is_current_month(timestamp):
                            current_tasks_list.append(task)
                return self.trim_completed(current_tasks_list)
            if parent == 'This Quarter':
                current_tasks_list = []
                for task in self.tasks:
                    timestamp_str = task.data.get('timestamps', {}).get('due', None)
                    if self.is_valid_iso_timestamp(timestamp_str):
                        timestamp = datetime.fromisoformat(timestamp_str)
                        if self.is_current_quarter(timestamp):
                            current_tasks_list.append(task)
                return self.trim_completed(current_tasks_list)            
            if parent == 'Tasks':
                current_tasks_list = [task for task in sorted(self.tasks) if task.data.get('parent', None) == None]
                return self.trim_completed(current_tasks_list)
            if parent == 'Projects':
                current_tasks_list = [task for task in sorted(self.tasks) if task.data.get('type', None).lower() == 'project']
                return self.trim_completed(current_tasks_list)
            print(f"Teach me what should go in the children of {parent}")
            return []
        # assume this is a real parent_id
        current_tasks_list = [task for task in sorted(self.tasks) if task.data.get('parent', None) == parent]
        return  self.trim_completed(current_tasks_list)

    def task_by_name(self, task_name, parent=None):
        """
        Grab a task from a list by id
        """
        if task_name in self.categories:
            return Task({"task_id": task_name, "name": task_name})
        
        current_task_list = self.tasks_by_parent(parent)
        for task in current_task_list:
            if task.data['name'] == task_name:
                return task
        # not found, check children:
        for task in current_task_list:
            return self.task_by_name(task_name, task.data['task_id'])
        return None

    def get(self, **kwargs):
        kwargs['method'] = 'GET'
        return self.request(**kwargs)
    
    def put(self, **kwargs):
        kwargs['method'] = 'PUT'
        return self.request(**kwargs)
    
    def post(self, **kwargs):
        kwargs['method'] = 'POST'
        return self.request(**kwargs)
    
    def delete(self, **kwargs):
        kwargs['method'] = 'DELETE'
        return self.request(**kwargs)

    def request(self, **kwargs):
        method = kwargs.get('method', 'GET')
        url = f"{self.cfg.get('BASE_URL')}/{kwargs['path']}"
        #print(f"{method} {url}")
        # Prepare the headers
        headers = {
            "Authorization": f"Bearer {self.cfg.get('AUTH_TOKEN')}",
            "Content-Type": "application/json"
        }
        payload = kwargs.get('payload', {})
        
        if method == 'GET':
            response = requests.get(url, headers=headers, json=payload)
        elif method == 'POST':
            response = requests.post(url, headers=headers, json=payload)
        elif method == 'PUT':
            response = requests.put(url, headers=headers, json=payload)
        elif method == 'DELETE':
            response = requests.delete(url, headers=headers, json=payload)
        else:
            return {"error": "unsupported http method", "method": method}
            
        if response.ok:
            try:
                return response.json()
            except requests.exceptions.JSONDecodeError:
                return {"error": "invalid json", "content": response.content}
        else:
            return {"error": "failed http response", "status_code": response.status_code, "reason": response.reason, "content": response.content}

# Example usage:
if __name__ == "__main__":
    task_list = TaskList()
    tasks = task_list.fetch_all()
    print(tasks)
