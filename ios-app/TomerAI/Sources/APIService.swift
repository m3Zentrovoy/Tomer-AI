import Foundation

// IP мака в локальной сети — обновить при смене сети
let API_BASE_URL = "http://192.168.1.88:8000"

enum APIError: Error {
    case invalidURL
    case networkError(Error)
    case serverError(Int)
    case decodingError(Error)
    case custom(String)
}

struct STTResponse: Decodable {
    let text: String
}

struct ChatResponse: Decodable {
    let response: String
}

struct PipelineStatusResponse: Decodable {
    let active: Bool
    let listening: Bool
}

class APIService {
    static let shared = APIService()
    private init() {}
    
    // 1. Speech-to-Text (fallback)
    func transcribe(audioURL: URL) async throws -> String {
        guard let url = URL(string: "\(API_BASE_URL)/api/stt") else { throw APIError.invalidURL }
        
        let audioData = try Data(contentsOf: audioURL)
        let boundary = UUID().uuidString
        
        var request = URLRequest(url: url)
        request.httpMethod = "POST"
        request.setValue("multipart/form-data; boundary=\(boundary)", forHTTPHeaderField: "Content-Type")
        
        var body = Data()
        body.append("--\(boundary)\r\n".data(using: .utf8)!)
        body.append("Content-Disposition: form-data; name=\"file\"; filename=\"recording.m4a\"\r\n".data(using: .utf8)!)
        body.append("Content-Type: audio/m4a\r\n\r\n".data(using: .utf8)!)
        body.append(audioData)
        body.append("\r\n--\(boundary)--\r\n".data(using: .utf8)!)
        
        request.httpBody = body
        
        let (data, response) = try await URLSession.shared.data(for: request)
        
        if let httpResponse = response as? HTTPURLResponse, !(200...299).contains(httpResponse.statusCode) {
            throw APIError.serverError(httpResponse.statusCode)
        }
        
        let result = try JSONDecoder().decode(STTResponse.self, from: data)
        return result.text
    }
    
    // 2. Chat LLM (fallback)
    func chat(message: String, history: [[String: String]]) async throws -> String {
        guard let url = URL(string: "\(API_BASE_URL)/api/chat") else { throw APIError.invalidURL }
        
        var request = URLRequest(url: url)
        request.httpMethod = "POST"
        request.setValue("application/json", forHTTPHeaderField: "Content-Type")
        
        let payload: [String: Any] = [
            "message": message,
            "history": history
        ]
        
        request.httpBody = try JSONSerialization.data(withJSONObject: payload)
        
        let (data, response) = try await URLSession.shared.data(for: request)
        
        if let httpResponse = response as? HTTPURLResponse, !(200...299).contains(httpResponse.statusCode) {
            throw APIError.serverError(httpResponse.statusCode)
        }
        
        let result = try JSONDecoder().decode(ChatResponse.self, from: data)
        return result.response
    }
    
    // 3. Text-to-Speech (fallback)
    func synthesize(text: String) async throws -> Data {
        guard let url = URL(string: "\(API_BASE_URL)/api/tts") else { throw APIError.invalidURL }
        
        var request = URLRequest(url: url)
        request.httpMethod = "POST"
        request.setValue("application/json", forHTTPHeaderField: "Content-Type")
        
        let payload: [String: Any] = ["text": text]
        request.httpBody = try JSONSerialization.data(withJSONObject: payload)
        
        let (data, response) = try await URLSession.shared.data(for: request)
        
        if let httpResponse = response as? HTTPURLResponse, !(200...299).contains(httpResponse.statusCode) {
            throw APIError.serverError(httpResponse.statusCode)
        }
        
        return data
    }
    
    // 4. Live Chat — Gemini Live (аудио → аудио)
    func liveChat(audioURL: URL) async throws -> Data {
        guard let url = URL(string: "\(API_BASE_URL)/api/live-chat") else { throw APIError.invalidURL }
        
        let audioData = try Data(contentsOf: audioURL)
        let boundary = UUID().uuidString
        
        var request = URLRequest(url: url)
        request.httpMethod = "POST"
        request.setValue("multipart/form-data; boundary=\(boundary)", forHTTPHeaderField: "Content-Type")
        
        var body = Data()
        body.append("--\(boundary)\r\n".data(using: .utf8)!)
        body.append("Content-Disposition: form-data; name=\"audio\"; filename=\"recording.m4a\"\r\n".data(using: .utf8)!)
        body.append("Content-Type: audio/m4a\r\n\r\n".data(using: .utf8)!)
        body.append(audioData)
        body.append("\r\n--\(boundary)--\r\n".data(using: .utf8)!)
        
        request.httpBody = body
        
        let (data, response) = try await URLSession.shared.data(for: request)
        
        if let httpResponse = response as? HTTPURLResponse, !(200...299).contains(httpResponse.statusCode) {
            throw APIError.serverError(httpResponse.statusCode)
        }
        
        return data
    }
    
    // 5. Pipeline Control
    func getPipelineStatus() async throws -> PipelineStatusResponse {
        guard let url = URL(string: "\(API_BASE_URL)/api/pipeline/status") else { throw APIError.invalidURL }
        
        let (data, response) = try await URLSession.shared.data(from: url)
        
        if let httpResponse = response as? HTTPURLResponse, !(200...299).contains(httpResponse.statusCode) {
            throw APIError.serverError(httpResponse.statusCode)
        }
        
        return try JSONDecoder().decode(PipelineStatusResponse.self, from: data)
    }
    
    func startPipeline() async throws {
        guard let url = URL(string: "\(API_BASE_URL)/api/pipeline/start") else { throw APIError.invalidURL }
        
        var request = URLRequest(url: url)
        request.httpMethod = "POST"
        
        let (_, response) = try await URLSession.shared.data(for: request)
        
        if let httpResponse = response as? HTTPURLResponse, !(200...299).contains(httpResponse.statusCode) {
            throw APIError.serverError(httpResponse.statusCode)
        }
    }
    
    func stopPipeline() async throws {
        guard let url = URL(string: "\(API_BASE_URL)/api/pipeline/stop") else { throw APIError.invalidURL }
        
        var request = URLRequest(url: url)
        request.httpMethod = "POST"
        
        let (_, response) = try await URLSession.shared.data(for: request)
        
        if let httpResponse = response as? HTTPURLResponse, !(200...299).contains(httpResponse.statusCode) {
            throw APIError.serverError(httpResponse.statusCode)
        }
    }
}
