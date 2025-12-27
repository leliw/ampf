from typing import List, Optional, Type

import httpx
from fastapi.testclient import TestClient
from pydantic import BaseModel


class ApiTestClient(TestClient):
    def get(self, url: httpx._types.URLTypes, status_code: Optional[int] = None, **kwargs) -> httpx.Response:
        response = super().get(url, **kwargs)
        if status_code is not None:
            assert response.status_code == status_code, f"Expected status code {status_code}, got {response.status_code}"
        return response

    def get_typed[T: BaseModel](self, url: httpx._types.URLTypes, status_code: int, ret_clazz: Type[T], **kwargs) -> T:
        response = self.get(url, status_code=status_code, **kwargs)
        resp = response.json()
        return ret_clazz.model_validate(resp)

    def get_typed_list[T: BaseModel](
        self, url: httpx._types.URLTypes, status_code: int, ret_clazz: Type[T], **kwargs
    ) -> List[T]:
        response = self.get(url, status_code=status_code, **kwargs)
        resp = response.json()
        if not isinstance(resp, list):
            raise ValueError("Response is not a list")
        return [ret_clazz.model_validate(item) for item in resp]

    def post(self, url: httpx._types.URLTypes, status_code: Optional[int] = None, **kwargs) -> httpx.Response:
        if "json" in kwargs and issubclass(kwargs["json"].__class__, BaseModel):
            kwargs["json"] = kwargs["json"].model_dump(mode="json")
        response = super().post(url, **kwargs)
        if status_code is not None:
            assert response.status_code == status_code, f"Expected status code {status_code}, got {response.status_code}"
        return response

    def post_typed[T: BaseModel](self, url: httpx._types.URLTypes, status_code: int, ret_clazz: Type[T], **kwargs) -> T:
        response = self.post(url, status_code=status_code, **kwargs)
        resp = response.json()
        return ret_clazz.model_validate(resp)

    def post_typed_list[T: BaseModel](self, url: httpx._types.URLTypes, status_code: int, ret_clazz: Type[T], **kwargs) -> List[T]:
        response = self.post(url, status_code=status_code, **kwargs)
        resp = response.json()
        if not isinstance(resp, list):
            raise ValueError("Response is not a list")
        return [ret_clazz.model_validate(item) for item in resp]

    def put(self, url: httpx._types.URLTypes, status_code: Optional[int] = None, **kwargs) -> httpx.Response:
        if "json" in kwargs and issubclass(kwargs["json"].__class__, BaseModel):
            kwargs["json"] = kwargs["json"].model_dump(mode="json")
        response = super().put(url, **kwargs)
        if status_code is not None:
            assert response.status_code == status_code, f"Expected status code {status_code}, got {response.status_code}"
        return response

    def put_typed[T: BaseModel](self, url: httpx._types.URLTypes, status_code: int, ret_clazz: Type[T], **kwargs) -> T:
        response = self.put(url, status_code=status_code, **kwargs)
        resp = response.json()
        return ret_clazz.model_validate(resp)

    def patch(self, url: httpx._types.URLTypes, status_code: Optional[int] = None, **kwargs) -> httpx.Response:
        if "json" in kwargs and issubclass(kwargs["json"].__class__, BaseModel):
            kwargs["json"] = kwargs["json"].model_dump(mode="json")
        response = super().patch(url, **kwargs)
        if status_code is not None:
            assert response.status_code == status_code, f"Expected status code {status_code}, got {response.status_code}"
        return response

    def patch_typed[T: BaseModel](self, url: httpx._types.URLTypes, status_code: int, ret_clazz: Type[T], **kwargs) -> T:
        response = self.patch(url, status_code=status_code, **kwargs)
        resp = response.json()
        return ret_clazz.model_validate(resp)
    
    def delete(self, url: httpx._types.URLTypes, status_code: Optional[int] = None, **kwargs) -> httpx.Response:
        response = super().delete(url, **kwargs)
        if status_code is not None:
            assert response.status_code == status_code, f"Expected status code {status_code}, got {response.status_code}"
        return response