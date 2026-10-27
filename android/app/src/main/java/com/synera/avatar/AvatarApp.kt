package com.synera.avatar

import android.app.Application
import com.synera.avatar.data.local.AppDatabase
import com.synera.avatar.data.repo.AvatarRepository
import com.synera.avatar.data.repo.SessionStore
import com.synera.avatar.sync.SyncWorker
import com.synera.avatar.util.L

/** Uygulama genelindeki nesneler elle kurulur (ADR-003: bağımlılık enjeksiyonu kütüphanesi yok). */
class AvatarApp : Application() {
    override fun onCreate() {
        super.onCreate()
        L.init(this)
    }

    private val database by lazy { AppDatabase.create(this) }

    val repository: AvatarRepository by lazy {
        AvatarRepository(
            sessions = SessionStore(this),
            dao = database.masterData(),
            sales = database.sales(),
            onSaleSaved = { SyncWorker.enqueue(this) },
        )
    }
}
