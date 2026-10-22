import Foundation
import Testing
@testable import BobbCore

@Test func remoteControlRequestsExpireAndRejectUnboundedLeases() throws {
    #expect(RemoteControlLease(id: "session", expires: 115).isActive(now: 100))
    #expect(!RemoteControlLease(id: "session", expires: 99).isActive(now: 100))
    #expect(!RemoteControlLease(id: "session", expires: 131).isActive(now: 100))
    #expect(!RemoteControlLease(id: "", expires: 115).isActive(now: 100))
    let file = FileManager.default.temporaryDirectory.appendingPathComponent(UUID().uuidString)
    defer { try? FileManager.default.removeItem(at: file) }
    try Data(#"{"id":"python-relay","expires":115}"#.utf8).write(to: file)
    #expect(RemoteControlLease.isActive(at: file, now: 100))
    #expect(!RemoteControlLease.isActive(at: file, now: 116))
    try Data("incomplete".utf8).write(to: file)
    #expect(!RemoteControlLease.isActive(at: file, now: 100))
}
