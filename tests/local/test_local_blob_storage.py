

import os

from ampf.local.local_blob_storage import LocalBlobStorage


def test_download_blob_without_metadata():
    # Given: A test file without metadata
    path = "./tests/data/"
    filename = "test.txt"
    assert os.path.exists(path + filename)
    # And: A storage
    storage = LocalBlobStorage(path, root_path=".")
    # When: Download the file
    blob = storage.download(filename)
    # Then: A blob is downloaded
    assert blob
    # And: The metadata is created from filename
    assert blob.metadata.filename == filename
    assert blob.metadata.content_type == "text/plain"

