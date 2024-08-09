import json

class Cfg():
    def __init__(self, file_name='cfg.json'):
        self.file_name = file_name
        self.cfg = self.load()
    
    def load(self):
        try:
            with open(self.file_name) as file:
                return json.load(file)
        except Exception as error_message:
            print(f"Unable to read {self.filename}: {error_message}")

    def save(self):
        try:
            with open(self.file_name, 'w') as file:
                json.dump(self.cfg, file)
        except FileNotFoundError:
            raise Exception(f"Configuration file {self.file_name} not found.")
        except json.JSONDecodeError:
            raise Exception(f"Configuration file {self.file_name} is not a valid JSON.")
    
    def get(self, key, default=None):
        value = self.cfg.get(key, default)
        if str(value).lower() in ['true', 'false']:
            return str(value).lower() == 'true'
        return self.cfg.get(key, default)
    
    def set(self, key, value):
        value = value.rstrip().lstrip()
        try:
            value = int(value)
        except ValueError:
            pass
        if value.lower == 'true':
            value = True
        if value.lower == 'false':
            value = False
        try:
            self.cfg[key] = value
            self.save()
            return True
        except Exception:
            return False
    
    def keys(self):
        return self.cfg.keys()
    
    def items(self):
        return self.cfg.items()
    
    def values(self):
        return self.cfg.values()
    