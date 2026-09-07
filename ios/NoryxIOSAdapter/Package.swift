// swift-tools-version: 5.9
import PackageDescription

let package = Package(
    name: "NoryxIOSAdapter",
    platforms: [.iOS(.v16)],
    products: [
        .library(name: "NoryxIOSAdapter", targets: ["NoryxIOSAdapter"])
    ],
    targets: [
        .target(name: "NoryxIOSAdapter"),
        .testTarget(name: "NoryxIOSAdapterTests", dependencies: ["NoryxIOSAdapter"])
    ]
)
