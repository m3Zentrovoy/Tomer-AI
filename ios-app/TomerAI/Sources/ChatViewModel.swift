import Foundation
import SwiftUI

enum Role: String {
    case user = "user"
    case assistant = "assistant"
}

struct Message: Identifiable {
    let id = UUID()
    let role: Role
    let text: String
    let timestamp: String
}

enum AppState: Equatable {
    case idle
    case recording
    case processing
    case playing
    case error(String)
}

@MainActor
class ChatViewModel: ObservableObject {
    @Published var messages: [Message] = []
    @Published var appState: AppState = .idle
    
    @Published var isPipelineActive = false
    @Published var isPipelineLoading = false
    
    private let recorder = AudioRecorder()
    private let player = AudioPlayer()
    
    private var isRequestingPermission = false
    
    func handleRecordStart() {
        guard appState == .idle, !isRequestingPermission, !isPipelineActive else { return }
        isRequestingPermission = true
        
        recorder.checkPermission { [weak self] allowed in
            guard let self = self else { return }
            self.isRequestingPermission = false
            if allowed {
                self.appState = .recording
                self.recorder.startRecording()
                self.player.stop()
            } else {
                self.appState = .error("Нет доступа к микрофону")
                DispatchQueue.main.asyncAfter(deadline: .now() + 3) {
                    if case .error(_) = self.appState { self.appState = .idle }
                }
            }
        }
    }
    
    func handleRecordStop() {
        guard appState == .recording else { return }
        
        if let audioURL = recorder.stopRecording() {
            processAudio(url: audioURL)
        } else {
            appState = .idle
        }
    }
    
    private func processAudio(url: URL) {
        appState = .processing
        
        Task {
            do {
                // 1. Speech to Text
                let transcribedText = try await APIService.shared.transcribe(audioURL: url)
                
                if transcribedText.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty {
                    throw APIError.custom("Голос не распознан")
                }
                
                let userMsg = Message(role: .user, text: transcribedText, timestamp: currentTime())
                messages.append(userMsg)
                
                let historyForBackend = messages.map { ["role": $0.role.rawValue, "content": $0.text] }
                
                // 2. Chat API
                let assistantText = try await APIService.shared.chat(message: transcribedText, history: historyForBackend)
                
                let assistantMsg = Message(role: .assistant, text: assistantText, timestamp: currentTime())
                messages.append(assistantMsg)
                
                // 3. Text to Speech
                let audioData = try await APIService.shared.synthesize(text: assistantText)
                
                // 4. Play Audio
                appState = .playing
                player.onFinish = { [weak self] in
                    self?.appState = .idle
                }
                player.play(data: audioData)
                
            } catch {
                print("Pipeline error: \(error)")
                appState = .error(error.localizedDescription)
                
                try? await Task.sleep(nanoseconds: 3_000_000_000)
                if case .error = appState {
                    appState = .idle
                }
            }
        }
    }
    
    private func currentTime() -> String {
        let formatter = DateFormatter()
        formatter.dateFormat = "HH:mm"
        return formatter.string(from: Date())
    }
    
    // MARK: - Pipeline (режим колонки)
    
    func fetchPipelineStatus() {
        Task {
            do {
                let status = try await APIService.shared.getPipelineStatus()
                self.isPipelineActive = status.active
            } catch {
                print("Failed to fetch pipeline status: \(error)")
            }
        }
    }
    
    func togglePipeline() {
        guard !isPipelineLoading else { return }
        isPipelineLoading = true
        
        Task {
            do {
                if isPipelineActive {
                    try await APIService.shared.stopPipeline()
                    self.isPipelineActive = false
                } else {
                    try await APIService.shared.startPipeline()
                    self.isPipelineActive = true
                }
            } catch {
                print("Failed to toggle pipeline: \(error)")
                self.appState = .error("Ошибка управления колонкой")
                
                try? await Task.sleep(nanoseconds: 3_000_000_000)
                if case .error = self.appState {
                    self.appState = .idle
                }
            }
            self.isPipelineLoading = false
        }
    }
}
