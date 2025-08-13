import logging
from typing import Annotated

from dotenv import load_dotenv
from fastapi import Depends, FastAPI, Request
from fastapi.concurrency import asynccontextmanager

from ampf.base import BaseAsyncFactory, BaseFactory

from .config import ServerConfig

load_dotenv()

_log = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    config = ServerConfig()
    app.state.config = config
    if config.gcp_root_storage or config.gcp_bucket_name:
        from ampf.gcp import GcpAsyncFactory, GcpFactory

        app.state.factory = GcpFactory(root_storage=config.gcp_root_storage, bucket_name=config.gcp_bucket_name)
        app.state.async_factory = GcpAsyncFactory(
            root_storage=config.gcp_root_storage, bucket_name=config.gcp_bucket_name
        )

        _log.info(f"GCP storage: {config.gcp_root_storage}")
        _log.info(f"GCP bucket: {config.gcp_bucket_name}")
    else:
        from ampf.local import LocalFactory

        app.state.factory = LocalFactory(config.data_dir)
        _log.info(f"Local storage: {config.data_dir}")
    yield


def get_app(request: Request) -> FastAPI:
    return request.app


AppDep = Annotated[FastAPI, Depends(get_app)]


def get_server_config(app: AppDep) -> ServerConfig:
    return app.state.config


ConfigDep = Annotated[ServerConfig, Depends(get_server_config)]


def get_factory(app: FastAPI = Depends(get_app)) -> BaseFactory:
    return app.state.factory


FactoryDep = Annotated[BaseFactory, Depends(get_factory)]


def get_async_factory(app: FastAPI = Depends(get_app)) -> BaseAsyncFactory:
    return app.state.async_factory


AsyncFactoryDep = Annotated[BaseAsyncFactory, Depends(get_async_factory)]
