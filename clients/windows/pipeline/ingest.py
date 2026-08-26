"""Copy and normalize a picked file into the clip library."""

from __future__ import annotations

from datetime import datetime
from pathlib import Path

from PySide6.QtCore import QObject, Signal

from clients.windows.pipeline.normalize import normalize_image, normalize_video
from clients.windows.store.library import (
    ClipKind,
    ClipMeta,
    ClipStatus,
    clip_dir,
    created_at_iso,
    display_name_now,
    media_path,
    new_clip_id,
    save_meta,
    thumb_path,
)


def write_clip_meta(
    clip_id: str,
    *,
    kind: ClipKind,
    width: int,
    height: int,
    fps: float,
    duration_ms: int,
) -> None:
    now = datetime.now().astimezone()
    save_meta(
        ClipMeta(
            clip_id=clip_id,
            created_at=created_at_iso(),
            display_name=display_name_now(now),
            duration_ms=duration_ms,
            width=width,
            height=height,
            fps=fps,
            kind=kind,
            status=ClipStatus.PENDING,
        )
    )


def ingest_image(src: Path) -> str:
    clip_id = new_clip_id()
    dest = clip_dir(clip_id) / "clip.jpg"
    width, height = normalize_image(src, dest, thumb_path(clip_id))
    write_clip_meta(
        clip_id,
        kind=ClipKind.IMAGE,
        width=width,
        height=height,
        fps=0.0,
        duration_ms=0,
    )
    return clip_id


def ingest_video(src: Path, *, start_s: float, duration_s: float) -> str:
    clip_id = new_clip_id()
    dest = media_path(
        ClipMeta(
            clip_id=clip_id,
            created_at=created_at_iso(),
            display_name=display_name_now(),
            kind=ClipKind.VIDEO,
        )
    )
    width, height, fps, out_ms = normalize_video(
        src, dest, thumb_path(clip_id), start_s=start_s, duration_s=duration_s
    )
    write_clip_meta(
        clip_id,
        kind=ClipKind.VIDEO,
        width=width,
        height=height,
        fps=fps,
        duration_ms=out_ms,
    )
    return clip_id


class IngestWorker(QObject):
    finished = Signal(str)
    failed = Signal(str)

    def __init__(
        self,
        *,
        kind: str,
        src: str,
        start_s: float = 0.0,
        duration_s: float = 0.0,
        delete_src: bool = False,
        parent: QObject | None = None,
    ) -> None:
        super().__init__(parent)
        self._kind = kind
        self._src = src
        self._start_s = start_s
        self._duration_s = duration_s
        self._delete_src = delete_src

    def run(self) -> None:
        src = Path(self._src)
        try:
            if self._kind == "image":
                clip_id = ingest_image(src)
            else:
                clip_id = ingest_video(
                    src, start_s=self._start_s, duration_s=self._duration_s
                )
            self.finished.emit(clip_id)
        except Exception as exc:  # noqa: BLE001
            self.failed.emit(str(exc))
        finally:
            if self._delete_src:
                src.unlink(missing_ok=True)
