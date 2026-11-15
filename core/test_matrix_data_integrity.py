from .matrix_data import ObjectManifest, verify_authenticated_object


def test_authenticated_object_requires_valid_tag_and_all_chunks():
    chunks = (b"noryx", b"matrix", b"payload")
    manifest = ObjectManifest.from_chunks(chunks)
    key = b"test-key-material-32-bytes-long!!"
    tag = manifest.authenticate(key)
    assert verify_authenticated_object(manifest, chunks, key, tag)
    assert not verify_authenticated_object(manifest, (b"noryx", b"tampered", b"payload"), key, tag)
    assert not verify_authenticated_object(manifest, chunks, key, "0" * 64)


def test_authenticated_object_rejects_reordered_or_missing_chunks():
    chunks = (b"first", b"second")
    manifest = ObjectManifest.from_chunks(chunks)
    key = b"another-test-key-material-32bytes"
    tag = manifest.authenticate(key)
    assert not verify_authenticated_object(manifest, tuple(reversed(chunks)), key, tag)
    assert not verify_authenticated_object(manifest, chunks[:1], key, tag)


def test_authenticated_object_rejects_invalid_manifest_type():
    assert not verify_authenticated_object(None, (b"chunk",), b"0123456789abcdef", "0" * 64)
