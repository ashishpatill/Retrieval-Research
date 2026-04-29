from __future__ import annotations

from typing import Any, Iterable, List


def _flatten(values: Any) -> Iterable[float]:
    if isinstance(values, list):
        for value in values:
            yield from _flatten(value)
    else:
        yield float(values)


def _map_nested(values: Any, fn):
    if isinstance(values, list):
        return [_map_nested(value, fn) for value in values]
    return fn(float(values))


def quantize_int8(values: Any) -> dict:
    max_abs = max((abs(value) for value in _flatten(values)), default=0.0)
    scale = max_abs / 127.0 if max_abs else 1.0
    return {
        "compression": "int8",
        "scale": scale,
        "values": _map_nested(values, lambda value: int(max(-127, min(127, round(value / scale))))),
    }


def dequantize_int8(payload: dict) -> Any:
    scale = float(payload.get("scale") or 1.0)
    return _map_nested(payload.get("values", []), lambda value: value * scale)


def maybe_compress_embeddings(embeddings: List[Any], compression: str = "none") -> List[Any]:
    if compression == "none":
        return embeddings
    if compression == "int8":
        return [quantize_int8(embedding) for embedding in embeddings]
    raise ValueError(f"Unsupported embedding compression: {compression}")


def maybe_decompress_embedding(embedding: Any) -> Any:
    if isinstance(embedding, dict) and embedding.get("compression") == "int8":
        return dequantize_int8(embedding)
    return embedding
