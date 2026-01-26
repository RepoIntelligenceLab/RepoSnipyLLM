import yaml
from pathlib import Path


class CommonUtils:

    @classmethod
    def find_root_dir(cls):
        """
        Find the root directory of the project.
        :return:
        """
        current_dir = Path(__file__).parent
        while current_dir.name != "RepoSnipyLLM":
            current_dir = current_dir.parent
        return current_dir

    @classmethod
    def get_sys_config(cls):
        """
        Get system configuration
        :return:
        """
        project_root = cls.find_root_dir()
        config_path = project_root / "config.yaml"
        config = yaml.safe_load(config_path.read_text())
        return config
