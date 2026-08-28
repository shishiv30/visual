import UIKit

enum Icons {
    static func image(_ name: String, color: UIColor = Theme.paper, pointSize: CGFloat = 24) -> UIImage {
        let fill: UIColor
        if name == "record" {
            fill = UIColor(rgb: 0xC62828)
        } else {
            fill = color
        }
        let d = paths[name] ?? ""
        let bezier = SvgPath.parse(d)
        let renderer = UIGraphicsImageRenderer(size: CGSize(width: pointSize, height: pointSize))
        return renderer.image { _ in
            fill.setFill()
            let scale = pointSize / 24
            let transform = CGAffineTransform(scaleX: scale, y: scale)
            let scaled = bezier.copy() as! UIBezierPath
            scaled.apply(transform)
            scaled.fill()
        }
    }

    static let paths: [String: String] = [
        "play": "M8 5.5v13l11-6.5L8 5.5z",
        "pause": "M7 5h3.5v14H7V5zm6.5 0H17v14h-3.5V5z",
        "thumb_up":
            "M1 21h4V9H1v12zm22-11c0-1.1-.9-2-2-2h-6.31l.95-4.57.03-.32c0-.41-.17-.79-.44-1.06L14.17 1 7.59 7.59C7.22 7.95 7 8.45 7 9v10c0 1.1.9 2 2 2h9c.83 0 1.54-.5 1.84-1.22l3.02-7.05c.09-.23.14-.47.14-.73v-2z",
        "thumb_down":
            "M15 3H6c-.83 0-1.54.5-1.84 1.22l-3.02 7.05c-.09.23-.14.47-.14.73v2c0 1.1.9 2 2 2h6.31l-.95 4.57-.03.32c0 .41.17.79.44 1.06L9.83 23l6.59-6.59c.36-.36.58-.86.58-1.41V5c0-1.1-.9-2-2-2zm4 0v12h4V3h-4z",
        "reanalyze": "M17.65 6.35A7.95 7.95 0 0 0 12 4V1L7 6l5 5V7a6 6 0 1 1-6 6H4a8 8 0 1 0 13.65-6.65z",
        "download": "M11 4h2v9.2l3.2-3.2 1.4 1.4L12 16.8 6.4 11.2l1.4-1.4L11 13.2V4zM5 18h14v2H5v-2z",
        "share": "M14 4h6v6h-2V7.4l-7.3 7.3-1.4-1.4L16.6 6H14V4zM6 6h6v2H8v10h10v-4h2v6H6V6z",
        "back": "M14.7 5.3 8 12l6.7 6.7 1.4-1.4L10.8 12l5.3-5.3-1.4-1.4z",
        "camera":
            "M9 4h6l1.5 2H20a2 2 0 0 1 2 2v11a2 2 0 0 1-2 2H4a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h3.5L9 4zm3 14a4.5 4.5 0 1 0 0-9 4.5 4.5 0 0 0 0 9zm0-2.2a2.3 2.3 0 1 1 0-4.6 2.3 2.3 0 0 1 0 4.6z",
        "import": "M11 3h2v10.2l3.2-3.2 1.4 1.4L12 17.2 6.4 11.4l1.4-1.4L11 13.2V3zM4 19h16v2H4v-2z",
        "delete": "M9 3h6l1 2h5v2H3V5h5l1-2zm1 6h2v9h-2V9zm4 0h2v9h-2V9zM7 9h2v9H7V9zm-1 12h12l1-12H5l1 12z",
        "report":
            "M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8l-6-6zm1 7V3.5L19.5 9H15zM8 13h2v5H8v-5zm3-2h2v7h-2v-7zm3 4h2v3h-2v-3z",
        "record": "M12 5a7 7 0 1 1 0 14 7 7 0 0 1 0-14z",
        "stop": "M6 6h12v12H6z",
        "ok": "M9.2 16.2 5.4 12.4l-1.4 1.4 5.2 5.2 11-11-1.4-1.4-9.6 9.6z",
    ]
}

enum PoseButtons {
    static func accent(icon: String, background: UIColor = Theme.deepPurple, height: CGFloat = Theme.controlHeight) -> UIButton {
        let button = UIButton(type: .system)
        button.backgroundColor = background
        button.layer.cornerRadius = 4
        button.tintColor = .white
        button.setImage(Icons.image(icon, color: .white), for: .normal)
        button.imageView?.contentMode = .scaleAspectFit
        button.contentEdgeInsets = UIEdgeInsets(top: 4, left: 8, bottom: 4, right: 8)
        button.heightAnchor.constraint(greaterThanOrEqualToConstant: height).isActive = true
        button.widthAnchor.constraint(greaterThanOrEqualToConstant: height).isActive = true
        return button
    }

    static func chrome(icon: String) -> UIButton {
        let button = UIButton(type: .system)
        button.backgroundColor = .clear
        button.tintColor = Theme.paper
        button.setImage(Icons.image(icon, color: Theme.paper), for: .normal)
        button.imageView?.contentMode = .scaleAspectFit
        button.contentEdgeInsets = UIEdgeInsets(top: 8, left: 8, bottom: 8, right: 8)
        button.heightAnchor.constraint(greaterThanOrEqualToConstant: 44).isActive = true
        button.widthAnchor.constraint(greaterThanOrEqualToConstant: 44).isActive = true
        return button
    }

    static func fieldBackground() -> UIView {
        let view = UIView()
        view.backgroundColor = UIColor(rgb: 0x2A2A2A)
        view.layer.cornerRadius = 8
        view.layer.borderWidth = 1
        view.layer.borderColor = UIColor(rgb: 0x3D3D3D).cgColor
        return view
    }
}

enum SvgPath {
    static func parse(_ data: String) -> UIBezierPath {
        let path = UIBezierPath()
        let tokens = tokenize(data)
        var i = 0
        var cx: CGFloat = 0
        var cy: CGFloat = 0
        var startX: CGFloat = 0
        var startY: CGFloat = 0
        var lastCmd: Character = " "
        var lastCtrl = CGPoint.zero
        var hasLastCtrl = false
        while i < tokens.count {
            var cmd: Character
            if let first = tokens[i].first, first.isLetter {
                cmd = first
                i += 1
            } else if lastCmd != " " {
                cmd = lastCmd == "M" ? "L" : lastCmd == "m" ? "l" : lastCmd
            } else {
                break
            }
            lastCmd = cmd
            let rel = cmd.isLowercase
            switch cmd.lowercased() {
            case "m":
                let p = readPoint(&i, tokens, cx, cy, rel)
                path.move(to: p)
                cx = p.x
                cy = p.y
                startX = cx
                startY = cy
                lastCmd = rel ? "l" : "L"
                hasLastCtrl = false
            case "l":
                let p = readPoint(&i, tokens, cx, cy, rel)
                path.addLine(to: p)
                cx = p.x
                cy = p.y
                hasLastCtrl = false
            case "h":
                let v = readNum(&i, tokens)
                cx = rel ? cx + v : v
                path.addLine(to: CGPoint(x: cx, y: cy))
                hasLastCtrl = false
            case "v":
                let v = readNum(&i, tokens)
                cy = rel ? cy + v : v
                path.addLine(to: CGPoint(x: cx, y: cy))
                hasLastCtrl = false
            case "c":
                let c1 = readPoint(&i, tokens, cx, cy, rel)
                let c2 = readPoint(&i, tokens, cx, cy, rel)
                let p = readPoint(&i, tokens, cx, cy, rel)
                path.addCurve(to: p, controlPoint1: c1, controlPoint2: c2)
                lastCtrl = c2
                hasLastCtrl = true
                cx = p.x
                cy = p.y
            case "s":
                let c1: CGPoint
                if hasLastCtrl, lastCmd.lowercased() == "c" || lastCmd.lowercased() == "s" {
                    c1 = CGPoint(x: 2 * cx - lastCtrl.x, y: 2 * cy - lastCtrl.y)
                } else {
                    c1 = CGPoint(x: cx, y: cy)
                }
                let c2 = readPoint(&i, tokens, cx, cy, rel)
                let p = readPoint(&i, tokens, cx, cy, rel)
                path.addCurve(to: p, controlPoint1: c1, controlPoint2: c2)
                lastCtrl = c2
                hasLastCtrl = true
                cx = p.x
                cy = p.y
            case "q":
                let c1 = readPoint(&i, tokens, cx, cy, rel)
                let p = readPoint(&i, tokens, cx, cy, rel)
                path.addQuadCurve(to: p, controlPoint: c1)
                lastCtrl = c1
                hasLastCtrl = true
                cx = p.x
                cy = p.y
            case "t":
                let c1: CGPoint
                if hasLastCtrl, lastCmd.lowercased() == "q" || lastCmd.lowercased() == "t" {
                    c1 = CGPoint(x: 2 * cx - lastCtrl.x, y: 2 * cy - lastCtrl.y)
                } else {
                    c1 = CGPoint(x: cx, y: cy)
                }
                let p = readPoint(&i, tokens, cx, cy, rel)
                path.addQuadCurve(to: p, controlPoint: c1)
                lastCtrl = c1
                hasLastCtrl = true
                cx = p.x
                cy = p.y
            case "a":
                let rx = readNum(&i, tokens)
                let ry = readNum(&i, tokens)
                let rot = readNum(&i, tokens)
                let large = readNum(&i, tokens) != 0
                let sweep = readNum(&i, tokens) != 0
                let p = readPoint(&i, tokens, cx, cy, rel)
                addArc(path, from: CGPoint(x: cx, y: cy), rx: rx, ry: ry, xRot: rot, large: large, sweep: sweep, to: p)
                cx = p.x
                cy = p.y
                hasLastCtrl = false
            case "z":
                path.close()
                cx = startX
                cy = startY
                hasLastCtrl = false
            default:
                break
            }
        }
        return path
    }

    private static func tokenize(_ data: String) -> [String] {
        var out: [String] = []
        var cur = ""
        for ch in data {
            if ch.isLetter {
                if !cur.isEmpty {
                    out.append(cur)
                    cur = ""
                }
                out.append(String(ch))
            } else if ch == "," || ch.isWhitespace {
                if !cur.isEmpty {
                    out.append(cur)
                    cur = ""
                }
            } else if ch == "-" || ch == "+" {
                if !cur.isEmpty, cur.last != "e", cur.last != "E" {
                    out.append(cur)
                    cur = String(ch)
                } else {
                    cur.append(ch)
                }
            } else if ch == ".", cur.contains(".") {
                out.append(cur)
                cur = String(ch)
            } else {
                cur.append(ch)
            }
        }
        if !cur.isEmpty {
            out.append(cur)
        }
        return out
    }

    private static func readNum(_ i: inout Int, _ tokens: [String]) -> CGFloat {
        guard i < tokens.count else { return 0 }
        let v = CGFloat(Double(tokens[i]) ?? 0)
        i += 1
        return v
    }

    private static func readPoint(_ i: inout Int, _ tokens: [String], _ cx: CGFloat, _ cy: CGFloat, _ rel: Bool) -> CGPoint {
        let x = readNum(&i, tokens)
        let y = readNum(&i, tokens)
        return rel ? CGPoint(x: cx + x, y: cy + y) : CGPoint(x: x, y: y)
    }

    private static func addArc(
        _ path: UIBezierPath,
        from: CGPoint,
        rx rawRx: CGFloat,
        ry rawRy: CGFloat,
        xRot: CGFloat,
        large: Bool,
        sweep: Bool,
        to: CGPoint
    ) {
        var rx = abs(rawRx)
        var ry = abs(rawRy)
        if rx == 0 || ry == 0 {
            path.addLine(to: to)
            return
        }
        let phi = xRot * .pi / 180
        let cosPhi = cos(phi)
        let sinPhi = sin(phi)
        let dx = (from.x - to.x) / 2
        let dy = (from.y - to.y) / 2
        let x1p = cosPhi * dx + sinPhi * dy
        let y1p = -sinPhi * dx + cosPhi * dy
        var lam = (x1p * x1p) / (rx * rx) + (y1p * y1p) / (ry * ry)
        if lam > 1 {
            let s = sqrt(lam)
            rx *= s
            ry *= s
            lam = 1
        }
        let sign: CGFloat = (large == sweep) ? -1 : 1
        let num = max(0, rx * rx * ry * ry - rx * rx * y1p * y1p - ry * ry * x1p * x1p)
        let den = rx * rx * y1p * y1p + ry * ry * x1p * x1p
        let coef = den == 0 ? 0 : sign * sqrt(num / den)
        let cxp = coef * (rx * y1p) / ry
        let cyp = coef * -(ry * x1p) / rx
        let cxc = cosPhi * cxp - sinPhi * cyp + (from.x + to.x) / 2
        let cyc = sinPhi * cxp + cosPhi * cyp + (from.y + to.y) / 2
        func angle(_ ux: CGFloat, _ uy: CGFloat, _ vx: CGFloat, _ vy: CGFloat) -> CGFloat {
            let dot = ux * vx + uy * vy
            let mag = sqrt(max(0, (ux * ux + uy * uy) * (vx * vx + vy * vy)))
            var ang = mag == 0 ? 0 : acos(max(-1, min(1, dot / mag)))
            if ux * vy - uy * vx < 0 {
                ang = -ang
            }
            return ang
        }
        let start = angle(1, 0, (x1p - cxp) / rx, (y1p - cyp) / ry)
        var delta = angle((x1p - cxp) / rx, (y1p - cyp) / ry, (-x1p - cxp) / rx, (-y1p - cyp) / ry)
        if !sweep, delta > 0 {
            delta -= 2 * .pi
        } else if sweep, delta < 0 {
            delta += 2 * .pi
        }
        let segs = Int(ceil(abs(delta) / (.pi / 2)))
        let step = delta / CGFloat(max(1, segs))
        for s in 0..<max(1, segs) {
            let a1 = start + step * CGFloat(s)
            let a2 = a1 + step
            let alpha = (4.0 / 3.0) * tan((a2 - a1) / 4)
            func pt(_ a: CGFloat) -> CGPoint {
                let x = rx * cos(a)
                let y = ry * sin(a)
                return CGPoint(
                    x: cosPhi * x - sinPhi * y + cxc,
                    y: sinPhi * x + cosPhi * y + cyc
                )
            }
            func dpt(_ a: CGFloat) -> CGPoint {
                let x = -rx * sin(a)
                let y = ry * cos(a)
                return CGPoint(x: cosPhi * x - sinPhi * y, y: sinPhi * x + cosPhi * y)
            }
            let p1 = pt(a1)
            let p2 = pt(a2)
            let d1 = dpt(a1)
            let d2 = dpt(a2)
            path.addCurve(
                to: p2,
                controlPoint1: CGPoint(x: p1.x + alpha * d1.x, y: p1.y + alpha * d1.y),
                controlPoint2: CGPoint(x: p2.x - alpha * d2.x, y: p2.y - alpha * d2.y)
            )
        }
    }
}

extension UIViewController {
    func poseAlert(titleKey: String, messageKey: String, ok: (() -> Void)? = nil) {
        let alert = UIAlertController(
            title: I18n.t(titleKey),
            message: I18n.t(messageKey),
            preferredStyle: .alert
        )
        alert.addAction(UIAlertAction(title: I18n.t("OK"), style: .default) { _ in ok?() })
        present(alert, animated: true)
    }
}
