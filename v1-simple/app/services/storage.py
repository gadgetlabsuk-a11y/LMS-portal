import os
from pathlib import Path
from typing import Protocol, runtime_checkable

@runtime_checkable
class StorageBackend(Protocol):
    def put(self, key: str, data: bytes, content_type: str) -> str: ...
    def get(self, key: str) -> bytes: ...
    def delete(self, key: str) -> None: ...
    def signed_url(self, key: str, expires_s: int = 300) -> str: ...


class LocalStorage:
    def __init__(self, base_dir: str = "uploads"):
        self.base_dir = Path(base_dir)
        self.base_dir.mkdir(parents=True, exist_ok=True)

    def put(self, key: str, data: bytes, content_type: str) -> str:
        path = self.base_dir / key
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)
        return key

    def get(self, key: str) -> bytes:
        return (self.base_dir / key).read_bytes()

    def delete(self, key: str) -> None:
        p = self.base_dir / key
        if p.exists():
            p.unlink()

    def signed_url(self, key: str, expires_s: int = 300) -> str:
        return f"/uploads/{key}"


class S3Storage:
    def __init__(self, bucket: str, region: str = "eu-west-2"):
        self.bucket = bucket
        self.region = region

    def _client(self):
        import boto3
        return boto3.client("s3", region_name=self.region)

    def put(self, key: str, data: bytes, content_type: str) -> str:
        self._client().put_object(Bucket=self.bucket, Key=key, Body=data, ContentType=content_type)
        return key

    def get(self, key: str) -> bytes:
        resp = self._client().get_object(Bucket=self.bucket, Key=key)
        return resp["Body"].read()

    def delete(self, key: str) -> None:
        self._client().delete_object(Bucket=self.bucket, Key=key)

    def signed_url(self, key: str, expires_s: int = 300) -> str:
        return self._client().generate_presigned_url(
            "get_object",
            Params={"Bucket": self.bucket, "Key": key},
            ExpiresIn=expires_s,
        )


def get_storage() -> LocalStorage | S3Storage:
    backend = os.environ.get("STORAGE_BACKEND", "local")
    if backend == "s3":
        return S3Storage(
            bucket=os.environ["S3_BUCKET"],
            region=os.environ.get("S3_REGION", "eu-west-2"),
        )
    return LocalStorage(base_dir=os.environ.get("UPLOAD_DIR", "uploads"))
