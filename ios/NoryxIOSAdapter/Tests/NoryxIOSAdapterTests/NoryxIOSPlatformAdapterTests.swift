import XCTest
@testable import NoryxIOSAdapter

final class NoryxIOSPlatformAdapterTests: XCTestCase {
    func testAuthorizedActionExecutes() async throws {
        let adapter = try NoryxIOSPlatformAdapter(deviceID: "ios-device", epoch: 7)
        await adapter.grant(capability: "notifications.write", expiresAt: Date(timeIntervalSince1970: 2_000_000_000))
        await adapter.registerHandler(for: "notifications.write") { _ in true }
        let action = try NoryxPlatformAction(
            actionID: "a1", deviceID: "ios-device", capability: "notifications.write", payload: "hello", epoch: 7
        )
        XCTAssertTrue(try await adapter.execute(action: action))
    }

    func testWrongDeviceIsRejected() async throws {
        let adapter = try NoryxIOSPlatformAdapter(deviceID: "ios-device")
        let action = try NoryxPlatformAction(actionID: "a1", deviceID: "other", capability: "x", payload: "p", epoch: 0)
        do {
            _ = try await adapter.execute(action: action)
            XCTFail("expected device mismatch")
        } catch {
            XCTAssertEqual(error as? NoryxAdapterError, .deviceMismatch)
        }
    }

    func testWrongEpochIsRejected() async throws {
        let adapter = try NoryxIOSPlatformAdapter(deviceID: "ios-device", epoch: 4)
        await adapter.grant(capability: "x", expiresAt: Date(timeIntervalSinceNow: 60))
        let action = try NoryxPlatformAction(actionID: "a1", deviceID: "ios-device", capability: "x", payload: "p", epoch: 3)
        do {
            _ = try await adapter.execute(action: action)
            XCTFail("expected epoch mismatch")
        } catch {
            XCTAssertEqual(error as? NoryxAdapterError, .epochMismatch)
        }
    }

    func testUnregisteredCapabilityIsRejected() async throws {
        let adapter = try NoryxIOSPlatformAdapter(deviceID: "ios-device")
        let action = try NoryxPlatformAction(actionID: "a1", deviceID: "ios-device", capability: "x", payload: "p", epoch: 0)
        do {
            _ = try await adapter.execute(action: action)
            XCTFail("expected capability denial")
        } catch {
            XCTAssertEqual(error as? NoryxAdapterError, .capabilityDenied)
        }
    }

    func testEpochRotationRevokesExistingGrant() async throws {
        let adapter = try NoryxIOSPlatformAdapter(deviceID: "ios-device", epoch: 1)
        await adapter.grant(capability: "x", expiresAt: Date(timeIntervalSinceNow: 60))
        await adapter.registerHandler(for: "x") { _ in true }
        await adapter.rotateEpoch(to: 2)
        let action = try NoryxPlatformAction(actionID: "a1", deviceID: "ios-device", capability: "x", payload: "p", epoch: 2)
        do {
            _ = try await adapter.execute(action: action)
            XCTFail("expected rotated capability to be revoked")
        } catch {
            XCTAssertEqual(error as? NoryxAdapterError, .capabilityDenied)
        }
    }

    func testExpiredGrantIsRejected() async throws {
        let adapter = try NoryxIOSPlatformAdapter(deviceID: "ios-device")
        await adapter.grant(capability: "x", expiresAt: Date(timeIntervalSince1970: 0))
        await adapter.registerHandler(for: "x") { _ in true }
        let action = try NoryxPlatformAction(actionID: "a1", deviceID: "ios-device", capability: "x", payload: "p", epoch: 0)
        do {
            _ = try await adapter.execute(action: action)
            XCTFail("expected expired grant")
        } catch {
            XCTAssertEqual(error as? NoryxAdapterError, .capabilityDenied)
        }
    }
}
