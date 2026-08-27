import UIKit

final class PlayerStageView: UIView {
    var onTap: (() -> Void)?
    private var srcW = 16
    private var srcH = 9
    private var heightConstraint: NSLayoutConstraint?

    override init(frame: CGRect) {
        super.init(frame: frame)
        backgroundColor = .black
        clipsToBounds = true
        let tap = UITapGestureRecognizer(target: self, action: #selector(tapped))
        tap.cancelsTouchesInView = false
        addGestureRecognizer(tap)
    }

    required init?(coder: NSCoder) {
        super.init(coder: coder)
        backgroundColor = .black
        clipsToBounds = true
    }

    func setAspect(width: Int, height: Int) {
        let nextW = max(1, width)
        let nextH = max(1, height)
        if nextW == srcW && nextH == srcH {
            return
        }
        srcW = nextW
        srcH = nextH
        updateHeight()
        invalidateIntrinsicContentSize()
        setNeedsLayout()
        superview?.setNeedsLayout()
    }

    override func didMoveToSuperview() {
        super.didMoveToSuperview()
        if heightConstraint == nil {
            let c = heightAnchor.constraint(equalToConstant: stagedHeight(for: bounds.width))
            c.priority = .required
            c.isActive = true
            heightConstraint = c
        }
    }

    override var intrinsicContentSize: CGSize {
        let width = bounds.width > 0 ? bounds.width : UIScreen.main.bounds.width - Theme.pageInset * 2
        return CGSize(width: UIView.noIntrinsicMetric, height: stagedHeight(for: width))
    }

    override func layoutSubviews() {
        super.layoutSubviews()
        updateHeight()
    }

    private func updateHeight() {
        let width = bounds.width > 1 ? bounds.width : UIScreen.main.bounds.width - Theme.pageInset * 2
        let h = stagedHeight(for: width)
        if heightConstraint?.constant != h {
            heightConstraint?.constant = h
        }
    }

    private func stagedHeight(for width: CGFloat) -> CGFloat {
        let maxH: CGFloat = 360
        let minH: CGFloat = 160
        let aspect = CGFloat(srcH) / CGFloat(srcW)
        return min(maxH, max(minH, width * aspect))
    }

    @objc private func tapped() {
        onTap?()
    }
}
