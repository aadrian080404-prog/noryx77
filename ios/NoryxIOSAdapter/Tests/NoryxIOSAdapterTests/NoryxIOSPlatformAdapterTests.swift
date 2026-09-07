import XCTest
@testable import NoryxIOSAdapter

final class NoryxIOSPlatformAdapterTests: XCTestCase {
    func testAuthorizedActionExecutes() async throws {
        let adapter = try NoryxIOSPlatformAdapter(deviceID: "ios-device", epoch: 7)
        let expiry = Date(timeIntervalSince1970: 2_000_000_000)
        await adapter.grant(capability: "notifications.write", expiresAt: expiry)
        var executed = false
        await adapter.registerHandler(for: "notifications.write") { _ in
            executed = true
            return true
        }
        let action = try NoryxPlatformAction(
            actionID: "a1", deviceID: "ios-device", capability: "notifications.write", payload: "hello", epoch: 7
        )
        XCTAssertTrue(try await adapter.execute(action: action))
        XCTAssertTrue(executed)
    }

    func testWrongDeviceIsRejected() async throws {
        let adapter = try NoryxIOSPlatformAdapter(deviceID: "ios-device")
        let action = try NoryxPlatformAction(actionID: "a1", deviceID: "other", capability: "x", payload: "p", epoch: 0)
        XCTAssertThrowsError(try await adapter.execute(action: action)) { error in
            XCTAssertEqual(error as? NoryxAdapterError, .deviceMismatch)
        }
    }

    func testWrongEpochIsRejected() async throws {
        let adapter = try NoryxIOSPlatformAdapter(deviceID: "ios-device", epoch: 4)
        await adapter.grant(capability: "x", expiresAt: Date(timeIntervalSinceNow: 60))
        let action = try NoryxPlatformAction(actionID: "a1", deviceID: "ios-device", capability: "x", payload: "p", epoch: 3)
        XCTAssertThrowsError(try await adapter.execute(action: action)) { error in
            XCTAssertEqual(error as? NoryxAdapterError, .epochMismatch)
        }
    }

    func testUnregisteredCapabilityIsRejected() async throws {
        let adapter = try NoryxIOSPlatformAdapter(deviceID: "ios-device")
        let action = try NoryxPlatformAction(actionID: "a1", deviceID: "ios-device", capability: "x", payload: "p", epoch: 0)
        XCTAssertThrowsError(try await adapter.execute(action: action)) { error in
            XCTAssertEqual(error as? NoryxAdapterError, .capabilityDenied)
        }
    }

    func testEpochRotationRevokesExistingGrant() async throws {
        let adapter = try NoryxIOSPlatformAdapter(deviceID: "ios-device", epoch: 1)
        await adapter.grant(capability: "x", expiresAt: Date(timeIntervalSinceNow: 60))
        await adapter.registerHandler(for: "x") { _ in true }
        await adapter.rotateEpoch(to: 2)
        let action = try NoryxPlatformAction(actionID: "a1", deviceID: "ios-device", capability: "x", payload: "p", epoch: 2)
        XCTAssertThrowsError(try await adapter.execute(action: action)) { error in
            XCTAssertEqual(error as? NoryxAdapterError, .capabilityDenied)
        }
    }
}
