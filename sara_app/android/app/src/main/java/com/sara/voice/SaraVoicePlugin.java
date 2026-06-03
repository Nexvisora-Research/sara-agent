package com.sara.voice;

import android.content.Context;
import android.content.Intent;
import android.os.Build;
import androidx.annotation.NonNull;
import io.flutter.embedding.engine.plugins.FlutterPlugin;
import io.flutter.plugin.common.MethodCall;
import io.flutter.plugin.common.MethodChannel;
import io.flutter.plugin.common.MethodChannel.MethodCallHandler;
import io.flutter.plugin.common.MethodChannel.Result;

/**
 * SaraVoicePlugin - Flutter plugin for native background service control.
 *
 * Bridges the Flutter Dart layer with the Android Foreground Service
 * for continuous wake word listening and WebSocket keep-alive.
 */
public class SaraVoicePlugin implements FlutterPlugin, MethodCallHandler {
    private static final String CHANNEL_NAME = "sara_voice/background";
    private Context context;
    private MethodChannel channel;
    private boolean serviceRunning = false;

    @Override
    public void onAttachedToEngine(@NonNull FlutterPluginBinding binding) {
        context = binding.getApplicationContext();
        channel = new MethodChannel(binding.getBinaryMessenger(), CHANNEL_NAME);
        channel.setMethodCallHandler(this);
    }

    @Override
    public void onDetachedFromEngine(@NonNull FlutterPluginBinding binding) {
        channel.setMethodCallHandler(null);
        channel = null;
        context = null;
    }

    @Override
    public void onMethodCall(@NonNull MethodCall call, @NonNull Result result) {
        switch (call.method) {
            case "startService":
                startService(call, result);
                break;
            case "stopService":
                stopService(result);
                break;
            case "updateConfig":
                updateConfig(call, result);
                break;
            case "ping":
                result.success(true);
                break;
            default:
                result.notImplemented();
        }
    }

    private void startService(MethodCall call, Result result) {
        Intent intent = new Intent(context, SaraVoiceService.class);
        intent.putExtra("serverUrl", call.argument("serverUrl"));
        intent.putExtra("deviceId", call.argument("deviceId"));
        intent.putExtra("wakeWordEnabled", call.argument("wakeWordEnabled"));
        intent.putExtra("notificationTitle", call.argument("notificationTitle"));
        intent.putExtra("notificationText", call.argument("notificationText"));

        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
            context.startForegroundService(intent);
        } else {
            context.startService(intent);
        }

        serviceRunning = true;
        result.success(true);
    }

    private void stopService(Result result) {
        Intent intent = new Intent(context, SaraVoiceService.class);
        context.stopService(intent);
        serviceRunning = false;
        result.success(true);
    }

    private void updateConfig(MethodCall call, Result result) {
        // In a real implementation, update the running service's config
        // via BroadcastReceiver or bound service interface
        result.success(true);
    }
}
