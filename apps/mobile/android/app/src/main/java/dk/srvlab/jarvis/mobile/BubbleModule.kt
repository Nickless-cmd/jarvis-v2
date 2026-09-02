package dk.srvlab.jarvis.mobile

import android.app.NotificationChannel
import android.app.NotificationManager
import android.app.PendingIntent
import android.content.Context
import android.content.Intent
import android.os.Build

import androidx.core.app.NotificationCompat
import androidx.core.app.NotificationManagerCompat
import androidx.core.app.Person
import androidx.core.content.pm.ShortcutInfoCompat
import androidx.core.content.pm.ShortcutManagerCompat
import androidx.core.graphics.drawable.IconCompat

import com.facebook.react.bridge.Promise
import com.facebook.react.bridge.ReactApplicationContext
import com.facebook.react.bridge.ReactContextBaseJavaModule
import com.facebook.react.bridge.ReactMethod

class BubbleModule(private val ctx: ReactApplicationContext) : ReactContextBaseJavaModule(ctx) {
  override fun getName(): String = "BubbleModule"

  private val channelId = "jarvis-bubbles"

  private fun ensureChannel() {
    if (Build.VERSION.SDK_INT < Build.VERSION_CODES.O) return
    val nm = ctx.getSystemService(Context.NOTIFICATION_SERVICE) as NotificationManager
    if (nm.getNotificationChannel(channelId) == null) {
      val ch = NotificationChannel(channelId, "Jarvis-bobler", NotificationManager.IMPORTANCE_HIGH)
      if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.R) ch.setAllowBubbles(true)
      nm.createNotificationChannel(ch)
    }
  }

  private fun person(): Person =
    Person.Builder()
      .setName("Jarvis")
      .setKey("jarvis")
      .setImportant(true)
      .setIcon(IconCompat.createWithResource(ctx, R.drawable.ic_notification))
      .build()

  private fun pushShortcut(sessionId: String, title: String): String {
    val shortcutId = "bubble-$sessionId"
    val intent = Intent(ctx, BubbleActivity::class.java).apply {
      action = Intent.ACTION_VIEW
      putExtra("sessionId", sessionId)
      putExtra("title", title)
    }
    val shortcut = ShortcutInfoCompat.Builder(ctx, shortcutId)
      .setLongLived(true)
      .setShortLabel(if (title.isBlank()) "Jarvis" else title)
      .setPerson(person())
      .setCategories(setOf("android.shortcut.conversation"))
      .setIntent(intent)
      .build()
    ShortcutManagerCompat.pushDynamicShortcut(ctx, shortcut)
    return shortcutId
  }

  private fun pendingFlags(): Int {
    val base = PendingIntent.FLAG_UPDATE_CURRENT
    return if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.S) base or PendingIntent.FLAG_MUTABLE else base
  }

  private fun postBubble(
    sessionId: String,
    title: String,
    body: String,
    autoExpand: Boolean,
    suppress: Boolean,
    ongoing: Boolean
  ) {
    ensureChannel()
    val shortcutId = pushShortcut(sessionId, title)
    val intent = Intent(ctx, BubbleActivity::class.java).apply {
      action = Intent.ACTION_VIEW
      putExtra("sessionId", sessionId)
      putExtra("title", title)
    }
    val pi = PendingIntent.getActivity(ctx, sessionId.hashCode(), intent, pendingFlags())
    val icon = IconCompat.createWithResource(ctx, R.drawable.ic_notification)
    val bubble = NotificationCompat.BubbleMetadata.Builder(pi, icon)
      .setDesiredHeight(600)
      .setAutoExpandBubble(autoExpand)
      .setSuppressNotification(suppress)
      .build()
    val msgStyle = NotificationCompat.MessagingStyle(person())
      .addMessage(if (body.isBlank()) "Jarvis" else body, System.currentTimeMillis(), person())
    val notif = NotificationCompat.Builder(ctx, channelId)
      .setSmallIcon(R.drawable.ic_notification)
      .setShortcutId(shortcutId)
      .setBubbleMetadata(bubble)
      .setStyle(msgStyle)
      .setOngoing(ongoing)
      .build()
    NotificationManagerCompat.from(ctx).notify(sessionId.hashCode(), notif)
  }

  @ReactMethod
  fun isSupported(promise: Promise) {
    if (Build.VERSION.SDK_INT < Build.VERSION_CODES.R) {
      promise.resolve(false)
      return
    }
    val nm = ctx.getSystemService(Context.NOTIFICATION_SERVICE) as NotificationManager
    promise.resolve(nm.areBubblesAllowed())
  }

  @ReactMethod
  fun floatCurrentChat(sessionId: String, title: String) {
    postBubble(sessionId, title, "Chat med Jarvis", autoExpand = true, suppress = true, ongoing = false)
  }

  @ReactMethod
  fun showConversationBubble(sessionId: String, title: String, body: String) {
    postBubble(sessionId, title, body, autoExpand = false, suppress = false, ongoing = false)
  }

  @ReactMethod
  fun setPersistent(enabled: Boolean, sessionId: String, title: String) {
    val id = if (sessionId.isBlank()) "default" else sessionId
    if (enabled) {
      postBubble(id, title, "Chat med Jarvis", autoExpand = false, suppress = false, ongoing = true)
    } else {
      NotificationManagerCompat.from(ctx).cancel(id.hashCode())
    }
  }
}
