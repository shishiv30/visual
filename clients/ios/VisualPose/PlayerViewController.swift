import AVFoundation
import UniformTypeIdentifiers
import UIKit

final class PlayerViewController: UIViewController, UIDocumentPickerDelegate {
    var library: Library!
    var onBack: (() -> Void)?

    private let stage = PlayerStageView()
    private let playerHost = UIView()
    private let imageView = UIImageView()
    private let overlay = PoseOverlayView()
    private let chromeScroll = UIScrollView()
    private let timeline = TimelineStripView()
    private let report = ReportPanelView()
    private let reportScroll = UIScrollView()
    private let back = FloatingBackButton()

    private let btnPlay = PoseButtons.chrome(icon: "play")
    private let btnLocator = UIButton(type: .system)
    private let btnSpeed = UIButton(type: .system)
    private let btnLike = PoseButtons.chrome(icon: "thumb_up")
    private let btnUnlike = PoseButtons.chrome(icon: "thumb_down")
    private let btnSkeleton = PoseButtons.chrome(icon: "reanalyze")
    private let btnDownload = PoseButtons.chrome(icon: "download")
    private let btnShare = PoseButtons.chrome(icon: "share")

    private var player: AVPlayer?
    private var playerLayer: AVPlayerLayer?
    private var timeObserver: Any?
    private var timelineFrames: [PoseFrame] = []
    private var playing = false
    private var playerEnded = false
    private var meta: ClipMeta?
    private var reportModel: StageReport?
    private var feedback = FrameFeedback.empty("")
    private var playStartMs: Int64 = 0
    private var playEndMs: Int64 = Int64.max / 4
    private var playerSpeed: Float = 1
    private var seekPending = false
    private var startAfterSeek = false
    private var pendingSeekMs: Int64 = 0
    private var generator: AVAssetImageGenerator?
    private var hudTMs: Int64 = 0
    private var hudVideoFrame = 0
    private var hudPoseI: Int?
    private var chromeHide: DispatchWorkItem?
    private let speeds: [Float] = [0.5, 0.75, 1, 1.25, 1.5, 2]
    private var exportURL: URL?

    override func viewDidLoad() {
        super.viewDidLoad()
        view.backgroundColor = Theme.surface
        imageView.contentMode = .scaleAspectFit
        imageView.isHidden = true
        overlay.setLetterbox(true)
        chromeScroll.backgroundColor = UIColor(white: 0, alpha: 0.6)
        chromeScroll.showsHorizontalScrollIndicator = false
        styleChromeText(btnLocator)
        styleChromeText(btnSpeed)
        btnSpeed.setTitle("1×", for: .normal)

        btnPlay.addAction(UIAction { [weak self] _ in self?.togglePlay() }, for: .touchUpInside)
        btnLocator.addAction(UIAction { [weak self] _ in self?.copyLocator() }, for: .touchUpInside)
        btnSpeed.addAction(UIAction { [weak self] _ in self?.cycleSpeed() }, for: .touchUpInside)
        btnLike.addAction(UIAction { [weak self] _ in self?.voteStage("like") }, for: .touchUpInside)
        btnUnlike.addAction(UIAction { [weak self] _ in self?.voteStage("unlike") }, for: .touchUpInside)
        btnSkeleton.addAction(UIAction { [weak self] _ in self?.voteSkeleton() }, for: .touchUpInside)
        btnDownload.addAction(UIAction { [weak self] _ in self?.downloadOverlay() }, for: .touchUpInside)
        btnShare.addAction(UIAction { [weak self] _ in self?.showShareMenu() }, for: .touchUpInside)
        stage.onTap = { [weak self] in self?.showChrome(autoHide: self?.playing == true) }
        timeline.onPlayhead = { [weak self] tMs in self?.seekPlayer(Int64(tMs), pause: false) }
        timeline.setTrimEnabled(false)
        report.onSeek = { [weak self] tMs in self?.seekPlayer(Int64(tMs), pause: true) }
        report.onJumpToSkillTree = { [weak self] in
            guard let self else { return }
            self.report.scrollToSkillTreeChapter(in: self.reportScroll)
        }

        let chrome = UIStackView(arrangedSubviews: [
            btnPlay, btnLocator, btnSpeed, btnLike, btnUnlike, btnSkeleton, btnDownload, btnShare,
        ])
        chrome.axis = .horizontal
        chrome.alignment = .center
        chrome.spacing = 4
        chrome.isLayoutMarginsRelativeArrangement = true
        chrome.layoutMargins = UIEdgeInsets(top: 8, left: 8, bottom: 8, right: 8)
        chromeScroll.addSubview(chrome)
        chrome.translatesAutoresizingMaskIntoConstraints = false

        playerHost.backgroundColor = .black
        [playerHost, imageView, overlay].forEach {
            $0.translatesAutoresizingMaskIntoConstraints = false
            stage.addSubview($0)
        }
        chromeScroll.translatesAutoresizingMaskIntoConstraints = false
        stage.addSubview(chromeScroll)
        NSLayoutConstraint.activate([
            playerHost.topAnchor.constraint(equalTo: stage.topAnchor),
            playerHost.leadingAnchor.constraint(equalTo: stage.leadingAnchor),
            playerHost.trailingAnchor.constraint(equalTo: stage.trailingAnchor),
            playerHost.bottomAnchor.constraint(equalTo: stage.bottomAnchor),
            imageView.topAnchor.constraint(equalTo: stage.topAnchor),
            imageView.leadingAnchor.constraint(equalTo: stage.leadingAnchor),
            imageView.trailingAnchor.constraint(equalTo: stage.trailingAnchor),
            imageView.bottomAnchor.constraint(equalTo: stage.bottomAnchor),
            overlay.topAnchor.constraint(equalTo: stage.topAnchor),
            overlay.leadingAnchor.constraint(equalTo: stage.leadingAnchor),
            overlay.trailingAnchor.constraint(equalTo: stage.trailingAnchor),
            overlay.bottomAnchor.constraint(equalTo: stage.bottomAnchor),
            chromeScroll.leadingAnchor.constraint(equalTo: stage.leadingAnchor),
            chromeScroll.trailingAnchor.constraint(equalTo: stage.trailingAnchor),
            chromeScroll.bottomAnchor.constraint(equalTo: stage.bottomAnchor),
            chromeScroll.heightAnchor.constraint(equalToConstant: 60),
        ])

        reportScroll.showsVerticalScrollIndicator = false
        reportScroll.addSubview(report)
        report.translatesAutoresizingMaskIntoConstraints = false

        let col = UIStackView(arrangedSubviews: [stage, timeline, reportScroll])
        col.axis = .vertical
        col.spacing = 0
        col.setCustomSpacing(Theme.spaceChapter, after: timeline)
        col.translatesAutoresizingMaskIntoConstraints = false
        stage.setContentHuggingPriority(.required, for: .vertical)
        stage.setContentCompressionResistancePriority(.required, for: .vertical)
        timeline.setContentHuggingPriority(.required, for: .vertical)
        view.addSubview(col)
        NSLayoutConstraint.activate([
            col.topAnchor.constraint(equalTo: view.safeAreaLayoutGuide.topAnchor, constant: Theme.floatingBack + Theme.pageInset),
            col.leadingAnchor.constraint(equalTo: view.leadingAnchor, constant: Theme.pageInset),
            col.trailingAnchor.constraint(equalTo: view.trailingAnchor, constant: -Theme.pageInset),
            col.bottomAnchor.constraint(equalTo: view.bottomAnchor),
            chrome.topAnchor.constraint(equalTo: chromeScroll.contentLayoutGuide.topAnchor),
            chrome.bottomAnchor.constraint(equalTo: chromeScroll.contentLayoutGuide.bottomAnchor),
            chrome.leadingAnchor.constraint(equalTo: chromeScroll.contentLayoutGuide.leadingAnchor),
            chrome.trailingAnchor.constraint(equalTo: chromeScroll.contentLayoutGuide.trailingAnchor),
            chrome.heightAnchor.constraint(equalTo: chromeScroll.frameLayoutGuide.heightAnchor),
            report.topAnchor.constraint(equalTo: reportScroll.contentLayoutGuide.topAnchor),
            report.leadingAnchor.constraint(equalTo: reportScroll.contentLayoutGuide.leadingAnchor),
            report.trailingAnchor.constraint(equalTo: reportScroll.contentLayoutGuide.trailingAnchor),
            report.bottomAnchor.constraint(equalTo: reportScroll.contentLayoutGuide.bottomAnchor),
            report.widthAnchor.constraint(equalTo: reportScroll.frameLayoutGuide.widthAnchor),
        ])
        back.attach(to: view)
        back.onTap = { [weak self] in
            self?.releasePlayer()
            self?.onBack?()
        }
        retranslate()
    }

    override func viewDidLayoutSubviews() {
        super.viewDidLayoutSubviews()
        playerLayer?.frame = playerHost.bounds
    }

    func open(clipId: String) {
        releasePlayer()
        let meta = library.loadMeta(clipId)
        self.meta = meta
        timelineFrames = AnalysisJson.load(library.analysisFile(clipId))
        reportModel = StageReportJson.load(library.stageReportFile(clipId))
        feedback = FrameFeedback.load(library.frameFeedbackFile(clipId), clipId: clipId)
        let window = Library.playWindowMs(meta)
        playStartMs = window.0
        playEndMs = meta.durationMs > 0 ? min(window.1, Int64(meta.durationMs)) : window.1
        playerSpeed = 1
        playerEnded = false
        let media = library.mediaFile(meta)
        stage.setAspect(width: meta.width, height: meta.height)
        report.bind(reportModel)
        let video = meta.kind == .video
        playerHost.isHidden = !video
        imageView.isHidden = video
        btnPlay.isHidden = !video
        btnSpeed.isHidden = !video
        timeline.isHidden = !video
        if video {
            timeline.bindVideo(url: media, duration: max(1, meta.durationMs))
            timeline.setTrimEnabled(false)
            timeline.setRange(startMs: Int(window.0), endMs: meta.playEndMs)
            timeline.setKeyframes(timelineFrames.map { Int($0.tMs) })
            let asset = AVAsset(url: media)
            let gen = AVAssetImageGenerator(asset: asset)
            gen.appliesPreferredTrackTransform = true
            gen.requestedTimeToleranceBefore = .zero
            gen.requestedTimeToleranceAfter = .zero
            generator = gen
            let item = AVPlayerItem(asset: asset)
            let player = AVPlayer(playerItem: item)
            player.actionAtItemEnd = .pause
            self.player = player
            let layer = AVPlayerLayer(player: player)
            layer.videoGravity = .resizeAspect
            playerHost.layer.addSublayer(layer)
            playerLayer = layer
            NotificationCenter.default.addObserver(
                self,
                selector: #selector(itemEnded),
                name: .AVPlayerItemDidPlayToEndTime,
                object: item
            )
            timeObserver = player.addPeriodicTimeObserver(
                forInterval: CMTime(value: 33, timescale: 1000),
                queue: .main
            ) { [weak self] time in
                self?.onTick(time)
            }
            seekClosest(playStartMs, startWhenDone: true)
            showChrome(autoHide: true)
        } else {
            timeline.clear()
            imageView.image = UIImage(contentsOfFile: media.path)
            updateHud(0)
            showChrome(autoHide: false)
        }
        syncLocator()
        syncFeedback()
        btnSpeed.setTitle("1×", for: .normal)
        retranslate()
    }

    func retranslate() {
        back.retranslate()
        btnPlay.accessibilityLabel = playing ? I18n.t("Pause") : I18n.t("Play")
        btnSpeed.accessibilityLabel = I18n.t("Speed")
        btnLike.accessibilityLabel = I18n.t("Like")
        btnUnlike.accessibilityLabel = I18n.t("Unlike")
        btnSkeleton.accessibilityLabel = I18n.t("Bad skeleton")
        btnDownload.accessibilityLabel = I18n.t("Download")
        btnShare.accessibilityLabel = I18n.t("Share")
        btnLocator.accessibilityLabel = I18n.t("Copy frame locator")
        report.retranslate()
    }

    func reloadReport() {
        if let meta {
            reportModel = StageReportJson.load(library.stageReportFile(meta.clipId))
            report.bind(reportModel)
        }
    }

    func releasePlayer() {
        chromeHide?.cancel()
        if let timeObserver, let player {
            player.removeTimeObserver(timeObserver)
        }
        timeObserver = nil
        NotificationCenter.default.removeObserver(self)
        player?.pause()
        player = nil
        playerLayer?.removeFromSuperlayer()
        playerLayer = nil
        playing = false
        playerEnded = false
        seekPending = false
        startAfterSeek = false
        hidePausedFrame()
        generator = nil
        meta = nil
        reportModel = nil
        feedback = FrameFeedback.empty("")
        overlay.setPoses([], frameWidth: 1, frameHeight: 1, box: nil)
        timeline.clear()
    }

    private func styleChromeText(_ button: UIButton) {
        button.setTitleColor(Theme.paper, for: .normal)
        button.titleLabel?.font = .systemFont(ofSize: 12)
        button.contentEdgeInsets = UIEdgeInsets(top: 8, left: 8, bottom: 8, right: 8)
        button.heightAnchor.constraint(greaterThanOrEqualToConstant: 44).isActive = true
        button.widthAnchor.constraint(greaterThanOrEqualToConstant: 44).isActive = true
    }

    private func onTick(_ time: CMTime) {
        if seekPending { return }
        let pos = Int64(CMTimeGetSeconds(time) * 1000)
        if ClipRange.pastPlayEnd(posMs: pos, endMs: playEndMs) {
            player?.pause()
            playing = false
            playerEnded = true
            btnPlay.setImage(Icons.image("play", color: Theme.paper), for: .normal)
            btnPlay.accessibilityLabel = I18n.t("Play")
            showChrome(autoHide: false)
            seekClosest(playEndMs - 1, startWhenDone: false)
            return
        }
        updateHud(pos)
    }

    @objc private func itemEnded() {
        playing = false
        playerEnded = true
        btnPlay.setImage(Icons.image("play", color: Theme.paper), for: .normal)
        btnPlay.accessibilityLabel = I18n.t("Play")
        showChrome(autoHide: false)
    }

    private func seekClosest(_ tMs: Int64, startWhenDone: Bool) {
        guard let player else { return }
        let clamped = ClipRange.clampPlayheadMs(tMs, startMs: playStartMs, endMs: playEndMs)
        pendingSeekMs = clamped
        seekPending = true
        startAfterSeek = startWhenDone
        let time = CMTime(value: clamped, timescale: 1000)
        player.seek(to: time, toleranceBefore: .zero, toleranceAfter: .zero) { [weak self] _ in
            self?.onSeekComplete()
        }
    }

    private func onSeekComplete() {
        seekPending = false
        if startAfterSeek {
            startAfterSeek = false
            playerEnded = false
            hidePausedFrame()
            player?.play()
            applySpeed()
            playing = true
            btnPlay.setImage(Icons.image("pause", color: Theme.paper), for: .normal)
            btnPlay.accessibilityLabel = I18n.t("Pause")
            showChrome(autoHide: true)
        } else if !playing {
            showPausedFrame(pendingSeekMs)
        }
        updateHud(pendingSeekMs)
    }

    private func togglePlay() {
        guard let player else { return }
        if player.rate > 0 {
            player.pause()
            playing = false
            btnPlay.setImage(Icons.image("play", color: Theme.paper), for: .normal)
            btnPlay.accessibilityLabel = I18n.t("Play")
            let pos = Int64(CMTimeGetSeconds(player.currentTime()) * 1000)
            showPausedFrame(pos)
            showChrome(autoHide: false)
            return
        }
        let pos = Int64(CMTimeGetSeconds(player.currentTime()) * 1000)
        if playerEnded || ClipRange.pastPlayEnd(posMs: pos, endMs: playEndMs) || pos < playStartMs {
            seekClosest(playStartMs, startWhenDone: true)
            return
        }
        hidePausedFrame()
        player.play()
        applySpeed()
        playing = true
        btnPlay.setImage(Icons.image("pause", color: Theme.paper), for: .normal)
        btnPlay.accessibilityLabel = I18n.t("Pause")
        showChrome(autoHide: true)
    }

    private func seekPlayer(_ tMs: Int64, pause: Bool) {
        let clamped = ClipRange.clampPlayheadMs(tMs, startMs: playStartMs, endMs: playEndMs)
        if pause, playing {
            player?.pause()
            playing = false
            btnPlay.setImage(Icons.image("play", color: Theme.paper), for: .normal)
            btnPlay.accessibilityLabel = I18n.t("Play")
            showChrome(autoHide: false)
        }
        playerEnded = false
        timeline.setPlayheadMs(Int(clamped))
        if !playing {
            showPausedFrame(clamped)
            updateHud(clamped)
        }
        seekClosest(clamped, startWhenDone: false)
        showChrome(autoHide: playing)
    }

    private func updateHud(_ tMs: Int64) {
        hudTMs = max(0, tMs)
        let fps = (meta?.fps ?? 0) > 1 ? (meta?.fps ?? 30) : 30
        hudVideoFrame = Int(Double(hudTMs) / 1000 * fps)
        let frame = PoseTimeline.nearest(timelineFrames, tMs: hudTMs)
        if let frame, let idx = timelineFrames.firstIndex(where: { $0.tMs == frame.tMs }) {
            hudPoseI = idx
        } else {
            hudPoseI = nil
        }
        if let frame {
            overlay.setPoses(frame.poses, frameWidth: frame.width, frameHeight: frame.height, box: frame.bbox)
        } else {
            overlay.setPoses([], frameWidth: 1, frameHeight: 1, box: nil)
        }
        timeline.setPlayheadMs(Int(hudTMs))
        syncLocator()
        syncFeedback()
    }

    private func showPausedFrame(_ tMs: Int64) {
        guard let generator, meta?.kind == .video else { return }
        let clamped = ClipRange.clampPlayheadMs(tMs, startMs: playStartMs, endMs: playEndMs)
        let time = CMTime(value: clamped, timescale: 1000)
        if let cg = try? generator.copyCGImage(at: time, actualTime: nil) {
            imageView.image = UIImage(cgImage: cg)
            imageView.isHidden = false
        }
    }

    private func hidePausedFrame() {
        if meta?.kind == .video {
            imageView.isHidden = true
            imageView.image = nil
        }
    }

    private func showChrome(autoHide: Bool) {
        chromeScroll.isHidden = false
        chromeHide?.cancel()
        view.setNeedsLayout()
        if autoHide, playing {
            let work = DispatchWorkItem { [weak self] in self?.hideChrome() }
            chromeHide = work
            DispatchQueue.main.asyncAfter(deadline: .now() + 3, execute: work)
        }
    }

    private func hideChrome() {
        if playing, !playerEnded {
            chromeScroll.isHidden = true
        }
    }

    private func cycleSpeed() {
        let idx = speeds.firstIndex { abs($0 - playerSpeed) < 0.01 } ?? 0
        playerSpeed = speeds[(idx + 1) % speeds.count]
        btnSpeed.setTitle("\(trimSpeed(playerSpeed))×", for: .normal)
        applySpeed()
        showChrome(autoHide: playing)
    }

    private func applySpeed() {
        player?.rate = playing ? playerSpeed : 0
    }

    private func trimSpeed(_ speed: Float) -> String {
        speed == Float(Int(speed)) ? "\(Int(speed))" : "\(speed)"
    }

    private func syncLocator() {
        let id = (meta?.clipId ?? "").replacingOccurrences(of: "-", with: "")
        btnLocator.setTitle(id.count >= 8 ? String(id.prefix(8)) : id, for: .normal)
    }

    private func syncFeedback() {
        let entry = feedback.frames["\(hudVideoFrame)"]
        setChecked(btnLike, entry?.stageVote == "like", Theme.lightPurple, "thumb_up")
        setChecked(btnUnlike, entry?.stageVote == "unlike", Theme.watermelon, "thumb_down")
        setChecked(btnSkeleton, entry?.skeletonOk == false, Theme.title, "reanalyze")
    }

    private func setChecked(_ button: UIButton, _ on: Bool, _ color: UIColor, _ icon: String) {
        button.setImage(Icons.image(icon, color: on ? color : Theme.paper), for: .normal)
    }

    private func voteStage(_ vote: String) {
        guard let meta else { return }
        feedback = FrameFeedback.toggleVote(
            file: library.frameFeedbackFile(meta.clipId),
            clipId: meta.clipId,
            videoFrame: hudVideoFrame,
            vote: vote,
            tMs: Double(hudTMs),
            poseIndex: hudPoseI,
            stageId: reportModel?.stageId ?? ""
        )
        syncFeedback()
        showChrome(autoHide: playing)
    }

    private func voteSkeleton() {
        guard let meta else { return }
        feedback = FrameFeedback.toggleSkeleton(
            file: library.frameFeedbackFile(meta.clipId),
            clipId: meta.clipId,
            videoFrame: hudVideoFrame,
            tMs: Double(hudTMs),
            poseIndex: hudPoseI,
            stageId: reportModel?.stageId ?? ""
        )
        syncFeedback()
        showChrome(autoHide: playing)
    }

    private func copyLocator() {
        guard let meta else { return }
        let frame = PoseTimeline.nearest(timelineFrames, tMs: hudTMs)
        var payload: [String: Any] = [
            "clip_id": meta.clipId,
            "short_id": btnLocator.title(for: .normal) ?? "",
            "display_name": meta.displayName,
            "video_frame": hudVideoFrame,
            "t_ms": Double(hudTMs),
            "fps": meta.fps,
            "stage_id": reportModel?.stageId ?? "",
        ]
        payload["pose_index"] = hudPoseI as Any
        if let frame {
            payload["blaze33"] = frame.blaze33.map {
                ["x": $0.x, "y": $0.y, "z": $0.z, "confidence": $0.confidence]
            }
        }
        if let data = try? JSONSerialization.data(withJSONObject: payload, options: [.prettyPrinted, .sortedKeys]),
           let text = String(data: data, encoding: .utf8) {
            UIPasteboard.general.string = text
            toast("Frame locator JSON copied")
        }
        showChrome(autoHide: playing)
    }

    private func downloadOverlay() {
        guard let stamped = stampedStill() else {
            toast("Export failed")
            return
        }
        exportURL = stamped
        let picker = UIDocumentPickerViewController(forExporting: [stamped], asCopy: true)
        picker.delegate = self
        present(picker, animated: true)
        showChrome(autoHide: playing)
    }

    func documentPicker(_ controller: UIDocumentPickerViewController, didPickDocumentsAt urls: [URL]) {
        toast("Download")
    }

    private func showShareMenu() {
        let sheet = UIAlertController(title: I18n.t("Share"), message: nil, preferredStyle: .actionSheet)
        for (key, template) in PlayerExport.shareTargets {
            sheet.addAction(UIAlertAction(title: I18n.t(key), style: .default) { [weak self] _ in
                self?.shareTo(template)
            })
        }
        sheet.addAction(UIAlertAction(title: I18n.t("Cancel"), style: .cancel))
        sheet.popoverPresentationController?.sourceView = btnShare
        present(sheet, animated: true)
        showChrome(autoHide: playing)
    }

    private func shareTo(_ template: String) {
        guard let stamped = stampedStill() else {
            toast("Export failed")
            return
        }
        let url = PlayerExport.shareUrl(template: template, text: I18n.t("Visual Pose"))
        let image = UIImage(contentsOfFile: stamped.path)
        let items: [Any] = [image as Any, url].compactMap { $0 }
        let activity = UIActivityViewController(activityItems: items, applicationActivities: nil)
        activity.popoverPresentationController?.sourceView = btnShare
        present(activity, animated: true)
    }

    private func stampedStill() -> URL? {
        guard let meta else { return nil }
        let src: UIImage?
        if meta.kind == .image {
            src = UIImage(contentsOfFile: library.mediaFile(meta).path)
        } else if let generator {
            let time = CMTime(value: hudTMs, timescale: 1000)
            src = (try? generator.copyCGImage(at: time, actualTime: nil)).map { UIImage(cgImage: $0) }
                ?? imageView.image
        } else {
            src = imageView.image
        }
        guard let src else { return nil }
        let frame = PoseTimeline.nearest(timelineFrames, tMs: hudTMs)
        let out = OverlayStamp.stamp(src: src, frame: frame)
        let dir = FileManager.default.temporaryDirectory.appendingPathComponent("share", isDirectory: true)
        try? FileManager.default.createDirectory(at: dir, withIntermediateDirectories: true)
        let name = PlayerExport.downloadFileName(displayName: meta.displayName, clipId: meta.clipId)
        let file = dir.appendingPathComponent(name)
        guard let data = out.jpegData(compressionQuality: 0.92) else { return nil }
        try? data.write(to: file)
        return file
    }

    private func toast(_ key: String) {
        let alert = UIAlertController(title: nil, message: I18n.t(key), preferredStyle: .alert)
        present(alert, animated: true)
        DispatchQueue.main.asyncAfter(deadline: .now() + 1.0) {
            alert.dismiss(animated: true)
        }
    }
}
