from s3_file_uploader import LocalObjectStore, Uploader


def test_upload_dedupes_by_digest():
    store = LocalObjectStore()
    u = Uploader(store)
    data = b"hello world"
    first = u.upload(data)
    second = u.upload(data)
    assert first["new"] is True
    assert second["new"] is False
    assert second["digest"] == first["digest"]
    assert u.duplicates == 1


def test_verify_detects_corruption():
    store = LocalObjectStore()
    u = Uploader(store)
    u.upload(b"intact")
    assert u.verify("invalid", b"anything") is False


def test_verify_roundtrip():
    store = LocalObjectStore()
    u = Uploader(store)
    data = b"sensitive bytes"
    res = u.upload(data)
    assert u.verify(res["digest"], data) is True
