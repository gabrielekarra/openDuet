import Foundation

/// A short-lived request made by the authenticated desktop relay. The OS file
/// lock still owns exclusivity; this marker only asks automation to yield it.
public struct RemoteControlLease: Codable, Sendable {
    public let id: String
    public let expires: TimeInterval

    public init(id: String, expires: TimeInterval) {
        self.id = id
        self.expires = expires
    }

    public func isActive(now: TimeInterval = Date().timeIntervalSince1970) -> Bool {
        !id.isEmpty && id.count <= 128 && expires.isFinite && expires > now && expires <= now + 30
    }

    public static func isActive(at url: URL, now: TimeInterval = Date().timeIntervalSince1970) -> Bool {
        guard let data = try? Data(contentsOf: url), data.count <= 4096,
              let lease = try? JSONDecoder().decode(Self.self, from: data) else { return false }
        return lease.isActive(now: now)
    }
}
