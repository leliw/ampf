from json import JSONDecodeError
from pathlib import Path
from typing import List, Type

import httpx2
from fastapi.testclient import TestClient
from pydantic import BaseModel


class ApiTestClient(TestClient):
    def _assert_response(self, response: httpx2.Response, status_code: int | None = None) -> None:
        if status_code is not None and response.status_code != status_code:
            try:
                r = response.json()
            except JSONDecodeError:
                r = response.text
            assert response.status_code == status_code, (
                f"Expected status code {status_code}, got {response.status_code}: {r}"
            )

    def get(self, url: httpx2._types.URLTypes | Path, status_code: int | None = None, **kwargs) -> httpx2.Response:
        if isinstance(url, Path):
            url = str(url)
        response = super().get(url, **kwargs)
        self._assert_response(response, status_code)
        return response

    def get_typed[T: BaseModel](
        self, url: httpx2._types.URLTypes | Path, status_code: int, ret_clazz: Type[T], **kwargs
    ) -> T:
        response = self.get(url, status_code=status_code, **kwargs)
        resp = response.json()
        return ret_clazz.model_validate(resp)

    def get_typed_list[T: BaseModel](
        self, url: httpx2._types.URLTypes | Path, status_code: int, ret_clazz: Type[T], **kwargs
    ) -> List[T]:
        response = self.get(url, status_code=status_code, **kwargs)
        resp = response.json()
        if not isinstance(resp, list):
            raise ValueError("Response is not a list")
        return [ret_clazz.model_validate(item) for item in resp]

    def _prepare_parameters(self, kwargs):
        if "json" in kwargs and isinstance(kwargs["json"], BaseModel):
            kwargs["json"] = kwargs["json"].model_dump(mode="json", include=kwargs["json"].model_fields_set)
        if "data" in kwargs and isinstance(kwargs["data"], BaseModel):
            kwargs["data"] = kwargs["data"].model_dump_json(include=kwargs["data"].model_fields_set)

    def post(self, url: httpx2._types.URLTypes | Path, status_code: int | None = None, **kwargs) -> httpx2.Response:
        if isinstance(url, Path):
            url = str(url)
        self._prepare_parameters(kwargs)
        response = super().post(url, **kwargs)
        self._assert_response(response, status_code)
        return response

    def post_typed[T: BaseModel](
        self, url: httpx2._types.URLTypes | Path, status_code: int, ret_clazz: Type[T], **kwargs
    ) -> T:
        response = self.post(url, status_code=status_code, **kwargs)
        resp = response.json()
        return ret_clazz.model_validate(resp)

    def post_typed_list[T: BaseModel](
        self, url: httpx2._types.URLTypes | Path, status_code: int, ret_clazz: Type[T], **kwargs
    ) -> List[T]:
        response = self.post(url, status_code=status_code, **kwargs)
        resp = response.json()
        if not isinstance(resp, list):
            raise ValueError("Response is not a list")
        return [ret_clazz.model_validate(item) for item in resp]

    def put(self, url: httpx2._types.URLTypes | Path, status_code: int | None = None, **kwargs) -> httpx2.Response:
        if isinstance(url, Path):
            url = str(url)
        self._prepare_parameters(kwargs)
        response = super().put(url, **kwargs)
        self._assert_response(response, status_code)
        return response

    def put_typed[T: BaseModel](
        self, url: httpx2._types.URLTypes | Path, status_code: int, ret_clazz: Type[T], **kwargs
    ) -> T:
        response = self.put(url, status_code=status_code, **kwargs)
        resp = response.json()
        return ret_clazz.model_validate(resp)

    def patch(self, url: httpx2._types.URLTypes | Path, status_code: int | None = None, **kwargs) -> httpx2.Response:
        if isinstance(url, Path):
            url = str(url)
        self._prepare_parameters(kwargs)
        response = super().patch(url, **kwargs)
        self._assert_response(response, status_code)
        return response

    def patch_typed[T: BaseModel](
        self, url: httpx2._types.URLTypes | Path, status_code: int, ret_clazz: Type[T], **kwargs
    ) -> T:
        response = self.patch(url, status_code=status_code, **kwargs)
        resp = response.json()
        return ret_clazz.model_validate(resp)

    def delete(self, url: httpx2._types.URLTypes | Path, status_code: int | None = None, **kwargs) -> httpx2.Response:
        if isinstance(url, Path):
            url = str(url)
        response = super().delete(url, **kwargs)
        self._assert_response(response, status_code)
        return response
