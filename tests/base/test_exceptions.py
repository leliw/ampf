


from ampf.base.exceptions import KeyExistsException, KeyNotExistsException


def test_key_not_exists_to_str():
    # Given:
    e = KeyNotExistsException("foo", str, "bar")
    # When:
    s = str(e)
    # Then:
    assert "KeyNotExistsException: collection_name=foo, clazz=<class 'str'>, key=bar" == s

def test_key_exists_to_str():
    # Given:
    e = KeyExistsException("foo", str, "bar")
    # When:
    s = str(e)
    # Then:
    assert "KeyExistsException: collection_name=foo, clazz=<class 'str'>, key=bar" == s