from io import BytesIO
from ampf.base.blob_model import Blob, BlobCreate


def test_get_content():
    # Given: A blob with data
    blob = Blob(name="foo", data=BytesIO(b"bar"))
    # When: I get the content
    content = blob.content
    # Then: The content is correct
    assert content == b"bar"

def test_set_content():
    # Given: A blob with content
    blob = Blob(name="foo", content=b"bar")
    # When: I set the content
    blob.content = b"baz"
    # Then: The content is correct
    assert blob.content == b"baz"

def test_blob_create_from_content_without_content_type():
    # When: Create from content without content-type
    blob_create = BlobCreate.from_content(b"bar")
    # Then: Content type is default
    assert blob_create.metadata
    assert blob_create.metadata.content_type == "application/octet-stream"

def test_blob_create_from_content_with_content_type():
    # When: Create from content with content-type
    blob_create = BlobCreate.from_content(b"bar", "text/plain")
    # Then: Content type is correct
    assert blob_create.metadata
    assert blob_create.metadata.content_type == "text/plain"

