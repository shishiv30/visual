import AVFoundation
import UIKit

final class RootViewController: UIViewController {
    private let library: Library
    private let athletes: Athletes
    private let engine = PoseEngine()
    private let listVC = ListViewController()
    private let captureVC = CaptureViewController()
    private let prepareVC = PrepareViewController()
    private let playerVC = PlayerViewController()
    private let loading = UIView()
    private let loadingSpinner = UIActivityIndicatorView(style: .large)
    private let loadingCaption = UILabel()
    private var analyzing = false
    private var page = Page.list
    private var curriculumCache: Curriculum?

    private enum Page { case list, capture, prepare, player }

    init() {
        let docs = FileManager.default.urls(for: .documentDirectory, in: .userDomainMask)[0]
        library = Library(docs.appendingPathComponent("library", isDirectory: true))
        athletes = Athletes(docs.appendingPathComponent("athletes.json"))
        super.init(nibName: nil, bundle: nil)
    }

    required init?(coder: NSCoder) {
        fatalError("init(coder:)")
    }

    override func viewDidLoad() {
        super.viewDidLoad()
        view.backgroundColor = Theme.surface
        embed(listVC)
        embed(captureVC)
        embed(prepareVC)
        embed(playerVC)
        captureVC.library = library
        prepareVC.library = library
        prepareVC.athletes = athletes
        playerVC.library = library
        listVC.onCamera = { [weak self] in self?.openCapture() }
        listVC.onImport = { [weak self] in self?.openImport() }
        listVC.onLanguageChanged = { [weak self] in self?.onLanguageChanged() }
        listVC.onOpenPrepare = { [weak self] id in self?.openPrepare(id) }
        listVC.onOpenPlayer = { [weak self] id in self?.openPlayer(id) }
        listVC.onReanalyze = { [weak self] id in
            self?.library.prepareReanalyze(id)
            self?.openPrepare(id)
        }
        listVC.onDelete = { [weak self] id in
            self?.library.deleteClip(id)
            if self?.page != .list {
                self?.goList()
            } else {
                self?.reloadList()
            }
        }
        captureVC.onBack = { [weak self] in self?.goList() }
        captureVC.onImported = { [weak self] in self?.goList() }
        captureVC.onBusy = { [weak self] kind in self?.showLoading(kind) }
        captureVC.onIdle = { [weak self] in self?.hideLoadingIfIdle() }
        prepareVC.onBack = { [weak self] in self?.goList() }
        prepareVC.onStartAnalysis = { [weak self] id in
            self?.enqueueAnalysis(id)
            self?.goList()
        }
        playerVC.onBack = { [weak self] in self?.goList() }

        loading.backgroundColor = Theme.surface
        loading.isHidden = true
        loadingSpinner.color = Theme.deepPurple
        loadingCaption.textColor = Theme.paper
        loadingCaption.font = .boldSystemFont(ofSize: 16)
        let loadCol = UIStackView(arrangedSubviews: [loadingSpinner, loadingCaption])
        loadCol.axis = .vertical
        loadCol.alignment = .center
        loadCol.spacing = Theme.spaceText
        loadCol.translatesAutoresizingMaskIntoConstraints = false
        loading.addSubview(loadCol)
        loading.translatesAutoresizingMaskIntoConstraints = false
        view.addSubview(loading)
        NSLayoutConstraint.activate([
            loading.topAnchor.constraint(equalTo: view.topAnchor),
            loading.leadingAnchor.constraint(equalTo: view.leadingAnchor),
            loading.trailingAnchor.constraint(equalTo: view.trailingAnchor),
            loading.bottomAnchor.constraint(equalTo: view.bottomAnchor),
            loadCol.centerXAnchor.constraint(equalTo: loading.centerXAnchor),
            loadCol.centerYAnchor.constraint(equalTo: loading.centerYAnchor),
        ])
        showPage(.list)
        reloadList()
    }

    override var preferredStatusBarStyle: UIStatusBarStyle { .lightContent }

    private func embed(_ child: UIViewController) {
        addChild(child)
        child.view.translatesAutoresizingMaskIntoConstraints = false
        view.addSubview(child.view)
        NSLayoutConstraint.activate([
            child.view.topAnchor.constraint(equalTo: view.topAnchor),
            child.view.leadingAnchor.constraint(equalTo: view.leadingAnchor),
            child.view.trailingAnchor.constraint(equalTo: view.trailingAnchor),
            child.view.bottomAnchor.constraint(equalTo: view.bottomAnchor),
        ])
        child.didMove(toParent: self)
    }

    private func showPage(_ next: Page) {
        page = next
        listVC.view.isHidden = next != .list
        captureVC.view.isHidden = next != .capture
        prepareVC.view.isHidden = next != .prepare
        playerVC.view.isHidden = next != .player
        view.bringSubviewToFront(loading)
    }

    private func reloadList() {
        listVC.reload(library: library)
    }

    private func openCapture() {
        showPage(.capture)
        captureVC.openCamera()
    }

    private func openImport() {
        showPage(.capture)
        captureVC.openImport()
    }

    private func goList() {
        captureVC.stopAndReset()
        prepareVC.releasePrepare()
        playerVC.releasePlayer()
        showPage(.list)
        reloadList()
    }

    private func openPrepare(_ clipId: String) {
        prepareVC.open(clipId: clipId)
        showPage(.prepare)
    }

    private func openPlayer(_ clipId: String) {
        playerVC.open(clipId: clipId)
        showPage(.player)
    }

    private func onLanguageChanged() {
        listVC.retranslate()
        captureVC.retranslate()
        prepareVC.retranslate()
        playerVC.retranslate()
        reprojectReports()
        reloadList()
    }

    private func enqueueAnalysis(_ clipId: String) {
        analyzing = true
        showLoading("analyze")
        DispatchQueue.global(qos: .userInitiated).async { [weak self] in
            self?.runAnalysis(clipId)
            DispatchQueue.main.async {
                self?.analyzing = false
                self?.hideLoadingIfIdle()
                if self?.page == .list {
                    self?.reloadList()
                }
            }
        }
    }

    private func runAnalysis(_ clipId: String) {
        do {
            let meta = library.loadMeta(clipId)
            let markers = try engine.createPair()
            defer { markers.close() }
            let frames: [PoseFrame]
            if meta.kind == .image {
                guard let image = UIImage(contentsOfFile: library.mediaFile(meta).path) else {
                    throw NSError(domain: "analyze", code: 1)
                }
                frames = VideoPose.analyzeBitmap(
                    image,
                    markers: markers,
                    device: engine.device,
                    seeds: meta.seeds,
                    seedBox: meta.seedBox
                )
            } else {
                let window = Library.playWindowMs(meta)
                let fps = meta.fps > 1 ? meta.fps : 30
                frames = VideoPose.analyze(
                    asset: AVAsset(url: library.mediaFile(meta)),
                    markers: markers,
                    device: engine.device,
                    startMs: window.0,
                    endMs: window.1,
                    seeds: meta.seeds,
                    seedBox: meta.seedBox,
                    fpsIn: fps,
                    onProgress: { _, _ in }
                )
            }
            AnalysisJson.save(library.analysisFile(clipId), clipId: clipId, frames: frames)
            let fps = meta.fps > 1 ? meta.fps : 15
            writeStageReport(clipId, frames, fps)
            var done = meta
            done.status = .done
            done.error = nil
            library.saveMeta(done)
        } catch {
            var failed = library.loadMeta(clipId)
            failed.status = .processing
            failed.error = error.localizedDescription
            library.saveMeta(failed)
        }
    }

    private func writeStageReport(_ clipId: String, _ frames: [PoseFrame], _ fps: Double) {
        let report = Assess.assessClip(
            clipId: clipId,
            frames: AnalysisJson.toAssessFrames(frames),
            fps: fps,
            curriculum: curriculum(),
            lang: I18n.language()
        )
        StageReportJson.save(library.stageReportFile(clipId), report)
    }

    private func curriculum() -> Curriculum {
        if let curriculumCache { return curriculumCache }
        let loaded = CurriculumLoader.loadFromBundle()
        curriculumCache = loaded
        return loaded
    }

    private func reprojectReports() {
        DispatchQueue.global(qos: .userInitiated).async { [weak self] in
            guard let self else { return }
            let cur = self.curriculum()
            let lang = I18n.language()
            for meta in self.library.listClips() where meta.status == .done {
                let frames = AnalysisJson.load(self.library.analysisFile(meta.clipId))
                if frames.contains(where: { $0.blaze33.count >= 33 }) {
                    let fps = meta.fps > 1 ? meta.fps : 15
                    let report = Assess.assessClip(
                        clipId: meta.clipId,
                        frames: AnalysisJson.toAssessFrames(frames),
                        fps: fps,
                        curriculum: cur,
                        lang: lang
                    )
                    StageReportJson.save(self.library.stageReportFile(meta.clipId), report)
                }
            }
            DispatchQueue.main.async {
                self.playerVC.reloadReport()
                if self.page == .list {
                    self.reloadList()
                }
            }
        }
    }

    private func showLoading(_ kind: String) {
        loadingCaption.text = kind == "import"
            ? I18n.t("Uploading and loading…")
            : I18n.t("Analyzing pose…")
        loading.isHidden = false
        loadingSpinner.startAnimating()
        view.bringSubviewToFront(loading)
    }

    private func hideLoadingIfIdle() {
        if !analyzing {
            loading.isHidden = true
            loadingSpinner.stopAnimating()
        }
    }
}
