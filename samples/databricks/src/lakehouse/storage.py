"""Restricted immutable artifacts and conditional cursor commits. No secret logging."""
import hashlib
import json
import os
import tempfile
from contextlib import contextmanager
from pathlib import Path
from urllib.parse import urlparse


class Conflict(RuntimeError):
    pass


def encode(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()


class Store:
    def json(self, key):
        data, etag = self.get(key)
        return (json.loads(data), etag) if data is not None else (None, None)

    def immutable(self, key, value):
        data = encode(value)
        try:
            self.put(key, data, None)
        except Conflict:
            if self.get(key)[0] != data:
                raise Conflict("Immutable artifact differs") from None

    @contextmanager
    def lock(self, owner, scope="customers"):
        import re
        if not re.fullmatch(r"[a-z_]+", scope):
            raise ValueError("Unsafe lock scope")
        # Never steal an apparently old lock: a paused writer may still be alive.
        self.put(f"locks/{scope}.json", encode({"owner": owner}), None)
        try:
            yield
        finally:
            self.delete(f"locks/{scope}.json")


class LocalStore(Store):
    """Local integration adapter. All artifacts stay under an explicit root."""
    def __init__(self, root):
        self.root = Path(root).resolve()
        self.root.mkdir(parents=True, exist_ok=True)

    def path(self, key):
        p = (self.root / key).resolve()
        if not p.is_relative_to(self.root):
            raise ValueError("Unsafe artifact key")
        return p

    def uri(self, key):
        return self.path(key).as_uri()

    def get(self, key):
        try:
            data = self.path(key).read_bytes()
            return data, hashlib.sha256(data).hexdigest()
        except FileNotFoundError:
            return None, None

    def put(self, key, data, expected):
        import fcntl
        p = self.path(key)
        p.parent.mkdir(parents=True, exist_ok=True)
        with open(self.root / '.cas.lock', 'a') as guard:
            fcntl.flock(guard, fcntl.LOCK_EX)
            if self.get(key)[1] != expected:
                raise Conflict("Artifact changed")
            fd, tmp = tempfile.mkstemp(dir=p.parent)
            try:
                with os.fdopen(fd, 'wb') as out:
                    out.write(data)
                    out.flush()
                    os.fsync(out.fileno())
                os.replace(tmp, p)
            finally:
                if os.path.exists(tmp):
                    os.unlink(tmp)

    def delete(self, key):
        self.path(key).unlink(missing_ok=True)


class S3Store(Store):
    def __init__(self, root, client=None):
        import boto3
        u = urlparse(root)
        if u.scheme != 's3' or not u.netloc:
            raise ValueError("Expected an s3://bucket/prefix root")
        self.bucket, self.prefix = u.netloc, u.path.strip('/')
        self.client = client or boto3.client('s3')

    def key(self, key):
        if '..' in key.split('/') or key.startswith('/'):
            raise ValueError("Unsafe artifact key")
        return '/'.join(x for x in [self.prefix, key] if x)

    def uri(self, key):
        return f's3://{self.bucket}/{self.key(key)}'

    def get(self, key):
        from botocore.exceptions import ClientError
        try:
            r = self.client.get_object(Bucket=self.bucket, Key=self.key(key))
            return r['Body'].read(), r['ETag']
        except ClientError as e:
            if e.response['Error']['Code'] in ('NoSuchKey', '404'):
                return None, None
            raise

    def put(self, key, data, expected):
        from botocore.exceptions import ClientError
        try:
            self.client.put_object(Bucket=self.bucket, Key=self.key(key), Body=data,
                                   **({'IfMatch': expected} if expected else {'IfNoneMatch': '*'}))
        except ClientError as e:
            if e.response['ResponseMetadata']['HTTPStatusCode'] in (409, 412):
                raise Conflict("Artifact changed") from None
            raise

    def delete(self, key):
        self.client.delete_object(Bucket=self.bucket, Key=self.key(key))
