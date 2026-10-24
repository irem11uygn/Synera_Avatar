package com.synera.avatar

import android.app.Application
import com.synera.avatar.data.local.AppDatabase
import com.synera.avatar.data.repo.AvatarRepository
import com.synera.avatar.data.repo.SessionStore

/** Uygulama genelindeki nesneler elle kurulur (ADR-003: bağımlılık enjeksiyonu kütüphanesi yok). */
class AvatarApp : Application() {
    val repository: AvatarRepository by lazy {
        AvatarRepository(SessionStore(this), AppDatabase.create(this).masterData())
    }
}
