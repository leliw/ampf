#/bin/sh

export ARTIFACT_REGISTRY_TOKEN=$(
    gcloud auth application-default print-access-token
)
export UV_PUBLISH_USERNAME=oauth2accesstoken
export UV_PUBLISH_PASSWORD="$ARTIFACT_REGISTRY_TOKEN"

rm -rf dist/
uv build
uv publish --index private-registry