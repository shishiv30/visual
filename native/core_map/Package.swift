// swift-tools-version: 5.9
import PackageDescription

let package = Package(
    name: "CoreMap",
    platforms: [.iOS(.v16)],
    products: [.library(name: "CoreMap", targets: ["CoreMap"])],
    targets: [
        .target(
            name: "CoreMap",
            path: ".",
            sources: ["core_map.c"],
            publicHeadersPath: ".",
            cSettings: [.headerSearchPath(".")],
        ),
    ]
)
