package local.visual.corepose

import android.content.Context
import org.json.JSONObject

object I18n {
    const val DEFAULT = "en"
    val SUPPORTED = listOf("en", "es", "zh", "ko", "ja", "fr", "de", "it", "pt")
    val LABELS = mapOf(
        "en" to "English",
        "es" to "Español",
        "zh" to "中文",
        "ko" to "한국어",
        "ja" to "日本語",
        "fr" to "Français",
        "de" to "Deutsch",
        "it" to "Italiano",
        "pt" to "Português",
    )

    private const val PREFS = "visual_prefs"
    private const val KEY_LANG = "language"

    private var catalog: Map<String, Map<String, String>> = emptyMap()
    private var lang: String = DEFAULT
    private var appContext: Context? = null

    fun init(context: Context) {
        appContext = context.applicationContext
        lang = context.getSharedPreferences(PREFS, Context.MODE_PRIVATE)
            .getString(KEY_LANG, DEFAULT)
            ?.takeIf { it in SUPPORTED }
            ?: DEFAULT
        catalog = loadCatalog(context)
    }

    fun language(): String = lang

    fun setLanguage(code: String) {
        val next = if (code in SUPPORTED) code else DEFAULT
        lang = next
        appContext?.getSharedPreferences(PREFS, Context.MODE_PRIVATE)
            ?.edit()
            ?.putString(KEY_LANG, next)
            ?.apply()
    }

    fun t(key: String, vars: Map<String, String> = emptyMap(), lang: String? = null): String {
        val code = lang ?: this.lang
        val raw = if (code == DEFAULT) {
            key
        } else {
            catalog[key]?.get(code) ?: key
        }
        return interpolate(raw, vars)
    }

    fun loadCatalogJson(json: String): Map<String, Map<String, String>> {
        val root = JSONObject(json)
        val strings = root.optJSONObject("strings") ?: return emptyMap()
        val out = HashMap<String, Map<String, String>>(strings.length())
        val keys = strings.keys()
        while (keys.hasNext()) {
            val key = keys.next()
            val node = strings.optJSONObject(key) ?: continue
            val langs = HashMap<String, String>()
            val langKeys = node.keys()
            while (langKeys.hasNext()) {
                val code = langKeys.next()
                langs[code] = node.optString(code)
            }
            out[key] = langs
        }
        return out
    }

    fun interpolate(template: String, vars: Map<String, String>): String {
        var out = template
        for ((name, value) in vars) {
            out = out.replace("{$name}", value)
            out = out.replace(Regex("\\{${Regex.escape(name)}:[^}]+\\}"), value)
        }
        return out
    }

    private fun loadCatalog(context: Context): Map<String, Map<String, String>> {
        return try {
            context.assets.open("strings.json").bufferedReader().use { loadCatalogJson(it.readText()) }
        } catch (_: Exception) {
            emptyMap()
        }
    }
}
