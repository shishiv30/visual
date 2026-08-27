import UIKit

final class FloatingBackButton: UIButton {
    var onTap: (() -> Void)?

    override init(frame: CGRect) {
        super.init(frame: frame)
        backgroundColor = UIColor(rgb: 0x1E1E1E, alpha: 0xE0 / 255)
        layer.cornerRadius = 8
        layer.borderWidth = 1
        layer.borderColor = UIColor(rgb: 0x3D3D3D).cgColor
        setImage(Icons.image("back", color: .white), for: .normal)
        imageView?.contentMode = .scaleAspectFit
        addTarget(self, action: #selector(tapped), for: .touchUpInside)
        accessibilityLabel = I18n.t("Back")
    }

    required init?(coder: NSCoder) {
        super.init(coder: coder)
    }

    func attach(to host: UIView) {
        host.addSubview(self)
        translatesAutoresizingMaskIntoConstraints = false
        NSLayoutConstraint.activate([
            widthAnchor.constraint(equalToConstant: Theme.floatingBack),
            heightAnchor.constraint(equalToConstant: Theme.floatingBack),
            leadingAnchor.constraint(equalTo: host.safeAreaLayoutGuide.leadingAnchor, constant: Theme.pageInset),
            topAnchor.constraint(equalTo: host.safeAreaLayoutGuide.topAnchor, constant: Theme.pageInset),
        ])
        host.bringSubviewToFront(self)
    }

    func retranslate() {
        accessibilityLabel = I18n.t("Back")
        setImage(Icons.image("back", color: .white), for: .normal)
    }

    @objc private func tapped() {
        onTap?()
    }
}
