"""Background MediaPipe analysis for library clips."""

from __future__ import annotations

import cv2
from PySide6.QtCore import QObject, QThread, Signal

from core.mediapipe_engine import MediaPipeEngine
from clients.windows.pipeline.clip_range import (
    collect_seeds,
    in_play_range,
    play_window_ms,
    seed_at,
)
from core.pose_track import (
    fill_low_score_poses,
    stabilize_pose_sequence,
    stabilize_weak_joints,
)
from core.person_roi import blend_hist, build_hist, denorm_box, search
from core.sports.assess import assess_clip
from core.sports.profile import AthleteContext
from core.sports.scene import SceneContext
from schemas.clip_analysis import (
    AnalyzedFrame,
    BlazeJoint,
    ClipAnalysis,
)
from schemas.core_inference import SourceKind
from clients.windows.store.library import (
    ClipKind,
    ClipMeta,
    ClipStatus,
    list_reports_for_athlete,
    load_meta,
    media_path,
    meta_path,
    save_analysis,
    save_meta,
    save_stage_report,
)

FRAME_STRIDE = 2


class AnalysisWorker(QObject):
    finished = Signal(str)
    failed = Signal(str, str)

    def __init__(self, clip_id: str, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self.clip_id = clip_id

    def run(self) -> None:
        try:
            meta = load_meta(self.clip_id)
            path = media_path(meta)
            engine = MediaPipeEngine(video=meta.kind != ClipKind.IMAGE)
            try:
                if meta.kind == ClipKind.IMAGE:
                    analysis = self._image(engine, meta, path)
                else:
                    analysis = self._video(engine, meta, path)
            finally:
                engine.close()
            if not meta_path(self.clip_id).is_file():
                self.failed.emit(self.clip_id, "clip deleted")
                return
            athlete = AthleteContext.from_profile_snapshot(
                meta.athlete, clip_date=meta.created_at
            )
            # We keep one frame in every FRAME_STRIDE, so the sample rate of
            # analysis.frames is source_fps / FRAME_STRIDE — not analysis.fps.
            # core/sports/signals.py:266 still divides by the source fps, which
            # inflates every frequency by exactly FRAME_STRIDE (the ~2x bug in
            # design §10); the new metrics layer must read fps_effective here
            # instead of recomputing it from fps.
            scene = SceneContext.from_dict(
                meta.scene, fps_effective=_effective_fps(analysis.fps)
            )
            analysis.athlete = athlete.to_dict()
            analysis.scene = scene.to_dict()
            save_analysis(analysis)
            # This athlete's earlier reports: the §8 tree needs them for
            # completed / locked, and the §5 prior needs them to stop a passed
            # rung swallowing the next one. Excluding this clip keeps a
            # re-analysis from reading its own previous verdict as history.
            history = list_reports_for_athlete(
                meta.athlete_key, exclude_clip_id=self.clip_id
            )
            save_stage_report(
                assess_clip(
                    analysis, athlete=athlete, scene=scene, history=history
                )
            )
            meta.status = ClipStatus.DONE
            meta.error = None
            save_meta(meta)
            self.finished.emit(self.clip_id)
        except Exception as exc:  # noqa: BLE001 — surface to UI
            try:
                if not meta_path(self.clip_id).is_file():
                    self.failed.emit(self.clip_id, str(exc))
                    return
                meta = load_meta(self.clip_id)
                meta.error = str(exc)
                save_meta(meta)
            except OSError:
                pass
            self.failed.emit(self.clip_id, str(exc))

    def _image(self, engine: MediaPipeEngine, meta: ClipMeta, path) -> ClipAnalysis:
        bgr = cv2.imread(str(path))
        if bgr is None:
            raise ValueError("cannot read image")
        result = engine.infer(
            bgr,
            source_kind=SourceKind.IMAGE,
            timestamp_ms=0.0,
            roi_hint=_seed_pixels(meta, bgr),
        )
        blaze = _blaze_joints(engine)
        frames = [
            AnalyzedFrame(
                t_ms=0.0,
                result=result,
                blaze33=blaze,
            )
        ]
        return ClipAnalysis(
            clip_id=meta.clip_id,
            fps=0.0,
            frame_count=1,
            frames=frames,
        )

    def _video(self, engine: MediaPipeEngine, meta: ClipMeta, path) -> ClipAnalysis:
        cap = cv2.VideoCapture(str(path))
        if not cap.isOpened():
            raise ValueError("cannot open video")
        fps = float(cap.get(cv2.CAP_PROP_FPS) or meta.fps or 30.0)
        start_ms, end_ms = play_window_ms(meta)
        seeds = collect_seeds(meta)
        half_ms = (1000.0 / max(fps, 1.0)) * FRAME_STRIDE / 2.0
        frames: list[AnalyzedFrame] = []
        index = 0
        hist = None
        box: tuple[float, float, float, float] | None = None
        while True:
            ok, bgr = cap.read()
            if not ok or bgr is None:
                break
            t_ms = float(cap.get(cv2.CAP_PROP_POS_MSEC))
            if t_ms <= 0.0:
                t_ms = index * (1000.0 / max(fps, 1.0))
            if t_ms > end_ms + 20.0:
                break
            if index % FRAME_STRIDE == 0 and in_play_range(t_ms, start_ms, end_ms):
                h, w = bgr.shape[:2]
                hit = seed_at(t_ms, seeds, half_ms)
                if hit is not None:
                    box = denorm_box(hit.box, w, h)
                    hist = build_hist(bgr, box)
                elif hist is None and meta.seed_box is not None:
                    box = denorm_box(meta.seed_box, w, h)
                    hist = build_hist(bgr, box)
                elif hist is not None and box is not None:
                    box = search(bgr, hist, box)
                result = engine.infer(
                    bgr,
                    source_kind=SourceKind.VIDEO_FRAME,
                    timestamp_ms=t_ms,
                    roi_hint=box,
                )
                if result.error is None and result.detections:
                    det_box = result.detections[0].bbox_xyxy
                    box = det_box
                    if hist is None:
                        hist = build_hist(bgr, det_box)
                    else:
                        hist = blend_hist(hist, build_hist(bgr, det_box))
                blaze = _blaze_joints(engine)
                frames.append(
                    AnalyzedFrame(
                        t_ms=t_ms,
                        result=result,
                        blaze33=blaze,
                    )
                )
            index += 1
        cap.release()
        # Per-joint bridging first (an ankle/foot dropout inside an otherwise
        # well-tracked frame never trips the whole-frame checks below, which
        # key off the overall pose score), then the existing whole-frame
        # low-score fill and spike correction.
        stabilize_weak_joints(frames)
        fill_low_score_poses(frames)
        stabilize_pose_sequence(frames)
        return ClipAnalysis(
            clip_id=meta.clip_id,
            fps=fps,
            frame_count=len(frames),
            frames=frames,
        )


def _effective_fps(source_fps: float) -> float | None:
    """Sample rate of the frames we kept: source fps ÷ FRAME_STRIDE.

    None for stills, where `fps` is 0 and no rate exists.
    """
    fps = float(source_fps or 0.0)
    if fps <= 0.0:
        return None
    return fps / float(FRAME_STRIDE)


def _blaze_joints(engine: MediaPipeEngine) -> list[BlazeJoint] | None:
    raw = engine.last_blaze33
    if raw is None or raw.shape[0] < 33:
        return None
    return [
        BlazeJoint(
            x=float(raw[i, 0]),
            y=float(raw[i, 1]),
            z=float(raw[i, 2]),
            confidence=float(raw[i, 3]),
        )
        for i in range(33)
    ]


def _seed_pixels(meta: ClipMeta, bgr) -> tuple[float, float, float, float] | None:
    seeds = collect_seeds(meta)
    if not seeds:
        return None
    h, w = bgr.shape[:2]
    return denorm_box(seeds[0].box, w, h)


class AnalysisQueue(QObject):
    clip_updated = Signal(str)
    busyChanged = Signal(bool)

    def __init__(self, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self._busy = False
        self._pending: list[str] = []
        self._thread: QThread | None = None
        self._worker: AnalysisWorker | None = None

    def is_busy(self) -> bool:
        return self._busy or bool(self._pending)

    def enqueue(self, clip_id: str) -> None:
        if self._busy and self._worker is not None and self._worker.clip_id == clip_id:
            return
        if clip_id not in self._pending:
            self._pending.append(clip_id)
        self._kick()
        self.busyChanged.emit(self.is_busy())

    def drop(self, clip_id: str) -> None:
        self._pending = [item for item in self._pending if item != clip_id]
        self.busyChanged.emit(self.is_busy())

    def _kick(self) -> None:
        if self._busy or not self._pending:
            return
        clip_id = self._pending.pop(0)
        self._busy = True
        thread = QThread()
        worker = AnalysisWorker(clip_id)
        worker.moveToThread(thread)
        thread.started.connect(worker.run)
        worker.finished.connect(self._on_done)
        worker.failed.connect(self._on_fail)
        worker.finished.connect(thread.quit)
        worker.failed.connect(thread.quit)
        thread.finished.connect(worker.deleteLater)
        thread.finished.connect(thread.deleteLater)
        self._thread = thread
        self._worker = worker
        thread.start()

    def _on_done(self, clip_id: str) -> None:
        self._busy = False
        self.clip_updated.emit(clip_id)
        self._kick()
        self.busyChanged.emit(self.is_busy())

    def _on_fail(self, clip_id: str, _message: str) -> None:
        self._busy = False
        self.clip_updated.emit(clip_id)
        self._kick()
        self.busyChanged.emit(self.is_busy())
