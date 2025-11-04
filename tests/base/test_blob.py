from ampf.base.blob_model import Blob


def test_get_content():
    # Given: A blob with data
    blob = Blob(name="foo", data=b"bar")
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