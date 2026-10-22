import AppKit
import Foundation
import Observation
import Security

/// Separate network-enabled service, owned by the app lifetime. The MLX daemon
/// remains a separate, network-isolated process. Remote access is opt-in.
@MainActor
@Observable
final class RemoteAccessService {
    static let shared = RemoteAccessService()
    private(set) var enabled = UserDefaults.standard.bool(forKey: "OpenDuetRemoteAccessEnabled")
    private(set) var status = ""
    private var process: Process?
    private var wakeLock: Process?
    private var monitor: Task<Void, Never>?
    private var nextAttempt = Date.distantPast
    private var failures = 0
    var onTakeover: (() -> Void)?

    var configurationURL: URL { AppPaths.dataDirectory.appendingPathComponent("Remote/openduet.toml") }

    func start() {
        guard monitor == nil, !AppPaths.flag("--mock-events") else { return }
        monitor = Task { [weak self] in
            while !Task.isCancelled {
                self?.tick()
                try? await Task.sleep(for: .milliseconds(250))
            }
        }
    }

    func stop() {
        monitor?.cancel(); monitor = nil
        if process?.isRunning == true { process?.terminate() }
        process = nil
        if wakeLock?.isRunning == true { wakeLock?.terminate() }
        wakeLock = nil
    }

    func setEnabled(_ value: Bool) {
        enabled = value
        UserDefaults.standard.set(value, forKey: "OpenDuetRemoteAccessEnabled")
        failures = 0; nextAttempt = .distantPast
        if !value {
            if process?.isRunning == true { process?.terminate() }
            process = nil; status = BobbCopy.t("Remote access is off", "Accesso remoto disattivato")
            if wakeLock?.isRunning == true { wakeLock?.terminate() }
            wakeLock = nil
        } else { tick() }
    }

    func copyAccessToken() {
        do {
            let value = try accessToken()
            NSPasteboard.general.clearContents()
            NSPasteboard.general.setString(value, forType: .string)
            status = BobbCopy.t("Access token copied. Use it to sign in from your other device.", "Token copiato. Usalo per accedere dall’altro dispositivo.")
        } catch {
            status = BobbCopy.t("Keychain access failed.", "Accesso al Portachiavi non riuscito.")
        }
    }

    func openConfiguration() { NSWorkspace.shared.selectFile(configurationURL.path, inFileViewerRootedAtPath: "") }

    private func tick() {
        if ScreenLease.remoteRequested { onTakeover?() }
        guard enabled else { return }
        if let process {
            if process.isRunning { return }
            self.process = nil
            failures += 1
            if failures >= 5, wakeLock?.isRunning == true { wakeLock?.terminate(); wakeLock = nil }
            nextAttempt = Date().addingTimeInterval(min(60, pow(2, Double(failures))))
            status = BobbCopy.t("Remote service stopped. Check its configuration or whether port 8765 is already in use.", "Il servizio remoto si è fermato. Controlla la configurazione o se la porta 8765 è già occupata.")
        }
        guard failures < 5, Date() >= nextAttempt else { return }
        do {
            try prepareConfiguration()
            let token = try accessToken()
            guard var command = DaemonCommand.resolve(dataDir: AppPaths.dataDirectory, modelsDir: AppPaths.modelsDirectory,
                                                       logFile: AppPaths.logsDirectory.appendingPathComponent("remote.log")) else {
                throw CocoaError(.fileNoSuchFile)
            }
            command.arguments = ["-s", "-m", "openduet", "--config", configurationURL.path,
                                 "--parent-pid", String(ProcessInfo.processInfo.processIdentifier)]
            command.environment["OPENDUET_TOKEN"] = token
            let child = Process()
            child.executableURL = command.executable
            child.arguments = command.arguments
            child.environment = command.environment
            child.currentDirectoryURL = command.workingDirectory
            child.standardOutput = FileHandle.nullDevice
            child.standardError = FileHandle.nullDevice
            try child.run()
            process = child
            if wakeLock?.isRunning != true {
                let awake = Process()
                awake.executableURL = URL(fileURLWithPath: "/usr/bin/caffeinate")
                awake.arguments = ["-i", "-w", String(ProcessInfo.processInfo.processIdentifier)]
                awake.standardOutput = FileHandle.nullDevice; awake.standardError = FileHandle.nullDevice
                try? awake.run()
                wakeLock = awake
            }
            status = BobbCopy.t("Remote service started on localhost:8765. Use a private network or HTTPS for remote access.", "Servizio remoto avviato su localhost:8765. Usa una rete privata o HTTPS per l’accesso dall’esterno.")
        } catch {
            failures += 1
            nextAttempt = Date().addingTimeInterval(10)
            status = BobbCopy.t("Could not start remote access. Check the Python workspace installation and Keychain.", "Impossibile avviare l’accesso remoto. Controlla l’installazione del workspace Python e il Portachiavi.")
        }
    }

    private func accessToken() throws -> String {
        let key = "OpenDuetRemoteAccessTokenReference"
        if let reference = UserDefaults.standard.string(forKey: key) { return try MCPSecrets.read(reference) }
        var bytes = [UInt8](repeating: 0, count: 32)
        guard SecRandomCopyBytes(kSecRandomDefault, bytes.count, &bytes) == errSecSuccess else {
            throw CocoaError(.fileReadUnknown)
        }
        let value = Data(bytes).base64EncodedString()
        UserDefaults.standard.set(try MCPSecrets.store(value), forKey: key)
        return value
    }

    private func prepareConfiguration() throws {
        let fm = FileManager.default
        let directory = configurationURL.deletingLastPathComponent()
        try fm.createDirectory(at: directory, withIntermediateDirectories: true, attributes: [.posixPermissions: 0o700])
        guard !fm.fileExists(atPath: configurationURL.path) else { return }
        let encoder = JSONEncoder(); encoder.outputFormatting = [.withoutEscapingSlashes]
        func quoted(_ value: String) throws -> String { String(decoding: try encoder.encode(value), as: UTF8.self) }
        let contents = """
        data_dir = \(try quoted(directory.appendingPathComponent("state").path))
        host = "127.0.0.1"
        port = 8765
        default_provider = "local"

        [providers.local]
        kind = "openai"
        base_url = "http://127.0.0.1:11434/v1"
        model = "qwen3.5:4b"

        [computers.host]
        name = "My Mac"
        host = "127.0.0.1"
        port = 5900
        screen_lock = \(try quoted(AppPaths.dataDirectory.appendingPathComponent("screen.lock").path))
        """
        try Data(contents.utf8).write(to: configurationURL, options: .atomic)
        try fm.setAttributes([.posixPermissions: 0o600], ofItemAtPath: configurationURL.path)
    }
}
