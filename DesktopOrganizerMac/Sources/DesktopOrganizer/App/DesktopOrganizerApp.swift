import AppKit
import SwiftUI

@main
struct DesktopOrganizerApp: App {
    @NSApplicationDelegateAdaptor(AppDelegate.self) private var appDelegate
    @State private var store = OrganizerStore(service: .live)

    var body: some Scene {
        WindowGroup("Desktop Organizer") {
            ContentView(store: store)
                .frame(minWidth: 920, minHeight: 640)
        }
        .defaultSize(width: 920, height: 640)
    }
}

final class AppDelegate: NSObject, NSApplicationDelegate {
    func applicationDidFinishLaunching(_ notification: Notification) {
        NSApp.setActivationPolicy(.regular)
        NSApp.activate(ignoringOtherApps: true)
    }
}
