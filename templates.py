"""
Module for managing templates on todo.coreyt.com
"""
import json
import requests
from copy import deepcopy
from datetime import datetime, timezone, timedelta, time
import pytz
from zoneinfo import ZoneInfo
from tzlocal import get_localzone_name
from cfg import Cfg

class Template:
    """
    Class for Template
    data is the main element which replaced the previous template=dict() handling
    The purpose of the class is to provide printing and sorting standards

    type:
        daily: daily reoccuring tasks, like morning routine items
        monthly: monthly reoccuring tasks
    class: 
        task: default class, creates a task based on the template in the parent task 
            identified in the template
        virtual: creates a task pointer for today, this week, or this month to link a task 
            to those lists
            

    """

    def __init__(self, template={}):
        self.type = None
        self.name = None
        self.days = None
        self.data = self.apply_defaults(deepcopy(template))
        self.refresh()
    
    def refresh(self):
        self.type = self.data['type']
        self.name = self.data['name']
        self.days = self.data['days']
    
    def apply_defaults(self, template):
        defaults = {
            'type': 'daily',
            'days': list(range(7))
        }
        for key, value in defaults.items():
            template[key] = template.get(key, value)           
        return template
    
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
        return f"{self.name} [{self.type}]: {ts}"
    
    def __lt__(self, other):
        return self.data['name'] < other.data['name']
    
    def __gt__(self, other):
        return self.data['name'] > other.data['name']

class TemplateList:
    """
    Class for TemplateList
    """
    def __init__(self):
        # Load configuration
        self.cfg = Cfg()
        self.templates = self.fetch_all()

    def as_object_list(self, items):
        items_list = list(items)
        new_items_list = []
        for idx, item in enumerate(items_list):
            new_items_list.append(Template(item))
        return new_items_list

    def fetch_all(self):
        self.templates = self.as_object_list(self.get(path="template"))
        return self.templates
    
    def search(self, **kwargs):
        query = kwargs.get('query', '-')
        if "field" in kwargs:
            field = kwargs['field']
            return self.as_object_list(self.get(path=f"template/search/{field}/{query}"))
        return self.as_object_list(self.get(path=f"template/search/{query}"))
    
    def get_template(self, **kwargs):
        template_id = kwargs.get('template_id', None)
        if template_id:
            return self.as_object_list(self.get(path=f"template/{template_id}"))
        return self.fetch_all()
    
    def add_template(self, **kwargs):
        template = kwargs.get('template', None)
        if not template:
            return {"error": "no_template"}
        # make it a template object to set defaults
        template = Template(template)
        print(json.dumps(template.data,indent=4))
        return self.post(path="template", payload=template.data)
    
    def update_template(self, **kwargs):
        print(kwargs.get('template'))
        template = kwargs.get('template', None)
        if not template:
            return {"error": "no_template"}
        # set updated timestamp
        template.updated()
        print(json.dumps(template.data,indent=4))
        return self.put(path=f"template/{template.data['template_id']}", payload=template.data)
    
    def delete_template(self, **kwargs):
        template_id = kwargs.get('template_id', None)
        if not template_id:
            return {"error": "no_template_id"}
        return self.delete(path=f"template/{template_id}")
    
    def template_by_id(self, template_id):
        """
        Grab a template from a list by id
        """
        for template in self.templates:
            if template.data['template_id'] == template_id:
                return template
        return None

    def templates_by_parent(self, parent=None):
        if not parent:
            current_templates_list = [template for template in self.templates if not template.data.get('parent', None)]
        else:
            current_templates_list = [template for template in sorted(self.templates) if template.data.get('parent', None) == parent]
        return current_templates_list

    def template_by_name(self, template_name, parent=None):
        """
        Grab a template from a list by id
        """
        current_template_list = self.templates_by_parent(parent)
        for template in current_template_list:
            if template.data['name'] == template_name:
                return template
        # not found, check children:
        for template in current_template_list:
            return self.template_by_name(template_name, template.data['template_id'])
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
    template_list = TemplateList()
    templates = template_list.fetch_all()
    print(templates)
