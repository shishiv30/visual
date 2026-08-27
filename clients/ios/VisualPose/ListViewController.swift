import UIKit

final class ListViewController: UIViewController {
    var onCamera: (() -> Void)?
    var onImport: (() -> Void)?
    var onLanguageChanged: (() -> Void)?
    var onOpenPrepare: ((String) -> Void)?
    var onOpenPlayer: ((String) -> Void)?
    var onReanalyze: ((String) -> Void)?
    var onDelete: ((String) -> Void)?

    private let btnCamera = PoseButtons.accent(icon: "camera")
    private let btnImport = PoseButtons.accent(icon: "import")
    private let labelLanguage = UILabel()
    private let btnLanguage = UIButton(type: .system)
    private let stack = UIStackView()
    private var library: Library?

    override func viewDidLoad() {
        super.viewDidLoad()
        view.backgroundColor = Theme.surface
        labelLanguage.textColor = Theme.paper
        labelLanguage.font = .systemFont(ofSize: 15)
        styleLanguageButton()
        btnCamera.addAction(UIAction { [weak self] _ in self?.onCamera?() }, for: .touchUpInside)
        btnImport.addAction(UIAction { [weak self] _ in self?.onImport?() }, for: .touchUpInside)
        btnLanguage.addAction(UIAction { [weak self] _ in self?.showLanguageMenu() }, for: .touchUpInside)

        let top = UIStackView(arrangedSubviews: [btnCamera, btnImport, UIView(), labelLanguage, btnLanguage])
        top.axis = .horizontal
        top.alignment = .center
        top.spacing = 10

        stack.axis = .vertical
        stack.spacing = Theme.spacePanel
        let scroll = UIScrollView()
        scroll.showsVerticalScrollIndicator = false
        scroll.addSubview(stack)
        stack.translatesAutoresizingMaskIntoConstraints = false

        let col = UIStackView(arrangedSubviews: [top, scroll])
        col.axis = .vertical
        col.spacing = Theme.spacePanel
        col.translatesAutoresizingMaskIntoConstraints = false
        view.addSubview(col)
        NSLayoutConstraint.activate([
            col.topAnchor.constraint(equalTo: view.safeAreaLayoutGuide.topAnchor, constant: Theme.reportInset),
            col.leadingAnchor.constraint(equalTo: view.safeAreaLayoutGuide.leadingAnchor, constant: Theme.reportInset),
            col.trailingAnchor.constraint(equalTo: view.safeAreaLayoutGuide.trailingAnchor, constant: -Theme.reportInset),
            col.bottomAnchor.constraint(equalTo: view.bottomAnchor),
            stack.topAnchor.constraint(equalTo: scroll.contentLayoutGuide.topAnchor),
            stack.leadingAnchor.constraint(equalTo: scroll.contentLayoutGuide.leadingAnchor),
            stack.trailingAnchor.constraint(equalTo: scroll.contentLayoutGuide.trailingAnchor),
            stack.bottomAnchor.constraint(equalTo: scroll.contentLayoutGuide.bottomAnchor),
            stack.widthAnchor.constraint(equalTo: scroll.frameLayoutGuide.widthAnchor),
        ])
        retranslate()
    }

    func reload(library: Library) {
        self.library = library
        stack.arrangedSubviews.forEach {
            stack.removeArrangedSubview($0)
            $0.removeFromSuperview()
        }
        for meta in library.listClips() {
            stack.addArrangedSubview(makeRow(meta, library: library))
        }
    }

    func retranslate() {
        btnCamera.accessibilityLabel = I18n.t("Camera")
        btnImport.accessibilityLabel = I18n.t("Import")
        labelLanguage.text = I18n.t("Language")
        let current = I18n.labels.first { $0.0 == I18n.language() }?.1 ?? I18n.language()
        btnLanguage.setTitle(current, for: .normal)
        if let library {
            reload(library: library)
        }
    }

    private func styleLanguageButton() {
        btnLanguage.backgroundColor = UIColor(rgb: 0x2A2A2A)
        btnLanguage.layer.cornerRadius = 8
        btnLanguage.layer.borderWidth = 1
        btnLanguage.layer.borderColor = UIColor(rgb: 0x3D3D3D).cgColor
        btnLanguage.setTitleColor(Theme.paper, for: .normal)
        btnLanguage.contentEdgeInsets = UIEdgeInsets(top: 6, left: 12, bottom: 6, right: 12)
        btnLanguage.heightAnchor.constraint(equalToConstant: Theme.controlHeight).isActive = true
        btnLanguage.widthAnchor.constraint(greaterThanOrEqualToConstant: 120).isActive = true
    }

    private func showLanguageMenu() {
        let sheet = UIAlertController(title: I18n.t("Language"), message: nil, preferredStyle: .actionSheet)
        for (code, label) in I18n.labels {
            sheet.addAction(UIAlertAction(title: label, style: .default) { [weak self] _ in
                if code != I18n.language() {
                    I18n.setLanguage(code)
                    self?.onLanguageChanged?()
                }
            })
        }
        sheet.addAction(UIAlertAction(title: I18n.t("Cancel"), style: .cancel))
        sheet.popoverPresentationController?.sourceView = btnLanguage
        present(sheet, animated: true)
    }

    private func makeRow(_ meta: ClipMeta, library: Library) -> UIView {
        let row = UIView()
        row.backgroundColor = UIColor(rgb: 0x1E1E1E)
        row.layer.cornerRadius = Theme.cardRadius
        row.clipsToBounds = true

        let hit = UIControl()
        hit.addAction(UIAction { [weak self] _ in self?.onRowClick(meta) }, for: .touchUpInside)

        let thumb = UIImageView()
        thumb.backgroundColor = .black
        thumb.contentMode = .scaleAspectFill
        thumb.clipsToBounds = true
        thumb.translatesAutoresizingMaskIntoConstraints = false
        NSLayoutConstraint.activate([
            thumb.widthAnchor.constraint(equalToConstant: 128),
            thumb.heightAnchor.constraint(equalToConstant: 72),
        ])
        let thumbURL = library.thumbFile(meta.clipId)
        if FileManager.default.fileExists(atPath: thumbURL.path),
           let image = UIImage(contentsOfFile: thumbURL.path) {
            thumb.image = image
        } else {
            let placeholder = UILabel()
            placeholder.text = I18n.t("No preview")
            placeholder.textColor = Theme.title
            placeholder.font = .systemFont(ofSize: 11)
            placeholder.textAlignment = .center
            placeholder.translatesAutoresizingMaskIntoConstraints = false
            thumb.addSubview(placeholder)
            NSLayoutConstraint.activate([
                placeholder.centerXAnchor.constraint(equalTo: thumb.centerXAnchor),
                placeholder.centerYAnchor.constraint(equalTo: thumb.centerYAnchor),
            ])
        }

        let name = UILabel()
        name.text = meta.displayName
        name.textColor = Theme.paper
        name.font = .systemFont(ofSize: 15)
        name.lineBreakMode = .byTruncatingTail

        let duration = UILabel()
        duration.text = Library.formatDurationMs(meta.durationMs, image: meta.kind == .image)
        duration.textColor = Theme.paper
        duration.font = .systemFont(ofSize: 13)

        var statusText = I18n.t(Library.statusKey(meta.status))
        if meta.error != nil {
            statusText = I18n.t("{status} (failed, retry)", vars: ["status": statusText])
        }
        let status = UILabel()
        status.text = statusText
        status.font = .systemFont(ofSize: 13)
        status.textColor = meta.status == .pending ? Theme.title : Theme.lightPurple

        let spinner = UIActivityIndicatorView(style: .medium)
        spinner.color = Theme.deepPurple
        spinner.transform = CGAffineTransform(scaleX: 0.7, y: 0.7)
        if meta.status == .processing {
            spinner.startAnimating()
        } else {
            spinner.isHidden = true
        }
        let statusRow = UIStackView(arrangedSubviews: [spinner, status, UIView()])
        statusRow.axis = .horizontal
        statusRow.alignment = .center
        statusRow.spacing = 6

        let mid = UIStackView(arrangedSubviews: [name, duration, statusRow])
        mid.axis = .vertical
        mid.spacing = 4
        mid.setContentHuggingPriority(.defaultLow, for: .horizontal)

        let btnReport = PoseButtons.accent(icon: "report")
        let btnReanalyze = PoseButtons.accent(icon: "reanalyze", background: Theme.medalAdvanced)
        let btnDelete = PoseButtons.accent(icon: "delete", background: Theme.watermelon)
        btnReport.accessibilityLabel = I18n.t("Report")
        btnReanalyze.accessibilityLabel = I18n.t("Reanalyze")
        btnDelete.accessibilityLabel = I18n.t("Delete")
        let hasReport = meta.status == .done && FileManager.default.fileExists(atPath: library.stageReportFile(meta.clipId).path)
        btnReport.isHidden = !hasReport
        btnReanalyze.isHidden = meta.status == .processing
        btnReport.addAction(UIAction { [weak self] _ in self?.onOpenPlayer?(meta.clipId) }, for: .touchUpInside)
        btnReanalyze.addAction(UIAction { [weak self] _ in self?.onReanalyze?(meta.clipId) }, for: .touchUpInside)
        btnDelete.addAction(UIAction { [weak self] _ in self?.confirmDelete(meta.clipId) }, for: .touchUpInside)

        let actions = UIStackView(arrangedSubviews: [btnReport, btnReanalyze, btnDelete])
        actions.axis = .horizontal
        actions.spacing = 4
        actions.alignment = .center
        let actionScroll = UIScrollView()
        actionScroll.showsHorizontalScrollIndicator = false
        actionScroll.addSubview(actions)
        actions.translatesAutoresizingMaskIntoConstraints = false
        NSLayoutConstraint.activate([
            actions.topAnchor.constraint(equalTo: actionScroll.contentLayoutGuide.topAnchor),
            actions.bottomAnchor.constraint(equalTo: actionScroll.contentLayoutGuide.bottomAnchor),
            actions.leadingAnchor.constraint(equalTo: actionScroll.contentLayoutGuide.leadingAnchor),
            actions.trailingAnchor.constraint(equalTo: actionScroll.contentLayoutGuide.trailingAnchor),
            actions.heightAnchor.constraint(equalTo: actionScroll.frameLayoutGuide.heightAnchor),
        ])

        let info = UIStackView(arrangedSubviews: [thumb, mid])
        info.axis = .horizontal
        info.alignment = .center
        info.spacing = 10
        info.isUserInteractionEnabled = false
        hit.addSubview(info)
        info.translatesAutoresizingMaskIntoConstraints = false

        let body = UIStackView(arrangedSubviews: [hit, actionScroll])
        body.axis = .horizontal
        body.alignment = .center
        body.spacing = 10
        body.isLayoutMarginsRelativeArrangement = true
        body.layoutMargins = UIEdgeInsets(top: 0, left: 0, bottom: 0, right: 8)
        body.translatesAutoresizingMaskIntoConstraints = false
        row.addSubview(body)
        NSLayoutConstraint.activate([
            info.topAnchor.constraint(equalTo: hit.topAnchor),
            info.leadingAnchor.constraint(equalTo: hit.leadingAnchor),
            info.trailingAnchor.constraint(equalTo: hit.trailingAnchor),
            info.bottomAnchor.constraint(equalTo: hit.bottomAnchor),
            body.topAnchor.constraint(equalTo: row.topAnchor),
            body.leadingAnchor.constraint(equalTo: row.leadingAnchor),
            body.trailingAnchor.constraint(equalTo: row.trailingAnchor),
            body.bottomAnchor.constraint(equalTo: row.bottomAnchor),
            actionScroll.widthAnchor.constraint(lessThanOrEqualToConstant: 160),
        ])
        return row
    }

    private func onRowClick(_ meta: ClipMeta) {
        switch meta.status {
        case .pending:
            onOpenPrepare?(meta.clipId)
        case .processing:
            poseAlert(
                titleKey: "Processing",
                messageKey: "This clip is still processing. Play it when it is done."
            )
        case .done:
            onOpenPlayer?(meta.clipId)
        }
    }

    private func confirmDelete(_ clipId: String) {
        let alert = UIAlertController(
            title: I18n.t("Delete"),
            message: I18n.t("Delete this clip and its local files? This cannot be undone."),
            preferredStyle: .alert
        )
        alert.addAction(UIAlertAction(title: I18n.t("OK"), style: .destructive) { [weak self] _ in
            self?.onDelete?(clipId)
        })
        alert.addAction(UIAlertAction(title: I18n.t("Cancel"), style: .cancel))
        present(alert, animated: true)
    }
}
