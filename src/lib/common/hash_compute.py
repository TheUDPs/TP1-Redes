import hashlib


def compute_chunk_sha256(chunk: bytes):
    hasher = hashlib.sha256()
    hasher.update(chunk)
    return hasher.hexdigest()[:10]
