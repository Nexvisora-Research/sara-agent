//
//  SaraVoiceBackgroundService.swift
//  Sara Voice
//
//  Native background audio service for iOS.
//  Keeps the audio session alive for wake word detection
//  when the app is in the background.
//

import Foundation
import AVFoundation
import UIKit

@objc class SaraVoiceBackgroundService: NSObject {
    static let shared = SaraVoiceBackgroundService()
    private var audioEngine: AVAudioEngine?
    private var isRunning = false

    private override init() {
        super.init()
        setupAudioSession()
    }

    private func setupAudioSession() {
        let session = AVAudioSession.sharedInstance()
        do {
            try session.setCategory(
                .playAndRecord,
                mode: .default,
                options: [.allowBluetooth, .mixWithOthers, .duckOthers]
            )
            try session.setActive(true)
        } catch {
            print("Audio session setup failed: \(error)")
        }
    }

    @objc func startService() -> Bool {
        guard !isRunning else { return true }

        // Register for background task
        let backgroundTask = UIApplication.shared.beginBackgroundTask { [weak self] in
            self?.stopService()
        }

        // Start audio engine for wake word detection
        startAudioCapture()

        isRunning = true
        print("Background service started")
        return true
    }

    @objc func stopService() -> Bool {
        guard isRunning else { return true }

        stopAudioCapture()
        isRunning = false
        print("Background service stopped")
        return true
    }

    private func startAudioCapture() {
        audioEngine = AVAudioEngine()
        guard let engine = audioEngine else { return }

        let inputNode = engine.inputNode
        let inputFormat = inputNode.outputFormat(forBus: 0)

        inputNode.installTap(onBus: 0, bufferSize: 512, format: inputFormat) { buffer, _ in
            // Process audio buffer for wake word detection
            // In a full implementation, this feeds buffers to Porcupine
            self.processAudioBuffer(buffer)
        }

        do {
            try engine.start()
        } catch {
            print("Audio engine start failed: \(error)")
        }
    }

    private func stopAudioCapture() {
        audioEngine?.stop()
        audioEngine?.inputNode.removeTap(onBus: 0)
        audioEngine = nil
    }

    private func processAudioBuffer(_ buffer: AVAudioPCMBuffer) {
        // Forward audio data to wake word detector via Flutter EventChannel
        // or process locally with Porcupine
    }

    @objc func ping() -> Bool {
        return isRunning
    }
}
