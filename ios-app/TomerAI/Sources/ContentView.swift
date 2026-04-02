import SwiftUI

struct ContentView: View {
    @StateObject private var viewModel = ChatViewModel()
    
    var body: some View {
        ZStack {
            // Dark Theme Background
            Color(white: 0.1).edgesIgnoringSafeArea(.all)
            
            VStack(spacing: 0) {
                // Header
                HStack {
                    ZStack {
                        Circle()
                            .fill(LinearGradient(colors: [Color.blue, Color.purple], startPoint: .topLeading, endPoint: .bottomTrailing))
                            .frame(width: 40, height: 40)
                        Image(systemName: "mic.fill")
                            .foregroundColor(.white)
                            .font(.system(size: 16, weight: .semibold))
                    }
                    
                    VStack(alignment: .leading, spacing: 2) {
                        Text("תומר (Tomer)")
                            .font(.system(size: 17, weight: .semibold))
                            .foregroundColor(.white)
                        HStack(spacing: 4) {
                            Circle()
                                .fill(Color.green)
                                .frame(width: 8, height: 8)
                                .shadow(color: Color.green.opacity(0.4), radius: 4)
                            Text("Онлайн")
                                .font(.system(size: 12, weight: .medium))
                                .foregroundColor(.green)
                                .textCase(.uppercase)
                        }
                    }
                    Spacer()
                    
                    // Pipeline Toggle Button
                    Button(action: {
                        viewModel.togglePipeline()
                    }) {
                        HStack(spacing: 6) {
                            if viewModel.isPipelineActive {
                                Circle()
                                    .fill(Color.green)
                                    .frame(width: 8, height: 8)
                                    .shadow(color: Color.green.opacity(0.6), radius: 4)
                                Text("Компаньон")
                                    .font(.system(size: 12, weight: .medium))
                                    .foregroundColor(Color(red: 0.14, green: 0.54, blue: 0.24)) // Dark Green
                                    .textCase(.uppercase)
                                    .lineLimit(1)
                                    .minimumScaleFactor(0.8)
                            } else {
                                Text("🎙️ Режим колонки")
                                    .font(.system(size: 12, weight: .medium))
                                    .foregroundColor(.gray)
                                    .textCase(.uppercase)
                                    .lineLimit(1)
                                    .minimumScaleFactor(0.8)
                            }
                        }
                        .padding(.horizontal, 12)
                        .padding(.vertical, 8)
                        .background(
                            viewModel.isPipelineActive
                            ? Color.green.opacity(0.15)
                            : Color(white: 0.2)
                        )
                        .cornerRadius(20)
                        .overlay(
                            RoundedRectangle(cornerRadius: 20)
                                .stroke(viewModel.isPipelineActive ? Color.green.opacity(0.3) : Color.clear, lineWidth: 1)
                        )
                    }
                    .disabled(viewModel.isPipelineLoading)
                    .opacity(viewModel.isPipelineLoading ? 0.5 : 1.0)
                }
                .padding(.horizontal)
                .padding(.vertical, 12)
                .background(Color(white: 0.15))
                
                // Chat List
                ScrollViewReader { proxy in
                    ScrollView {
                        LazyVStack(spacing: 16) {
                            ForEach(viewModel.messages) { message in
                                MessageBubble(message: message)
                            }
                            // Invisible view to scroll to bottom
                            Color.clear
                                .frame(height: 1)
                                .id("bottom")
                        }
                        .padding()
                        .padding(.bottom, 100) // Space for bottom pad
                    }
                    .onChange(of: viewModel.messages.count) { _ in
                        withAnimation {
                            proxy.scrollTo("bottom", anchor: .bottom)
                        }
                    }
                    .onChange(of: viewModel.appState) { _ in
                        withAnimation {
                            proxy.scrollTo("bottom", anchor: .bottom)
                        }
                    }
                }
            }
            
            // Bottom Controls Layer
            VStack {
                Spacer()
                
                VStack(spacing: 8) {
                    // Status text
                    Text(statusText(for: viewModel.appState))
                        .font(.system(size: 14, weight: .medium))
                        .foregroundColor(.gray)
                        .padding(.horizontal, 16)
                        .padding(.vertical, 6)
                        .background(Capsule().fill(Color(white: 0.2)))
                        .opacity(viewModel.appState == .idle ? 0.7 : 1.0)
                    
                    // Main Record Button
                    Button(action: {}) {
                        ZStack {
                            // Pulsing rings for recording
                            if viewModel.appState == .recording {
                                Circle()
                                    .stroke(Color.red.opacity(0.3), lineWidth: 2)
                                    .frame(width: 90, height: 90)
                                    .scaleEffect(1.2)
                                    .animation(.easeInOut(duration: 1.5).repeatForever(autoreverses: true), value: viewModel.appState)
                                
                                Circle()
                                    .stroke(Color.red.opacity(0.5), lineWidth: 2)
                                    .frame(width: 80, height: 80)
                                    .scaleEffect(1.1)
                                    .animation(.easeInOut(duration: 1.2).repeatForever(autoreverses: true), value: viewModel.appState)
                            }
                            
                            // Base Button
                            Circle()
                                .fill(buttonColor(for: viewModel.appState))
                                .frame(width: 72, height: 72)
                                .shadow(color: buttonShadow(for: viewModel.appState), radius: 10, x: 0, y: 4)
                            
                            // Icon inside
                            if viewModel.appState == .processing {
                                ProgressView()
                                    .progressViewStyle(CircularProgressViewStyle(tint: .gray))
                                    .scaleEffect(1.5)
                            } else {
                                Image(systemName: "mic.fill")
                                    .font(.system(size: 32))
                                    .foregroundColor(iconColor(for: viewModel.appState))
                            }
                        }
                    }
                    .simultaneousGesture(
                        DragGesture(minimumDistance: 0)
                            .onChanged { _ in
                                if viewModel.appState == .idle {
                                    viewModel.handleRecordStart()
                                }
                            }
                            .onEnded { _ in
                                if viewModel.appState == .recording {
                                    viewModel.handleRecordStop()
                                }
                            }
                    )
                    .disabled(viewModel.appState == .processing || viewModel.appState == .playing)
                }
                .padding(.bottom, 30)
                .frame(maxWidth: .infinity)
                .background(
                    LinearGradient(colors: [Color(white: 0.1, opacity: 0.0), Color(white: 0.1, opacity: 0.9)], startPoint: .top, endPoint: .bottom)
                        .edgesIgnoringSafeArea(.bottom)
                )
            }
        }
        .onAppear {
            viewModel.fetchPipelineStatus()
        }
    }
    
    // UI Helpers
    private func statusText(for state: AppState) -> String {
        switch state {
        case .idle: return "Нажмите и удерживайте"
        case .recording: return "Слушаю..."
        case .processing: return "Анализирую..."
        case .playing: return "Отвечает..."
        case .error(let msg): return "Ошибка: \(msg)"
        }
    }
    
    private func buttonColor(for state: AppState) -> Color {
        switch state {
        case .recording:
            return Color.red // We can use gradient in a slightly more complex view
        case .processing:
            return Color(white: 0.25)
        case .idle, .playing, .error:
            return Color.white
        }
    }
    
    private func buttonShadow(for state: AppState) -> Color {
        switch state {
        case .recording: return Color.red.opacity(0.4)
        case .idle: return Color.blue.opacity(0.3)
        default: return Color.clear
        }
    }
    
    private func iconColor(for state: AppState) -> Color {
        switch state {
        case .recording: return .white
        default: return .blue
        }
    }
}

struct MessageBubble: View {
    let message: Message
    
    var body: some View {
        HStack(alignment: .bottom, spacing: 8) {
            if message.role != .user {
                // Assistant Avatar
                ZStack {
                    Circle()
                        .fill(LinearGradient(colors: [Color.blue, Color.purple], startPoint: .topLeading, endPoint: .bottomTrailing))
                        .frame(width: 28, height: 28)
                    Image(systemName: "mic.fill")
                        .foregroundColor(.white)
                        .font(.system(size: 12))
                }
            } else {
                Spacer()
            }
            
            VStack(alignment: message.role == .user ? .trailing : .leading, spacing: 4) {
                Text(message.text)
                    .font(.system(size: 16))
                    .foregroundColor(message.role == .user ? .white : .white)
                    .padding(.horizontal, 16)
                    .padding(.vertical, 12)
                    .background(
                        message.role == .user
                        ? AnyView(LinearGradient(colors: [Color.blue, Color(red: 0, green: 0.3, blue: 0.9)], startPoint: .top, endPoint: .bottom))
                        : AnyView(Color(white: 0.2))
                    )
                    .cornerRadius(20)
                    .overlay(
                        RoundedRectangle(cornerRadius: 20)
                            .stroke(message.role == .user ? Color.clear : Color(white: 0.3), lineWidth: 1)
                    )
                
                Text(message.timestamp)
                    .font(.system(size: 11))
                    .foregroundColor(.gray)
                    .padding(.horizontal, 4)
            }
            
            if message.role == .user {
                // User Avatar placeholder if we wanted one, otherwise we just leave space
            } else {
                Spacer()
            }
        }
        .environment(\.layoutDirection, hasRTLCharacters(message.text) ? .rightToLeft : .leftToRight)
    }
    
    // Quick RTL check for Hebrew
    func hasRTLCharacters(_ string: String) -> Bool {
        let pattern = ".*[\\u0590-\\u05FF]+.*"
        let test = NSPredicate(format: "SELF MATCHES %@", pattern)
        return test.evaluate(with: string)
    }
}

#Preview {
    ContentView()
}
