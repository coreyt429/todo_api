"""
Module for managing tasks on todo.coreyt.com
"""
import json
import requests
from copy import deepcopy
from datetime import datetime, timezone, timedelta, time
import pytz
from tzlocal import get_localzone




class Task:
    """
    Class for Task
    data is the main element which replaced the previous task=dict() handling
    The purpose of the class is to provide printing and sorting standards
    """

    def __init__(self, task={}):
        self.data = self.apply_defaults(deepcopy(task))
    
    def apply_defaults(self, task):
        defaults = {
            'parent': None,
            'status': 'not_started',
            'ts_created': self.get_current_iso_timestamp(),
            'ts_due': self.get_gmt_iso_for_local_5pm(), 
            'type': 'task'
        }
        for key, value in defaults.items():
            task[key] = task.get(key, value)
                    
        return task
    
    def get_gmt_iso_for_local_5pm(self, days=0):
        # Get the local timezone object from the system
        local_tz = get_localzone()

        # Get the current date in the local timezone and add the specified number of days
        local_now = datetime.now(local_tz) + timedelta(days=days)

        # Create a datetime object for 5:00 PM today in the local timezone
        local_5pm = local_tz.localize(datetime.combine(local_now.date(), time(17, 0, 0)))

        # Convert the local 5:00 PM time to UTC
        utc_5pm = local_5pm.astimezone(pytz.utc)

        # Return the UTC datetime object in ISO 8601 format
        return utc_5pm.isoformat()
    
    def normalize_to_local_timezone(self, iso_timestamp):
        # Parse the ISO 8601 timestamp to a datetime object
        utc_dt = datetime.fromisoformat(iso_timestamp)

        # Ensure the datetime object is aware (i.e., it has timezone info)
        if utc_dt.tzinfo is None:
            utc_dt = utc_dt.replace(tzinfo=pytz.utc)
        else:
            utc_dt = utc_dt.astimezone(pytz.utc)

        # Get the local timezone object
        local_tz = get_localzone()

        # Convert the UTC datetime to local timezone
        local_dt = utc_dt.astimezone(local_tz)

        # Return the datetime object in ISO 8601 format
        return local_dt.isoformat()
    
    def get_current_iso_timestamp(self):
        return datetime.now(timezone.utc).isoformat()
    
    def updated(self, timestamp=None):
        if not timestamp:
            timestamp = self.get_current_iso_timestamp()
        self.data['ts_updated'] = timestamp

    def  __str__(self):
        t = self.data
        ts = t.get('ts_due', 'no due date')
        if not ts == 'no due date':
            ts = self.normalize_to_local_timezone(ts)
        return f"{t['name']} [{t['status']}]: {ts}"
    
    def __lt__(self, other):
        return self.data['name'] < other.data['name']
    
    def __gt__(self, other):
        return self.data['name'] > other.data['name']

class TaskList:
    """
    Class for TaskList
    """
    def __init__(self):
        # Load configuration
        try:
            with open('cfg.json') as file:
                self.cfg = json.load(file)
        except FileNotFoundError:
            raise Exception("Configuration file 'cfg.json' not found.")
        except json.JSONDecodeError:
            raise Exception("Configuration file 'cfg.json' is not a valid JSON.")

    def as_object_list(self, items):
        items_list = list(items)
        new_items_list = []
        for idx, item in enumerate(items_list):
            new_items_list.append(Task(item))
        return new_items_list

    def fetch_all(self):
        return self.as_object_list(self.get(path="tasks"))
    
    def search(self, **kwargs):
        query = kwargs.get('query', '-')
        if "field" in kwargs:
            field = kwargs['field']
            #                     /tasks/search/Name/2"
            return self.as_object_list(self.get(path=f"tasks/search/{field}/{query}"))
        return self.as_object_list(self.get(path=f"tasks/search/{query}"))
    
    def get_task(self, **kwargs):
        task_id = kwargs.get('task_id', None)
        if task_id:
            return self.as_object_list(self.get(path=f"tasks/task_id/{task_id}"))
        return self.fetch_all()
    
    def add_task(self, **kwargs):
        task = kwargs.get('task', None)
        if not task:
            return {"error": "no_task"}
        # make it a task object to set defaults
        task = Task(task)
        print(json.dumps(task.data,indent=4))
        return self.post(path="tasks", payload=task.data)
    
    def update_task(self, **kwargs):
        print(kwargs.get('task'))
        task = kwargs.get('task', None)
        if not task:
            return {"error": "no_task"}
        # set updated timestamp
        task.updated()
        print(json.dumps(task.data,indent=4))
        return self.put(path=f"tasks/{task.data['task_id']}", payload=task.data)
    
    def delete_task(self, **kwargs):
        task_id = kwargs.get('task_id', None)
        if not task_id:
            return {"error": "no_task_id"}
        return self.delete(path=f"tasks/delete/{task_id}")
    
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
        url = f"{self.cfg['BASE_URL']}/{kwargs['path']}"
        print(f"{method} {url}")
        # Prepare the headers
        headers = {
            "Authorization": f"Bearer {self.cfg['AUTH_TOKEN']}",
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
