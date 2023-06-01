from contextlib import contextmanager
from pathlib import Path

from invoke import task, Context


class Paths:
    here = Path(__file__).parent
    repo_root = here

    @staticmethod
    @contextmanager
    def cd(c: Context, p: Path):
        with c.cd(str(p)):
            yield


@task
def compile_requirements(c):
    with Paths.cd(c, Paths.repo_root):
        c.run("pip-compile --resolver=backtracking -v -o requirements.txt")
