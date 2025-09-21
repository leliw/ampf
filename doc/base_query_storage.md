# BaseQueryStorage

Base class for storage implementations which store Pydantic objects and support query by filters.
It is an extension of `BaseStorage` and `BaseQuery` or `BaseAsyncStorage` and `BaseAsyncQuery`.

Type parameter:

* T - Pydantic class stored in storage

## Constructor

The constructor parameters are the same as in `BaseStorage` or `BaseAsyncStorage`.

## Implemented methods

These methods are implemented in `BaseQuery` & `BaseAsyncQuery`.

* where(self, field: str, op: str, value: str) -> BaseQuery[T]: Define filter for query
* find_nearest(self, embedding: List[float], limit: Optional[int] = None) -> Iterable[T]: Find nearest items by embedding
* get_all(self) -> Iterable[T]: Get all the values in the storage which match the filter

## Usage

Synchronous example:

```python
# Given: Stored two elements with the same value and one with other
storage.save(D(name="foo", value="beer"))
storage.save(D(name="bar", value="beer"))
storage.save(D(name="baz", value="wine"))
# When: Get all items with "beer"
ret = list(storage.where("value", "==", "beer").get_all())
# Then: Two items are returned
assert len(ret) == 2
assert ret[0].name == "foo"
assert ret[1].name == "bar"
```

Asynchronous example:

```python
# Given: Stored two elements with the same value and one with other
await storage.save(D(name="foo", value="beer"))
await storage.save(D(name="bar", value="beer"))
await storage.save(D(name="baz", value="wine"))
# When: Get all items with "beer"
ret = [item async for item in storage.where("value", "==", "beer").get_all()]
# Then: Two items are returned
assert len(ret) == 2
assert ret[0].name == "foo"
assert ret[1].name == "bar"
```

Where and find_nearest can be combined:

```python
# Given: Data with embedding
tc1 = D(name="test1", value="1", embedding=[1.0, 2.0, 3.0])
tc2 = D(name="test2", value="2", embedding=[4.0, 5.0, 6.0])
# And: They are stored
storage.put("test1", tc1)
storage.put("test2", tc2)
# When: Find nearest with extra filter
nearest = list([x for x in storage.where("name", "==", "test1").find_nearest(tc1.embedding or [])])
# Then: Only one is returned
assert len(nearest) == 1
assert nearest[0] == tc1
```
