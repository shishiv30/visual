import AVFoundation
import PhotosUI
import UniformTypeIdentifiers
import UIKit

final class CaptureViewController: UIViewController, AVCaptureFileOutputRecordingDelegate, UIDocumentPickerDelegate, PHPickerViewControllerDelegate {
    var library: Library!
    var onBack: (() -> Void)?
    var onImported: (() -> Void)?
    var onBusy: ((String) -> Void)?
    var onIdle: (() -> Void)?

    private let preview = AVCaptureVideoPreviewLayer()
    private let previewHost = UIView()
    private let hint = UILabel()
    private let denied = UIView()
    private let deniedTitle = UILabel()
    private let deniedBody = UILabel()
    private let btnAllow = UIButton(type: .system)
    private let btnRecord = PoseButtons.chrome(icon: "record")
    private let btnImport = PoseButtons.accent(icon: "import")
    private let bar = UIStackView()
    private let back = FloatingBackButton()
    private let session = AVCaptureSession()
    private let movieOutput = AVCaptureMovieFileOutput()
    private var cameraBound = false
    private var pendingImport = false
    private var recordingURL: URL?

    override func viewDidLoad() {
        super.viewDidLoad()
        view.backgroundColor = Theme.surface
        previewHost.backgroundColor = .black
        preview.videoGravity = .resizeAspectFill
        preview.session = session
        previewHost.layer.addSublayer(preview)

        hint.textColor = UIColor(rgb: 0xDDDDDD)
        hint.font = .systemFont(ofSize: 16)
        hint.textAlignment = .center

        denied.isHidden = true
        denied.backgroundColor = Theme.surface
        deniedTitle.textColor = Theme.paper
        deniedTitle.font = .boldSystemFont(ofSize: 20)
        deniedTitle.textAlignment = .center
        deniedTitle.numberOfLines = 0
        deniedBody.textColor = Theme.paper
        deniedBody.font = .systemFont(ofSize: 16)
        deniedBody.textAlignment = .center
        deniedBody.numberOfLines = 0
        btnAllow.backgroundColor = Theme.deepPurple
        btnAllow.setTitleColor(.white, for: .normal)
        btnAllow.layer.cornerRadius = 4
        btnAllow.contentEdgeInsets = UIEdgeInsets(top: 8, left: 12, bottom: 8, right: 12)
        btnAllow.addAction(UIAction { [weak self] _ in self?.requestCameraOrSettings() }, for: .touchUpInside)
        let deniedCol = UIStackView(arrangedSubviews: [deniedTitle, deniedBody, btnAllow])
        deniedCol.axis = .vertical
        deniedCol.alignment = .center
        deniedCol.spacing = Theme.spaceText
        deniedCol.translatesAutoresizingMaskIntoConstraints = false
        denied.addSubview(deniedCol)

        btnRecord.addAction(UIAction { [weak self] _ in self?.toggleRecord() }, for: .touchUpInside)
        btnImport.addAction(UIAction { [weak self] _ in self?.pickMedia() }, for: .touchUpInside)
        bar.axis = .horizontal
        bar.alignment = .center
        bar.spacing = 8
        bar.isLayoutMarginsRelativeArrangement = true
        bar.layoutMargins = UIEdgeInsets(top: Theme.pageInset, left: Theme.pageInset, bottom: Theme.pageInset, right: Theme.pageInset)
        bar.addArrangedSubview(btnRecord)
        bar.addArrangedSubview(btnImport)
        bar.addArrangedSubview(UIView())

        [previewHost, hint, denied, bar].forEach {
            $0.translatesAutoresizingMaskIntoConstraints = false
            view.addSubview($0)
        }
        NSLayoutConstraint.activate([
            previewHost.topAnchor.constraint(equalTo: view.topAnchor),
            previewHost.leadingAnchor.constraint(equalTo: view.leadingAnchor),
            previewHost.trailingAnchor.constraint(equalTo: view.trailingAnchor),
            previewHost.bottomAnchor.constraint(equalTo: bar.topAnchor),
            hint.centerXAnchor.constraint(equalTo: view.centerXAnchor),
            hint.centerYAnchor.constraint(equalTo: view.centerYAnchor),
            denied.topAnchor.constraint(equalTo: view.topAnchor),
            denied.leadingAnchor.constraint(equalTo: view.leadingAnchor),
            denied.trailingAnchor.constraint(equalTo: view.trailingAnchor),
            denied.bottomAnchor.constraint(equalTo: view.bottomAnchor),
            deniedCol.centerYAnchor.constraint(equalTo: denied.centerYAnchor),
            deniedCol.leadingAnchor.constraint(equalTo: denied.leadingAnchor, constant: Theme.spacePanel),
            deniedCol.trailingAnchor.constraint(equalTo: denied.trailingAnchor, constant: -Theme.spacePanel),
            bar.leadingAnchor.constraint(equalTo: view.leadingAnchor),
            bar.trailingAnchor.constraint(equalTo: view.trailingAnchor),
            bar.bottomAnchor.constraint(equalTo: view.safeAreaLayoutGuide.bottomAnchor),
        ])
        back.attach(to: view)
        back.onTap = { [weak self] in self?.goBack() }
        movieOutput.maxRecordedDuration = CMTime(seconds: Double(Library.maxMs) / 1000, preferredTimescale: 1)
        retranslate()
    }

    override func viewDidLayoutSubviews() {
        super.viewDidLayoutSubviews()
        preview.frame = previewHost.bounds
    }

    func openCamera() {
        pendingImport = false
        setChromeHidden(false)
        denied.isHidden = true
        let status = AVCaptureDevice.authorizationStatus(for: .video)
        if status == .authorized {
            startCamera()
        } else if status == .notDetermined {
            AVCaptureDevice.requestAccess(for: .video) { [weak self] granted in
                DispatchQueue.main.async {
                    if granted {
                        self?.startCamera()
                    } else {
                        self?.showDenied(permission: true)
                    }
                }
            }
        } else {
            showDenied(permission: true)
        }
    }

    func openImport() {
        pendingImport = true
        stopCamera()
        setChromeHidden(true)
        pickMedia()
    }

    func stopAndReset() {
        pendingImport = false
        if movieOutput.isRecording {
            movieOutput.stopRecording()
        }
        stopCamera()
        setChromeHidden(false)
        previewHost.isHidden = false
        hint.isHidden = false
    }

    func retranslate() {
        hint.text = I18n.t("Camera preview")
        btnImport.accessibilityLabel = I18n.t("Import…")
        back.retranslate()
        syncRecordButton()
        if !denied.isHidden {
            showDenied(permission: AVCaptureDevice.authorizationStatus(for: .video) != .authorized)
        }
    }

    private func goBack() {
        if movieOutput.isRecording {
            movieOutput.stopRecording()
        }
        stopCamera()
        onBack?()
    }

    private func setChromeHidden(_ hidden: Bool) {
        previewHost.isHidden = hidden
        hint.isHidden = hidden
        bar.isHidden = hidden
        back.isHidden = hidden
    }

    private func pickMedia() {
        var config = PHPickerConfiguration()
        config.filter = .videos
        config.selectionLimit = 1
        let picker = PHPickerViewController(configuration: config)
        picker.delegate = self
        present(picker, animated: true)
    }

    func picker(_ picker: PHPickerViewController, didFinishPicking results: [PHPickerResult]) {
        picker.dismiss(animated: true)
        guard let result = results.first else {
            if pendingImport { pendingImport = false; onBack?() }
            return
        }
        result.itemProvider.loadFileRepresentation(forTypeIdentifier: UTType.movie.identifier) { [weak self] url, error in
            guard let url = url, error == nil else {
                if self?.pendingImport == true { DispatchQueue.main.async { self?.onBack?() } }
                return
            }
            let tmp = FileManager.default.temporaryDirectory.appendingPathComponent(url.lastPathComponent)
            try? FileManager.default.copyItem(at: url, to: tmp)
            DispatchQueue.main.async { self?.ingest(url: tmp) }
        }
    }

    func documentPickerWasCancelled(_ controller: UIDocumentPickerViewController) {
        if pendingImport { pendingImport = false; onBack?() }
    }

    func documentPicker(_ controller: UIDocumentPickerViewController, didPickDocumentsAt urls: [URL]) {
        guard let url = urls.first else {
            if pendingImport { onBack?() }
            return
        }
        ingest(url: url)
    }

    private func ingest(url: URL) {
        let scoped = url.startAccessingSecurityScopedResource()
        defer { if scoped { url.stopAccessingSecurityScopedResource() } }
        onBusy?("import")
        DispatchQueue.global(qos: .userInitiated).async { [weak self] in
            do {
                try self?.importURL(url)
                DispatchQueue.main.async {
                    self?.onIdle?()
                    self?.pendingImport = false
                    self?.onImported?()
                }
            } catch {
                DispatchQueue.main.async {
                    self?.onIdle?()
                    self?.poseAlert(titleKey: "Import failed", messageKey: "Could not read video.")
                    self?.pendingImport = false
                    self?.onImported?()
                }
            }
        }
    }

    private func importURL(_ url: URL) throws {
        let ext = url.pathExtension.lowercased()
        let imageExt = ["jpg", "jpeg", "png", "webp", "bmp", "heic"]
        if imageExt.contains(ext) {
            try MediaIngest(library: library).fromImage(url)
        } else {
            try MediaIngest(library: library).fromVideo(url)
        }
    }

    private func startCamera() {
        denied.isHidden = true
        previewHost.isHidden = false
        if cameraBound { return }
        session.beginConfiguration()
        session.sessionPreset = .hd1280x720
        session.inputs.forEach { session.removeInput($0) }
        session.outputs.forEach { session.removeOutput($0) }
        let device = AVCaptureDevice.default(.builtInWideAngleCamera, for: .video, position: .back)
            ?? AVCaptureDevice.default(for: .video)
        guard let device, let input = try? AVCaptureDeviceInput(device: device) else {
            session.commitConfiguration()
            showDenied(permission: false)
            return
        }
        if session.canAddInput(input) { session.addInput(input) }
        if session.canAddOutput(movieOutput) { session.addOutput(movieOutput) }
        session.commitConfiguration()
        cameraBound = true
        DispatchQueue.global(qos: .userInitiated).async { [weak self] in
            self?.session.startRunning()
        }
    }

    private func stopCamera() {
        if movieOutput.isRecording {
            movieOutput.stopRecording()
        }
        if session.isRunning {
            session.stopRunning()
        }
        cameraBound = false
        syncRecordButton()
    }

    private func toggleRecord() {
        if movieOutput.isRecording {
            movieOutput.stopRecording()
            return
        }
        if !cameraBound {
            poseAlert(titleKey: "Camera device", messageKey: "Could not open the camera.")
            return
        }
        let url = FileManager.default.temporaryDirectory.appendingPathComponent("record_\(Int(Date().timeIntervalSince1970)).mp4")
        recordingURL = url
        movieOutput.startRecording(to: url, recordingDelegate: self)
        syncRecordButton()
    }

    func fileOutput(
        _ output: AVCaptureFileOutput,
        didFinishRecordingTo outputFileURL: URL,
        from connections: [AVCaptureConnection],
        error: Error?
    ) {
        syncRecordButton()
        let attrs = try? FileManager.default.attributesOfItem(atPath: outputFileURL.path)
        let size = (attrs?[.size] as? NSNumber)?.intValue ?? 0
        if error != nil || size < 64 {
            try? FileManager.default.removeItem(at: outputFileURL)
            return
        }
        ingest(url: outputFileURL)
    }

    private func syncRecordButton() {
        if movieOutput.isRecording {
            btnRecord.setImage(Icons.image("stop", color: Theme.paper), for: .normal)
            btnRecord.accessibilityLabel = I18n.t("Stop")
        } else {
            btnRecord.setImage(Icons.image("record"), for: .normal)
            btnRecord.accessibilityLabel = I18n.t("Record")
        }
    }

    private func showDenied(permission: Bool) {
        denied.isHidden = false
        if permission {
            deniedTitle.text = I18n.t("Camera permission required")
            deniedBody.text = I18n.t("Grant camera access to run pose tracking.")
            btnAllow.setTitle(I18n.t("Allow camera"), for: .normal)
        } else {
            deniedTitle.text = I18n.t("Camera unavailable")
            deniedBody.text = I18n.t("No camera found. On the emulator, use a virtual scene or webcam.")
            btnAllow.setTitle(I18n.t("Retry"), for: .normal)
        }
    }

    private func requestCameraOrSettings() {
        let status = AVCaptureDevice.authorizationStatus(for: .video)
        if status == .authorized {
            startCamera()
            return
        }
        if status == .notDetermined {
            AVCaptureDevice.requestAccess(for: .video) { [weak self] granted in
                DispatchQueue.main.async {
                    if granted { self?.startCamera() } else { self?.showDenied(permission: true) }
                }
            }
            return
        }
        if let url = URL(string: UIApplication.openSettingsURLString) {
            UIApplication.shared.open(url)
        }
    }
}

struct MediaIngest {
    let library: Library

    func fromImage(_ url: URL) throws {
        let clipId = library.newClipId()
        let dir = library.clipDir(clipId)
        try FileManager.default.createDirectory(at: dir, withIntermediateDirectories: true)
        let dest = dir.appendingPathComponent("clip.jpg")
        let data = try Data(contentsOf: url)
        guard let image = UIImage(data: data) else { throw NSError(domain: "ingest", code: 1) }
        guard let jpeg = image.jpegData(compressionQuality: 0.9) else { throw NSError(domain: "ingest", code: 1) }
        try jpeg.write(to: dest)
        writeThumb(image, to: library.thumbFile(clipId))
        let meta = ClipMeta(
            clipId: clipId,
            createdAt: Library.createdAtIso(),
            displayName: Library.displayNameNow(),
            durationMs: 0,
            width: max(1, Int(image.size.width * image.scale)),
            height: max(1, Int(image.size.height * image.scale)),
            fps: 1,
            kind: .image,
            status: .pending
        )
        library.saveMeta(meta)
    }

    func fromVideo(_ url: URL) throws {
        let clipId = library.newClipId()
        let dir = library.clipDir(clipId)
        try FileManager.default.createDirectory(at: dir, withIntermediateDirectories: true)
        let dest = dir.appendingPathComponent("clip.mp4")
        if FileManager.default.fileExists(atPath: dest.path) {
            try FileManager.default.removeItem(at: dest)
        }
        try FileManager.default.copyItem(at: url, to: dest)
        let asset = AVAsset(url: dest)
        let durationMs = Int(CMTimeGetSeconds(asset.duration) * 1000)
        var width = 1
        var height = 1
        if let track = asset.tracks(withMediaType: .video).first {
            let size = track.naturalSize.applying(track.preferredTransform)
            width = max(1, Int(abs(size.width)))
            height = max(1, Int(abs(size.height)))
        }
        let fps = Double(asset.tracks(withMediaType: .video).first?.nominalFrameRate ?? 30)
        writeVideoThumb(asset, to: library.thumbFile(clipId))
        let playEnd = durationMs > Int(Library.maxMs) ? Int(Library.maxMs) : nil
        let meta = ClipMeta(
            clipId: clipId,
            createdAt: Library.createdAtIso(),
            displayName: Library.displayNameNow(),
            durationMs: durationMs,
            width: width,
            height: height,
            fps: fps > 1 ? fps : 30,
            kind: .video,
            status: .pending,
            playEndMs: playEnd
        )
        library.saveMeta(meta)
        try? FileManager.default.removeItem(at: url)
    }

    private func writeThumb(_ image: UIImage, to dest: URL) {
        let w: CGFloat = 256
        let h: CGFloat = 144
        let renderer = UIGraphicsImageRenderer(size: CGSize(width: w, height: h))
        let out = renderer.image { ctx in
            UIColor.black.setFill()
            ctx.fill(CGRect(x: 0, y: 0, width: w, height: h))
            let scale = max(w / image.size.width, h / image.size.height)
            let dw = image.size.width * scale
            let dh = image.size.height * scale
            image.draw(in: CGRect(x: (w - dw) / 2, y: (h - dh) / 2, width: dw, height: dh))
        }
        try? out.jpegData(compressionQuality: 0.8)?.write(to: dest)
    }

    private func writeVideoThumb(_ asset: AVAsset, to dest: URL) {
        let gen = AVAssetImageGenerator(asset: asset)
        gen.appliesPreferredTrackTransform = true
        if let cg = try? gen.copyCGImage(at: .zero, actualTime: nil) {
            writeThumb(UIImage(cgImage: cg), to: dest)
        }
    }
}
