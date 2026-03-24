from __future__ import annotations

import os
from typing import Any

from hatchling.builders.hooks.plugin.interface import BuildHookInterface


class build_hook(BuildHookInterface):
    def initialize(self, version: str, build_data: dict[str, Any]) -> None:
        del version

        if self.target_name != "sdist":
            return

        gitignore_path = os.path.join(self.root, ".gitignore")
        force_include = build_data.get("force_include", {})
        if gitignore_path in force_include:
            force_include.pop(gitignore_path, None)
