"""
Module for managing tasks on todo.coreyt.com
"""
import json
import requests

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

    def fetch_all(self):
        return self.get(path="tasks")
    
    def search(self, **kwargs):
        query = kwargs.get('query', '-')
        if "field" in kwargs:
            field = kwargs['field']
            #                     /tasks/search/Name/2"
            return self.get(path=f"tasks/search/{field}/{query}")
        return self.get(path=f"tasks/search/{query}")
    
    def get_task(self, **kwargs):
        task_id = kwargs.get('task_id', None)
        if task_id:
            return self.get(path=f"tasks/task_id/{task_id}")
        return self.fetch_all()
    
    def add_task(self, **kwargs):
        task = kwargs.get('task', None)
        if not task:
            return {"error": "no_task"}
        return self.post(path="tasks", payload=task)
    
    def delete_task(self, **kwargs):
        task_id = kwargs.get('task_id', None)
        if not task_id:
            return {"error": "no_task_id"}
        return self.post(path=f"tasks/delete/{task_id}")
    
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
        print(url)
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
