package com.sara.voice;

import android.app.Notification;
import android.app.NotificationChannel;
import android.app.NotificationManager;
import android.app.PendingIntent;
import android.app.Service;
import android.content.Intent;
import android.os.Build;
import android.os.IBinder;
import android.util.Log;
import androidx.annotation.Nullable;
import androidx.core.app.NotificationCompat;

/**
 * Foreground Service for continuous wake word detection.
 *
 * Keeps the app alive in the background, maintaining the
 * WebSocket connection to the Voice Gateway and listening
 * for the wake word even when the UI is not visible.
 */
public class SaraVoiceService extends Service {
    private static final String TAG = "SaraVoiceService";
    private static final int NOTIFICATION_ID = 1001;
    private static final String CHANNEL_ID = "sara_voice_channel";

    @Override
    public void onCreate() {
        super.onCreate();
        createNotificationChannel();
        Log.d(TAG, "Sara Voice Service created");
    }

    @Override
    public int onStartCommand(Intent intent, int flags, int startId) {
        String notificationTitle = intent.getStringExtra("notificationTitle");
        String notificationText = intent.getStringExtra("notificationText");
        if (notificationTitle == null) notificationTitle = "Sara Voice";
        if (notificationText == null) notificationText = "Listening for wake word...";

        Notification notification = new NotificationCompat.Builder(this, CHANNEL_ID)
                .setContentTitle(notificationTitle)
                .setContentText(notificationText)
                .setSmallIcon(android.R.drawable.ic_btn_speak_now)
                .setPriority(NotificationCompat.PRIORITY_LOW)
                .setOngoing(true)
                .build();

        startForeground(NOTIFICATION_ID, notification);
        Log.d(TAG, "Sara Voice Service running in foreground");

        return START_STICKY;
    }

    @Nullable
    @Override
    public IBinder onBind(Intent intent) {
        return null;
    }

    @Override
    public void onDestroy() {
        super.onDestroy();
        Log.d(TAG, "Sara Voice Service destroyed");
    }

    private void createNotificationChannel() {
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
            NotificationChannel channel = new NotificationChannel(
                    CHANNEL_ID,
                    "Sara Voice",
                    NotificationManager.IMPORTANCE_LOW
            );
            channel.setDescription("Wake word detection service");
            NotificationManager manager = getSystemService(NotificationManager.class);
            if (manager != null) {
                manager.createNotificationChannel(channel);
            }
        }
    }
}
