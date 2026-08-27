import AVFoundation
import UIKit

final class PrepareViewController: UIViewController {
    var library: Library!
    var athletes: Athletes!
    var onBack: (() -> Void)?
    var onStartAnalysis: ((String) -> Void)?

    private let canvas = SeedCanvasView()
    private let timeLabel = UILabel()
    private let timeline = TimelineStripView()
    private let rangeLabel = UILabel()
    private let btnStart = PoseButtons.accent(icon: "ok")
    private let back = FloatingBackButton()

    private let labelProfile = UILabel()
    private let labelName = UILabel()
    private let labelBirthday = UILabel()
    private let labelHeight = UILabel()
    private let labelGender = UILabel()
    private let labelWeight = UILabel()
    private let labelSki = UILabel()
    private let unitHeight = UILabel()
    private let unitWeight = UILabel()
    private let unitSki = UILabel()
    private let btnProfile = UIButton(type: .system)
    private let btnGender = UIButton(type: .system)
    private let inputName = UITextField()
    private let inputBirthday = UIButton(type: .system)
    private let inputHeight = UITextField()
    private let inputWeight = UITextField()
    private let inputSki = UITextField()

    private var meta: ClipMeta?
    private var generator: AVAssetImageGenerator?
    private var prepareTMs = 0
    private var prepareInMs = 0
    private var prepareOutMs: Int?
    private var prepareSeeds: [Int: SeedMark] = [:]
    private var birthday = Calendar.current.date(from: DateComponents(year: 1990, month: 1, day: 1)) ?? Date()
    private var loadingProfile = false
    private var gender: AthleteGender = .unspecified
    private var profileKey = ""
    private let genderOrder: [AthleteGender] = [.unspecified, .female, .male, .other]

    override func viewDidLoad() {
        super.viewDidLoad()
        view.backgroundColor = Theme.surface
        timeLabel.textColor = Theme.paper
        rangeLabel.textColor = Theme.paper
        rangeLabel.numberOfLines = 0
        [labelProfile, labelName, labelBirthday, labelHeight, labelGender, labelWeight, labelSki].forEach {
            $0.textColor = Theme.paper
        }
        [unitHeight, unitWeight, unitSki].forEach { $0.textColor = Theme.title }

        styleField(btnProfile)
        styleField(btnGender)
        styleField(inputBirthday)
        styleTextField(inputName)
        styleTextField(inputHeight)
        styleTextField(inputWeight)
        styleTextField(inputSki)
        inputName.keyboardType = .default
        inputHeight.keyboardType = .decimalPad
        inputWeight.keyboardType = .decimalPad
        inputSki.keyboardType = .decimalPad
        inputHeight.text = "170"
        inputWeight.text = "65"
        inputSki.text = "160"

        btnStart.addAction(UIAction { [weak self] _ in self?.startAnalysis() }, for: .touchUpInside)
        btnProfile.addAction(UIAction { [weak self] _ in self?.showProfileMenu() }, for: .touchUpInside)
        btnGender.addAction(UIAction { [weak self] _ in self?.showGenderMenu() }, for: .touchUpInside)
        inputBirthday.addAction(UIAction { [weak self] _ in self?.showBirthdayPicker() }, for: .touchUpInside)
        canvas.boxCommitted = { [weak self] in self?.commitBox() }
        timeline.onPlayhead = { [weak self] tMs in
            self?.prepareTMs = tMs
            self?.showFrame()
        }
        timeline.onRange = { [weak self] startMs, endMs in
            self?.prepareInMs = startMs
            self?.prepareOutMs = endMs
            self?.refreshLabels()
        }
        timeline.setTrimEnabled(true)

        let nameCol = labeled(labelName, inputName)
        let birthCol = labeled(labelBirthday, inputBirthday)
        let heightField = unitField(inputHeight, unitHeight)
        let heightCol = labeled(labelHeight, heightField)
        let genderCol = labeled(labelGender, btnGender)
        let weightField = unitField(inputWeight, unitWeight)
        let weightCol = labeled(labelWeight, weightField)
        let skiField = unitField(inputSki, unitSki)
        let skiCol = labeled(labelSki, skiField)

        let row1 = cols(nameCol, birthCol)
        let row2 = cols(heightCol, genderCol)
        let row3 = cols(weightCol, skiCol)

        let form = UIStackView(arrangedSubviews: [labelProfile, btnProfile, row1, row2, row3, btnStart, rangeLabel])
        form.axis = .vertical
        form.spacing = Theme.spaceText
        form.setCustomSpacing(6, after: labelProfile)
        form.setCustomSpacing(Theme.spacePanel, after: row3)
        form.setCustomSpacing(Theme.spacePanel, after: btnStart)
        btnStart.contentHorizontalAlignment = .left

        let formScroll = UIScrollView()
        formScroll.showsVerticalScrollIndicator = false
        formScroll.addSubview(form)
        form.translatesAutoresizingMaskIntoConstraints = false

        let col = UIStackView(arrangedSubviews: [canvas, timeLabel, timeline, formScroll])
        col.axis = .vertical
        col.spacing = Theme.spacePanel
        col.translatesAutoresizingMaskIntoConstraints = false
        canvas.setContentHuggingPriority(.required, for: .vertical)
        timeline.setContentHuggingPriority(.required, for: .vertical)
        view.addSubview(col)
        NSLayoutConstraint.activate([
            col.topAnchor.constraint(equalTo: view.safeAreaLayoutGuide.topAnchor, constant: Theme.floatingBack + Theme.pageInset),
            col.leadingAnchor.constraint(equalTo: view.leadingAnchor, constant: Theme.pageInset),
            col.trailingAnchor.constraint(equalTo: view.trailingAnchor, constant: -Theme.pageInset),
            col.bottomAnchor.constraint(equalTo: view.bottomAnchor, constant: -Theme.pageInset),
            form.topAnchor.constraint(equalTo: formScroll.contentLayoutGuide.topAnchor),
            form.leadingAnchor.constraint(equalTo: formScroll.contentLayoutGuide.leadingAnchor),
            form.trailingAnchor.constraint(equalTo: formScroll.contentLayoutGuide.trailingAnchor),
            form.bottomAnchor.constraint(equalTo: formScroll.contentLayoutGuide.bottomAnchor),
            form.widthAnchor.constraint(equalTo: formScroll.frameLayoutGuide.widthAnchor),
            btnProfile.heightAnchor.constraint(equalToConstant: 44),
            btnGender.heightAnchor.constraint(equalToConstant: 44),
            inputBirthday.heightAnchor.constraint(equalToConstant: 44),
        ])
        back.attach(to: view)
        back.onTap = { [weak self] in
            self?.releasePrepare()
            self?.onBack?()
        }
        retranslate()
    }

    func open(clipId: String) {
        releasePrepare()
        let meta = library.loadMeta(clipId)
        self.meta = meta
        prepareInMs = meta.playStartMs
        prepareOutMs = meta.playEndMs
        prepareTMs = prepareInMs
        prepareSeeds = [:]
        let loaded = meta.seeds.isEmpty
            ? (meta.seedBox.map { [SeedMark(tMs: 0, box: $0)] } ?? [])
            : meta.seeds
        for item in loaded {
            prepareSeeds[seedFrameKey(item.tMs)] = item
        }
        reloadProfiles(meta.athleteKey)
        if let key = meta.athleteKey, athletes.getByKey(key) != nil {
            applyProfileKey(key)
        } else if let athlete = meta.athlete {
            fillFromProfile(athlete)
        }
        let media = library.mediaFile(meta)
        if meta.kind == .image {
            timeline.isHidden = true
            let bmp = UIImage(contentsOfFile: media.path)
            canvas.setFrame(bmp)
            DispatchQueue.main.async { [weak self] in
                self?.canvas.setBoxNorm(self?.seedNear(Double(self?.prepareTMs ?? 0))?.box)
            }
        } else {
            timeline.isHidden = false
            let asset = AVAsset(url: media)
            let gen = AVAssetImageGenerator(asset: asset)
            gen.appliesPreferredTrackTransform = true
            gen.requestedTimeToleranceBefore = .zero
            gen.requestedTimeToleranceAfter = .zero
            generator = gen
            let window = Library.playWindowMs(meta)
            if meta.playEndMs != nil {
                prepareOutMs = Int(window.1)
            }
            if meta.playStartMs != 0 || meta.playEndMs != nil {
                prepareInMs = Int(window.0)
            }
            prepareTMs = prepareInMs
            timeline.bindVideo(url: media, duration: max(1, meta.durationMs))
            timeline.setRange(startMs: prepareInMs, endMs: prepareOutMs)
            syncKeyframes()
            showFrame()
        }
        refreshLabels()
    }

    func retranslate() {
        back.retranslate()
        btnStart.accessibilityLabel = I18n.t("Start analysis")
        labelProfile.text = I18n.t("Saved profile")
        labelName.text = I18n.t("Name")
        labelBirthday.text = I18n.t("Birthday")
        labelHeight.text = I18n.t("Height")
        labelGender.text = I18n.t("Gender")
        labelWeight.text = I18n.t("Weight")
        labelSki.text = I18n.t("Ski length")
        unitHeight.text = I18n.t(" cm")
        unitWeight.text = I18n.t(" kg")
        unitSki.text = I18n.t(" cm")
        refreshGenderTitle()
        reloadProfiles(profileKey)
        refreshBirthdayLabel()
        refreshLabels()
    }

    func releasePrepare() {
        timeline.clear()
        generator = nil
        canvas.setFrame(nil)
        meta = nil
        prepareSeeds.removeAll()
    }

    private func showFrame() {
        guard let generator else { return }
        let time = CMTime(value: CMTimeValue(prepareTMs), timescale: 1000)
        if let cg = try? generator.copyCGImage(at: time, actualTime: nil) {
            canvas.setFrame(UIImage(cgImage: cg))
        }
        DispatchQueue.main.async { [weak self] in
            guard let self else { return }
            self.canvas.setBoxNorm(self.seedNear(Double(self.prepareTMs))?.box)
        }
        timeline.setPlayheadMs(prepareTMs)
        refreshLabels()
    }

    private func refreshLabels() {
        guard let meta else { return }
        timeLabel.text = "\(Library.formatDurationMs(prepareTMs)) / \(Library.formatDurationMs(meta.durationMs))"
        let out = prepareOutMs ?? meta.durationMs
        rangeLabel.text = I18n.t(
            "In {lo:.1f}s → out {hi:.1f}s (logical, original file unchanged)",
            vars: [
                "lo": String(format: "%.1f", Double(prepareInMs) / 1000),
                "hi": String(format: "%.1f", Double(out) / 1000),
            ]
        )
    }

    private func commitBox() {
        if let box = canvas.boxNorm() {
            prepareSeeds[seedFrameKey(Double(prepareTMs))] = SeedMark(tMs: Double(prepareTMs), box: box)
            syncKeyframes()
        }
    }

    private func startAnalysis() {
        guard var meta else { return }
        if prepareSeeds.isEmpty, let live = canvas.boxNorm() {
            prepareSeeds[seedFrameKey(Double(prepareTMs))] = SeedMark(tMs: Double(prepareTMs), box: live)
        }
        if prepareSeeds.isEmpty {
            poseAlert(titleKey: "No box", messageKey: "Record at least one person box.")
            return
        }
        guard let athlete = readAthlete() else {
            poseAlert(
                titleKey: "Athlete info required",
                messageKey: "Enter name, height, weight, and ski length, or pick a saved profile."
            )
            return
        }
        reloadProfiles(athlete.key)
        let seeds = prepareSeeds.values.sorted { $0.tMs < $1.tMs }
        meta.seeds = seeds
        meta.seedBox = seeds.first?.box
        meta.playStartMs = prepareInMs
        meta.playEndMs = prepareOutMs
        meta.athleteKey = athlete.key
        meta.athlete = athlete
        meta.status = .processing
        meta.error = nil
        library.saveMeta(meta)
        let clipId = meta.clipId
        releasePrepare()
        onStartAnalysis?(clipId)
    }

    private func seedFrameKey(_ tMs: Double) -> Int {
        let fps = max(meta?.fps ?? 30, 1)
        return Int((tMs / (1000 / fps)).rounded())
    }

    private func seedNear(_ tMs: Double) -> SeedMark? {
        if let hit = prepareSeeds[seedFrameKey(tMs)] { return hit }
        var hit: SeedMark?
        var best = 40.0
        for item in prepareSeeds.values {
            let delta = abs(item.tMs - tMs)
            if delta <= best {
                best = delta
                hit = item
            }
        }
        return hit
    }

    private func syncKeyframes() {
        timeline.setKeyframes(prepareSeeds.values.map { Int($0.tMs) })
    }

    private func showBirthdayPicker() {
        let picker = UIDatePicker()
        picker.datePickerMode = .date
        picker.preferredDatePickerStyle = .wheels
        picker.date = birthday
        picker.overrideUserInterfaceStyle = .dark
        let alert = UIAlertController(title: I18n.t("Birthday"), message: "\n\n\n\n\n\n\n\n\n", preferredStyle: .alert)
        alert.view.addSubview(picker)
        picker.translatesAutoresizingMaskIntoConstraints = false
        NSLayoutConstraint.activate([
            picker.centerXAnchor.constraint(equalTo: alert.view.centerXAnchor),
            picker.topAnchor.constraint(equalTo: alert.view.topAnchor, constant: 50),
        ])
        alert.addAction(UIAlertAction(title: I18n.t("OK"), style: .default) { [weak self] _ in
            self?.birthday = picker.date
            self?.refreshBirthdayLabel()
        })
        alert.addAction(UIAlertAction(title: I18n.t("Cancel"), style: .cancel))
        present(alert, animated: true)
    }

    private func refreshBirthdayLabel() {
        let fmt = DateFormatter()
        fmt.locale = Locale(identifier: "en_US_POSIX")
        fmt.dateFormat = I18n.t("MM/dd/yyyy")
        inputBirthday.setTitle(fmt.string(from: birthday), for: .normal)
        inputBirthday.setTitleColor(Theme.paper, for: .normal)
    }

    private func birthdayIso() -> String {
        let c = Calendar.current.dateComponents([.year, .month, .day], from: birthday)
        return String(format: "%04d-%02d-%02d", c.year ?? 1990, c.month ?? 1, c.day ?? 1)
    }

    private func refreshGenderTitle() {
        let labels: [AthleteGender: String] = [
            .unspecified: I18n.t("Unspecified"),
            .female: I18n.t("Female"),
            .male: I18n.t("Male"),
            .other: I18n.t("Other"),
        ]
        btnGender.setTitle(labels[gender], for: .normal)
        btnGender.setTitleColor(Theme.paper, for: .normal)
    }

    private func showGenderMenu() {
        let sheet = UIAlertController(title: I18n.t("Gender"), message: nil, preferredStyle: .actionSheet)
        for g in genderOrder {
            let title: String
            switch g {
            case .unspecified: title = I18n.t("Unspecified")
            case .female: title = I18n.t("Female")
            case .male: title = I18n.t("Male")
            case .other: title = I18n.t("Other")
            }
            sheet.addAction(UIAlertAction(title: title, style: .default) { [weak self] _ in
                self?.gender = g
                self?.refreshGenderTitle()
            })
        }
        sheet.addAction(UIAlertAction(title: I18n.t("Cancel"), style: .cancel))
        sheet.popoverPresentationController?.sourceView = btnGender
        present(sheet, animated: true)
    }

    private func reloadProfiles(_ preserveKey: String?) {
        loadingProfile = true
        profileKey = preserveKey ?? ""
        if profileKey.isEmpty {
            btnProfile.setTitle(I18n.t("New profile"), for: .normal)
        } else {
            btnProfile.setTitle(profileKey, for: .normal)
        }
        btnProfile.setTitleColor(Theme.paper, for: .normal)
        loadingProfile = false
    }

    private func showProfileMenu() {
        let sheet = UIAlertController(title: I18n.t("Saved profile"), message: nil, preferredStyle: .actionSheet)
        sheet.addAction(UIAlertAction(title: I18n.t("New profile"), style: .default) { [weak self] _ in
            self?.profileKey = ""
            self?.reloadProfiles("")
        })
        for item in athletes.list() {
            sheet.addAction(UIAlertAction(title: item.key, style: .default) { [weak self] _ in
                self?.applyProfileKey(item.key)
            })
        }
        sheet.addAction(UIAlertAction(title: I18n.t("Cancel"), style: .cancel))
        sheet.popoverPresentationController?.sourceView = btnProfile
        present(sheet, animated: true)
    }

    private func applyProfileKey(_ key: String) {
        guard let profile = athletes.getByKey(key) else { return }
        fillFromProfile(profile)
        profileKey = profile.key
        reloadProfiles(profile.key)
    }

    private func fillFromProfile(_ profile: AthleteProfile) {
        inputName.text = profile.name
        inputHeight.text = Athletes.formatMeasure(profile.heightCm)
        inputWeight.text = Athletes.formatMeasure(profile.weightKg)
        inputSki.text = Athletes.formatMeasure(profile.skiCm)
        gender = profile.gender
        refreshGenderTitle()
        if !profile.birthday.isEmpty {
            let parts = profile.birthday.split(separator: "-").compactMap { Int($0) }
            if parts.count >= 3 {
                birthday = Calendar.current.date(from: DateComponents(year: parts[0], month: parts[1], day: parts[2])) ?? birthday
            }
        } else {
            birthday = Calendar.current.date(from: DateComponents(year: 1990, month: 1, day: 1)) ?? Date()
        }
        refreshBirthdayLabel()
    }

    private func readAthlete() -> AthleteProfile? {
        let name = inputName.text?.trimmingCharacters(in: .whitespaces) ?? ""
        if name.isEmpty { return nil }
        guard let height = Float(inputHeight.text ?? ""),
              let weight = Float(inputWeight.text ?? ""),
              let ski = Float(inputSki.text ?? "")
        else { return nil }
        return try? athletes.upsert(
            name: name,
            weightKg: weight,
            heightCm: height,
            skiCm: ski,
            birthday: birthdayIso(),
            gender: gender
        )
    }

    private func styleField(_ button: UIButton) {
        button.backgroundColor = UIColor(rgb: 0x2A2A2A)
        button.layer.cornerRadius = 8
        button.layer.borderWidth = 1
        button.layer.borderColor = UIColor(rgb: 0x3D3D3D).cgColor
        button.contentHorizontalAlignment = .left
        button.contentEdgeInsets = UIEdgeInsets(top: 0, left: 12, bottom: 0, right: 12)
    }

    private func styleTextField(_ field: UITextField) {
        field.backgroundColor = UIColor(rgb: 0x2A2A2A)
        field.layer.cornerRadius = 8
        field.layer.borderWidth = 1
        field.layer.borderColor = UIColor(rgb: 0x3D3D3D).cgColor
        field.textColor = Theme.paper
        field.leftView = UIView(frame: CGRect(x: 0, y: 0, width: 12, height: 44))
        field.leftViewMode = .always
        field.heightAnchor.constraint(equalToConstant: 44).isActive = true
        field.autocorrectionType = .no
    }

    private func labeled(_ label: UILabel, _ field: UIView) -> UIStackView {
        let col = UIStackView(arrangedSubviews: [label, field])
        col.axis = .vertical
        col.spacing = 6
        return col
    }

    private func unitField(_ field: UITextField, _ unit: UILabel) -> UIView {
        field.backgroundColor = .clear
        field.layer.borderWidth = 0
        let box = UIView()
        box.backgroundColor = UIColor(rgb: 0x2A2A2A)
        box.layer.cornerRadius = 8
        box.layer.borderWidth = 1
        box.layer.borderColor = UIColor(rgb: 0x3D3D3D).cgColor
        let row = UIStackView(arrangedSubviews: [field, unit])
        row.axis = .horizontal
        row.alignment = .center
        row.isLayoutMarginsRelativeArrangement = true
        row.layoutMargins = UIEdgeInsets(top: 0, left: 0, bottom: 0, right: 12)
        row.translatesAutoresizingMaskIntoConstraints = false
        box.addSubview(row)
        NSLayoutConstraint.activate([
            box.heightAnchor.constraint(equalToConstant: 44),
            row.topAnchor.constraint(equalTo: box.topAnchor),
            row.bottomAnchor.constraint(equalTo: box.bottomAnchor),
            row.leadingAnchor.constraint(equalTo: box.leadingAnchor),
            row.trailingAnchor.constraint(equalTo: box.trailingAnchor),
        ])
        return box
    }

    private func cols(_ a: UIView, _ b: UIView) -> UIStackView {
        let row = UIStackView(arrangedSubviews: [a, b])
        row.axis = .horizontal
        row.distribution = .fillEqually
        row.spacing = Theme.spacePanel
        return row
    }
}
