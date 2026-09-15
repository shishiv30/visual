import UIKit

final class ReportPanelView: UIView {
    var onSeek: ((Int) -> Void)?
    var onJumpToSkillTree: (() -> Void)?

    private let empty = UILabel()
    private let heroCard = UIStackView()
    private let heroSpacer = UIView()
    private let blocks = (0..<5).map { _ in UIStackView() }
    private let chapters = (0..<5).map { _ in UIStackView() }
    private let titles = (0..<5).map { _ in UILabel() }
    private var report: StageReport?

    override init(frame: CGRect) {
        super.init(frame: frame)
        let root = UIStackView()
        root.axis = .vertical
        root.translatesAutoresizingMaskIntoConstraints = false
        addSubview(root)
        NSLayoutConstraint.activate([
            root.topAnchor.constraint(equalTo: topAnchor, constant: Theme.reportInset),
            root.leadingAnchor.constraint(equalTo: leadingAnchor, constant: Theme.reportInset),
            root.trailingAnchor.constraint(equalTo: trailingAnchor, constant: -Theme.reportInset),
            root.bottomAnchor.constraint(equalTo: bottomAnchor, constant: -Theme.reportInset),
        ])
        empty.textColor = Theme.title
        empty.font = .systemFont(ofSize: 16)
        empty.numberOfLines = 0
        root.addArrangedSubview(empty)
        heroCard.axis = .vertical
        heroCard.isHidden = true
        root.addArrangedSubview(heroCard)
        heroSpacer.heightAnchor.constraint(equalToConstant: Theme.spaceChapter - Theme.spaceText).isActive = true
        root.addArrangedSubview(heroSpacer)
        for i in 0..<5 {
            titles[i].textColor = Theme.title
            titles[i].font = .systemFont(ofSize: 32)
            titles[i].numberOfLines = 0
            chapters[i].axis = .vertical
            chapters[i].spacing = Theme.spacePanel
            blocks[i].axis = .vertical
            blocks[i].spacing = Theme.spaceText
            blocks[i].addArrangedSubview(titles[i])
            blocks[i].addArrangedSubview(chapters[i])
            if i > 0 {
                let spacer = UIView()
                spacer.heightAnchor.constraint(equalToConstant: Theme.spaceChapter - Theme.spaceText).isActive = true
                root.addArrangedSubview(spacer)
            }
            root.addArrangedSubview(blocks[i])
        }
        retranslate()
        bind(nil)
    }

    required init?(coder: NSCoder) {
        super.init(coder: coder)
    }

    func retranslate() {
        empty.text = I18n.t("No stage report yet. Analyze a clip offline first.")
        titles[0].text = I18n.t("Summary")
        titles[1].text = I18n.t("Checkpoints")
        titles[2].text = I18n.t("Next steps")
        titles[3].text = I18n.t("Skill tree")
        titles[4].text = I18n.t("Filming and scoring")
        bind(report)
    }

    func bind(_ next: StageReport?) {
        report = next
        let has = next != nil
        empty.isHidden = has
        heroCard.isHidden = !has
        heroSpacer.isHidden = !has
        heroCard.arrangedSubviews.forEach {
            heroCard.removeArrangedSubview($0)
            $0.removeFromSuperview()
        }
        for i in 0..<5 {
            blocks[i].isHidden = !has
            chapters[i].arrangedSubviews.forEach {
                chapters[i].removeArrangedSubview($0)
                $0.removeFromSuperview()
            }
        }
        guard let next else { return }
        fillHero(next)
        fillCh1(next)
        fillCh2(next)
        fillCh3(next)
        fillCh4(next)
        fillCh5(next)
    }

    /// Scrolls the given scroll view so the Skill tree chapter (chapter 4, "Next steps"
    /// plan cards notwithstanding — the tree itself lives in chapter index 3) is visible.
    func scrollToSkillTreeChapter(in scrollView: UIScrollView, animated: Bool = true) {
        let frame = blocks[3].convert(blocks[3].bounds, to: scrollView)
        scrollView.scrollRectToVisible(frame, animated: animated)
    }

    /// "Level & next step" hero card — first thing in the scrollable report, ahead of
    /// Chapter 1 (Summary). Not sticky: it scrolls away with the rest of the content.
    private func fillHero(_ report: StageReport) {
        let inner = card()
        inner.addArrangedSubview(iconRow([(ReportTheme.medalColor(stageId: report.stageId), "trophy")], report.stageName))
        let pct = String(format: "%.0f", report.confidence * 100)
        inner.addArrangedSubview(meta(I18n.t("Confidence {pct:.0f}%", vars: ["pct": pct])))
        if let topName = report.nextLevelNames.first {
            let link = UIButton(type: .system)
            link.setTitle(I18n.t("Next up: {name}", vars: ["name": topName]), for: .normal)
            link.setTitleColor(Theme.link, for: .normal)
            link.titleLabel?.font = .systemFont(ofSize: 15)
            link.titleLabel?.numberOfLines = 0
            link.contentHorizontalAlignment = .left
            link.addAction(UIAction { [weak self] _ in self?.onJumpToSkillTree?() }, for: .touchUpInside)
            inner.addArrangedSubview(link)
        } else {
            let fallback = report.readyForNextStage
                ? I18n.t("Passed this level. Choose a next level on the skill tree.")
                : I18n.t("Not passed — train the lowest-scoring checkpoint.")
            inner.addArrangedSubview(meta(fallback))
        }
        heroCard.addArrangedSubview(wrapCard(inner))
    }

    private func fillCh1(_ report: StageReport) {
        let overview = card()
        overview.addArrangedSubview(iconRow([(ReportTheme.medalColor(stageId: report.stageId), "trophy")], report.stageName))
        if !report.stageFocus.isEmpty {
            overview.addArrangedSubview(meta(report.stageFocus))
        }
        chapters[0].addArrangedSubview(wrapCard(overview))

        let terrain = card()
        let gate = report.readyForNextStage
            ? I18n.t("Passed this level. Choose a next level on the skill tree.")
            : I18n.t("Not passed — train the lowest-scoring checkpoint.")
        let trail = report.terrainName.isEmpty ? I18n.t("—") : report.terrainName
        let line = "\(I18n.t("Suggested trail rating")): \(trail) · \(gate)"
        let diamonds = ReportTheme.terrainDiamondColors(report.terrainId).map { ($0, "diamond") }
        terrain.addArrangedSubview(iconRow(diamonds, line))
        if !report.terrainDesc.isEmpty {
            terrain.addArrangedSubview(meta(report.terrainDesc))
        }
        chapters[0].addArrangedSubview(wrapCard(terrain))

        addRingRow(
            chapters[0],
            [
                (report.score0100, I18n.t("Heuristic score (0-100, not FIS)"), ReportTheme.scorePurple(report.score0100)),
                (report.confidence * 100, I18n.t("Confidence"), ReportTheme.scorePurple(report.confidence * 100)),
            ]
        )

        if let posture = report.posture {
            let note = card()
            note.addArrangedSubview(meta(I18n.t(
                "Four posture scores are coach heuristics (0–100), not lab biomechanics; they are not true speed, meter turn radius, or peak ski pressure."
            )))
            chapters[0].addArrangedSubview(wrapCard(note))
            addRingRow(
                chapters[0],
                [
                    (posture.stability, I18n.t("Stability"), ReportTheme.scorePurple(posture.stability)),
                    (posture.coordination, I18n.t("Coordination"), ReportTheme.scorePurple(posture.coordination)),
                    (posture.control, I18n.t("Control"), ReportTheme.scorePurple(posture.control)),
                    (posture.balance, I18n.t("Balance"), ReportTheme.scorePurple(posture.balance)),
                ]
            )
        }

        let kps = ReportTheme.sortedKeypoints(report.keypoints)
        let perRow = kps.count >= 5 ? 3 : 2
        addRingRow(
            chapters[0],
            kps.map { ($0.score, $0.name.isEmpty ? $0.id : $0.name, ReportTheme.scorePurple($0.score)) },
            perRow: perRow
        )

        let timelineCard = card()
        timelineCard.addArrangedSubview(meta(I18n.t("Stability over time (time × frame score)")))
        let chart = ScoreTimelineView()
        chart.setPoints(report.scoreSeries)
        chart.onSeek = { [weak self] ms in self?.onSeek?(ms) }
        timelineCard.addArrangedSubview(chart)
        chapters[0].addArrangedSubview(wrapCard(timelineCard))
    }

    private func fillCh2(_ report: StageReport) {
        let kps = ReportTheme.sortedKeypoints(report.keypoints)
        let perRow = kps.count >= 5 ? 3 : 2
        var row: UIStackView?
        for (i, item) in kps.enumerated() {
            if i % perRow == 0 {
                row = equalHeightRow()
                chapters[1].addArrangedSubview(row!)
            }
            let inner = card()
            let ring = ScoreRingView()
            ring.setScore(item.score, label: item.name.isEmpty ? item.id : item.name, ringColor: ReportTheme.scorePurple(item.score))
            inner.addArrangedSubview(ring)
            inner.addArrangedSubview(advice(item.status == .pass ? item.good : item.bad))
            if let ms = item.evidenceMs {
                inner.addArrangedSubview(seekLink(ReportTheme.formatEvidenceMs(ms), Int(ms)))
            }
            row?.addArrangedSubview(wrapCard(inner))
        }
    }

    private func fillCh3(_ report: StageReport) {
        if report.readyForNextStage {
            let ready = card()
            ready.addArrangedSubview(advice(I18n.t("Passed this level. Choose a next level on the skill tree.")))
            chapters[2].addArrangedSubview(wrapCard(ready))
            let topId = report.nextLevelIds.first ?? ""
            let topName = report.nextLevelNames.first ?? ""
            func isRecommended(_ plan: LevelPlan) -> Bool {
                if !topId.isEmpty { return plan.levelId == topId }
                if !topName.isEmpty { return plan.levelName == topName }
                return false
            }
            // Recommended plan first; each element's flag is computed once
            // (a partition, not a pairwise comparator) to match the
            // key-based sort used on the other two platforms.
            let sortedPlans = report.nextPlans.filter(isRecommended) + report.nextPlans.filter { !isRecommended($0) }
            for plan in sortedPlans {
                chapters[2].addArrangedSubview(wrapCard(planCard(plan, recommended: isRecommended(plan)), accent: isRecommended(plan)))
            }
            return
        }
        let summary = card()
        var lines: [String] = [I18n.t("Not passed — train the lowest-scoring checkpoint.")]
        let weak = report.keypoints.first { $0.id == report.weakestCheckpointId }
        if let weak {
            lines.append("\(I18n.t("Weakest checkpoint")): \(weak.name)")
            lines.append(weak.bad)
        }
        addLines(summary, lines, paper: true)
        chapters[2].addArrangedSubview(wrapCard(summary))
        if let ms = weak?.evidenceMs {
            let linkCard = card()
            linkCard.addArrangedSubview(seekLink("\(I18n.t("Problem frame")) \(ReportTheme.formatEvidenceMs(ms))", Int(ms)))
            chapters[2].addArrangedSubview(wrapCard(linkCard))
        }
        if let weak {
            chapters[2].addArrangedSubview(wrapCard(drillsCard(weak.drills, weak.name)))
        }
        let failItems = ReportTheme.sortedKeypoints(report.keypoints).filter {
            $0.status == .fail && (weak == nil || $0.id != weak?.id)
        }
        for item in failItems {
            chapters[2].addArrangedSubview(wrapCard(drillsCard(item.drills, item.name)))
        }
    }

    private func fillCh4(_ report: StageReport) {
        let inner = card()
        let tree = SkillTreeView()
        tree.setRoute(report.treePath)
        inner.addArrangedSubview(tree)
        if report.readyForNextStage, !report.nextLevelNames.isEmpty {
            let perRow = 2
            let names = report.nextLevelNames
            for start in stride(from: 0, to: names.count, by: perRow) {
                let row = UIStackView()
                row.axis = .horizontal
                row.alignment = .leading
                row.spacing = 8
                for i in start..<min(start + perRow, names.count) {
                    let recommended = i == 0
                    let text = recommended
                        ? I18n.t("Recommended next: {name}", vars: ["name": names[i]])
                        : names[i]
                    row.addArrangedSubview(chip(text, accent: recommended))
                }
                let spacer = UIView()
                spacer.setContentHuggingPriority(.defaultLow, for: .horizontal)
                row.addArrangedSubview(spacer)
                inner.addArrangedSubview(row)
            }
        }
        chapters[3].addArrangedSubview(wrapCard(inner))
    }

    private func fillCh5(_ report: StageReport) {
        var lines: [String] = [report.disclaimer]
        if report.heuristicNotFisCarve {
            lines.append(I18n.t("Carve points are heuristics, not FIS carving scores."))
        }
        for step in report.filmSteps {
            lines.append("• \(step)")
        }
        let inner = card()
        addLines(inner, lines, paper: false)
        chapters[4].addArrangedSubview(wrapCard(inner))
    }

    private func planCard(_ plan: LevelPlan, recommended: Bool) -> UIStackView {
        let inner = card()
        if recommended {
            inner.addArrangedSubview(chip(I18n.t("Recommended next"), accent: true))
        }
        if !plan.levelName.isEmpty {
            inner.addArrangedSubview(iconRow([(ReportTheme.medalColor(stageId: plan.levelId), "trophy")], plan.levelName))
        }
        addLines(inner, drillLines(plan.drills, plan.venues), paper: true)
        return inner
    }

    private func drillsCard(_ drills: [DrillPayload], _ title: String) -> UIStackView {
        let inner = card()
        var lines: [String] = []
        if !title.isEmpty { lines.append(title) }
        lines.append(contentsOf: drillLines(drills, []))
        addLines(inner, lines, paper: true)
        return inner
    }

    private func drillLines(_ drills: [DrillPayload], _ venues: [VenuePayload]) -> [String] {
        var lines: [String] = []
        for drill in drills {
            lines.append("\(I18n.t("Drills")): \(drill.title.isEmpty ? drill.name : drill.title)")
            if !drill.desc.isEmpty { lines.append(drill.desc) }
            let steps = drill.training.isEmpty ? drill.steps : drill.training
            for step in steps { lines.append("• \(step)") }
            for venue in drill.venues {
                lines.append("\(I18n.t("Training venue")): \(venue.name)")
                if !venue.tips.isEmpty { lines.append(venue.tips) }
            }
        }
        for venue in venues {
            lines.append("\(I18n.t("Training venue")): \(venue.name)")
            if !venue.desc.isEmpty { lines.append(venue.desc) }
            if !venue.tips.isEmpty { lines.append(venue.tips) }
        }
        return lines
    }

    private func addRingRow(_ parent: UIStackView, _ items: [(Double?, String, UIColor)], perRow: Int = 2) {
        var row: UIStackView?
        for (i, item) in items.enumerated() {
            if i % perRow == 0 {
                row = equalHeightRow()
                parent.addArrangedSubview(row!)
            }
            let inner = card()
            let ring = ScoreRingView()
            ring.setScore(item.0, label: item.1, ringColor: item.2)
            inner.addArrangedSubview(ring)
            row?.addArrangedSubview(wrapCard(inner))
        }
    }

    private func addLines(_ parent: UIStackView, _ lines: [String], paper: Bool) {
        for line in lines where !line.trimmingCharacters(in: .whitespaces).isEmpty {
            parent.addArrangedSubview(paper ? advice(line) : meta(line))
        }
    }

    private func card() -> UIStackView {
        let stack = UIStackView()
        stack.axis = .vertical
        stack.spacing = Theme.spaceText
        stack.isLayoutMarginsRelativeArrangement = true
        stack.layoutMargins = UIEdgeInsets(
            top: Theme.pageInset, left: Theme.pageInset, bottom: Theme.pageInset, right: Theme.pageInset
        )
        return stack
    }

    private func wrapCard(_ inner: UIView, accent: Bool = false) -> UIStackView {
        let shell = UIStackView()
        shell.axis = .vertical
        shell.alignment = .fill
        shell.backgroundColor = accent ? Theme.deepPurple.withAlphaComponent(0.35) : Theme.card
        shell.layer.cornerRadius = Theme.cardRadius
        if accent {
            shell.layer.borderWidth = 1
            shell.layer.borderColor = Theme.currentTree.cgColor
        }
        shell.clipsToBounds = true
        shell.addArrangedSubview(inner)
        let spacer = UIView()
        spacer.setContentHuggingPriority(.defaultLow, for: .vertical)
        spacer.setContentCompressionResistancePriority(.defaultLow, for: .vertical)
        shell.addArrangedSubview(spacer)
        return shell
    }

    /// A small pill-shaped label used for next-step chips (gate/accent style for the
    /// top-priority "Recommended next" entry, neutral for the rest).
    private func chip(_ text: String, accent: Bool) -> UIView {
        let wrap = UIStackView()
        wrap.axis = .vertical
        wrap.isLayoutMarginsRelativeArrangement = true
        wrap.layoutMargins = UIEdgeInsets(top: 6, left: 10, bottom: 6, right: 10)
        wrap.backgroundColor = accent ? Theme.currentTree : Theme.ringTrack
        wrap.layer.cornerRadius = 14
        wrap.clipsToBounds = true
        wrap.setContentHuggingPriority(.required, for: .horizontal)
        let label = UILabel()
        label.text = text
        label.textColor = accent ? Theme.deepPurple : Theme.paper
        label.font = accent ? .boldSystemFont(ofSize: 13) : .systemFont(ofSize: 13)
        label.numberOfLines = 0
        wrap.addArrangedSubview(label)
        return wrap
    }

    private func equalHeightRow() -> UIStackView {
        let row = UIStackView()
        row.axis = .horizontal
        row.alignment = .fill
        row.distribution = .fillEqually
        row.spacing = Theme.spacePanel
        return row
    }

    private func iconRow(_ icons: [(UIColor, String)], _ text: String) -> UIStackView {
        let row = UIStackView()
        row.axis = .horizontal
        row.alignment = .center
        row.spacing = 8
        for (color, kind) in icons {
            let icon = TrophyIconView(diamond: kind == "diamond", tint: color)
            icon.translatesAutoresizingMaskIntoConstraints = false
            NSLayoutConstraint.activate([
                icon.widthAnchor.constraint(equalToConstant: 22),
                icon.heightAnchor.constraint(equalToConstant: 22),
            ])
            row.addArrangedSubview(icon)
        }
        let label = UILabel()
        label.text = text
        label.textColor = Theme.paper
        label.font = .systemFont(ofSize: 16)
        label.numberOfLines = 0
        row.addArrangedSubview(label)
        return row
    }

    private func meta(_ text: String) -> UILabel {
        let label = UILabel()
        label.text = text
        label.textColor = Theme.title
        label.font = .systemFont(ofSize: 14)
        label.numberOfLines = 0
        return label
    }

    private func advice(_ text: String) -> UILabel {
        let label = UILabel()
        label.text = text
        label.textColor = Theme.paper
        label.font = .systemFont(ofSize: 15)
        label.numberOfLines = 0
        return label
    }

    private func seekLink(_ label: String, _ tMs: Int) -> UIButton {
        let button = UIButton(type: .system)
        button.setTitle(label, for: .normal)
        button.setTitleColor(Theme.link, for: .normal)
        button.titleLabel?.font = .systemFont(ofSize: 15)
        button.titleLabel?.numberOfLines = 0
        button.contentHorizontalAlignment = .left
        button.addAction(UIAction { [weak self] _ in self?.onSeek?(tMs) }, for: .touchUpInside)
        return button
    }
}

final class TrophyIconView: UIView {
    private let diamond: Bool
    private let tint: UIColor

    init(diamond: Bool, tint: UIColor) {
        self.diamond = diamond
        self.tint = tint
        super.init(frame: .zero)
        backgroundColor = .clear
        isOpaque = false
    }

    required init?(coder: NSCoder) {
        fatalError("init(coder:)")
    }

    override func draw(_ rect: CGRect) {
        let path = UIBezierPath()
        let w = bounds.width
        let h = bounds.height
        let outline = diamond && tint.argb == Theme.terrainBlack.argb
        let stroke: CGFloat = outline ? 1 : 0
        let pad = stroke / 2 + 1
        if diamond {
            path.move(to: CGPoint(x: w / 2, y: pad))
            path.addLine(to: CGPoint(x: w - pad, y: h / 2))
            path.addLine(to: CGPoint(x: w / 2, y: h - pad))
            path.addLine(to: CGPoint(x: pad, y: h / 2))
            path.close()
        } else {
            path.move(to: CGPoint(x: w * 0.25, y: h * 0.15))
            path.addLine(to: CGPoint(x: w * 0.75, y: h * 0.15))
            path.addLine(to: CGPoint(x: w * 0.68, y: h * 0.45))
            path.addLine(to: CGPoint(x: w * 0.55, y: h * 0.45))
            path.addLine(to: CGPoint(x: w * 0.55, y: h * 0.72))
            path.addLine(to: CGPoint(x: w * 0.72, y: h * 0.85))
            path.addLine(to: CGPoint(x: w * 0.28, y: h * 0.85))
            path.addLine(to: CGPoint(x: w * 0.45, y: h * 0.72))
            path.addLine(to: CGPoint(x: w * 0.45, y: h * 0.45))
            path.addLine(to: CGPoint(x: w * 0.32, y: h * 0.45))
            path.close()
        }
        tint.setFill()
        path.fill()
        if outline {
            UIColor.white.setStroke()
            path.lineWidth = stroke
            path.stroke()
        }
    }
}
