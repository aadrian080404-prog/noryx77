import Foundation

public actor NoryxIOSPlatformAdapter: Sendable {
    public typealias ActionHandler = @Sendable (NoryxPlatformAction) -> Bool
    public static let maxTextBytes = 1_024
    public static let maxConsumedActions = 4_096

    public let deviceID: String
    private let clock: @Sendable () -> Date
    private var grants: [String: Date] = [:]
    private var handlers: [String: ActionHandler] = [:]
    private var consumedActionIDs: Set<String> = []
    private var currentEpoch: UInt64

    public init(deviceID: String, epoch: UInt64 = 0, clock: @escaping @Sendable () -> Date = Date.init) throws {
        guard Self.validText(deviceID) else {
            throw NoryxAdapterError.invalidRequest
        }
        self.deviceID = deviceID
        self.currentEpoch = epoch
        self.clock = clock
    }

    public func rotateEpoch(to epoch: UInt64) {
        guard epoch > currentEpoch else { return }
        currentEpoch = epoch
        grants.removeAll(keepingCapacity: true)
        handlers.removeAll(keepingCapacity: true)
        consumedActionIDs.removeAll(keepingCapacity: true)
    }

    public func grant(capability: String, expiresAt: Date) {
        guard Self.validText(capability) else { return }
        grants[capability] = expiresAt
    }

    public func revoke(capability: String) {
        grants.removeValue(forKey: capability)
        handlers.removeValue(forKey: capability)
    }

    public func registerHandler(for capability: String, handler: @escaping ActionHandler) {
        guard grants[capability] != nil, Self.validText(capability) else { return }
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
        guard !consumedActionIDs.contains(action.actionID) else {
            throw NoryxAdapterError.replayedAction
        }
        guard consumedActionIDs.count < Self.maxConsumedActions else {
            throw NoryxAdapterError.replayCapacityExceeded
        }
        guard handler(action) == true else {
            throw NoryxAdapterError.capabilityDenied
        }
        consumedActionIDs.insert(action.actionID)
        return true
    }

    private static func validText(_ value: String) -> Bool {
        !value.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty
            && value.utf8.count <= maxTextBytes
    }
}
