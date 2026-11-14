from ecosystem.structural_manifest import FRONT_REQUIRED_PATHS, missing_paths


def test_all_four_fronts_are_declared():
    assert set(FRONT_REQUIRED_PATHS) == {"jarvis", "browser", "hypersynth", "orchestration"}
    assert all(paths for paths in FRONT_REQUIRED_PATHS.values())


def test_all_declared_structural_paths_exist():
    assert missing_paths() == ()
