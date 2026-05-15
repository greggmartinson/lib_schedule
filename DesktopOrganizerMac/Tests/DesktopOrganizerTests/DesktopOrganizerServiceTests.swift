import Foundation
import XCTest
@testable import DesktopOrganizer

final class DesktopOrganizerServiceTests: XCTestCase {
    func testPreviewRoutesFilesByRule() throws {
        let workspace = try TestWorkspace()
        defer { workspace.cleanup() }

        try workspace.createDesktopFile(
            named: "Family.jpg",
            createdAt: workspace.now.addingTimeInterval(-600)
        )
        try workspace.createDesktopFile(
            named: "Movie Trailer.mov",
            createdAt: workspace.now.addingTimeInterval(-600)
        )
        try workspace.createDesktopFile(
            named: "Meeting Notes.docx",
            createdAt: workspace.now.addingTimeInterval(-600)
        )
        try workspace.createDesktopFile(
            named: "Screenshot 2026-05-10 at 8.12.00 AM.png",
            createdAt: workspace.now.addingTimeInterval(-172_800)
        )
        try workspace.createDesktopFile(
            named: "Screenshot 2026-05-14 at 8.12.00 AM.png",
            createdAt: workspace.now.addingTimeInterval(-3_600)
        )

        let service = workspace.makeService()
        let actions = try service.previewActions()

        XCTAssertEqual(actions.count, 4)
        XCTAssertEqual(destination(for: "Family.jpg", in: actions), .pictures)
        XCTAssertEqual(destination(for: "Movie Trailer.mov", in: actions), .movies)
        XCTAssertEqual(destination(for: "Meeting Notes.docx", in: actions), .documents)
        XCTAssertEqual(destination(for: "Screenshot 2026-05-10 at 8.12.00 AM.png", in: actions), .trash)
        XCTAssertNil(destination(for: "Screenshot 2026-05-14 at 8.12.00 AM.png", in: actions))
    }

    func testPreviewAvoidsDestinationNameCollisions() throws {
        let workspace = try TestWorkspace()
        defer { workspace.cleanup() }

        try workspace.createDesktopFile(
            named: "Meeting Notes.docx",
            createdAt: workspace.now.addingTimeInterval(-600)
        )
        try workspace.createFile(at: workspace.configuration.documentsURL.appendingPathComponent("Meeting Notes.docx"))

        let service = workspace.makeService()
        let action = try XCTUnwrap(try service.previewActions().first)

        XCTAssertEqual(action.destination, .documents)
        XCTAssertEqual(action.destinationURL?.lastPathComponent, "Meeting Notes 2.docx")
    }

    private func destination(for filename: String, in actions: [OrganizerAction]) -> OrganizerDestination? {
        actions.first { $0.sourceURL.lastPathComponent == filename }?.destination
    }
}

private struct TestWorkspace {
    let rootURL: URL
    let configuration: OrganizerConfiguration
    let now: Date

    private let fileManager = FileManager.default

    init() throws {
        now = Date(timeIntervalSince1970: 1_715_668_800)
        rootURL = fileManager.temporaryDirectory.appendingPathComponent(UUID().uuidString, isDirectory: true)

        let desktopURL = rootURL.appendingPathComponent("Desktop", isDirectory: true)
        let moviesURL = rootURL.appendingPathComponent("Movies", isDirectory: true)
        let picturesURL = rootURL.appendingPathComponent("Pictures", isDirectory: true)
        let documentsURL = rootURL.appendingPathComponent("Documents", isDirectory: true)

        for directory in [desktopURL, moviesURL, picturesURL, documentsURL] {
            try fileManager.createDirectory(at: directory, withIntermediateDirectories: true, attributes: nil)
        }

        configuration = OrganizerConfiguration(
            desktopURL: desktopURL,
            moviesURL: moviesURL,
            picturesURL: picturesURL,
            documentsURL: documentsURL
        )
    }

    func makeService() -> DesktopOrganizerService {
        DesktopOrganizerService(
            fileManager: fileManager,
            configuration: configuration,
            now: { now }
        )
    }

    func createDesktopFile(named name: String, createdAt: Date) throws {
        let fileURL = configuration.desktopURL.appendingPathComponent(name)
        try createFile(at: fileURL)

        try fileManager.setAttributes(
            [
                .creationDate: createdAt,
                .modificationDate: createdAt
            ],
            ofItemAtPath: fileURL.path
        )
    }

    func createFile(at url: URL) throws {
        try fileManager.createDirectory(
            at: url.deletingLastPathComponent(),
            withIntermediateDirectories: true,
            attributes: nil
        )

        try Data("sample".utf8).write(to: url)
    }

    func cleanup() {
        try? fileManager.removeItem(at: rootURL)
    }
}
