package local.visual.corepose

import java.net.URLEncoder
import java.nio.charset.StandardCharsets

object PlayerExport {
    val SHARE_TARGETS = listOf(
        "YouTube" to "https://www.youtube.com/upload",
        "TikTok" to "https://www.tiktok.com/upload",
        "X" to "https://twitter.com/intent/tweet?text={text}",
        "Facebook" to "https://www.facebook.com/sharer/sharer.php",
        "Weibo" to "https://service.weibo.com/share/share.php?title={text}",
        "Bilibili" to "https://member.bilibili.com/platform/upload/video/frame",
    )

    fun shareUrl(template: String, text: String): String {
        val encoded = URLEncoder.encode(text, StandardCharsets.UTF_8).replace("+", "%20")
        return template.replace("{text}", encoded)
    }

    fun downloadFileName(displayName: String?, clipId: String?): String {
        val raw = displayName?.ifBlank { null } ?: clipId?.ifBlank { null } ?: "overlay"
        val stem = raw.replace(Regex("[\\\\/:*?\"<>|]"), "_")
        return if (stem.endsWith(".jpg", ignoreCase = true)) stem else "$stem.jpg"
    }
}
