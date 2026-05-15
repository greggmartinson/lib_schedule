// swift-tools-version: 5.10
import PackageDescription

let package = Package(
    name: "DesktopOrganizerMac",
    platforms: [
        .macOS(.v14)
    ],
    products: [
        .executable(
            name: "DesktopOrganizer",
            targets: ["DesktopOrganizer"]
        )
    ],
    targets: [
        .executableTarget(
            name: "DesktopOrganizer"
        ),
        .testTarget(
            name: "DesktopOrganizerTests",
            dependencies: ["DesktopOrganizer"]
        )
    ]
)
