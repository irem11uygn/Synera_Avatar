package com.synera.avatar.data.repo

import android.content.Context
import android.content.SharedPreferences
import androidx.core.content.edit
import com.synera.avatar.BuildConfig
import java.security.GeneralSecurityException
import java.security.ProviderException
import java.util.UUID

data class Session(
    val token: String,
    val username: String,
    val fullName: String,
    val warehouseCode: String?,
    /** Satış gönderiminde kullanılır; eski sürümden kalan oturumda yoktur (yeniden giriş istenir). */
    val warehouseId: Long?,
)

/**
 * Sunucu adresi ve oturum bilgisi uygulamaya özel SharedPreferences'ta tutulur. Belirteç düz metin
 * olarak yazılmaz: Android Keystore anahtarıyla şifrelenir (TokenCipher). Eski sürümün şifresiz
 * belirteci ilk okumada şifrelenip silinir.
 */
class SessionStore(context: Context, private val cipher: TokenCipher = TokenCipher.keystore()) {
    private val prefs = context.getSharedPreferences("oturum", Context.MODE_PRIVATE)

    /** Çözülmüş belirteç; her istekte Keystore'a gitmemek için yalnız bellekte tutulur. */
    @Volatile
    private var cachedToken: String? = null

    var serverUrl: String
        get() = prefs.getString(KEY_SERVER, null) ?: BuildConfig.DEFAULT_SERVER_URL
        set(value) = prefs.edit { putString(KEY_SERVER, value.trim()) }

    fun current(): Session? {
        val token = readToken() ?: return null
        return Session(
            token = token,
            username = prefs.getString(KEY_USERNAME, "").orEmpty(),
            fullName = prefs.getString(KEY_FULL_NAME, "").orEmpty(),
            warehouseCode = prefs.getString(KEY_WAREHOUSE, null),
            warehouseId = prefs.getLong(KEY_WAREHOUSE_ID, NO_ID).takeIf { it != NO_ID },
        )
    }

    fun lastUsername(): String? = prefs.getString(KEY_USERNAME, null)

    fun save(session: Session) = prefs.edit {
        storeToken(session.token)
        putString(KEY_USERNAME, session.username)
        putString(KEY_FULL_NAME, session.fullName)
        putString(KEY_WAREHOUSE, session.warehouseCode)
        if (session.warehouseId != null) putLong(KEY_WAREHOUSE_ID, session.warehouseId) else remove(KEY_WAREHOUSE_ID)
    }

    /** Bu kurulumun kalıcı kimliği (satışların hangi cihazdan geldiği); ilk kullanımda üretilir. */
    val deviceId: String
        get() = prefs.getString(KEY_DEVICE, null) ?: ("android-" + UUID.randomUUID().toString().take(8)).also {
            prefs.edit { putString(KEY_DEVICE, it) }
        }

    /** Çıkışta belirteç silinir; kullanıcı adı bir sonraki girişte veri temizliği kararı için kalır. */
    fun clearToken() {
        cachedToken = null
        prefs.edit {
            remove(KEY_TOKEN)
            remove(KEY_PLAIN_TOKEN)
        }
    }

    private fun readToken(): String? {
        cachedToken?.let { return it }
        prefs.getString(KEY_PLAIN_TOKEN, null)?.let { plain ->
            prefs.edit { storeToken(plain) }
            return plain
        }
        val sealed = prefs.getString(KEY_TOKEN, null) ?: return null
        return cipher.open(sealed).also { opened ->
            if (opened == null) prefs.edit { remove(KEY_TOKEN) } else cachedToken = opened
        }
    }

    /**
     * Keystore bu cihazda çalışmazsa belirteç diske hiç yazılmaz: oturum uygulama kapanana kadar
     * bellekte sürer, sonra yeniden giriş istenir (şifresiz saklamaya geri dönülmez).
     */
    private fun SharedPreferences.Editor.storeToken(plain: String) {
        cachedToken = plain
        remove(KEY_PLAIN_TOKEN)
        val sealed = try {
            cipher.seal(plain)
        } catch (e: GeneralSecurityException) {
            null
        } catch (e: ProviderException) {
            null
        }
        if (sealed != null) putString(KEY_TOKEN, sealed) else remove(KEY_TOKEN)
    }

    private companion object {
        const val KEY_SERVER = "server_url"
        const val KEY_TOKEN = "token_sifreli"
        const val KEY_PLAIN_TOKEN = "token" // eski sürüm, şifresiz
        const val KEY_USERNAME = "username"
        const val KEY_FULL_NAME = "full_name"
        const val KEY_WAREHOUSE = "warehouse_code"
        const val KEY_WAREHOUSE_ID = "warehouse_id"
        const val KEY_DEVICE = "device_id"
        const val NO_ID = -1L
    }
}
