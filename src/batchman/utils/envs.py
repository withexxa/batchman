import os
from typing import Dict, List, Optional, Union


def read_env_vars(env_vars: Union[List[str], str]) -> Dict[str, Optional[str]]:
    if isinstance(env_vars, str):
        env_vars = [env_vars]

    return {env_var: os.getenv(env_var) for env_var in env_vars}
