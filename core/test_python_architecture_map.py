from core.python_architecture_map import PythonArchitectureMapper


def test_mapper_builds_deterministic_module_edges_and_surface_map(tmp_path):
    package = tmp_path / "sample"
    package.mkdir()
    (package / "__init__.py").write_text("from . import worker\n", encoding="utf-8")
    (package / "worker.py").write_text(
        "import os\nimport socket\n"
        "def run():\n    return socket.gethostname()\n"
        "if __name__ == '__main__':\n    run()\n",
        encoding="utf-8",
    )
    report = PythonArchitectureMapper().inspect(tmp_path)
    worker = next(item for item in report.modules if item.module == "sample.worker")
    assert worker.entrypoint
    assert "run" in worker.definitions
    assert "network" in worker.capability_surfaces
    assert "process_and_filesystem" in worker.capability_surfaces
    assert ("sample", "sample.worker") in report.internal_edges
    assert report.files_scanned == 2


def test_mapper_never_follows_symlinks_and_reports_parse_errors(tmp_path):
    (tmp_path / "broken.py").write_text("def broken(:\n", encoding="utf-8")
    external = tmp_path.parent / "external.py"
    external.write_text("import subprocess\n", encoding="utf-8")
    (tmp_path / "linked.py").symlink_to(external)
    report = PythonArchitectureMapper().inspect(tmp_path)
    assert report.files_scanned == 0
    assert report.parse_errors == ("parse_error:broken.py:SyntaxError",)


def test_mapper_enforces_bounded_file_count(tmp_path):
    for name in ("a.py", "b.py", "c.py"):
        (tmp_path / name).write_text("VALUE = 1\n", encoding="utf-8")
    report = PythonArchitectureMapper(max_files=2).inspect(tmp_path)
    assert report.files_scanned == 2
    assert "file_limit_reached" in report.parse_errors
