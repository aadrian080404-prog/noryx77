import Foundation

public enum NoryxPlatform: String, Sendable {
    case ios
}

public enum NoryxInteraction: String, Sendable {
    case text
    case voice
    case notification
    case systemEvent
}

public struct NoryxPlatformRequest: Sendable, Equatable {
    public let requestID: String
    public let deviceID: String
    public let platform: NoryxPlatform
    public let interaction: NoryxInteraction
    public let payload: String

    public init(requestID: String, deviceID: String, interaction: NoryxInteraction, payload: String) throws {
        guard !requestID.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty,
              !deviceID.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty,
              !payload.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty else {
            throw NoryxAdapterError.invalidRequest
        }
        self.requestID = requestID
        self.deviceID = deviceID
        self.platform = .ios
        self.interaction = interaction
        self.payload = payload
    }
}

public struct NoryxPlatformAction: Sendable, Equatable {
    public let actionID: String
    public let deviceID: String
    public let capability: String
    public let payload: String
    public let epoch: UInt64

    public init(actionID: String, deviceID: String, capability: String, payload: String, epoch: UInt64) throws {
        guard !actionID.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty,
              !deviceID.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty,
              !capability.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty,
              !payload.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty else {
            throw NoryxAdapterError.invalidAction
        }
        self.actionID = actionID
        self.deviceID = deviceID
        self.capability = capability
        self.payload = payload
        self.epoch = epoch
    }
}

public enum NoryxAdapterError: Error, Equatable {
    case invalidRequest
    case invalidAction
    case deviceMismatch
    case epochMismatch
    case capabilityDenied
    case handlerMissing
}
