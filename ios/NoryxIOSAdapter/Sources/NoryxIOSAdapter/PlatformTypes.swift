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
    public static let maxTextBytes = 1_024
    public let requestID: String
    public let deviceID: String
    public let platform: NoryxPlatform
    public let interaction: NoryxInteraction
    public let payload: String

    public init(requestID: String, deviceID: String, interaction: NoryxInteraction, payload: String) throws {
        guard Self.validText(requestID), Self.validText(deviceID), Self.validText(payload) else {
            throw NoryxAdapterError.invalidRequest
        }
        self.requestID = requestID
        self.deviceID = deviceID
        self.platform = .ios
        self.interaction = interaction
        self.payload = payload
    }

    private static func validText(_ value: String) -> Bool {
        !value.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty
            && value.utf8.count <= maxTextBytes
    }
}

public struct NoryxPlatformAction: Sendable, Equatable {
    public static let maxTextBytes = 1_024
    public let actionID: String
    public let deviceID: String
    public let capability: String
    public let payload: String
    public let epoch: UInt64

    public init(actionID: String, deviceID: String, capability: String, payload: String, epoch: UInt64) throws {
        guard Self.validText(actionID), Self.validText(deviceID), Self.validText(capability), Self.validText(payload) else {
            throw NoryxAdapterError.invalidAction
        }
        self.actionID = actionID
        self.deviceID = deviceID
        self.capability = capability
        self.payload = payload
        self.epoch = epoch
    }

    private static func validText(_ value: String) -> Bool {
        !value.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty
            && value.utf8.count <= maxTextBytes
    }
}

public enum NoryxAdapterError: Error, Equatable {
    case invalidRequest
    case invalidAction
    case deviceMismatch
    case epochMismatch
    case capabilityDenied
    case handlerMissing
    case replayedAction
    case replayCapacityExceeded
}
