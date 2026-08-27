import UIKit

@main
final class AppDelegate: UIResponder, UIApplicationDelegate {
    var window: UIWindow?

    func application(
        _ application: UIApplication,
        didFinishLaunchingWithOptions launchOptions: [UIApplication.LaunchOptionsKey: Any]? = nil
    ) -> Bool {
        if let url = Bundle.main.url(forResource: "strings", withExtension: "json"),
           let json = try? String(contentsOf: url, encoding: .utf8) {
            I18n.initCatalog(json: json, storedLang: nil)
        }
        let window = UIWindow(frame: UIScreen.main.bounds)
        window.backgroundColor = Theme.surface
        window.rootViewController = RootViewController()
        window.makeKeyAndVisible()
        self.window = window
        return true
    }
}
