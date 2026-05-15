import Foundation
import UniformTypeIdentifiers

struct OrganizerConfiguration {
    let desktopURL: URL
    let moviesURL: URL
    let picturesURL: URL
    let documentsURL: URL

    static var live: OrganizerConfiguration {
        let fileManager = FileManager.default

        return OrganizerConfiguration(
            desktopURL: fileManager.urls(for: .desktopDirectory, in: .userDomainMask).first
                ?? fileManager.homeDirectoryForCurrentUser.appendingPathComponent("Desktop", isDirectory: true),
            moviesURL: fileManager.urls(for: .moviesDirectory, in: .userDomainMask).first
                ?? fileManager.homeDirectoryForCurrentUser.appendingPathComponent("Movies", isDirectory: true),
            picturesURL: fileManager.urls(for: .picturesDirectory, in: .userDomainMask).first
                ?? fileManager.homeDirectoryForCurrentUser.appendingPathComponent("Pictures", isDirectory: true),
            documentsURL: fileManager.urls(for: .documentDirectory, in: .userDomainMask).first
                ?? fileManager.homeDirectoryForCurrentUser.appendingPathComponent("Documents", isDirectory: true)
        )
    }
}

enum DesktopOrganizerError: LocalizedError {
    case desktopUnavailable(URL)

    var errorDescription: String? {
        switch self {
        case .desktopUnavailable(let url):
            return "Desktop Organizer could not open \(url.path). Check that the folder exists and that the app has permission to access your Desktop."
        }
    }
}

struct DesktopOrganizerService {
    let fileManager: FileManager
    let configuration: OrganizerConfiguration
    var now: () -> Date = Date.init

    static var live: DesktopOrganizerService {
        DesktopOrganizerService(
            fileManager: .default,
            configuration: .live
        )
    }

    func previewActions() throws -> [OrganizerAction] {
        guard fileManager.fileExists(atPath: configuration.desktopURL.path) else {
            throw DesktopOrganizerError.desktopUnavailable(configuration.desktopURL)
        }

        let resourceKeys: Set<URLResourceKey> = [
            .isRegularFileKey,
            .isAliasFileKey,
            .contentTypeKey,
            .creationDateKey,
            .contentModificationDateKey
        ]

        let items = try fileManager.contentsOfDirectory(
            at: configuration.desktopURL,
            includingPropertiesForKeys: Array(resourceKeys),
            options: [.skipsHiddenFiles, .skipsPackageDescendants]
        )

        let actions = try items.compactMap { fileURL -> OrganizerAction? in
            let values = try fileURL.resourceValues(forKeys: resourceKeys)

            guard values.isRegularFile == true, values.isAliasFile != true else {
                return nil
            }

            return action(for: fileURL, values: values)
        }

        return actions.sorted {
            $0.sourceURL.lastPathComponent.localizedCaseInsensitiveCompare($1.sourceURL.lastPathComponent) == .orderedAscending
        }
    }

    func organizeDesktop() throws -> OrganizerSummary {
        let actions = try previewActions()

        for action in actions {
            try perform(action)
        }

        return OrganizerSummary(actions: actions)
    }
}

private extension DesktopOrganizerService {
    static let imageExtensions: Set<String> = [
        "avif", "bmp", "gif", "heic", "jpeg", "jpg", "png", "tif", "tiff", "webp"
    ]

    static let movieExtensions: Set<String> = [
        "avi", "m4v", "mkv", "mov", "mp4", "mpeg", "mpg", "webm", "wmv"
    ]

    static let wordExtensions: Set<String> = [
        "doc", "docx", "dot", "dotx"
    ]

    func action(for fileURL: URL, values: URLResourceValues) -> OrganizerAction? {
        if isScreenshot(fileURL, values: values) {
            guard isOlderThanOneDay(values) else {
                return nil
            }

            return OrganizerAction(
                sourceURL: fileURL,
                destination: .trash,
                destinationURL: nil,
                reason: "Screenshot older than one day"
            )
        }

        if isWordDocument(fileURL, values: values) {
            return OrganizerAction(
                sourceURL: fileURL,
                destination: .documents,
                destinationURL: uniqueDestinationURL(for: fileURL, in: configuration.documentsURL),
                reason: "Word document"
            )
        }

        if isMovie(fileURL, values: values) {
            return OrganizerAction(
                sourceURL: fileURL,
                destination: .movies,
                destinationURL: uniqueDestinationURL(for: fileURL, in: configuration.moviesURL),
                reason: "Movie file"
            )
        }

        if isPhoto(fileURL, values: values) {
            return OrganizerAction(
                sourceURL: fileURL,
                destination: .pictures,
                destinationURL: uniqueDestinationURL(for: fileURL, in: configuration.picturesURL),
                reason: "Photo or image file"
            )
        }

        return nil
    }

    func perform(_ action: OrganizerAction) throws {
        switch action.destination {
        case .trash:
            try fileManager.trashItem(at: action.sourceURL, resultingItemURL: nil)
        case .documents:
            try move(action.sourceURL, toDirectory: configuration.documentsURL)
        case .movies:
            try move(action.sourceURL, toDirectory: configuration.moviesURL)
        case .pictures:
            try move(action.sourceURL, toDirectory: configuration.picturesURL)
        }
    }

    func move(_ sourceURL: URL, toDirectory directory: URL) throws {
        try fileManager.createDirectory(
            at: directory,
            withIntermediateDirectories: true,
            attributes: nil
        )

        let destinationURL = uniqueDestinationURL(for: sourceURL, in: directory)
        try fileManager.moveItem(at: sourceURL, to: destinationURL)
    }

    func uniqueDestinationURL(for sourceURL: URL, in directory: URL) -> URL {
        let extensionSuffix = sourceURL.pathExtension
        let baseName = sourceURL.deletingPathExtension().lastPathComponent

        var candidate = directory.appendingPathComponent(sourceURL.lastPathComponent)
        var index = 2

        while fileManager.fileExists(atPath: candidate.path) {
            let nextName = extensionSuffix.isEmpty
                ? "\(baseName) \(index)"
                : "\(baseName) \(index).\(extensionSuffix)"
            candidate = directory.appendingPathComponent(nextName)
            index += 1
        }

        return candidate
    }

    func isOlderThanOneDay(_ values: URLResourceValues) -> Bool {
        let referenceDate = values.creationDate ?? values.contentModificationDate ?? now()
        return now().timeIntervalSince(referenceDate) >= 86_400
    }

    func isScreenshot(_ fileURL: URL, values: URLResourceValues) -> Bool {
        guard isPhoto(fileURL, values: values) else {
            return false
        }

        let lowercaseName = fileURL.lastPathComponent.lowercased()
        return lowercaseName.contains("screenshot") || lowercaseName.contains("screen shot")
    }

    func isWordDocument(_ fileURL: URL, values: URLResourceValues) -> Bool {
        if let contentType = values.contentType,
           Self.wordExtensions.contains(contentType.preferredFilenameExtension?.lowercased() ?? "") {
            return true
        }

        return Self.wordExtensions.contains(fileURL.pathExtension.lowercased())
    }

    func isMovie(_ fileURL: URL, values: URLResourceValues) -> Bool {
        if let contentType = values.contentType, contentType.conforms(to: .movie) {
            return true
        }

        return Self.movieExtensions.contains(fileURL.pathExtension.lowercased())
    }

    func isPhoto(_ fileURL: URL, values: URLResourceValues) -> Bool {
        if let contentType = values.contentType, contentType.conforms(to: .image) {
            return true
        }

        return Self.imageExtensions.contains(fileURL.pathExtension.lowercased())
    }
}
