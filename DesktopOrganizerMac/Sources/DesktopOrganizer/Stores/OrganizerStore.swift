import Foundation
import Observation

@MainActor
@Observable
final class OrganizerStore {
    private let service: DesktopOrganizerService

    var preview: [OrganizerAction] = []
    var isWorking = false
    var statusMessage = "Scan your Desktop to preview the cleanup rules."
    var errorMessage: String?
    var lastRunDate: Date?

    init(service: DesktopOrganizerService) {
        self.service = service
    }

    var summary: OrganizerSummary {
        OrganizerSummary(actions: preview)
    }

    var desktopPath: String {
        Self.tildePath(for: service.configuration.desktopURL)
    }

    var moviesPath: String {
        Self.tildePath(for: service.configuration.moviesURL)
    }

    var picturesPath: String {
        Self.tildePath(for: service.configuration.picturesURL)
    }

    var documentsPath: String {
        Self.tildePath(for: service.configuration.documentsURL)
    }

    func refreshPreview() {
        guard !isWorking else {
            return
        }

        isWorking = true
        statusMessage = "Scanning Desktop..."

        defer {
            isWorking = false
        }

        do {
            let actions = try service.previewActions()
            preview = actions
            errorMessage = nil
            statusMessage = actions.isEmpty
                ? "Desktop is already tidy for these rules."
                : "Preview ready: \(actions.count) item(s) match your rules."
        } catch {
            errorMessage = error.localizedDescription
            statusMessage = "Desktop Organizer hit an error."
        }
    }

    func organizeDesktop() {
        guard !isWorking else {
            return
        }

        isWorking = true
        statusMessage = "Organizing Desktop..."

        defer {
            isWorking = false
        }

        do {
            let summary = try service.organizeDesktop()
            preview = try service.previewActions()
            errorMessage = nil
            lastRunDate = Date()
            statusMessage = Self.completionMessage(for: summary)
        } catch {
            errorMessage = error.localizedDescription
            statusMessage = "Desktop Organizer hit an error."
        }
    }
}

private extension OrganizerStore {
    static func tildePath(for url: URL) -> String {
        let homePath = FileManager.default.homeDirectoryForCurrentUser.path
        let path = url.path

        guard path.hasPrefix(homePath) else {
            return path
        }

        return "~" + path.dropFirst(homePath.count)
    }

    static func completionMessage(for summary: OrganizerSummary) -> String {
        guard summary.totalCount > 0 else {
            return "Nothing needed to change."
        }

        var fragments: [String] = []

        if summary.movedCount > 0 {
            let noun = summary.movedCount == 1 ? "item" : "items"
            fragments.append("moved \(summary.movedCount) \(noun)")
        }

        if summary.trashedCount > 0 {
            let noun = summary.trashedCount == 1 ? "screenshot" : "screenshots"
            fragments.append("trashed \(summary.trashedCount) \(noun)")
        }

        return "Finished: " + fragments.joined(separator: " and ") + "."
    }
}
