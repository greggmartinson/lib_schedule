import Foundation

enum OrganizerDestination: String, CaseIterable, Hashable {
    case movies
    case pictures
    case documents
    case trash

    var title: String {
        switch self {
        case .movies:
            return "Movies"
        case .pictures:
            return "Pictures"
        case .documents:
            return "Documents"
        case .trash:
            return "Trash"
        }
    }

    var systemImage: String {
        switch self {
        case .movies:
            return "film.stack"
        case .pictures:
            return "photo.stack"
        case .documents:
            return "doc.text"
        case .trash:
            return "trash"
        }
    }
}

struct OrganizerAction: Identifiable, Hashable {
    let sourceURL: URL
    let destination: OrganizerDestination
    let destinationURL: URL?
    let reason: String

    var id: URL {
        sourceURL
    }

    var actionLabel: String {
        switch destination {
        case .trash:
            return "Move to Trash"
        case .movies, .pictures, .documents:
            return "Move to \(destination.title)"
        }
    }

    var destinationDisplayText: String {
        switch destination {
        case .trash:
            return "Trash"
        case .movies, .pictures, .documents:
            return destinationURL.map(Self.tildePath(for:)) ?? destination.title
        }
    }

    private static func tildePath(for url: URL) -> String {
        let homePath = FileManager.default.homeDirectoryForCurrentUser.path
        let path = url.path

        guard path.hasPrefix(homePath) else {
            return path
        }

        return "~" + path.dropFirst(homePath.count)
    }
}

struct OrganizerSummary {
    let actions: [OrganizerAction]

    var totalCount: Int {
        actions.count
    }

    var movedCount: Int {
        actions.filter { $0.destination != .trash }.count
    }

    var trashedCount: Int {
        actions.filter { $0.destination == .trash }.count
    }

    func count(for destination: OrganizerDestination) -> Int {
        actions.filter { $0.destination == destination }.count
    }
}
