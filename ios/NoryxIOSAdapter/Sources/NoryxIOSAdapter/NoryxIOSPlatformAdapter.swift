import Foundation

public actor NoryxIOSPlatformAdapter {
    public typealias ActionHandler = @Sendable (NoryxPlatformAction) -> Bool

    public nonisolated let deviceID: String
    private let clock: @Sendable () -> Date
    private var grants: [String: Date] = [:]
    private var handlers: [String: ActionHandler] = [:]
    private var currentEpoch: UInt64

    public init(deviceID: String, epoch: UInt64 = 0, clock: @escaping @Sendable () -> Date = Date.init) throws {
        guard !deviceID.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty else {
            throw NoryxAdapterError.invalidRequest
        }
        self.deviceID = deviceID
        self.currentEpoch = epoch
        self.clock = clock
    }

    public func rotateEpoch(to epoch: UInt64) {
        guard epoch >= currentEpoch else { return }
        currentEpoch = epoch
        grants.removeAll(keepingCapacity: true)
        handlers.removeAll(keepingCapacity: true)
    }

    public func grant(capability: String, expiresAt: Date) {
        guard !capability.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty else { return }
        grants[capability] = expiresAt
    }

    public func revoke(capability: String) {
        grants.removeValue(forKey: capability)
        handlers.removeValue(forKey: capability)
    }

    public func registerHandler(for capability: String, handler: @escaping ActionHandler) {
        guard grants[capability] != nil else { return }
        handlers[capability] = handler
    }

    public func receive(request: NoryxPlatformRequest) throws -> NoryxPlatformRequest {
        guard request.platform == .ios, request.deviceID == deviceID else {
            throw NoryxAdapterError.deviceMismatch
        }
        return request
    }

    @discardableResult
    public func execute(action: NoryxPlatformAction) throws -> Bool {
        guard action.deviceID == deviceID else { throw NoryxAdapterError.deviceMismatch }
        guard action.epoch == currentEpoch else { throw NoryxAdapterError.epochMismatch }
        guard let expiry = grants[action.capability], clock() <= expiry else {
            throw NoryxAdapterError.capabilityDenied
        }
        guard let handler = handlers[action.capability] else {
            throw NoryxAdapterError.handlerMissing
        }
        guard handler(action) == true else {
            throw NoryxAdapterError.capabilityDenied
        }
        return true
    }
}
