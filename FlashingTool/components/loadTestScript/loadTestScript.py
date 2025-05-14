import configparser

class LoadTestScript:
    def __init__(self, ini_file_path):
        self.ini_file_path = ini_file_path
        self.config = configparser.ConfigParser()
        self.config.read(self.ini_file_path)

    def load_script(self):
        for section in self.config.sections():
            print(f"[{section}]")
            for option in self.config.options(section):
                value = self.config.get(section, option)
                print(f"{option} = {value}")