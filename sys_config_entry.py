class SysConfigEntry:
    _instance = None

    def __new__(cls, file_path):
        if cls._instance is None:
            cls._instance = super(SysConfigEntry, cls).__new__(cls)
            cls._instance.file_path = file_path
            cls._instance.config = cls._instance._parse_config_file()
        return cls._instance

    def _parse_config_file(self):
        config = {}
        try:
            with open(self.file_path, 'r') as file:
                for line in file:
                    line = line.strip()
                    if line and not line.startswith('#'):
                        key, value = line.split('=', 1)
                        config[key.strip()] = value.strip()
        except (IOError, OSError) as e:
            print(f"Failed to read config file: {e}")
        return config

    def get(self, key, default=None):
        return self.config.get(key, default)

    def __getitem__(self, key):
        return self.config[key]

    def __setitem__(self, key, value):
        self.config[key] = value

    def __delitem__(self, key):
        del self.config[key]

    def __contains__(self, key):
        return key in self.config

    def items(self):
        return self.config.items()

    def keys(self):
        return self.config.keys()

    def values(self):
        return self.config.values()

    def reload(self):
        self.config = self._parse_config_file()
