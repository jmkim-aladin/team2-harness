import Darwin
import Foundation
import Security

// This binary is intentionally a pipe-only boundary.  It is used by the
// daemon/installer, not as an interactive keychain utility.

private let maxRequestBytes = 512 * 1024
private let maxPathBytes = 4096
private let maxServiceBytes = 128
private let maxAccountBytes = 512
private let maxValueBytes = 256 * 1024
private let maxItems = 4

private let allowedServices: Set<String> = [
    "cool-prod",
    "lego-prod",
    "cool-prod-observer",
    "lego-prod-observer",
    "cool-prod-profile",
    "lego-prod-profile",
    "cool-prod-observer-profile",
    "lego-prod-observer-profile",
]

private enum HelperError: Error {
    case rejected
    case invalidRequest
    case invalidPath
    case invalidIdentity
    case invalidSecret
    case keychainFailure
    case keychainStatus(OSStatus)
    case unsupported
}

private struct Request: Decodable {
    let mode: String
    let path: String
    let unlockPassword: String?
    let items: [Item]?
    let service: String?
    let account: String?

    enum CodingKeys: String, CodingKey {
        case mode
        case path
        case unlockPassword = "unlock_password"
        case items
        case service
        case account
    }
}

private struct Item: Decodable {
    let service: String
    let account: String
    let value: String
}

private struct SuccessResponse: Encodable {
    let value: String?
    let created: Bool?

    static func value(_ value: String) -> SuccessResponse {
        SuccessResponse(value: value, created: nil)
    }

    static func created() -> SuccessResponse {
        SuccessResponse(value: nil, created: true)
    }
}

private struct ErrorResponse: Encodable {
    let error: String
}

private func writeJSON<T: Encodable>(_ object: T) {
    do {
        let data = try JSONEncoder().encode(object)
        FileHandle.standardOutput.write(data)
        FileHandle.standardOutput.write(Data([0x0a]))
    } catch {
        // JSONEncoder cannot fail for the response structs above.  Keep the
        // fallback generic if a future response field changes that invariant.
        FileHandle.standardError.write(Data("error\n".utf8))
        exit(1)
    }
}

private func reject(_ error: HelperError = .rejected) -> Never {
    let message: String
    switch error {
    case .keychainStatus(errSecInteractionNotAllowed): message = "keychain_interaction_required"
    case .keychainStatus(errSecItemNotFound): message = "keychain_item_not_found"
    case .keychainStatus(errSecUserCanceled): message = "keychain_access_cancelled"
    case .keychainStatus(let status): message = "keychain_status_\(status)"
    case .invalidPath: message = "keychain_path_invalid"
    case .invalidSecret: message = "keychain_value_invalid"
    default: message = "request_rejected"
    }
    writeJSON(ErrorResponse(error: message))
    FileHandle.standardError.write(Data("error\n".utf8))
    exit(1)
}

private func readRequest() -> Data {
    var data = Data()
    data.reserveCapacity(min(maxRequestBytes, 16 * 1024))
    var buffer = [UInt8](repeating: 0, count: 16 * 1024)

    while true {
        let count = buffer.withUnsafeMutableBytes { rawBuffer -> Int in
            guard let baseAddress = rawBuffer.baseAddress else { return -1 }
            return Darwin.read(STDIN_FILENO, baseAddress, rawBuffer.count)
        }

        if count == 0 {
            break
        }
        if count < 0 {
            if errno == EINTR { continue }
            reject(.invalidRequest)
        }
        if data.count + count > maxRequestBytes {
            reject(.invalidRequest)
        }
        data.append(contentsOf: buffer[0..<count])
    }
    return data
}

private func hasNUL(_ value: String) -> Bool {
    value.utf8.contains(0)
}

private func validateUTF8String(_ value: String, maxBytes: Int, allowEmpty: Bool = false) throws {
    let byteCount = value.utf8.count
    guard byteCount <= maxBytes, (allowEmpty || byteCount > 0), !hasNUL(value) else {
        throw HelperError.invalidRequest
    }
}

private func validateIdentity(service: String, account: String) throws {
    guard allowedServices.contains(service) else {
        throw HelperError.invalidIdentity
    }
    try validateUTF8String(service, maxBytes: maxServiceBytes)
    try validateUTF8String(account, maxBytes: maxAccountBytes)
    if service.hasSuffix("-profile") && account != "profile" {
        throw HelperError.invalidIdentity
    }
}

private func validatePath(_ path: String) throws -> String {
    try validateUTF8String(path, maxBytes: maxPathBytes)
    guard path.hasPrefix("/") else { throw HelperError.invalidPath }
    guard !path.contains("\0") else { throw HelperError.invalidPath }

    let url = URL(fileURLWithPath: path).standardizedFileURL
    let standardized = url.path
    guard standardized.hasPrefix("/") else { throw HelperError.invalidPath }
    return standardized
}

private func pathExists(_ path: String) -> Bool {
    var info = stat()
    return lstat(path, &info) == 0
}

private func pathIsSymlink(_ path: String) -> Bool {
    var info = stat()
    guard lstat(path, &info) == 0 else { return false }
    return (info.st_mode & S_IFMT) == S_IFLNK
}

private func ensureRegularKeychainPath(_ path: String, mustExist: Bool) throws {
    if mustExist {
        guard pathExists(path), !pathIsSymlink(path) else { throw HelperError.invalidPath }
        var info = stat()
        guard lstat(path, &info) == 0, (info.st_mode & S_IFMT) == S_IFREG else {
            throw HelperError.invalidPath
        }
    } else if pathExists(path) || pathIsSymlink(path) {
        // Creation is deliberately no-clobber.  This also rejects a dangling
        // symlink at the requested destination.
        throw HelperError.invalidPath
    }
}

private func withUTF8Bytes<T>(_ value: String, _ body: (UnsafeRawPointer, UInt32) throws -> T) rethrows -> T {
    let data = Data(value.utf8)
    return try data.withUnsafeBytes { rawData in
        let pointer = rawData.baseAddress ?? UnsafeRawPointer(bitPattern: 1)!
        return try body(pointer, UInt32(data.count))
    }
}

private func withPasswordBytes<T>(_ value: String, _ body: (UnsafeRawPointer, UInt32) throws -> T) throws -> T {
    try validateUTF8String(value, maxBytes: maxValueBytes)
    return try withUTF8Bytes(value, body)
}

private func statusIsSuccess(_ status: OSStatus) -> Bool {
    status == errSecSuccess
}

private func openKeychain(_ path: String) throws -> SecKeychain {
    var keychain: SecKeychain?
    let status = SecKeychainOpen(path, &keychain)
    guard status == errSecSuccess, let keychain else { throw HelperError.keychainStatus(status) }
    return keychain
}

private func unlock(_ keychain: SecKeychain, password: String) throws {
    try withPasswordBytes(password) { pointer, length in
        let status = SecKeychainUnlock(keychain, length, pointer, true)
        guard statusIsSuccess(status) else { throw HelperError.keychainFailure }
    }
}

private func addGenericPassword(
    _ keychain: SecKeychain,
    service: String,
    account: String,
    value: String
) throws {
    try withUTF8Bytes(service) { servicePointer, serviceLength in
        try withUTF8Bytes(account) { accountPointer, accountLength in
            try withPasswordBytes(value) { valuePointer, valueLength in
                let status = SecKeychainAddGenericPassword(
                    keychain,
                    serviceLength,
                    servicePointer.assumingMemoryBound(to: CChar.self),
                    accountLength,
                    accountPointer.assumingMemoryBound(to: CChar.self),
                    valueLength,
                    valuePointer,
                    nil
                )
                guard status == errSecSuccess else { throw HelperError.keychainFailure }
            }
        }
    }
}

private func findGenericPassword(
    _ keychain: SecKeychain,
    service: String,
    account: String
) throws -> String {
    var passwordLength: UInt32 = 0
    var passwordData: UnsafeMutableRawPointer?

    let status: OSStatus = try withUTF8Bytes(service) { servicePointer, serviceLength in
        try withUTF8Bytes(account) { accountPointer, accountLength in
            SecKeychainFindGenericPassword(
                keychain,
                serviceLength,
                servicePointer.assumingMemoryBound(to: CChar.self),
                accountLength,
                accountPointer.assumingMemoryBound(to: CChar.self),
                &passwordLength,
                &passwordData,
                nil
            )
        }
    }
    guard status == errSecSuccess, let passwordData else { throw HelperError.keychainStatus(status) }
    defer { SecKeychainItemFreeContent(nil, passwordData) }

    let bytes = Data(bytes: passwordData, count: Int(passwordLength))
    guard let value = String(data: bytes, encoding: .utf8), !hasNUL(value) else {
        throw HelperError.invalidSecret
    }
    return value
}

private func createKeychain(path: String, password: String, items: [Item]) throws {
    try ensureRegularKeychainPath(path, mustExist: false)

    var keychain: SecKeychain?
    let status: OSStatus = try withPasswordBytes(password) { passwordPointer, passwordLength in
        SecKeychainCreate(
            path,
            passwordLength,
            passwordPointer,
            false,
            nil,
            &keychain
        )
    }
    guard status == errSecSuccess, let keychain else { throw HelperError.keychainFailure }

    do {
        try unlock(keychain, password: password)
        for item in items {
            try addGenericPassword(keychain, service: item.service, account: item.account, value: item.value)
        }
        // The installer creates the parent directory.  Restrict the database
        // file itself to the service account after Security creates it.
        guard chmod(path, S_IRUSR | S_IWUSR) == 0 else { throw HelperError.keychainFailure }
    } catch {
        // The destination did not exist before this call.  Removing a
        // partially-created keychain prevents a failed install from leaving a
        // file that appears provisioned.  No existing path is ever removed.
        SecKeychainSetUserInteractionAllowed(false)
        _ = SecKeychainDelete(keychain)
        throw error
    }
}

private func getValue(path: String, password: String, service: String, account: String) throws -> String {
    try ensureRegularKeychainPath(path, mustExist: true)
    let keychain = try openKeychain(path)
    try unlock(keychain, password: password)
    return try findGenericPassword(keychain, service: service, account: account)
}

private func readLoginValue(path: String, service: String, account: String) throws -> String {
    try ensureRegularKeychainPath(path, mustExist: true)
    let basename = URL(fileURLWithPath: path).lastPathComponent.lowercased()
    guard basename.contains("login") else { throw HelperError.invalidPath }
    let keychain = try openKeychain(path)
    return try findGenericPassword(keychain, service: service, account: account)
}

private func validateRequest(_ request: Request) throws {
    guard request.mode == "create" || request.mode == "get" || request.mode == "read-login" else {
        throw HelperError.unsupported
    }
    _ = try validatePath(request.path)

    switch request.mode {
    case "create":
        guard let password = request.unlockPassword, let items = request.items,
              !items.isEmpty, items.count <= maxItems else { throw HelperError.invalidRequest }
        try validateUTF8String(password, maxBytes: maxValueBytes)
        var identities = Set<String>()
        for item in items {
            try validateIdentity(service: item.service, account: item.account)
            try validateUTF8String(item.value, maxBytes: maxValueBytes, allowEmpty: true)
            let identity = "\(item.service)\u{1F}\(item.account)"
            guard identities.insert(identity).inserted else { throw HelperError.invalidIdentity }
        }
    case "get":
        guard let password = request.unlockPassword, let service = request.service,
              let account = request.account else { throw HelperError.invalidRequest }
        try validateUTF8String(password, maxBytes: maxValueBytes)
        try validateIdentity(service: service, account: account)
    case "read-login":
        guard let service = request.service, let account = request.account else {
            throw HelperError.invalidRequest
        }
        try validateIdentity(service: service, account: account)
    default:
        throw HelperError.unsupported
    }
}

private func run() throws -> SuccessResponse {
    guard isatty(STDIN_FILENO) == 0, isatty(STDOUT_FILENO) == 0 else {
        throw HelperError.rejected
    }
    SecKeychainSetUserInteractionAllowed(false)

    let requestData = readRequest()
    guard requestData.count <= maxRequestBytes else { throw HelperError.invalidRequest }
    let request: Request
    do {
        request = try JSONDecoder().decode(Request.self, from: requestData)
    } catch {
        throw HelperError.invalidRequest
    }
    try validateRequest(request)
    let path = try validatePath(request.path)
    // The current-user login keychain may require the human's macOS access
    // confirmation for this newly built helper. Dedicated test keychains stay
    // noninteractive. The caller bounds the lifetime of either operation.
    if request.mode == "read-login" {
        SecKeychainSetUserInteractionAllowed(true)
    }

    switch request.mode {
    case "create":
        guard let password = request.unlockPassword, let items = request.items else {
            throw HelperError.invalidRequest
        }
        try createKeychain(path: path, password: password, items: items)
        return .created()
    case "get":
        guard let password = request.unlockPassword, let service = request.service,
              let account = request.account else { throw HelperError.invalidRequest }
        return .value(try getValue(path: path, password: password, service: service, account: account))
    case "read-login":
        guard let service = request.service, let account = request.account else {
            throw HelperError.invalidRequest
        }
        return .value(try readLoginValue(path: path, service: service, account: account))
    default:
        throw HelperError.unsupported
    }
}

do {
    writeJSON(try run())
    exit(0)
} catch let error as HelperError {
    reject(error)
} catch {
    reject()
}
