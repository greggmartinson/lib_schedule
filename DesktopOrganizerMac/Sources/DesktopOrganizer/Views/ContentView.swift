import SwiftUI

struct ContentView: View {
    let store: OrganizerStore

    private let gridColumns = [
        GridItem(.flexible(), spacing: 12),
        GridItem(.flexible(), spacing: 12)
    ]

    var body: some View {
        ZStack {
            LinearGradient(
                colors: [
                    Color(nsColor: .windowBackgroundColor),
                    Color.accentColor.opacity(0.10)
                ],
                startPoint: .topLeading,
                endPoint: .bottomTrailing
            )
            .ignoresSafeArea()

            VStack(alignment: .leading, spacing: 20) {
                header
                rulesGrid
                statsRow
                previewPanel
                controlBar
            }
            .padding(24)
        }
        .onAppear {
            if store.preview.isEmpty && !store.isWorking {
                store.refreshPreview()
            }
        }
    }

    private var header: some View {
        VStack(alignment: .leading, spacing: 10) {
            Text("Desktop Organizer")
                .font(.system(size: 34, weight: .bold, design: .rounded))

            Text("Scans \(store.desktopPath) and follows your cleanup rules. Recent screenshots stay on the desktop for a day, then older ones go to the Trash.")
                .font(.title3)
                .foregroundStyle(.secondary)
        }
    }

    private var rulesGrid: some View {
        LazyVGrid(columns: gridColumns, spacing: 12) {
            RuleCard(
                title: "Movies",
                subtitle: "Move matching files to \(store.moviesPath)",
                systemImage: "film.stack",
                tint: .blue
            )

            RuleCard(
                title: "Photos",
                subtitle: "Move image files to \(store.picturesPath)",
                systemImage: "photo.stack",
                tint: .green
            )

            RuleCard(
                title: "Word Docs",
                subtitle: "Move .doc and .docx files to \(store.documentsPath)",
                systemImage: "doc.text",
                tint: .orange
            )

            RuleCard(
                title: "Old Screenshots",
                subtitle: "Trash screenshots once they are older than one day",
                systemImage: "trash",
                tint: .red
            )
        }
    }

    private var statsRow: some View {
        HStack(spacing: 12) {
            StatCard(title: "Movies", count: store.summary.count(for: .movies), tint: .blue)
            StatCard(title: "Photos", count: store.summary.count(for: .pictures), tint: .green)
            StatCard(title: "Docs", count: store.summary.count(for: .documents), tint: .orange)
            StatCard(title: "Trash", count: store.summary.count(for: .trash), tint: .red)
        }
    }

    private var previewPanel: some View {
        VStack(alignment: .leading, spacing: 14) {
            HStack {
                Text("Preview")
                    .font(.title2.weight(.semibold))

                Spacer()

                Text("\(store.preview.count) pending")
                    .font(.subheadline.weight(.medium))
                    .foregroundStyle(.secondary)
            }

            if store.preview.isEmpty {
                ContentUnavailableView(
                    "No matching desktop files",
                    systemImage: "checkmark.circle",
                    description: Text("The desktop already matches your rules, or it only contains recent screenshots that should stay put for now.")
                )
                .frame(maxWidth: .infinity, maxHeight: .infinity)
            } else {
                Table(store.preview) {
                    TableColumn("File") { action in
                        VStack(alignment: .leading, spacing: 2) {
                            Text(action.sourceURL.lastPathComponent)
                                .font(.body.weight(.medium))
                                .lineLimit(1)

                            Text(action.sourceURL.deletingLastPathComponent().path)
                                .font(.caption)
                                .foregroundStyle(.secondary)
                                .lineLimit(1)
                        }
                    }
                    .width(min: 210, ideal: 280)

                    TableColumn("Action") { action in
                        Label(action.actionLabel, systemImage: action.destination.systemImage)
                    }
                    .width(min: 150, ideal: 190)

                    TableColumn("Destination") { action in
                        Text(action.destinationDisplayText)
                            .lineLimit(1)
                    }
                    .width(min: 170, ideal: 240)

                    TableColumn("Reason") { action in
                        Text(action.reason)
                            .lineLimit(2)
                    }
                    .width(min: 150, ideal: 210)
                }
                .frame(minHeight: 300)
            }
        }
        .padding(18)
        .background(.regularMaterial, in: RoundedRectangle(cornerRadius: 22, style: .continuous))
    }

    private var controlBar: some View {
        HStack(spacing: 16) {
            VStack(alignment: .leading, spacing: 5) {
                Label(
                    store.errorMessage ?? store.statusMessage,
                    systemImage: store.errorMessage == nil ? "info.circle" : "exclamationmark.triangle.fill"
                )
                .foregroundStyle(store.errorMessage == nil ? Color.secondary : Color.red)

                Text("macOS may ask for one-time access to Desktop, Documents, Pictures, or Movies the first time you run it.")
                    .font(.caption)
                    .foregroundStyle(.secondary)
            }

            Spacer()

            if store.isWorking {
                ProgressView()
                    .controlSize(.small)
            }

            Button("Refresh Preview") {
                store.refreshPreview()
            }
            .disabled(store.isWorking)

            Button("Organize Desktop") {
                store.organizeDesktop()
            }
            .keyboardShortcut(.defaultAction)
            .disabled(store.preview.isEmpty || store.isWorking)
        }
        .padding(18)
        .background(.ultraThinMaterial, in: RoundedRectangle(cornerRadius: 22, style: .continuous))
    }
}

private struct RuleCard: View {
    let title: String
    let subtitle: String
    let systemImage: String
    let tint: Color

    var body: some View {
        HStack(alignment: .top, spacing: 14) {
            Image(systemName: systemImage)
                .font(.title2)
                .foregroundStyle(tint)
                .frame(width: 30)

            VStack(alignment: .leading, spacing: 4) {
                Text(title)
                    .font(.headline)

                Text(subtitle)
                    .font(.subheadline)
                    .foregroundStyle(.secondary)
            }

            Spacer(minLength: 0)
        }
        .padding(16)
        .background(.thinMaterial, in: RoundedRectangle(cornerRadius: 18, style: .continuous))
    }
}

private struct StatCard: View {
    let title: String
    let count: Int
    let tint: Color

    var body: some View {
        VStack(alignment: .leading, spacing: 8) {
            Text(title)
                .font(.subheadline.weight(.medium))
                .foregroundStyle(.secondary)

            Text("\(count)")
                .font(.system(size: 28, weight: .bold, design: .rounded))
                .foregroundStyle(tint)
        }
        .frame(maxWidth: .infinity, alignment: .leading)
        .padding(16)
        .background(.thinMaterial, in: RoundedRectangle(cornerRadius: 18, style: .continuous))
    }
}
